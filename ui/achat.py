"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/achat.py
Module Bon de Commande (BC) : saisie des articles à commander + génération PDF.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os

from ui.theme import COLORS, FONTS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_secondary_button, make_danger_button,
                         make_input, make_combobox, SeparatorLine, BadgeLabel)
import database.db_manager as db
from services.pdf_generator import generer_bon_commande_pdf
from services.config_manager import get_config
from ui.pdf_viewer import ouvrir_pdf_viewer


class AchatFrame(ctk.CTkFrame):
    """Module Bon de Commande — saisie et génération PDF."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._articles: list[dict] = []
        self._search_timer = None
        self._editing_index = None
        self._build_ui()

    def refresh(self):
        # Proposer un nouveau numéro de BC et mettre à jour la liste des fournisseurs
        try:
            self.var_num_bc.set(db.get_num_document('COMMANDE'))
        except Exception:
            pass
        self._update_fournisseurs_list()

    def _update_fournisseurs_list(self):
        """Recharge dynamiquement tous les fournisseurs créés dans le menu déroulant."""
        try:
            fournisseurs = db.get_all_fournisseurs()
            noms = [f['nom'] for f in fournisseurs if f.get('nom')]
            if hasattr(self, 'cb_fournisseur'):
                self.cb_fournisseur.configure(values=noms if noms else ['Aucun fournisseur'])
                if noms and not self.var_fournisseur.get():
                    self.var_fournisseur.set(noms[0])
        except Exception:
            pass

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text='🛒  Bon de Commande — Achat',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        self.badge_articles = BadgeLabel(header, '0 article(s)', color=COLORS['primary'])
        self.badge_articles.pack(side='left', padx=14, pady=(4, 0))

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Corps : 2 colonnes ───────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=24, pady=12)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        # ── Panneau gauche : Formulaire ajout d'article ──────────────────────
        left_outer = ctk.CTkFrame(
            body, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        left_outer.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        ctk.CTkLabel(
            left_outer, text='➕  Ajouter un Article',
            font=FONTS['subtitle'],
            text_color=COLORS['primary']
        ).pack(anchor='w', padx=16, pady=(16, 4))

        SeparatorLine(left_outer).pack(fill='x', padx=16, pady=(0, 8))

        # Zone défilante pour le formulaire
        left = ctk.CTkScrollableFrame(
            left_outer, fg_color='transparent',
            scrollbar_button_color=COLORS['primary'],
            scrollbar_button_hover_color=COLORS['primary_dark']
        )
        left.pack(fill='both', expand=True, padx=0, pady=(0, 8))

        # ─ En-tête du BC ─────────────────────────────────────────────────
        doc_frame = ctk.CTkFrame(left, fg_color=COLORS['bg_hover'], corner_radius=10)
        doc_frame.pack(fill='x', padx=16, pady=(4, 14))

        self._lbl(doc_frame, '🔢  N° Bon de Commande')
        self.var_num_bc = tk.StringVar()
        try:
            self.var_num_bc.set(db.get_num_document('COMMANDE'))
        except Exception:
            self.var_num_bc.set('BC-001')

        self.e_num_bc = make_input(doc_frame, placeholder='BC-001', textvariable=self.var_num_bc)
        self.e_num_bc.pack(fill='x', padx=12, pady=(0, 8))

        self._lbl(doc_frame, '🏭  Fournisseur / Société *')
        self.var_fournisseur = tk.StringVar()
        self.cb_fournisseur = make_combobox(doc_frame, values=[], variable=self.var_fournisseur, width=280)
        self.cb_fournisseur.pack(fill='x', padx=12, pady=(0, 12))
        self._update_fournisseurs_list()

        # ─ Article ───────────────────────────────────────────────────────
        self._lbl(left, '🏷️  Référence de la pièce')
        f_ref = ctk.CTkFrame(left, fg_color='transparent')
        f_ref.pack(fill='x', padx=16, pady=(0, 10))

        self.var_ref = tk.StringVar()
        self.e_ref = ctk.CTkEntry(
            f_ref,
            textvariable=self.var_ref,
            placeholder_text='Ex: REF-8820',
            fg_color=COLORS['bg_input'],
            border_color=COLORS['primary'],
            border_width=2,
            text_color=COLORS['text_primary'],
            font=FONTS['body_bold'],
            corner_radius=10,
            height=42
        )
        self.e_ref.pack(side='left', fill='x', expand=True, padx=(0, 6))

        self._lbl(left, '📝  Désignation de la pièce *')
        self.var_design = tk.StringVar()
        self.e_design = make_input(
            left,
            placeholder='Désignation libre de la pièce à commander...',
            textvariable=self.var_design
        )
        self.e_design.pack(fill='x', padx=16, pady=(0, 10))

        self._lbl(left, '🔢  Quantité à Commander')
        self.var_qte = tk.StringVar(value='1')
        self.e_qte = make_input(left, placeholder='1', textvariable=self.var_qte)
        self.e_qte.pack(fill='x', padx=16, pady=(0, 10))

        self._lbl(left, '📦  Unité')
        self.var_unite = tk.StringVar(value='Unité')
        from ui.theme import UNITES
        self.cb_unite = make_combobox(left, UNITES, variable=self.var_unite)
        self.cb_unite.pack(fill='x', padx=16, pady=(0, 10))

        self._lbl(left, '💬  Observation')
        self.e_obs = make_input(left, placeholder='Observation / Urgence...')
        self.e_obs.pack(fill='x', padx=16, pady=(0, 14))

        self.btn_ajouter = make_primary_button(
            left, 'Ajouter à la Commande', command=self._ajouter_article,
            icon='➕', width=240
        )
        self.btn_ajouter.pack(fill='x', padx=16, pady=(0, 8))

        make_secondary_button(
            left, '🔄 Réinitialiser', command=self._reset_form, width=200
        ).pack(padx=16, pady=(0, 16))

        # ── Panneau droit : Tableau de la commande ────────────────────────────
        right = ctk.CTkFrame(
            body, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))

        right_header = ctk.CTkFrame(right, fg_color='transparent')
        right_header.pack(fill='x', padx=16, pady=(12, 8))

        ctk.CTkLabel(
            right_header, text='📋  Articles de la Commande',
            font=FONTS['subtitle'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        # Bandeau total
        self.lbl_total = ctk.CTkLabel(
            right_header, text='Total : 0 article(s)',
            font=FONTS['body_bold'],
            text_color=COLORS['text_secondary']
        )
        self.lbl_total.pack(side='right')

        SeparatorLine(right).pack(fill='x', padx=16)

        tv_frame = ctk.CTkFrame(right, fg_color='transparent')
        tv_frame.pack(fill='both', expand=True, padx=8, pady=8)

        self.tv = StyledTreeview(
            tv_frame,
            columns=['num', 'ref', 'designation', 'qte', 'unite', 'obs'],
            headings=['N°', 'Référence', 'Désignation', 'Qté', 'Unité', 'Observation'],
            col_widths=[40, 120, 220, 70, 70, 130]
        )
        self.tv.pack(side='left', fill='both', expand=True)
        self.tv.bind('<Double-1>', lambda e: self._editer_ligne())
        add_scrollbar(tv_frame, self.tv)

        # ── Barre d'actions commande ──────────────────────────────────────────
        actions = ctk.CTkFrame(right, fg_color='transparent')
        actions.pack(fill='x', padx=16, pady=(0, 14))

        make_danger_button(
            actions, '🗑️ Supprimer Ligne', command=self._supprimer_ligne, width=170
        ).pack(side='left')

        make_secondary_button(
            actions, '✏️ Modifier Ligne', command=self._editer_ligne, width=160
        ).pack(side='left', padx=4)

        make_secondary_button(
            actions, '🗑️ Vider Tout', command=self._vider_commande, width=140
        ).pack(side='left', padx=4)

        # Bouton principal — générer PDF
        btn_pdf = ctk.CTkButton(
            actions,
            text='📄  Générer Bon de Commande PDF',
            command=self._generer_bon_commande,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color=COLORS['text_white'],
            font=FONTS['body_bold'],
            corner_radius=10,
            height=44,
            width=280
        )
        btn_pdf.pack(side='right')

    def _lbl(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text,
            font=FONTS['body_bold'],
            text_color=COLORS['text_secondary']
        ).pack(anchor='w', padx=16, pady=(0, 2))

    # ── Bon de Commande autonome (aucune liaison avec le stock) ────────────────

    # ── Actions ────────────────────────────────────────────────────────────────
    def _editer_ligne(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner une ligne à modifier.', parent=self)
            return
        try:
            idx = int(sel[0])
        except (ValueError, IndexError):
            return
        if 0 <= idx < len(self._articles):
            self._editing_index = idx
            art = self._articles[idx]
            self.var_ref.set(art.get('reference', ''))
            self.var_design.set(art.get('designation', ''))
            self.var_qte.set(str(art.get('quantite', 1)))
            self.var_unite.set(art.get('unite', 'Unité'))
            self.e_obs.delete(0, 'end')
            self.e_obs.insert(0, art.get('observation', ''))
            if hasattr(self, 'btn_ajouter'):
                self.btn_ajouter.configure(text='💾 Mettre à jour')

    def _ajouter_article(self):
        ref    = self.var_ref.get().strip()
        design = self.var_design.get().strip()
        obs    = self.e_obs.get().strip()
        unite  = self.var_unite.get()

        if not ref:
            messagebox.showerror('Erreur', 'La référence est obligatoire.', parent=self)
            return
        if not design:
            messagebox.showerror('Erreur', 'La désignation est obligatoire.', parent=self)
            return

        try:
            qte = int(self.var_qte.get().strip())
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Erreur', 'Quantité invalide (entier > 0 requis).', parent=self)
            return

        # Vérifier si l'article est déjà présent dans la commande (éviter les doublons involontaires)
        for i, a in enumerate(self._articles):
            if i != self._editing_index and a.get('reference', '').strip().upper() == ref.upper():
                messagebox.showwarning(
                    'Article déjà présent',
                    f"L'article avec la référence '{ref}' est déjà dans la commande (ligne {i+1}).\n"
                    f"Modifiez directement la ligne existante ou ajustez sa quantité.",
                    parent=self
                )
                return

        item = {
            'reference': ref,
            'designation': design,
            'quantite': qte,
            'unite': unite,
            'observation': obs,
        }

        if self._editing_index is not None and 0 <= self._editing_index < len(self._articles):
            self._articles[self._editing_index] = item
            self._editing_index = None
        else:
            self._articles.append(item)

        self._refresh_table()
        self._reset_article_fields()

    def _supprimer_ligne(self):
        sel = self.tv.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._articles):
            self._articles.pop(idx)
            self._editing_index = None
            if hasattr(self, 'btn_ajouter'):
                self.btn_ajouter.configure(text='Ajouter à la Commande')
            self._refresh_table()

    def _vider_commande(self):
        if self._articles:
            if messagebox.askyesno('Vider', 'Vider toute la commande ?', parent=self):
                self._articles.clear()
                self._editing_index = None
                if hasattr(self, 'btn_ajouter'):
                    self.btn_ajouter.configure(text='Ajouter à la Commande')
                self._refresh_table()

    def _refresh_table(self):
        for item in self.tv.get_children():
            self.tv.delete(item)

        for i, art in enumerate(self._articles):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tv.insert('', 'end', iid=str(i), values=(
                str(i + 1),
                art['reference'],
                art['designation'],
                str(art['quantite']),
                art['unite'],
                art.get('observation', '')
            ), tags=(tag,))
        self.tv.autofit_columns()

        nb = len(self._articles)
        total_qte = sum(a['quantite'] for a in self._articles)
        self.badge_articles.configure(text=f'{nb} article(s)')
        self.lbl_total.configure(text=f'Total : {nb} article(s)  |  {total_qte} unités')

    def _reset_article_fields(self):
        self._editing_index = None
        self.var_ref.set('')
        self.var_design.set('')
        self.var_qte.set('1')
        self.e_obs.delete(0, 'end')
        if hasattr(self, 'btn_ajouter'):
            self.btn_ajouter.configure(text='Ajouter à la Commande')
        self.e_ref.focus()

    def _reset_form(self):
        self._articles.clear()
        self._refresh_table()
        self._reset_article_fields()
        self._update_fournisseurs_list()
        try:
            self.var_num_bc.set(db.get_num_document('COMMANDE'))
        except Exception:
            pass

    def _generer_bon_commande(self):
        if not self._articles:
            messagebox.showerror('Erreur', 'Ajoutez au moins un article avant de générer le bon.', parent=self)
            return

        num_bc     = self.var_num_bc.get().strip() or 'BC-001'
        fournisseur= self.var_fournisseur.get().strip()

        if not fournisseur or fournisseur == 'Aucun fournisseur':
            messagebox.showerror('Erreur Obligatoire', 'Le champ Fournisseur / Société est obligatoire pour générer le Bon de Commande.', parent=self)
            self.cb_fournisseur.focus()
            return

        pdf_dir = get_config('pdf_directory', '')
        chemin_pdf = ''
        try:
            chemin_pdf = generer_bon_commande_pdf(
                num_bc=num_bc,
                fournisseur=fournisseur,
                articles=self._articles,
                motif='',
                pdf_dir=pdf_dir or None
            )
        except Exception as e:
            messagebox.showerror('Erreur PDF', f'Erreur lors de la génération :\n{e}', parent=self)
            return

        try:
            db.enregistrer_bon_commande(
                num_bc=num_bc,
                fournisseur=fournisseur,
                articles=self._articles,
                chemin_pdf=chemin_pdf
            )
        except Exception as e:
            messagebox.showerror('Erreur Base de Données', f'Erreur lors de l\'enregistrement de la commande :\n{e}', parent=self)
            return

        msg = f'✅ Bon de Commande {num_bc} généré avec succès ! ({len(self._articles)} article(s))'
        show_it = messagebox.askyesno('PDF Généré', msg + '\n\nAfficher le PDF ?', parent=self)
        if show_it and os.path.exists(chemin_pdf):
            ouvrir_pdf_viewer(self, chemin_pdf, title=f'Bon de Commande {num_bc}')

        self._reset_form()
