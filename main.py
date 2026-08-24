"""
SARL AYRIS — Gestionnaire de Stock
Point d'entrée principal de l'application.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import customtkinter as ctk


def main():
    """Lance l'application SARL AYRIS Stock avec authentification."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('sarl.nomade.ayris.stock.v3')
    except Exception:
        pass

    # ── Initialiser la base de données ───────────────────────────────────────
    from database.db_manager import initialize_database
    initialize_database()

    # ── Configurer CustomTkinter & Alignement DPI ───────────────────────────
    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_appearance_mode('light')
    ctk.set_default_color_theme('blue')

    # ── Écran de connexion / authentification (instantané sans délai) ────────
    from ui.login import LoginWindow
    login = LoginWindow()
    login.mainloop()

    if not login.authenticated:
        sys.exit(0)

    # ── Lancer la fenêtre principale ─────────────────────────────────────────
    from ui.main_window import MainWindow
    app = MainWindow()

    def on_closing():
        app.destroy()
        sys.exit(0)

    app.protocol('WM_DELETE_WINDOW', on_closing)
    app.mainloop()


if __name__ == '__main__':
    main()
