"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/login.py
Fenêtre de connexion avec authentification (nom d'utilisateur / mot de passe).
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
from pathlib import Path

# Identifiants officiels
VALID_CREDENTIALS = {
    "magasinier": "magasinier",
}


class LoginWindow(ctk.CTk):
    """Fenêtre d'authentification AYRIS — apparaît avant la fenêtre principale."""

    def __init__(self):
        super().__init__()

        self.authenticated = False
        self.title("SARL NOMADE AYRIS — Authentification")
        self.geometry("500x640")
        self.resizable(False, False)
        self.configure(fg_color="#0B2E6B")

        # Icône Ayris
        BASE_DIR = Path(__file__).parent.parent
        ico_path = str(BASE_DIR / 'assets' / 'ayris.ico')
        png_path = str(BASE_DIR / 'assets' / 'logo_circle.png')
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
                self.wm_iconbitmap(ico_path)
            except Exception:
                pass
        if os.path.exists(png_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(png_path)
                self._app_icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._app_icon_photo)
            except Exception:
                pass

        # Centrer la fenêtre
        self.update_idletasks()
        w, h = 500, 640
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self.bind("<Return>", lambda e: self._login())

    def _build_ui(self):
        # ── Logo / En-tête ────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=(24, 0))

        # Essayer de charger le logo
        BASE_DIR = Path(__file__).parent.parent
        logo_path = str(BASE_DIR / 'assets' / 'logo_nomade_ayris.png')
        if os.path.exists(logo_path):
            try:
                from PIL import Image
                import customtkinter as ctk_mod
                logo_img = ctk_mod.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(90, 70)
                )
                ctk.CTkLabel(logo_frame, image=logo_img, text="").pack()
            except Exception:
                pass

        ctk.CTkLabel(
            logo_frame,
            text="SARL NOMADE AYRIS",
            font=("Segoe UI", 22, "bold"),
            text_color="#FFFFFF"
        ).pack(pady=(6, 0))

        ctk.CTkLabel(
            logo_frame,
            text="Eau de Source Naturelle",
            font=("Segoe UI", 12),
            text_color="#93C5FD"
        ).pack()

        # ── Carte de connexion ────────────────────────────────────────────────
        card = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=0
        )
        card.pack(fill="both", expand=True, padx=28, pady=20)

        ctk.CTkLabel(
            card,
            text="🔐  Connexion",
            font=("Segoe UI", 20, "bold"),
            text_color="#0B2E6B"
        ).pack(pady=(16, 2))

        ctk.CTkLabel(
            card,
            text="Saisissez vos identifiants pour accéder au système",
            font=("Segoe UI", 11),
            text_color="#64748B"
        ).pack(pady=(0, 14))

        # Séparateur
        sep = ctk.CTkFrame(card, height=1, fg_color="#E2E8F0")
        sep.pack(fill="x", padx=20, pady=(0, 14))

        # Champ Nom d'utilisateur
        ctk.CTkLabel(
            card,
            text="👤  Nom d'utilisateur",
            font=("Segoe UI", 13, "bold"),
            text_color="#374151",
            anchor="w"
        ).pack(fill="x", padx=24)

        self.e_user = ctk.CTkEntry(
            card,
            placeholder_text="Nom d'utilisateur...",
            font=("Segoe UI", 14),
            fg_color="#F8FAFC",
            border_color="#004899",
            border_width=2,
            text_color="#0F172A",
            corner_radius=10,
            height=44
        )
        self.e_user.pack(fill="x", padx=24, pady=(4, 10))
        self.e_user.focus()

        # Champ Mot de passe
        ctk.CTkLabel(
            card,
            text="🔒  Mot de passe",
            font=("Segoe UI", 13, "bold"),
            text_color="#374151",
            anchor="w"
        ).pack(fill="x", padx=24)

        self.e_pass = ctk.CTkEntry(
            card,
            placeholder_text="Mot de passe...",
            show="●",
            font=("Segoe UI", 14),
            fg_color="#F8FAFC",
            border_color="#004899",
            border_width=2,
            text_color="#0F172A",
            corner_radius=10,
            height=44
        )
        self.e_pass.pack(fill="x", padx=24, pady=(4, 4))

        # Message d'erreur
        self.lbl_error = ctk.CTkLabel(
            card,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color="#DC2626"
        )
        self.lbl_error.pack(pady=(0, 4))

        # Bouton Se connecter
        self.btn_login = ctk.CTkButton(
            card,
            text="🔑  Se connecter",
            command=self._login,
            fg_color="#004899",
            hover_color="#0B2E6B",
            text_color="white",
            font=("Segoe UI", 15, "bold"),
            corner_radius=12,
            height=48
        )
        self.btn_login.pack(fill="x", padx=24, pady=(4, 14))

        # Pied de carte
        ctk.CTkLabel(
            card,
            text="Système de Gestion de Stock & Logistique\nv3.5 Enterprise — AYRIS",
            font=("Segoe UI", 10),
            text_color="#94A3B8",
            justify="center"
        ).pack(pady=(0, 12))

    def _login(self):
        username = self.e_user.get().strip().lower()
        password = self.e_pass.get().strip()

        if not username or not password:
            self._show_error("⚠  Veuillez remplir tous les champs.")
            return

        if VALID_CREDENTIALS.get(username) == password:
            self.authenticated = True
            self.destroy()
        else:
            self._show_error("❌  Nom d'utilisateur ou mot de passe incorrect.")
            self.e_pass.delete(0, "end")
            self.e_pass.focus()
            # Animation shake
            self._shake()

    def _show_error(self, msg: str):
        self.lbl_error.configure(text=msg)

    def _shake(self):
        """Micro-animation de secousse sur la fenêtre."""
        x0 = self.winfo_x()
        y0 = self.winfo_y()
        for dx in [8, -8, 6, -6, 4, -4, 2, -2, 0]:
            self.geometry(f"+{x0 + dx}+{y0}")
            self.update()
            self.after(18)
