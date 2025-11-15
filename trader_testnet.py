# trader_testnet.py
import ccxt
import os
from dotenv import load_dotenv
load_dotenv()

class TestnetTrader:
    def __init__(self):
        self.ex = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_API_SECRET'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'urls': {
                'api': {
                    'public': 'https://testnet.binancefuture.com/fapi/v1',
                    'private': 'https://testnet.binancefuture.com/fapi/v1',
                }
            }
        })

    def place_order(self, symbol, side, entry, conf):
        try:
            balance = self.ex.fetch_balance()['USDT']['free']
            risk = balance * 0.01
            qty = (risk * 10) / entry
            sl = entry * (0.98 if side == 'buy' else 1.02)
            tp = entry * (1.03 if side == 'buy' else 0.97)
            order = self.ex.create_order(symbol, 'limit', side, round(qty, 6), entry,
                params={'stopLoss': sl, 'takeProfit': tp})
            return f"**AUTO-TRADED (TESTNET):** {side.upper()} @ ${entry} | Qty: {qty:.4f} | SL: ${sl:,.2f} | TP: ${tp:,.2f}"
        except Exception as e:
            return f"TESTNET TRADE FAILED: {e}"
