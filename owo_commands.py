# owo_commands.py — raw Discord HTTP sender, captcha detection, message poll

import requests
import json
import time
import threading
import logging
import random

logger = logging.getLogger('OWOCommands')

DISCORD_API  = 'https://discord.com/api/v9'
OWO_BOT_ID   = '408785106942164992'

# hCaptcha site config for OWO (used when captcha solver key provided)
OWO_CAPTCHA_SITEKEY = 'ab803635-dc14-4f49-b39b-d4fb6e6b06a0'
OWO_CAPTCHA_PAGE    = 'https://owobot.com'

class OWOCommands:
    def __init__(self, token: str, channel_id: str, proxy=None,
                 on_captcha=None, on_message=None):
        self.token      = token
        self.channel_id = channel_id
        self.proxy      = {'http': proxy, 'https': proxy} if proxy else None
        self.on_captcha = on_captcha
        self.on_message = on_message
        self._last_msg_id = None
        self._poll_thread = threading.Thread(target=self._poll_messages, daemon=True)
        self._poll_thread.start()

    def _headers(self) -> dict:
        return {
            'Authorization': self.token,
            'Content-Type':  'application/json',
            'User-Agent':    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

    def send_command(self, command: str) -> bool:
        """Send `owo <command>` as a Discord message."""
        payload = {'content': f'owo {command}', 'tts': False}
        url     = f'{DISCORD_API}/channels/{self.channel_id}/messages'
        try:
            r = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                proxies=self.proxy,
                timeout=15,
            )
            if r.status_code == 429:
                retry = r.json().get('retry_after', 5)
                logger.warning(f'Rate limited — sleeping {retry}s')
                time.sleep(float(retry))
                return self.send_command(command)
            if r.status_code not in (200, 201):
                logger.error(f'send_command failed: {r.status_code} {r.text[:200]}')
                return False
            return True
        except Exception as e:
            logger.error(f'send_command exception: {e}')
            return False

    def submit_captcha(self, captcha_token: str) -> str:
        """OWO accepts captcha via a specific endpoint interaction."""
        # OWO Bot uses a custom verification; send the token as a DM command workaround
        # Real integration: POST to OWO's verify endpoint with the solved token
        payload = {'content': f'owo verify {captcha_token}'}
        url     = f'{DISCORD_API}/channels/{self.channel_id}/messages'
        try:
            r = requests.post(url, headers=self._headers(), json=payload,
                              proxies=self.proxy, timeout=15)
            return r.text[:100]
        except Exception as e:
            return str(e)

    def _poll_messages(self):
        """Background poll for OWO bot responses. Checks for captcha triggers."""
        while True:
            try:
                url    = f'{DISCORD_API}/channels/{self.channel_id}/messages?limit=5'
                r      = requests.get(url, headers=self._headers(),
                                      proxies=self.proxy, timeout=15)
                if r.status_code != 200:
                    time.sleep(5)
                    continue
                msgs = r.json()
                for msg in msgs:
                    if msg.get('author', {}).get('id') != OWO_BOT_ID:
                        continue
                    msg_id  = msg['id']
                    content = msg.get('content', '')
                    embeds  = msg.get('embeds', [])

                    if msg_id == self._last_msg_id:
                        break
                    self._last_msg_id = msg_id

                    # captcha detection
                    captcha_triggers = [
                        'are you human', 'captcha', 'verify', 'i am not a bot',
                        'suspended', 'type the following'
                    ]
                    combined = content.lower() + json.dumps(embeds).lower()
                    if any(t in combined for t in captcha_triggers):
                        if self.on_captcha:
                            threading.Thread(
                                target=self.on_captcha,
                                args=(OWO_CAPTCHA_SITEKEY, OWO_CAPTCHA_PAGE),
                                daemon=True
                            ).start()

                    if self.on_message and content:
                        self.on_message(content)

            except Exception as e:
                logger.error(f'poll error: {e}')
            time.sleep(random.uniform(3, 6))
