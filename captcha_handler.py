# captcha_handler.py — multi-key hCaptcha solver pool (capsolver + 2captcha)

import requests
import time
import logging
import sqlite3
import os

logger = logging.getLogger('CaptchaHandler')
DB_PATH = os.environ.get('DB_PATH', 'z3nith.db')

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def get_all_keys():
    conn = _conn()
    rows = conn.execute('SELECT * FROM captcha_keys WHERE active = 1').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_key(key: str, provider: str = 'capsolver'):
    conn = _conn()
    conn.execute('INSERT INTO captcha_keys (key, provider) VALUES (?, ?)', (key, provider))
    conn.commit()
    conn.close()

def delete_key(key_id: int):
    conn = _conn()
    conn.execute('DELETE FROM captcha_keys WHERE id = ?', (key_id,))
    conn.commit()
    conn.close()


class CaptchaHandler:
    def solve(self, sitekey: str, page_url: str) -> str | None:
        keys = get_all_keys()
        if not keys:
            logger.warning('No captcha keys configured — captcha cannot be solved automatically')
            return None
        for key_row in keys:
            token = self._try_solve(key_row['key'], key_row['provider'], sitekey, page_url)
            if token:
                return token
        return None

    def _try_solve(self, api_key: str, provider: str,
                   sitekey: str, page_url: str) -> str | None:
        try:
            if provider == 'capsolver':
                return self._capsolver(api_key, sitekey, page_url)
            elif provider == '2captcha':
                return self._twocaptcha(api_key, sitekey, page_url)
            else:
                logger.warning(f'Unknown provider: {provider}')
                return None
        except Exception as e:
            logger.error(f'Solver error ({provider}): {e}')
            return None

    def _capsolver(self, api_key: str, sitekey: str, page_url: str) -> str | None:
        create_url = 'https://api.capsolver.com/createTask'
        payload = {
            'clientKey': api_key,
            'task': {
                'type':        'HCaptchaTaskProxyless',
                'websiteURL':  page_url,
                'websiteKey':  sitekey,
            }
        }
        r = requests.post(create_url, json=payload, timeout=20)
        data = r.json()
        if data.get('errorId', 1) != 0:
            logger.error(f'Capsolver create error: {data}')
            return None
        task_id = data['taskId']

        for _ in range(30):
            time.sleep(4)
            result_r = requests.post(
                'https://api.capsolver.com/getTaskResult',
                json={'clientKey': api_key, 'taskId': task_id},
                timeout=20,
            )
            res = result_r.json()
            if res.get('status') == 'ready':
                return res['solution']['gRecaptchaResponse']
            if res.get('errorId', 0) != 0:
                logger.error(f'Capsolver task error: {res}')
                return None
        return None

    def _twocaptcha(self, api_key: str, sitekey: str, page_url: str) -> str | None:
        # submit
        r = requests.post(
            'https://2captcha.com/in.php',
            data={
                'key':     api_key,
                'method':  'hcaptcha',
                'sitekey': sitekey,
                'pageurl': page_url,
                'json':    1,
            },
            timeout=20,
        )
        data = r.json()
        if data.get('status') != 1:
            logger.error(f'2captcha submit error: {data}')
            return None
        req_id = data['request']

        for _ in range(30):
            time.sleep(5)
            res = requests.get(
                f'https://2captcha.com/res.php?key={api_key}&action=get&id={req_id}&json=1',
                timeout=20,
            ).json()
            if res.get('status') == 1:
                return res['request']
            if res.get('request') == 'ERROR_CAPTCHA_UNSOLVABLE':
                return None
        return None
