"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/main_window.py
Fenêtre principale avec sidebar bleu marine, logo officiel Ayris parfaitement proportionné, et fond watermark visible sur tous les écrans.
"""

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
from pathlib import Path

from ui.theme import COLORS, FONTS, SIDEBAR_ITEMS

BASE_DIR       = Path(__file__).parent.parent
LOGO_PATH      = str(BASE_DIR / 'assets' / 'logo_nomade_ayris.png')
WATERMARK_PATH = str(BASE_DIR / 'assets' / 'watermark.png')


class MainWindow(ctk.CTk):
    """Fenêtre principale SARL NOMADE AYRIS — thème clair ERP avec watermark permanent."""

    def __init__(self):
        super().__init__()

        self.title('SARL NOMADE AYRIS — Système de Gestion de Stock & Logistique')
        self.configure(fg_color=COLORS['bg_dark'])

        # ── Détecter la résolution écran et adapter la géométrie ───────────────────
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Adapter la taille de la fenêtre à la résolution
        if sw <= 1280:
            win_w, win_h = int(sw * 0.92), int(sh * 0.88)
            self._sidebar_width = 220
        elif sw <= 1600:
            win_w, win_h = int(sw * 0.85), int(sh * 0.85)
            self._sidebar_width = 240
        else:
            win_w, win_h = 1380, 880
            self._sidebar_width = 260

        self.geometry(f'{win_w}x{win_h}')
        self.minsize(1080, 680)

        self._set_window_icon()

        self._active_key = None
        self._frames = {}
        self._nav_buttons = {}
        self._last_win_state = None

        self._build_ui()
        self.navigate_to('dashboard')
        self.center_window()

        # ── Écouter les changements de taille/état de la fenêtre ────────────────
        self.bind('<Configure>', self._on_window_configure)

    def _set_window_icon(self):
        """Définit le logo officiel Ayris comme icône de fenêtre et barre des tâches."""
        ico_path = str(BASE_DIR / 'assets' / 'ayris.ico')
        png_path = str(BASE_DIR / 'assets' / 'logo_circle.png')

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass
            try:
                self.wm_iconbitmap(ico_path)
            except Exception:
                pass

        if os.path.exists(png_path):
            try:
                img = Image.open(png_path)
                self._app_icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._app_icon_photo)
            except Exception:
                pass

    def center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{(sw - w)//2}+{(sh - h)//2}')

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar bleu marine ──────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(
            self,
            fg_color=COLORS['bg_sidebar'],
            corner_radius=0,
            width=self._sidebar_width,
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)

        # ─ Logo AYRIS officiel sans déformation dans la sidebar ───────────────
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        logo_frame.pack(fill='x', padx=0, pady=0)

        logo_inner = ctk.CTkFrame(logo_frame, fg_color='transparent')
        logo_inner.pack(fill='x', pady=(16, 6))

        if os.path.exists(LOGO_PATH):
            try:
                pil_img = Image.open(LOGO_PATH).convert('RGBA')
                # Ratio d'origine 1024 x 801 (1.278) -> Taille 192 x 150 sans déformation !
                logo_img = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(192, 150)
                )
                lbl_logo = ctk.CTkLabel(logo_inner, image=logo_img, text='')
                lbl_logo.pack(pady=4, padx=10)
            except Exception:
                self._draw_text_logo(logo_inner)
        else:
            self._draw_text_logo(logo_inner)

        # Ligne séparatrice sous le logo
        ctk.CTkFrame(
            self.sidebar,
            fg_color='#1D5197',
            height=1,
            corner_radius=0
        ).pack(fill='x', padx=20, pady=(4, 8))

        # ─ Navigation items ───────────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        nav_frame.pack(fill='x', pady=(4, 0), padx=10)

        for item in SIDEBAR_ITEMS:
            btn = self._make_nav_button(nav_frame, item)
            btn.pack(fill='x', pady=3)
            self._nav_buttons[item['key']] = btn

        # ─ Bas de sidebar ─────────────────────────────────────────────────
        ctk.CTkFrame(self.sidebar, fg_color='#1D5197',
                     height=1, corner_radius=0).pack(side='bottom', fill='x')

        bottom = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        bottom.pack(side='bottom', fill='x', padx=10, pady=10)

        ctk.CTkLabel(
            bottom, text='v3.5 Enterprise — AYRIS',
            font=FONTS['small_bold'],
            text_color=COLORS['sidebar_text']
        ).pack(pady=2)

        # ── Zone de contenu principal (fond clair + watermark AYRIS visible) ──
        self.content_area = ctk.CTkFrame(
            self, fg_color=COLORS['bg_dark'],
            corner_radius=0
        )
        self.content_area.grid(row=0, column=1, sticky='nsew')
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Background Watermark AYRIS visible permanent
        if os.path.exists(WATERMARK_PATH):
            try:
                wm_pil = Image.open(WATERMARK_PATH).convert('RGBA')
                wm_img = ctk.CTkImage(
                    light_image=wm_pil,
                    dark_image=wm_pil,
                    size=(560, 438)
                )
                self.bg_watermark_lbl = ctk.CTkLabel(self.content_area, image=wm_img, text='', fg_color='transparent')
                self.bg_watermark_lbl.place(relx=0.5, rely=0.5, anchor='center')
            except Exception:
                pass

    def _draw_text_logo(self, parent):
        ctk.CTkLabel(
            parent, text='💧',
            font=('Segoe UI Emoji', 32),
            text_color=COLORS['accent']
        ).pack(pady=(14, 0))
        ctk.CTkLabel(
            parent, text='AYRIS',
            font=('Segoe UI', 20, 'bold'),
            text_color=COLORS['text_white']
        ).pack()
        ctk.CTkLabel(
            parent, text='EAU DE SOURCE',
            font=('Segoe UI', 9, 'bold'),
            text_color=COLORS['sidebar_icon']
        ).pack(pady=(0, 12))

    def _on_window_configure(self, event):
        """Gère le redimensionnement et la bascule plein écran."""
        # Seulement traiter les événements de la fenêtre principale (pas les widgets enfants)
        if event.widget is not self:
            return

        # Détecter le changement d'état (maximisé / réduit / normal)
        try:
            current_state = self.state()
        except Exception:
            return

        if current_state != self._last_win_state:
            self._last_win_state = current_state
            # Forcer un rafraîchissement après la bascule plein écran
            self.after(100, self._force_layout_refresh)

    def _force_layout_refresh(self):
        """Force le recalcul de la disposition lors du redimensionnement."""
        try:
            self.update_idletasks()

            # Si un frame actif existe, le re-grid proprement sans réexécuter de requêtes SQL
            if self._active_key and self._active_key in self._frames:
                frame = self._frames[self._active_key]
                frame.grid_forget()
                frame.grid(row=0, column=0, sticky='nsew')
        except Exception:
            pass

    def _make_nav_button(self, parent, item: dict) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=f"  {item['icon']}   {item['label']}",
            command=lambda k=item['key']: self.navigate_to(k),
            fg_color='transparent',
            hover_color='#1D5197',
            text_color=COLORS['sidebar_text'],
            font=FONTS['subtitle'],
            corner_radius=10,
            height=44,
            anchor='w',
        )

    def navigate_to(self, key: str):
        if self._active_key == key:
            return

        if self._active_key and self._active_key in self._nav_buttons:
            self._nav_buttons[self._active_key].configure(
                fg_color='transparent',
                text_color=COLORS['sidebar_text'],
            )

        self._active_key = key
        if key in self._nav_buttons:
            self._nav_buttons[key].configure(
                fg_color=COLORS['sidebar_active_bg'],
                text_color=COLORS['sidebar_text_active'],
            )

        is_new = key not in self._frames
        if is_new:
            self._frames[key] = self._create_frame(key)

        for f in self._frames.values():
            f.grid_forget()

        self._frames[key].grid(row=0, column=0, sticky='nsew')

        frame = self._frames[key]
        # Rafraîchir seulement si l'écran existait déjà (car __init__ le fait au moment de la création)
        if not is_new and hasattr(frame, 'refresh') and key != 'options':
            frame.refresh()

        if key == 'saisie' and hasattr(frame, '_set_focus_ref'):
            self.after(150, frame._set_focus_ref)

    def _create_frame(self, key: str) -> ctk.CTkFrame:
        from ui.dashboard import DashboardFrame
        from ui.fournisseurs import FournisseursFrame
        from ui.catalogue import CatalogueFrame
        from ui.engins import EnginsFrame
        from ui.outillage import OutillageFrame
        from ui.saisie import SaisieFrame
        from ui.inventaire import InventaireFrame
        from ui.historique import HistoriqueFrame
        from ui.options import OptionsFrame
        from ui.achat import AchatFrame

        mapping = {
            'dashboard':   DashboardFrame,
            'fournisseurs': FournisseursFrame,
            'catalogue':   CatalogueFrame,
            'engins':      EnginsFrame,
            'outillage':   OutillageFrame,
            'saisie':      SaisieFrame,
            'achat':       AchatFrame,
            'inventaire':  InventaireFrame,
            'historique':  HistoriqueFrame,
            'options':     OptionsFrame,
        }
        cls = mapping.get(key)
        if cls:
            frame = cls(self.content_area)
            # Rendre le fond semi-transparent si possible pour voir le watermark
            return frame

        frame = ctk.CTkFrame(self.content_area, fg_color=COLORS['bg_dark'])
        ctk.CTkLabel(frame, text=f'Écran : {key}',
                     font=FONTS['title'],
                     text_color=COLORS['text_primary']).place(relx=0.5, rely=0.5, anchor='center')
        return frame
