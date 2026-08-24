"""
SARL AYRIS — Script de compilation PyInstaller
Génère un .exe autonome Windows (one-file).

Usage :
    python build.py
"""

import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
MAIN_SCRIPT = BASE_DIR / 'main.py'
APP_NAME = 'SARL_Ayris_Stock'
ICON_PATH = BASE_DIR / 'assets' / 'ayris.ico'


def build():
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onefile',                         # Fichier .exe unique
        '--windowed',                        # Pas de console (GUI only)
        f'--name={APP_NAME}',
        '--clean',

        # Données à inclure
        '--add-data', f'{BASE_DIR / "database"};database',
        '--add-data', f'{BASE_DIR / "ui"};ui',
        '--add-data', f'{BASE_DIR / "services"};services',
        '--add-data', f'{BASE_DIR / "assets"};assets',

        # Imports cachés nécessaires
        '--hidden-import', 'customtkinter',
        '--hidden-import', 'tkinter',
        '--hidden-import', 'tkinter.ttk',
        '--hidden-import', 'reportlab',
        '--hidden-import', 'reportlab.graphics',
        '--hidden-import', 'reportlab.platypus',
        '--hidden-import', 'reportlab.lib',
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'PIL',
        '--hidden-import', 'sqlite3',
        '--hidden-import', 'tkcalendar',
        '--hidden-import', 'babel.numbers',

        # Collectes de paquets complets
        '--collect-all', 'customtkinter',
        '--collect-all', 'reportlab',
        '--collect-all', 'openpyxl',
        '--collect-all', 'tkcalendar',
        '--collect-all', 'babel',
    ]

    if ICON_PATH.exists():
        cmd.extend(['--icon', str(ICON_PATH)])

    cmd.append(str(MAIN_SCRIPT))

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print('='*60)
    print('  SARL AYRIS Stock -- Compilation PyInstaller')
    print('='*60)

    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        exe_path = BASE_DIR / 'dist' / f'{APP_NAME}.exe'
        print('\n' + '='*60)
        print('  [OK]  COMPILATION REUSSIE !')
        print(f'  Fichier EXE : {exe_path}')
        print('='*60)
    else:
        print('\n' + '='*60)
        print('  [ERREUR]  ERREUR DE COMPILATION')
        print('='*60)
        sys.exit(1)


if __name__ == '__main__':
    build()
