# web_ui.py
from flask import Flask, render_template
import os

app = Flask(__name__)

def read_log():
    if not os.path.exists('signals.log'): return []
    with open('signals.log') as f:
        return f.readlines()[-30:]

@app.route('/')
def home():
    from datetime import datetime
    return render_template('page.html', signals=read_log(), now=datetime.utcnow().strftime('%H:%M GMT'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
