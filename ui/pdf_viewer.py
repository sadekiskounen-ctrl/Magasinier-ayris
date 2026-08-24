"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/pdf_viewer.py
Visionneuse PDF intégrée — affiche le PDF dans une fenêtre modale premium
avec options de téléchargement et d'impression. Évite le téléchargement automatique.
"""

import os
import subprocess
import sys
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from ui.theme import COLORS, FONTS


class PDFViewerModal(ctk.CTkToplevel):
    """
    Fenêtre modale pour visionner un PDF généré.
    Affiche les informations du document et propose Télécharger / Imprimer.
    Si fitz (PyMuPDF) est disponible, affiche les pages sous forme d'images.
    """

    def __init__(self, parent, pdf_path: str, title: str = "Visualisation PDF"):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.doc_title = title
        self._pages_images = []
        self._current_page = 0

        self.title(f"📄  {title}")
        self.geometry("860x680")
        self.minsize(700, 500)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self._build_ui()
        self._load_pdf()

    def _build_ui(self):
        # ── Barre supérieure ──────────────────────────────────────────────────
        top_bar = ctk.CTkFrame(self, fg_color=COLORS['bg_card'],
                               corner_radius=0, border_width=0)
        top_bar.pack(fill='x', padx=0, pady=0)

        ctk.CTkLabel(
            top_bar, text=f"📄  {self.doc_title}",
            font=FONTS['title'], text_color=COLORS['text_primary']
        ).pack(side='left', padx=20, pady=12)

        # Boutons à droite
        btn_frame = ctk.CTkFrame(top_bar, fg_color='transparent')
        btn_frame.pack(side='right', padx=16, pady=8)

        ctk.CTkButton(
            btn_frame, text='🖨️  Imprimer',
            command=self._imprimer,
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['bg_selected'],
            text_color=COLORS['text_primary'],
            font=FONTS['body_bold'],
            corner_radius=8, height=38, width=140
        ).pack(side='left', padx=6)

        ctk.CTkButton(
            btn_frame, text='💾  Télécharger',
            command=self._telecharger,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color='white',
            font=FONTS['body_bold'],
            corner_radius=8, height=38, width=160
        ).pack(side='left', padx=6)

        ctk.CTkButton(
            btn_frame, text='✕',
            command=self.destroy,
            fg_color=COLORS['danger'],
            hover_color='#DC2626',
            text_color='white',
            font=FONTS['body_bold'],
            corner_radius=8, height=38, width=40
        ).pack(side='left', padx=(6, 0))

        # ── Zone principale (canvas scrollable) ───────────────────────────────
        self.content_frame = ctk.CTkScrollableFrame(
            self, fg_color='#2D3748', corner_radius=0
        )
        self.content_frame.pack(fill='both', expand=True, padx=0, pady=0)

        # Navigation pages (visible si plusieurs pages)
        self.nav_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'],
                                      corner_radius=0)
        self.nav_frame.pack(fill='x', side='bottom')
        self.lbl_page = ctk.CTkLabel(self.nav_frame, text='',
                                      font=FONTS['body_bold'],
                                      text_color=COLORS['text_secondary'])
        self.lbl_page.pack(side='left', padx=20, pady=8)

        # Chemin fichier
        ctk.CTkLabel(
            self.nav_frame,
            text=f"📁  {self.pdf_path}",
            font=FONTS['small'],
            text_color=COLORS['text_muted']
        ).pack(side='right', padx=16, pady=8)

    def _load_pdf(self):
        """Charge et affiche le PDF (avec PyMuPDF si disponible, sinon fallback info)."""
        if not os.path.exists(self.pdf_path):
            self._show_error("Fichier PDF introuvable :\n" + self.pdf_path)
            return

        # Essayer PyMuPDF (fitz)
        try:
            import fitz  # PyMuPDF
            self._render_with_fitz(fitz)
        except ImportError:
            self._show_fallback_info()

    def _render_with_fitz(self, fitz):
        """Rendu des pages PDF en images avec PyMuPDF."""
        try:
            doc = fitz.open(self.pdf_path)
            nb_pages = len(doc)

            for w in self.content_frame.winfo_children():
                w.destroy()

            self._tk_images = []

            for page_num in range(nb_pages):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(1.8, 1.8)  # zoom 180%
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convertir en PhotoImage
                img_data = pix.tobytes("ppm")
                tk_img = tk.PhotoImage(data=img_data)
                self._tk_images.append(tk_img)

                # Label séparateur
                if page_num > 0:
                    ctk.CTkLabel(
                        self.content_frame,
                        text=f"─── Page {page_num + 1} ───",
                        font=FONTS['body_bold'],
                        text_color='#94A3B8'
                    ).pack(pady=8)

                # Afficher la page
                lbl = tk.Label(
                    self.content_frame,
                    image=tk_img,
                    bg='#2D3748',
                    relief='flat',
                    borderwidth=0
                )
                lbl.pack(pady=(8, 0), padx=16)

            doc.close()
            self.lbl_page.configure(text=f"📄  {nb_pages} page(s)")

        except Exception as e:
            self._show_error(f"Erreur lors du rendu PDF :\n{e}")

    def _show_fallback_info(self):
        """Affiche les infos du fichier si PyMuPDF n'est pas installé."""
        for w in self.content_frame.winfo_children():
            w.destroy()

        # Icône et message central
        info_card = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS['bg_card'],
            corner_radius=16, border_width=1,
            border_color=COLORS['border']
        )
        info_card.pack(expand=True, padx=40, pady=40, fill='both')

        ctk.CTkLabel(
            info_card, text='📄',
            font=('Segoe UI Emoji', 64),
            text_color=COLORS['primary']
        ).pack(pady=(32, 8))

        ctk.CTkLabel(
            info_card, text='Document PDF Généré',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack()

        ctk.CTkLabel(
            info_card, text='Le document a été créé avec succès.',
            font=FONTS['body'],
            text_color=COLORS['text_secondary']
        ).pack(pady=(4, 16))

        # Infos fichier
        try:
            size_kb = os.path.getsize(self.pdf_path) / 1024
            size_str = f"{size_kb:.1f} Ko"
        except Exception:
            size_str = "N/A"

        details_frame = ctk.CTkFrame(info_card, fg_color=COLORS['bg_hover'], corner_radius=10)
        details_frame.pack(fill='x', padx=32, pady=(0, 16))

        for label, value in [
            ('📁 Fichier', os.path.basename(self.pdf_path)),
            ('📂 Dossier', os.path.dirname(self.pdf_path)),
            ('📏 Taille', size_str),
        ]:
            row = ctk.CTkFrame(details_frame, fg_color='transparent')
            row.pack(fill='x', padx=16, pady=4)
            ctk.CTkLabel(row, text=label, font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary'], width=100, anchor='w').pack(side='left')
            ctk.CTkLabel(row, text=value, font=FONTS['body'],
                         text_color=COLORS['text_primary'], wraplength=500, anchor='w').pack(side='left')

        ctk.CTkLabel(
            info_card,
            text='💡  Pour afficher l\'aperçu des pages, installez PyMuPDF : pip install pymupdf',
            font=FONTS['small'],
            text_color=COLORS['text_muted'],
            fg_color=COLORS['bg_hover'],
            corner_radius=6
        ).pack(fill='x', padx=32, pady=(0, 24))

        self.lbl_page.configure(text="📄  Aperçu non disponible (PyMuPDF requis)")

    def _show_error(self, msg: str):
        """Affiche un message d'erreur dans la zone de contenu."""
        for w in self.content_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.content_frame,
            text=f"⚠️  {msg}",
            font=FONTS['body'],
            text_color=COLORS['danger'],
            wraplength=600
        ).pack(expand=True, pady=40)

    def _telecharger(self):
        """Copie le PDF vers un emplacement choisi par l'utilisateur."""
        dest = filedialog.asksaveasfilename(
            title='Enregistrer le PDF sous…',
            defaultextension='.pdf',
            initialfile=os.path.basename(self.pdf_path),
            filetypes=[('PDF', '*.pdf'), ('Tous les fichiers', '*.*')],
            parent=self
        )
        if not dest:
            return
        try:
            shutil.copy2(self.pdf_path, dest)
            messagebox.showinfo(
                '✅  Téléchargement réussi',
                f'Le fichier a été enregistré :\n{dest}',
                parent=self
            )
        except Exception as e:
            messagebox.showerror('Erreur', f'Impossible d\'enregistrer :\n{e}', parent=self)

    def _imprimer(self):
        """Lance l'impression via le gestionnaire PDF du système."""
        if not os.path.exists(self.pdf_path):
            messagebox.showerror('Erreur', 'Fichier PDF introuvable.', parent=self)
            return
        try:
            if sys.platform == 'win32':
                os.startfile(self.pdf_path, 'print')
            elif sys.platform == 'darwin':
                subprocess.Popen(['lpr', self.pdf_path])
            else:
                subprocess.Popen(['lp', self.pdf_path])
        except Exception as e:
            # Fallback : ouvrir le fichier pour impression manuelle
            try:
                os.startfile(self.pdf_path)
            except Exception:
                messagebox.showerror('Erreur Impression',
                                     f'Impossible d\'imprimer :\n{e}', parent=self)


def ouvrir_pdf_viewer(parent, pdf_path: str, title: str = "Bon PDF"):
    """
    Ouvre le visualiseur PDF intégré au lieu d'os.startfile().
    Retourne l'instance de PDFViewerModal.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        messagebox.showwarning('PDF introuvable',
                               f'Le fichier PDF est introuvable :\n{pdf_path}',
                               parent=parent)
        return None
    viewer = PDFViewerModal(parent, pdf_path, title)
    return viewer
