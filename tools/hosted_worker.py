"""Standalone hosted worker; never starts Bot API polling or interactive login."""

import asyncio
import json
import os
from pathlib import Path
import sys

from tools.yougen_agent import run
from tools.yougen_queue import Queue
from tools.yougen_worker import Panel


def load_config(directory):
    directory = Path(directory).resolve()
    path = directory / 'yougen' / 'bridge.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    if config.get('profile') != 'independent':
        raise ValueError('Нужна отдельная серверная сессия, не копия Telegram Desktop.')
    session = path.parent / 'provider.session'
    if not session.is_file() or session.is_symlink():
        raise ValueError('Не найдена отдельная provider.session.')
    if not isinstance(config.get('user_id'), int) or config['user_id'] <= 0:
        raise ValueError('Неверный ID владельца.')
    if not isinstance(config.get('api_id'), int) or not config.get('api_hash'):
        raise ValueError('Не заданы параметры Telegram API.')
    if config.get('target') != '@kinomobi_bot':
        raise ValueError('Не подтверждён основной бот KinoTime.')
    Panel(config['panel_url'], config['panel_token'], config['instance_id'])
    config['session'] = str(session)
    return config, path


def main():
    directory = Path(os.environ.get('DATA_DIR', '/app/data'))
    try:
        config, path = load_config(directory)
        print('KinoTime Worker: отдельный обработчик запущен.', flush=True)
        asyncio.run(run(config, Queue(path.parent / 'remote.sqlite'), True, path))
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as error:
        # Credentials and session contents must never enter hosting logs.
        print('KinoTime Worker: запуск невозможен (' + type(error).__name__
              + '). Проверьте приватные файлы в DATA_DIR/yougen.', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
