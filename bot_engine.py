# bot_engine.py — per-account threaded runner, command dispatch, stats

import threading
import time
import random
import logging
from database import get_account, get_all_accounts, get_settings
from owo_commands import OWOCommands
from captcha_handler import CaptchaHandler

logger = logging.getLogger('BotEngine')
logging.basicConfig(level=logging.INFO)

class AccountWorker:
    """One worker thread per Discord account."""

    def __init__(self, acc_id: int, socketio, settings: dict):
        self.acc_id   = acc_id
        self.socketio = socketio
        self.settings = settings
        self.running  = False
        self.paused   = False   # captcha pause
        self.thread   = None
        self.stats    = {
            'hunts': 0, 'battles': 0, 'commands': 0,
            'captchas': 0, 'status': 'stopped', 'uptime': 0,
            'last_command': None, 'balance': 0,
        }
        self._start_time = None
        self.owo    = None
        self.captcha_handler = CaptchaHandler()

    def start(self):
        if self.running:
            return {'status': 'already_running'}
        acc = get_account(self.acc_id)
        if not acc:
            return {'status': 'not_found'}
        self.owo     = OWOCommands(
            token      = acc['token'],
            channel_id = acc['channel_id'],
            proxy      = acc['proxy'] or None,
            on_captcha = self._on_captcha,
            on_message = self._on_message,
        )
        self.running     = True
        self.paused      = False
        self._start_time = time.time()
        self.stats['status'] = 'running'
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._emit_stats()
        return {'status': 'started'}

    def stop(self):
        self.running = False
        self.stats['status'] = 'stopped'
        self._emit_stats()
        return {'status': 'stopped'}

    def _run_loop(self):
        s = self.settings
        sell_interval = int(s.get('sell_interval_minutes', 60)) * 60
        last_sell     = 0
        hunt_min      = int(s.get('hunt_min_delay', 15))
        hunt_max      = int(s.get('hunt_max_delay', 20))

        while self.running:
            if self.paused:
                time.sleep(2)
                continue

            now = time.time()

            # sell on interval
            if s.get('sell_enabled', '1') == '1' and (now - last_sell) >= sell_interval:
                sell_what = s.get('sell_what', 'all')
                self.owo.send_command(f'sell {sell_what}')
                self.stats['commands'] += 1
                last_sell = now
                self._emit_stats()

            # hunt
            if s.get('hunt_enabled', '1') == '1':
                self.owo.send_command('hunt')
                self.stats['hunts']    += 1
                self.stats['commands'] += 1
                self.stats['last_command'] = 'hunt'
                self._emit_stats()
                self._sleep_jitter(hunt_min, hunt_max)
                if not self.running or self.paused:
                    continue

            # battle
            if s.get('battle_enabled', '1') == '1':
                self.owo.send_command('battle')
                self.stats['battles']  += 1
                self.stats['commands'] += 1
                self.stats['last_command'] = 'battle'
                self._emit_stats()
                self._sleep_jitter(hunt_min, hunt_max)
                if not self.running or self.paused:
                    continue

            # pray
            if s.get('pray_enabled', '1') == '1':
                self.owo.send_command('pray')
                self.stats['commands'] += 1
                self.stats['last_command'] = 'pray'
                self._emit_stats()
                self._sleep_jitter(5, 8)
                if not self.running or self.paused:
                    continue

            # curse
            if s.get('curse_enabled', '1') == '1':
                self.owo.send_command('curse')
                self.stats['commands'] += 1
                self.stats['last_command'] = 'curse'
                self._emit_stats()
                self._sleep_jitter(5, 8)
                if not self.running or self.paused:
                    continue

            # daily
            # daily runs once per session on first cycle, tracked by flag
            if s.get('daily_enabled', '1') == '1' and not getattr(self, '_daily_sent', False):
                self.owo.send_command('daily')
                self.stats['commands'] += 1
                self._daily_sent = True
                self._emit_stats()

            self._sleep_jitter(2, 5)

    def _on_captcha(self, sitekey: str, page_url: str):
        """Called by OWOCommands when captcha detected. Pauses account, tries to solve."""
        self.paused = True
        self.stats['status'] = 'captcha'
        self.stats['captchas'] += 1
        self._emit_stats()
        self._emit_log(f'[CAPTCHA] account {self.acc_id} paused — solving...')

        token = self.captcha_handler.solve(sitekey, page_url)
        if token:
            result = self.owo.submit_captcha(token)
            self._emit_log(f'[CAPTCHA] solved — result: {result}')
        else:
            self._emit_log('[CAPTCHA] no key available — staying paused. Add a capsolver/2captcha key.')

        self.paused = False
        self.stats['status'] = 'running'
        self._emit_stats()

    def _on_message(self, content: str):
        self._emit_log(f'[MSG] {content}')
        # crude balance parse: "You now have X cowoncy"
        import re
        m = re.search(r'(\d+)\s+cowoncy', content, re.IGNORECASE)
        if m:
            self.stats['balance'] = int(m.group(1))
            self._emit_stats()

    def _sleep_jitter(self, mn: int, mx: int):
        delay = random.uniform(mn, mx)
        for _ in range(int(delay * 10)):
            if not self.running:
                break
            time.sleep(0.1)

    def _emit_stats(self):
        if self._start_time:
            self.stats['uptime'] = int(time.time() - self._start_time)
        self.socketio.emit('account_stats', {'id': self.acc_id, 'stats': self.stats})

    def _emit_log(self, msg: str):
        self.socketio.emit('log', {'id': self.acc_id, 'msg': msg})


class BotEngine:
    def __init__(self, socketio):
        self.socketio = socketio
        self.workers: dict[int, AccountWorker] = {}

    def _get_or_create_worker(self, acc_id: int) -> AccountWorker:
        if acc_id not in self.workers:
            settings = get_settings()
            self.workers[acc_id] = AccountWorker(acc_id, self.socketio, settings)
        return self.workers[acc_id]

    def start_account(self, acc_id: int):
        w = self._get_or_create_worker(acc_id)
        return w.start()

    def stop_account(self, acc_id: int):
        if acc_id in self.workers:
            return self.workers[acc_id].stop()
        return {'status': 'not_running'}

    def start_all(self):
        accounts = get_all_accounts()
        results  = {}
        for acc in accounts:
            if acc['enabled']:
                results[acc['id']] = self.start_account(acc['id'])
        return results

    def stop_all(self):
        results = {}
        for acc_id in list(self.workers.keys()):
            results[acc_id] = self.stop_account(acc_id)
        return results

    def give_all(self, target_uid: str, amount: int):
        """Send `owo give <target_uid> <amount>` from every running account."""
        results = {}
        for acc_id, worker in self.workers.items():
            if worker.running and not worker.paused:
                worker.owo.send_command(f'give {target_uid} {amount}')
                worker.stats['commands'] += 1
                results[acc_id] = 'sent'
            else:
                results[acc_id] = 'skipped_not_running'
        return results

    def get_all_stats(self):
        return {
            acc_id: worker.stats
            for acc_id, worker in self.workers.items()
        }
