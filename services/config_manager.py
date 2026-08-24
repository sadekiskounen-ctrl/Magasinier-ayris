"""
SARL AYRIS - Gestionnaire de Stock
Module: services/config_manager.py
Gère la configuration persistante de l'application (JSON).
"""

import json
import os
from pathlib import Path


def get_config_path() -> str:
    local_app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    app_dir = Path(local_app_data) / 'SARL_Ayris_Stock'
    app_dir.mkdir(parents=True, exist_ok=True)
    return str(app_dir / 'config.json')


DEFAULT_CONFIG = {
    'pdf_directory': str(Path.home() / 'Documents' / 'SARL_Ayris_PDF'),
    'imprimante': '',
    'theme': 'dark',
}


def load_config() -> dict:
    path = get_config_path()
    if not os.path.exists(path):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        # S'assurer que toutes les clés par défaut existent
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    path = get_config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_config(key: str, default=None):
    cfg = load_config()
    return cfg.get(key, default)


def set_config(key: str, value):
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
