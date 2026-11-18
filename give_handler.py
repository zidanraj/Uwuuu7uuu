# give_handler.py — ogive_all endpoint helper (imported by main.py via bot_engine)
# Already wired into BotEngine.give_all() — this module is a standalone util
# for direct CLI usage or testing.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import get_all_accounts, init_db
from owo_commands import OWOCommands

def cli_give_all(target_uid: str, amount: int):
    init_db()
    accounts = get_all_accounts()
    if not accounts:
        print('No accounts in DB.')
        return
    for acc in accounts:
        if not acc['enabled']:
            continue
        owo = OWOCommands(
            token      = acc['token'],
            channel_id = acc['channel_id'],
            proxy      = acc['proxy'] or None,
        )
        ok = owo.send_command(f'give {target_uid} {amount}')
        print(f"[{acc['name']}] give {target_uid} {amount} -> {'OK' if ok else 'FAIL'}")

if __name__ == '__main__':
    # python give_handler.py <uid> <amount>
    if len(sys.argv) < 3:
        print('usage: python give_handler.py <target_uid> <amount>')
        sys.exit(1)
    cli_give_all(sys.argv[1], int(sys.argv[2]))
