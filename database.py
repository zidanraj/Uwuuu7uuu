# database.py — SQLite schema, account CRUD, settings store

import sqlite3
import json
import os

DB_PATH = os.environ.get('DB_PATH', 'z3nith.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            token      TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            proxy      TEXT DEFAULT '',
            enabled    INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS captcha_keys (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            key      TEXT NOT NULL,
            provider TEXT DEFAULT 'capsolver',
            active   INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # defaults
    defaults = {
        'sell_interval_minutes': '60',
        'sell_what': 'all',
        'give_amount': '1000',
        'owo_prefix': 'owo',
        'hunt_enabled': '1',
        'battle_enabled': '1',
        'pray_enabled': '1',
        'curse_enabled': '1',
        'daily_enabled': '1',
        'coinflip_enabled': '0',
        'slots_enabled': '0',
        'hunt_min_delay': '15',
        'hunt_max_delay': '20',
    }
    for k, v in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))
    conn.commit()
    conn.close()

def get_all_accounts():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM accounts').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_account(name, token, channel_id, proxy=''):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        'INSERT INTO accounts (name, token, channel_id, proxy) VALUES (?, ?, ?, ?)',
        (name, token, channel_id, proxy)
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id

def delete_account(acc_id):
    conn = get_conn()
    conn.execute('DELETE FROM accounts WHERE id = ?', (acc_id,))
    conn.commit()
    conn.close()

def update_account(acc_id, **kwargs):
    conn = get_conn()
    for key, val in kwargs.items():
        conn.execute(f'UPDATE accounts SET {key} = ? WHERE id = ?', (val, acc_id))
    conn.commit()
    conn.close()

def get_account(acc_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM accounts WHERE id = ?', (acc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_settings():
    conn = get_conn()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def save_settings(data: dict):
    conn = get_conn()
    for k, v in data.items():
        conn.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            (k, str(v))
        )
    conn.commit()
    conn.close()
