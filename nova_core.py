# nova_core.py — GROK NOVA BOT v7
import requests, time, os, logging
from telegram import Bot
from datetime import datetime
from dotenv import load_dotenv
from trader_testnet import TestnetTrader

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=TOKEN)
trader = TestnetTrader()

logging.basicConfig(filename='signals.log', level=logging.INFO,
                    format='%(asctime)s | %(message)s')

# --- DATA & INDICATORS (same as original) ---
def get_all_symbols():
    try:
        data = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10).json()
        return [d['symbol'] for d in data if d['symbol'].endswith('USDT') and float(d['volume']) > 100]
    except:
        return ['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT']

def get_klines(symbol, interval='4h', limit=100):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = requests.get(url, timeout=10).json()
        return [(float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])) for c in data]
    except: return []

def calculate_indicators(klines):
    if len(klines) < 50: return None
    c = [k[3] for k in klines]; h = [k[1] for k in klines]; l = [k[2] for k in klines]; v = [k[4] for k in klines]
    price = c[-1]
    delta = [c[i]-c[i-1] for i in range(1, len(c))]
    gain = sum([d for d in delta[-14:] if d>0])/14
    loss = sum([abs(d) for d in delta[-14:] if d<0])/14
    rsi = 100 - (100/(1 + gain/(loss+1e-8))) if loss != 0 else 100
    ema12 = sum(c[-12:])/12; ema26 = sum(c[-26:])/26; macd = ema12 - ema26
    sma20 = sum(c[-20:])/20; std = (sum([(x-sma20)**2 for x in c[-20:]])/20)**0.5
    upper, lower = sma20 + 2*std, sma20 - 2*std
    near_bottom = price <= lower * 1.02; near_top = price >= upper * 0.98
    ema9 = sum(c[-9:])/9; ema21 = sum(c[-21:])/21; ema_cross = ema9 > ema21
    k = 100 * (price - min(l[-14:])) / (max(h[-14:]) - min(l[-14:]) + 1e-8)
    stoch_oversold = k < 20; stoch_overbought = k > 80
    vol_spike = v[-1] > sum(v[-20:])/20 * 2
    obv = [v[0]]; [obv.append(obv[-1] + v[i] if c[i]>c[i-1] else obv[-1] - v[i] if c[i]<c[i-1] else obv[-1]) for i in range(1,len(c))]
    obv_up = obv[-1] > obv[-5]
    return {
        'price': price, 'rsi': rsi, 'macd_bull': macd > 0, 'near_bottom': near_bottom, 'near_top': near_top,
        'vol_spike': vol_spike, 'ema_cross': ema_cross, 'stoch_oversold': stoch_oversold, 'stoch_overbought': stoch_overbought,
        'obv_up': obv_up
    }

def grok_confidence(symbol, ind):
    if not ind: return 0, 'HOLD', 0
    score = 0
    if ind['rsi'] < 30: score += 3
    if ind['rsi'] < 20: score += 2
    if ind['macd_bull']: score += 2
    if ind['near_bottom']: score += 3
    if ind['ema_cross']: score += 2
    if ind['stoch_oversold']: score += 2
    if ind['obv_up']: score += 1
    if ind['vol_spike']: score += 1.5
    signal = 'BUY' if score >= 8 else 'HOLD'
    entry = ind['price'] * 0.98
    return min(10, round(score, 1)), signal, round(entry, 6)

def find_elite(tf='4h'):
    interval_map = {'15m': '15m', '4h': '4h', '1d': '1d', '1w': '1w'}
    interval = interval_map.get(tf, '4h')
    symbols = get_all_symbols()[:100]
    elite = []
    for sym in symbols:
        try:
            klines = get_klines(sym, interval)
            ind = calculate_indicators(klines)
            conf, signal, entry = grok_confidence(sym, ind)
            if conf >= 8.0 and signal == 'BUY':
                elite.append({
                    'symbol': sym.replace('USDT','/USDT'), 'price': ind['price'],
                    'entry': entry, 'signal': signal, 'conf': conf, 'tf': tf
                })
        except: continue
    elite.sort(key=lambda x: x['conf'], reverse=True)
    return elite[:2]

def make_message(trade, rank):
    action = "Enter Long" if trade['signal'] == 'BUY' else "Enter Short"
    return f"""
**{rank+1}. {trade['symbol']} [{trade['tf'].upper()}]** — BULL MARKET ({trade['conf']}/10)
Current Price: ${trade['price']:,.2f}
**{action} at: ${trade['entry']}**
**How to Trade:**
1. Open Binance/Bybit
2. Search {trade['symbol']}
3. Set limit order at ${trade['entry']}
4. Risk 1% | SL: 2% | TP: 3%
AI + 9 Indicators confirm. DYOR.
    """.strip()

# --- MAIN LOOP ---
last_sent = {}
while True:
    try:
        now = datetime.utcnow()
        if now.hour % 4 == 0 and now.minute < 5:
            for tf in ['15m', '4h', '1d', '1w']:
                key = f"{tf}_{now.hour}"
                if key not in last_sent:
                    elite = find_elite(tf)
                    if elite:
                        msg_lines = [make_message(t, i) for i, t in enumerate(elite)]
                        full_msg = f"**GROK NOVA SIGNALS** — {now.strftime('%H:%M')} GMT\n\n" + \
                                   "\n\n---\n\n".join(msg_lines)
                        bot.send_message(chat_id=CHAT_ID, text=full_msg, parse_mode="Markdown")
                        logging.info(f"SIGNAL | {tf} | {elite[0]['symbol']} | {elite[0]['conf']}")

                        # AUTO-TRADE TOP SIGNAL
                        top = elite[0]
                        side = 'buy' if top['signal'] == 'BUY' else 'sell'
                        symbol = top['symbol'].replace('/USDT', 'USDT')
                        trade_result = trader.place_order(symbol, side, top['entry'], top['conf'])
                        bot.send_message(chat_id=CHAT_ID, text=trade_result)

                    last_sent[key] = now.timestamp()
        time.sleep(300)
    except Exception as e:
        logging.error(f"ERROR: {e}")
        time.sleep(60)
