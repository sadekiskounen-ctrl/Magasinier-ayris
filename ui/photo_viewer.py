"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/photo_viewer.py
Fenêtre modale de visualisation et de gestion d'une photo de pièce.
- Affiche la photo centrée et proportionnée
- Options : Remplacer la photo, Supprimer (avec confirmation), Fermer
- Gestion propre de la mémoire et gestion d'erreurs (fichier manquant, corrompu).
"""

import os
from pathlib import Path
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk

from ui.theme import COLORS, FONTS
from ui.widgets import make_primary_button, make_secondary_button, make_danger_button, SeparatorLine
import database.db_manager as db
from services.photo_service import resoudre_chemin_absolu, traiter_et_enregistrer_photo, FORMATS_ACCEPTES


class PhotoViewerModal(ctk.CTkToplevel):
    """Fenêtre modale élégante pour voir ou remplacer la photo d'une pièce."""

    def __init__(self, parent, piece_id: int = None, code_barres: str = None, on_update=None):
        super().__init__(parent)
        self.piece_id = piece_id
        self.code_barres = code_barres
        self.on_update = on_update

        # Retrouver les infos de la pièce si nécessaire
        self.piece_info = None
        if self.piece_id:
            self.piece_info = db.get_produit_by_id(self.piece_id)
        elif self.code_barres:
            self.piece_info = db.find_produit_by_ref_or_last4(self.code_barres)
            if self.piece_info:
                self.piece_id = self.piece_info['id']

        self.title("📷  Photo de la Pièce")
        self.geometry("640x660")
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        # Centrage sur l'écran
        self.update_idletasks()
        w, h = 640, 660
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._current_photo_record = None
        self._tk_image = None  # Conserver la référence pour éviter le garbage collection

        self._build_ui()
        self._charger_photo()

    def _build_ui(self):
        # ── En-tête ──
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(16, 6))

        ref_str = self.piece_info.get('code_barres', self.code_barres or '—') if self.piece_info else (self.code_barres or '—')
        des_str = self.piece_info.get('designation', 'Pièce de Rechange') if self.piece_info else 'Pièce de Rechange'

        ctk.CTkLabel(
            header, text=f"📷  {des_str}",
            font=FONTS['title'], text_color=COLORS['text_primary'],
            wraplength=580, justify='left'
        ).pack(anchor='w')

        ctk.CTkLabel(
            header, text=f"Référence : {ref_str}",
            font=FONTS['mono'], text_color=COLORS['primary']
        ).pack(anchor='w', pady=(2, 0))

        SeparatorLine(self).pack(fill='x', padx=20, pady=8)

        # ── Zone d'affichage de l'image au centre ──
        self.image_container = ctk.CTkFrame(
            self, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1, border_color=COLORS['border']
        )
        self.image_container.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        self.lbl_image = ctk.CTkLabel(self.image_container, text="", text_color=COLORS['text_muted'])
        self.lbl_image.pack(expand=True, fill='both', padx=10, pady=10)

        # ── Barre d'informations sous l'image ──
        self.lbl_info = ctk.CTkLabel(
            self, text="",
            font=FONTS['small'], text_color=COLORS['text_secondary']
        )
        self.lbl_info.pack(fill='x', padx=20, pady=(0, 6))

        # ── Boutons d'actions en bas ──
        btn_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], height=56, border_width=1, border_color=COLORS['border'])
        btn_frame.pack(side='bottom', fill='x')

        make_secondary_button(btn_frame, 'Fermer', command=self.destroy, width=110).pack(side='right', padx=14, pady=10)

        self.btn_remplacer = make_primary_button(
            btn_frame, '🔄 Remplacer photo', command=self._importer_photo, icon='', width=160
        )
        self.btn_remplacer.pack(side='right', padx=4, pady=10)

        self.btn_supprimer = make_danger_button(
            btn_frame, '🗑️ Supprimer', command=self._confirmer_suppression, width=120
        )
        self.btn_supprimer.pack(side='left', padx=14, pady=10)

    def _charger_photo(self):
        """Charge l'image depuis le chemin enregistré en base sans bloquer."""
        if not self.piece_id:
            self._afficher_message_aucun("Aucun identifiant de pièce associé.")
            return

        rec = db.get_photo_piece(self.piece_id)
        self._current_photo_record = rec

        if not rec or not rec.get('chemin'):
            self._afficher_message_aucun("Aucune photo enregistrée pour cette pièce.")
            self.btn_remplacer.configure(text="➕ Ajouter photo")
            self.btn_supprimer.configure(state='disabled')
            self.lbl_info.configure(text="Astuce : Vous pouvez ajouter une photo dès maintenant.")
            return

        self.btn_remplacer.configure(text="🔄 Remplacer photo")
        self.btn_supprimer.configure(state='normal')

        chemin_brut = rec.get('chemin', '')
        chemin_absolu = resoudre_chemin_absolu(chemin_brut)

        if not chemin_absolu or not os.path.exists(chemin_absolu):
            self._afficher_message_aucun(
                f"⚠️ Le fichier photo est introuvable sur le disque :\n{chemin_brut}\n\n"
                "Le fichier a peut-être été déplacé ou supprimé du dossier photos_pieces."
            )
            self.lbl_info.configure(text=f"Chemin BDD : {chemin_brut} (Inaccessible)")
            return

        # Chargement et affichage avec Pillow
        try:
            with Image.open(chemin_absolu) as img:
                # Calcul des dimensions d'affichage (max 580x420)
                max_w, max_h = 580, 420
                orig_w, orig_h = img.size

                ratio = min(max_w / orig_w, max_h / orig_h)
                disp_w = max(1, int(orig_w * ratio))
                disp_h = max(1, int(orig_h * ratio))

                img_disp = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
                self._tk_image = ImageTk.PhotoImage(img_disp)

            self.lbl_image.configure(image=self._tk_image, text="")
            date_ajout = rec.get('date_ajout', 'Date inconnue')
            self.lbl_info.configure(
                text=f"📁 {Path(chemin_brut).name}  |  Ajoutée le : {date_ajout}  |  Résolution originale : {orig_w}x{orig_h} px"
            )

        except Exception as e:
            self._afficher_message_aucun(f"Erreur lors de la lecture de l'image :\n{e}")
            self.lbl_info.configure(text="Fichier corrompu ou illisible.")

    def _afficher_message_aucun(self, msg: str):
        self._tk_image = None
        self.lbl_image.configure(image="", text=msg)

    def _importer_photo(self):
        """Ouvre l'explorateur pour choisir et enregistrer une nouvelle photo."""
        file_types = [
            ("Images compatibles", "*.jpg;*.jpeg;*.png;*.bmp;*.webp"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("PNG", "*.png"),
            ("Tous les fichiers", "*.*")
        ]
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Sélectionner une photo pour la pièce",
            filetypes=file_types
        )
        if not chosen:
            return

        if not self.piece_id:
            messagebox.showerror("Erreur", "Pièce non identifiée pour l'enregistrement.", parent=self)
            return

        # Traitement et compression via le service
        ok, res = traiter_et_enregistrer_photo(chosen, self.piece_id)
        if not ok:
            messagebox.showerror("Erreur Traitement Photo", res, parent=self)
            return

        # Sauvegarde du chemin relatif en base
        try:
            db.enregistrer_photo_piece(self.piece_id, res)
            messagebox.showinfo("Photo Enregistrée", "La photo de la pièce a été enregistrée avec succès !", parent=self)
            self._charger_photo()
            if self.on_update:
                self.on_update()
        except Exception as e:
            messagebox.showerror("Erreur BDD", f"Impossible d'enregistrer la photo en base :\n{e}", parent=self)

    def _confirmer_suppression(self):
        """Supprime la liaison de la photo avec confirmation explicite."""
        if not self.piece_id or not self._current_photo_record:
            return

        rep = messagebox.askyesno(
            "Confirmer la suppression",
            "Voulez-vous dissocier cette photo de la pièce ?\n(Le fichier restera conservé en sécurité).",
            parent=self
        )
        if rep:
            try:
                db.supprimer_photo_piece(self.piece_id)
                messagebox.showinfo("Photo Supprimée", "La photo a été retirée de la pièce.", parent=self)
                self._charger_photo()
                if self.on_update:
                    self.on_update()
            except Exception as e:
                messagebox.showerror("Erreur BDD", f"Impossible de supprimer la photo :\n{e}", parent=self)


def ouvrir_photo_viewer(parent, piece_id: int = None, code_barres: str = None, on_update=None):
    """Fonction utilitaire pour ouvrir la fenêtre de photo de manière sécurisée."""
    return PhotoViewerModal(parent, piece_id=piece_id, code_barres=code_barres, on_update=on_update)

