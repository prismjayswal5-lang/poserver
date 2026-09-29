
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import sqlite3
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, origins=['*'], supports_credentials=True)

DB = 'licenses.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        profile TEXT,
        expires TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()

def make_key():
    return 'PO-' + secrets.token_hex(6).upper()

def valid_license(key):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM licenses WHERE key=? AND is_active=1', (key,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    expires = datetime.fromisoformat(row[3])
    if datetime.now() > expires:
        return None
    return {'key': row[1], 'profile': row[2]}

@app.route('/')
def home():
    return 'Server is running!'

@app.route('/create-license')
def create_license():
    key = make_key()
    expires = (datetime.now() + timedelta(days=30)).isoformat()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT INTO licenses (key, profile, expires) VALUES (?, ?, ?)',
              (key, 'Guru', expires))
    conn.commit()
    conn.close()
    return jsonify({'license': key, 'expires_in': '30 days'})

@app.route('/script-endpoint/', methods=['POST'])
def script_endpoint():
    script = """
(function(){
    if (window.__PO_LOADED__) return;
    window.__PO_LOADED__ = true;
    const SERVER = 'https://prism007.pythonanywhere.com';
    const modal = document.createElement('div');
    modal.innerHTML = '<div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:Arial;"><div style="background:#1a1d2e;padding:25px;border-radius:20px;color:white;width:85%;max-width:350px;"><h2 style="text-align:center;color:#6c5ce7;margin-top:0;">Pocket Option Script</h2><label style="display:block;margin:15px 0 5px;font-size:13px;">License Key</label><input id="po-key" placeholder="Enter license key" style="width:100%;padding:10px;border-radius:8px;background:#252840;color:white;border:1px solid #444;box-sizing:border-box;"><button id="po-btn" style="width:100%;padding:14px;margin-top:20px;background:linear-gradient(135deg,#6c5ce7,#a29bfe);color:white;border:none;border-radius:10px;font-size:15px;font-weight:bold;cursor:pointer;">Activate License</button><div id="po-status" style="text-align:center;margin-top:10px;font-size:13px;min-height:20px;"></div></div></div>';
    document.body.appendChild(modal);
    document.getElementById('po-btn').onclick = async () => {
        const key = document.getElementById('po-key').value.trim();
        const status = document.getElementById('po-status');
        if (!key) { status.textContent = 'Key daalo'; status.style.color = 'red'; return; }
        status.textContent = 'Checking...'; status.style.color = '#a29bfe';
        try {
            const res = await fetch(SERVER + '/verify/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({license: key})
            });
            const data = await res.json();
            if (data.success) {
                status.textContent = 'Activated!'; status.style.color = '#00b894';
                localStorage.setItem('po_lic', key);
                setTimeout(() => { modal.remove(); liveUI(); }, 800);
            } else {
                status.textContent = 'Invalid key'; status.style.color = 'red';
            }
        } catch(e) {
            status.textContent = 'Network error'; status.style.color = 'red';
        }
    };
    function liveUI() {
        setInterval(() => {
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0 && el.textContent === 'DEMO') {
                    el.textContent = 'LIVE';
                    el.style.color = '#00b894';
                }
            });
        }, 500);
    }
    const saved = localStorage.getItem('po_lic');
    if (saved) {
        fetch(SERVER + '/verify/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({license: saved})
        }).then(r => r.json()).then(d => {
            if (d.success) { modal.remove(); liveUI(); }
        }).catch(() => {});
    }
})();
"""
    resp = make_response(script)
    resp.headers['Content-Type'] = 'application/javascript'
    return resp

@app.route('/verify/', methods=['POST'])
def verify():
    data = request.get_json() or {}
    key = data.get('license', '').strip().upper()
    lic = valid_license(key)
    if lic:
        return jsonify({'success': True, 'profile': lic['profile']})
    return jsonify({'success': False, 'error': 'Invalid'})

init_db()

if __name__ == '__main__':
    app.run()
