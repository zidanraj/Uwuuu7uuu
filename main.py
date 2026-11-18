
# main.py — Flask entry point, Socket.IO server, Render startup target

import os
import threading
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from database import init_db, get_all_accounts, add_account, delete_account, update_account
from bot_engine import BotEngine

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'z3nith-uwu-secret-2024')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

bot_engine = BotEngine(socketio)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/accounts', methods=['GET'])
def api_get_accounts():
    accounts = get_all_accounts()
    return jsonify(accounts)

@app.route('/api/accounts', methods=['POST'])
def api_add_account():
    data = request.json
    token   = data.get('token', '').strip()
    name    = data.get('name', '').strip()
    channel = data.get('channel_id', '').strip()
    proxy   = data.get('proxy', '').strip()
    if not token or not name or not channel:
        return jsonify({'error': 'token, name, channel_id required'}), 400
    acc_id = add_account(name, token, channel, proxy)
    socketio.emit('accounts_updated', get_all_accounts())
    return jsonify({'id': acc_id, 'status': 'added'})

@app.route('/api/accounts/<int:acc_id>', methods=['DELETE'])
def api_delete_account(acc_id):
    bot_engine.stop_account(acc_id)
    delete_account(acc_id)
    socketio.emit('accounts_updated', get_all_accounts())
    return jsonify({'status': 'deleted'})

@app.route('/api/start/<int:acc_id>', methods=['POST'])
def api_start(acc_id):
    result = bot_engine.start_account(acc_id)
    return jsonify(result)

@app.route('/api/stop/<int:acc_id>', methods=['POST'])
def api_stop(acc_id):
    result = bot_engine.stop_account(acc_id)
    return jsonify(result)

@app.route('/api/start_all', methods=['POST'])
def api_start_all():
    result = bot_engine.start_all()
    return jsonify(result)

@app.route('/api/stop_all', methods=['POST'])
def api_stop_all():
    result = bot_engine.stop_all()
    return jsonify(result)

@app.route('/api/give_all', methods=['POST'])
def api_give_all():
    data = request.json
    target_uid = data.get('target_uid', '').strip()
    amount     = int(data.get('amount', 0))
    if not target_uid or amount <= 0:
        return jsonify({'error': 'target_uid and amount required'}), 400
    result = bot_engine.give_all(target_uid, amount)
    return jsonify(result)

@app.route('/api/captcha_keys', methods=['GET'])
def api_get_captcha_keys():
    from captcha_handler import get_all_keys
    return jsonify(get_all_keys())

@app.route('/api/captcha_keys', methods=['POST'])
def api_add_captcha_key():
    data = request.json
    key  = data.get('key', '').strip()
    provider = data.get('provider', 'capsolver').strip()
    if not key:
        return jsonify({'error': 'key required'}), 400
    from captcha_handler import add_key
    add_key(key, provider)
    return jsonify({'status': 'added'})

@app.route('/api/captcha_keys/<int:key_id>', methods=['DELETE'])
def api_delete_captcha_key(key_id):
    from captcha_handler import delete_key
    delete_key(key_id)
    return jsonify({'status': 'deleted'})

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify(bot_engine.get_all_stats())

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    from database import get_settings, save_settings
    if request.method == 'POST':
        save_settings(request.json)
        return jsonify({'status': 'saved'})
    return jsonify(get_settings())

@socketio.on('connect')
def on_connect():
    emit('accounts_updated', get_all_accounts())
    emit('stats_update', bot_engine.get_all_stats())

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
