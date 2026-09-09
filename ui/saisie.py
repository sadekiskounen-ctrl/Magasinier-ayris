"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/saisie.py
Écran de saisie des Mouvements (Sortie, Réception Multi-Lignes, Retour Magasin) avec Références et Sélection Lignes/Machines.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os

from ui.theme import COLORS, FONTS, SERVICES, LIGNES, get_machines_pour_lignes
from ui.widgets import (make_primary_button, make_success_button, make_secondary_button,
                         make_input, make_combobox, SeparatorLine, make_label,
                         make_danger_button, StyledTreeview, add_scrollbar, BadgeLabel,
                         MultiSelectLignesWidget, AutocompleteDesignationInput)
import database.db_manager as db
from services.pdf_generator import generer_bon_pdf
from services.config_manager import get_config
from ui.pdf_viewer import ouvrir_pdf_viewer


class SaisieFrame(ctk.CTkFrame):
    """Écran de saisie multi-lignes pour Bons de Sortie, Réception, et Retour."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._mode = 'SORTIE'  # 'SORTIE', 'ENTREE', 'RETOUR'
        self._produit_actuel = None
        self._articles_list = []
        self._search_timer = None
        self._editing_index = None

        self._build_ui()
        self._set_focus_ref()

    def refresh(self):
        self._update_fournisseurs_list()

    def _update_fournisseurs_list(self):
        """Recharge dynamiquement la liste des fournisseurs dans le menu déroulant."""
        try:
            fournisseurs = db.get_all_fournisseurs()
            noms = [f['nom'] for f in fournisseurs if f.get('nom')]
            if hasattr(self, 'cb_fournisseur_br'):
                self.cb_fournisseur_br.configure(values=noms if noms else ['Aucun fournisseur'])
                if noms and not self.var_fournisseur_br.get():
                    self.var_fournisseur_br.set(noms[0])
        except Exception:
            pass

    def _build_ui(self):
        # ── En-tête avec mode switcher ─────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text='🔄  Saisie Mouvements & Bons Multi-Produits',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        mode_frame = ctk.CTkFrame(
            header, fg_color=COLORS['bg_card'],
            corner_radius=10, border_width=1,
            border_color=COLORS['border']
        )
        mode_frame.pack(side='left', padx=20)

        self.btn_mode_sortie = ctk.CTkButton(
            mode_frame, text='📤  Bon de Sortie',
            command=lambda: self._set_mode('SORTIE'),
            fg_color=COLORS['danger'],
            hover_color='#DC2626',
            text_color='white',
            font=FONTS['body_bold'],
            corner_radius=8,
            height=40, width=170
        )
        self.btn_mode_sortie.pack(side='left', padx=3, pady=3)

        self.btn_mode_entree = ctk.CTkButton(
            mode_frame, text='📥  Bon de Réception',
            command=lambda: self._set_mode('ENTREE'),
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['bg_selected'],
            text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'],
            corner_radius=8,
            height=40, width=190
        )
        self.btn_mode_entree.pack(side='left', padx=3, pady=3)

        self.btn_mode_retour = ctk.CTkButton(
            mode_frame, text='↩️  Bon de Retour',
            command=lambda: self._set_mode('RETOUR'),
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['bg_selected'],
            text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'],
            corner_radius=8,
            height=40, width=170
        )
        self.btn_mode_retour.pack(side='left', padx=3, pady=3)

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Zone de contenu ──
        self.body = ctk.CTkFrame(self, fg_color='transparent')
        self.body.pack(fill='both', expand=True, padx=24, pady=12)

        self._render_mode_ui()

    def _set_mode(self, mode: str):
        self._mode = mode
        self._editing_index = None
        active_color_map = {
            'SORTIE': COLORS['danger'],
            'ENTREE': COLORS['success'],
            'RETOUR': COLORS['warning']
        }
        for m, btn in [('SORTIE', self.btn_mode_sortie), ('ENTREE', self.btn_mode_entree), ('RETOUR', self.btn_mode_retour)]:
            if m == mode:
                btn.configure(fg_color=active_color_map[m], text_color='white')
            else:
                btn.configure(fg_color=COLORS['bg_hover'], text_color=COLORS['text_secondary'])

        self._produit_actuel = None
        self._articles_list = []
        self._render_mode_ui()

    def _render_mode_ui(self):
        for w in self.body.winfo_children():
            w.destroy()

        self._build_ui_multi_ligne()
        self.after(100, self._set_focus_ref)

    # ── UI MULTI-LIGNES (SORTIE, ENTREE, RETOUR) ──────────────────────────────
    def _build_ui_multi_ligne(self):
        self.body.grid_columnconfigure(0, weight=3, minsize=450)
        self.body.grid_columnconfigure(1, weight=2, minsize=380)
        self.body.grid_rowconfigure(0, weight=1)

        # ── Panneau Gauche : Document Header + Tableau des articles ───────────
        doc_panel = ctk.CTkFrame(
            self.body, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        doc_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        if self._mode == 'SORTIE':
            title_text = '📤  BON DE SORTIE MULTI-PRODUITS'
            title_color = COLORS['danger']
        elif self._mode == 'ENTREE':
            title_text = '📥  BON DE RÉCEPTION MULTI-PRODUITS'
            title_color = COLORS['success']
        else:
            title_text = '↩️  BON DE RETOUR MULTI-PRODUITS'
            title_color = COLORS['warning']

        ctk.CTkLabel(
            doc_panel, text=title_text,
            font=FONTS['title'],
            text_color=title_color
        ).pack(pady=(16, 4), padx=16, anchor='w')
        SeparatorLine(doc_panel).pack(fill='x', padx=16, pady=(0, 12))

        # Cartouche En-tête du Document
        doc_header = ctk.CTkFrame(doc_panel, fg_color=COLORS['bg_hover'], corner_radius=10)
        doc_header.pack(fill='x', padx=16, pady=(0, 12))

        num_defaut = db.get_num_document(self._mode)
        self.var_num_doc = tk.StringVar(value=num_defaut)

        # N° Bon
        doc_label_map = {'SORTIE': 'N° Bon de Sortie :', 'ENTREE': 'N° Bon de Réception :', 'RETOUR': 'N° Bon de Retour :'}
        ctk.CTkLabel(doc_header, text=doc_label_map[self._mode], font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary']).grid(row=0, column=0, padx=12, pady=8, sticky='w')
        self.e_num_doc = make_input(doc_header, placeholder='N° Bon', width=170, textvariable=self.var_num_doc)
        self.e_num_doc.grid(row=0, column=1, padx=6, pady=8, sticky='w')

        # Mode-specific header fields
        if self._mode == 'ENTREE':
            ctk.CTkLabel(doc_header, text='Fournisseur * :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=0, column=2, padx=12, pady=8, sticky='w')
            self.var_fournisseur_br = tk.StringVar()
            self.cb_fournisseur_br = make_combobox(doc_header, values=[], width=220, variable=self.var_fournisseur_br)
            self.cb_fournisseur_br.grid(row=0, column=3, padx=6, pady=8, sticky='ew')
            self._update_fournisseurs_list()

            ctk.CTkLabel(doc_header, text='Motif / Remarque :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=1, column=0, padx=12, pady=8, sticky='w')
            self.var_motif = tk.StringVar()
            self.e_motif = make_input(doc_header, placeholder='Motif (optionnel)...', textvariable=self.var_motif)
            self.e_motif.grid(row=1, column=1, columnspan=3, padx=6, pady=8, sticky='ew')

        elif self._mode == 'SORTIE':
            ctk.CTkLabel(doc_header, text='Service Bénéficiaire * :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=0, column=2, padx=12, pady=8, sticky='w')
            self.var_service = tk.StringVar(value='Production')
            self.cb_service = make_combobox(doc_header, SERVICES, variable=self.var_service, width=220)
            self.cb_service.grid(row=0, column=3, padx=6, pady=8, sticky='ew')

            ctk.CTkLabel(doc_header, text='Nom Demandeur * :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=1, column=0, padx=12, pady=8, sticky='w')
            self.var_demandeur = tk.StringVar()
            self.e_demandeur = make_input(doc_header, placeholder='Nom du demandeur...', textvariable=self.var_demandeur, width=170)
            self.e_demandeur.grid(row=1, column=1, padx=6, pady=8, sticky='w')

            ctk.CTkLabel(doc_header, text='Motif / Raison :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=1, column=2, padx=12, pady=8, sticky='w')
            self.var_motif = tk.StringVar()
            self.e_motif = make_input(doc_header, placeholder='Motif...', textvariable=self.var_motif)
            self.e_motif.grid(row=1, column=3, padx=6, pady=8, sticky='ew')

        else:  # RETOUR
            ctk.CTkLabel(doc_header, text='Service Remettant * :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=0, column=2, padx=12, pady=8, sticky='w')
            self.var_service = tk.StringVar(value='Production')
            self.cb_service = make_combobox(doc_header, SERVICES, variable=self.var_service, width=220)
            self.cb_service.grid(row=0, column=3, padx=6, pady=8, sticky='ew')

            ctk.CTkLabel(doc_header, text='Retourné par * :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=1, column=0, padx=12, pady=8, sticky='w')
            self.var_retourne_par = tk.StringVar()
            self.e_retourne_par = make_input(doc_header, placeholder='Agent effectuant le retour...', textvariable=self.var_retourne_par, width=170)
            self.e_retourne_par.grid(row=1, column=1, padx=6, pady=8, sticky='w')

            ctk.CTkLabel(doc_header, text='Motif / Raison :', font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary']).grid(row=1, column=2, padx=12, pady=8, sticky='w')
            self.var_motif = tk.StringVar()
            self.e_motif = make_input(doc_header, placeholder='Motif du retour...', textvariable=self.var_motif)
            self.e_motif.grid(row=1, column=3, padx=6, pady=8, sticky='ew')

        doc_header.grid_columnconfigure(3, weight=1)

        # Tableau des articles
        tv_frame = ctk.CTkFrame(doc_panel, fg_color='transparent')
        tv_frame.pack(fill='both', expand=True, padx=16, pady=(0, 8))

        self.tv_articles = StyledTreeview(
            tv_frame,
            columns=['code', 'designation', 'qte', 'unite', 'ligne', 'machine'],
            headings=['Référence', 'Désignation', 'Qté', 'Unité', 'Ligne(s)', 'Machine'],
            col_widths=[130, 240, 90, 80, 160, 160],
            stretch_cols=True
        )
        self.tv_articles.pack(side='left', fill='both', expand=True)
        self.tv_articles.bind('<Double-1>', lambda e: self._editer_ligne())
        add_scrollbar(tv_frame, self.tv_articles)

        action_bar = ctk.CTkFrame(doc_panel, fg_color='transparent')
        action_bar.pack(fill='x', padx=16, pady=(0, 16))

        make_danger_button(action_bar, '🗑️ Supprimer Ligne', command=self._supprimer_ligne, width=170).pack(side='left')
        make_secondary_button(action_bar, '✏️ Modifier Ligne', command=self._editer_ligne, width=170).pack(side='left', padx=8)

        val_btn_bg = COLORS['danger'] if self._mode == 'SORTIE' else (COLORS['success'] if self._mode == 'ENTREE' else COLORS['warning'])
        val_btn_hover = '#DC2626' if self._mode == 'SORTIE' else ('#16A34A' if self._mode == 'ENTREE' else '#D97706')
        val_btn_text = f"✅ Valider {doc_label_map[self._mode][:6]} & Générer PDF"

        self.btn_valider = ctk.CTkButton(
            action_bar,
            text=val_btn_text,
            command=self._valider_bon_multi,
            fg_color=val_btn_bg,
            hover_color=val_btn_hover,
            text_color='white',
            font=FONTS['body_bold'],
            corner_radius=10,
            height=42,
            width=270
        )
        self.btn_valider.pack(side='right')

        # ── Panneau Droit : Formulaire Ajout Produit + Fiche Produit ──────────
        add_panel = ctk.CTkFrame(
            self.body, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        add_panel.grid(row=0, column=1, sticky='nsew', padx=(10, 0))

        scroll_add = ctk.CTkScrollableFrame(add_panel, fg_color='transparent', scrollbar_button_color=COLORS['primary'])
        scroll_add.pack(fill='both', expand=True, padx=8, pady=8)

        ctk.CTkLabel(
            scroll_add, text='➕  Ajouter un Produit au Bon',
            font=FONTS['subtitle'], text_color=COLORS['primary']
        ).pack(pady=(8, 4), padx=12, anchor='w')
        SeparatorLine(scroll_add).pack(fill='x', padx=12, pady=(0, 10))

        # Référence
        self._section_lbl(scroll_add, '🏷️  Référence (ou 4 derniers car.) *')
        self.var_ref = tk.StringVar()
        self.e_ref = ctk.CTkEntry(
            scroll_add,
            textvariable=self.var_ref,
            placeholder_text='Ex: REF-8820',
            fg_color=COLORS['bg_input'],
            border_color=COLORS['primary'],
            border_width=2,
            text_color=COLORS['text_primary'],
            font=FONTS['body_bold'],
            corner_radius=10,
            height=40
        )
        self.e_ref.pack(fill='x', padx=12, pady=(0, 8))
        self.var_ref.trace_add('write', self._on_ref_change)
        self.e_ref.bind('<Return>', self._on_ref_enter)

        # Dynamic reference status badge
        self.lbl_ref_status = ctk.CTkLabel(
            scroll_add,
            text='',
            font=FONTS['small_bold'],
            corner_radius=6,
            height=24
        )

        # Désignation avec Autocomplétion
        self._section_lbl(scroll_add, '📝  Désignation (Recherche auto) *')
        self.var_designation = tk.StringVar()
        self.e_designation_directe = AutocompleteDesignationInput(
            scroll_add,
            placeholder='Taper pour rechercher une pièce...',
            textvariable=self.var_designation,
            on_select=self._on_designation_autocomplete_select
        )
        self.e_designation_directe.pack(fill='x', padx=12, pady=(0, 8))

        # Quantité
        qte_label_text = '🔢  Quantité Reçue *' if self._mode == 'ENTREE' else ('🔢  Quantité Sortie *' if self._mode == 'SORTIE' else '🔢  Quantité Retournée *')
        self._section_lbl(scroll_add, qte_label_text)
        self.var_qte = tk.StringVar(value='1')
        self.var_qte.trace_add('write', lambda *_: self._update_ref_status())
        self.e_qte = make_input(scroll_add, placeholder='1', textvariable=self.var_qte)
        self.e_qte.pack(fill='x', padx=12, pady=(0, 8))

        # Unité (Menu déroulant)
        self._section_lbl(scroll_add, '📦  Unité *')
        self.var_unite = tk.StringVar(value='Unité')
        from ui.theme import UNITES
        self.cb_unite = make_combobox(scroll_add, UNITES, variable=self.var_unite)
        self.cb_unite.pack(fill='x', padx=12, pady=(0, 8))

        # Utilité / Ligne(s)
        self._section_lbl(scroll_add, '🏭  Utilité / Ligne(s) *')
        self.widget_lignes = MultiSelectLignesWidget(
            scroll_add,
            options=LIGNES,
            default_selected=['KHS1'],
            on_change=self._on_lignes_changed
        )
        self.widget_lignes.pack(fill='x', padx=12, pady=(0, 8))

        # Type Machine
        self._section_lbl(scroll_add, '⚙️  Nom de la Machine *')
        self.var_machine = tk.StringVar(value='Blomax')
        self.cb_machine = make_combobox(
            scroll_add,
            get_machines_pour_lignes(['KHS1']),
            variable=self.var_machine
        )
        self.cb_machine.pack(fill='x', padx=12, pady=(0, 12))

        self.btn_ajouter_ligne = make_primary_button(
            scroll_add, '➕ Ajouter à la Liste', command=self._ajouter_ligne,
            icon='', width=240
        )
        self.btn_ajouter_ligne.pack(fill='x', padx=12, pady=(4, 12))

        self.fiche_panel = ctk.CTkFrame(scroll_add, fg_color='transparent')
        self.fiche_panel.pack(fill='both', expand=True, padx=4, pady=(0, 4))
        self._build_fiche_vide()

    def _on_lignes_changed(self, selected_lignes: list):
        """Met à jour les machines selon les lignes sélectionnées."""
        machines = get_machines_pour_lignes(selected_lignes)
        self.cb_machine.configure(values=machines)
        current = self.var_machine.get()
        if current not in machines:
            self.var_machine.set(machines[0])

    def _section_lbl(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text,
            font=FONTS['body_bold'],
            text_color=COLORS['text_secondary'],
            wraplength=340,
            justify='left'
        ).pack(anchor='w', padx=12, pady=(0, 2))

    # ── LOGIQUE DE RECHERCHE & Saisie ──
    def _on_designation_autocomplete_select(self, produit: dict):
        """Quand une pièce est choisie via l'autocomplétion de désignation."""
        if not produit:
            return
        code = produit.get('code_barres', '')
        if code:
            self.var_ref.set(code)
            self._lookup_product(code)

    def _set_focus_ref(self):
        try:
            self.e_ref.focus()
        except Exception:
            pass

    def _on_ref_change(self, *_):
        if hasattr(self, '_search_timer') and self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None

        code = self.var_ref.get().strip()
        self._update_ref_status()
        if len(code) >= 4:
            self._search_timer = self.after(250, lambda: self._do_debounced_lookup(code))

    def _do_debounced_lookup(self, code: str):
        self._search_timer = None
        self._lookup_product(code)

    def _on_ref_enter(self, event):
        if hasattr(self, '_search_timer') and self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None
        code = self.var_ref.get().strip()
        if code:
            self._lookup_product(code)

    def _update_ref_status(self):
        """Mets à jour l'indicateur visuel dynamique sous la référence (doublon bon, produit existant ou nouveau)."""
        if not hasattr(self, 'lbl_ref_status'):
            return

        ref = self.var_ref.get().strip()
        if not ref:
            self.lbl_ref_status.pack_forget()
            return

        # 1. Vérification si la référence est déjà dans la liste du bon en cours
        in_current_list = any(
            art.get('reference', '').strip().upper() == ref.upper()
            for idx, art in enumerate(self._articles_list)
            if idx != self._editing_index
        )

        if in_current_list:
            self.lbl_ref_status.configure(
                text=' ⚠️ Référence déjà présente dans ce bon ! ',
                fg_color='#7F1D1D',
                text_color='#FCA5A5'
            )
            self.lbl_ref_status.pack(fill='x', padx=12, pady=(0, 6), before=self.e_designation_directe)
            return

        # 2. Vérification si la référence existe déjà en base de données
        produit_db = db.find_produit_by_ref_or_last4(ref)
        if produit_db and produit_db.get('code_barres', '').strip().upper() == ref.upper():
            qte_stock = produit_db.get('quantite_stock', 0)
            unite_str = produit_db.get('unite', 'Unité')
            if self._mode == 'ENTREE':
                try:
                    q_input = int(self.var_qte.get().strip())
                    if q_input <= 0: q_input = 0
                except (ValueError, AttributeError):
                    q_input = 1
                new_total = qte_stock + q_input
                self.lbl_ref_status.configure(
                    text=f' ℹ️ Pièce EXISTANTE — Stock : {qte_stock} ➔ Nouveau stock après réception : {new_total} {unite_str} ',
                    fg_color='#14532D',
                    text_color='#86EFAC'
                )
            else:
                self.lbl_ref_status.configure(
                    text=f' ℹ️ Pièce EXISTANTE en base (Stock actuel : {qte_stock} {unite_str}) ',
                    fg_color='#14532D',
                    text_color='#86EFAC'
                )
            self.lbl_ref_status.pack(fill='x', padx=12, pady=(0, 6), before=self.e_designation_directe)
        elif self._mode == 'ENTREE' and len(ref) >= 2:
            self.lbl_ref_status.configure(
                text=' 🆕 NOUVELLE Pièce (Sera créée dans le système lors de la réception) ',
                fg_color='#1E3A8A',
                text_color='#93C5FD'
            )
            self.lbl_ref_status.pack(fill='x', padx=12, pady=(0, 6), before=self.e_designation_directe)
        else:
            self.lbl_ref_status.pack_forget()

    def _lookup_product(self, code: str):
        produit = db.find_produit_by_ref_or_last4(code)
        if produit:
            if self.var_ref.get().strip() != produit['code_barres']:
                self.var_ref.set(produit['code_barres'])

            self._produit_actuel = produit
            self._build_fiche_produit(produit)

            self.var_designation.set(produit['designation'])
            if produit.get('unite') and hasattr(self, 'var_unite'):
                self.var_unite.set(produit['unite'])
            if hasattr(self, 'widget_lignes'):
                l_str = produit.get('utilite_ligne', 'KHS1')
                self.widget_lignes.set_selected([l.strip() for l in l_str.split(',')])
            if hasattr(self, 'var_machine'):
                m_str = produit.get('nom_machine', 'N/A')
                self.var_machine.set(m_str)
        else:
            self._produit_actuel = None
            self._build_fiche_vide()
        self._update_ref_status()

    def _build_fiche_vide(self):
        for w in self.fiche_panel.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.fiche_panel, text='🏷️',
            font=('Segoe UI Emoji', 36),
            text_color=COLORS['text_muted']
        ).pack(expand=True, pady=(12, 2))

        ctk.CTkLabel(
            self.fiche_panel, text='Saisir référence...',
            font=FONTS['body_bold'],
            text_color=COLORS['text_muted']
        ).pack()

    def _build_fiche_produit(self, produit: dict):
        for w in self.fiche_panel.winfo_children():
            w.destroy()

        fiche_header = ctk.CTkFrame(self.fiche_panel, fg_color=COLORS['bg_hover'], corner_radius=10)
        fiche_header.pack(fill='x', padx=8, pady=(4, 4))

        ctk.CTkLabel(
            fiche_header, text=produit['designation'],
            font=FONTS['body_bold'], text_color=COLORS['text_primary'],
            wraplength=280, justify='left'
        ).pack(anchor='w', padx=10, pady=(6, 2))

        ctk.CTkLabel(
            fiche_header, text=f"🏷️ Réf : {produit['code_barres']}",
            font=FONTS['mono'], text_color=COLORS['primary']
        ).pack(anchor='w', padx=10, pady=(0, 6))

        stock_val = produit.get('quantite_stock', 0)
        seuil = produit.get('seuil_alerte', 5)
        stock_color = COLORS['danger'] if stock_val <= seuil else COLORS['success']

        stock_info = ctk.CTkFrame(self.fiche_panel, fg_color=COLORS['bg_card'], corner_radius=8,
                                  border_width=1, border_color=COLORS['border'])
        stock_info.pack(fill='x', padx=8, pady=2)
        ctk.CTkLabel(stock_info, text=f"Stock Actuel : {stock_val} {produit.get('unite','')}",
                     font=FONTS['body_bold'], text_color=stock_color).pack(padx=10, pady=4)

    # ── GESTION DE LA LISTE MULTI-LIGNES ──
    def _editer_ligne(self):
        sel = self.tv_articles.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner une ligne à modifier dans le tableau.', parent=self)
            return
        try:
            idx = int(sel[0])
        except (ValueError, IndexError):
            return

        if 0 <= idx < len(self._articles_list):
            self._editing_index = idx
            item = self._articles_list[idx]

            self.var_ref.set(item.get('reference', ''))
            self.var_designation.set(item.get('designation', ''))
            self.var_qte.set(str(item.get('quantite', 1)))
            if hasattr(self, 'var_unite'):
                self.var_unite.set(item.get('unite', 'Unité'))

            if hasattr(self, 'widget_lignes'):
                l_str = item.get('utilite_ligne', 'KHS1')
                self.widget_lignes.set_selected([l.strip() for l in l_str.split(',') if l.strip()])
            if hasattr(self, 'var_machine'):
                self.var_machine.set(item.get('nom_machine', 'N/A'))

            # Fiche produit si disponible
            self._lookup_product(item.get('reference', ''))

            if hasattr(self, 'btn_ajouter_ligne'):
                self.btn_ajouter_ligne.configure(text='💾 Mettre à jour la Ligne')

    def _ajouter_ligne(self):
        reference = self.var_ref.get().strip()
        designation = self.var_designation.get().strip()
        unite = self.var_unite.get() if hasattr(self, 'var_unite') else 'Unité'
        selected_lignes = self.widget_lignes.get_selected()
        lignes_str = ", ".join(selected_lignes)
        machine = self.var_machine.get()

        if not reference:
            messagebox.showerror('Erreur', 'La référence est obligatoire.', parent=self)
            return
        if not designation:
            messagebox.showerror('Erreur', 'La désignation est obligatoire.', parent=self)
            return

        try:
            qte = int(self.var_qte.get().strip())
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Erreur', 'La quantité doit être un entier positif.', parent=self)
            return

        # ── Contrôle Anti-Doublon dans le Bon en cours ────────────────────────
        for idx, art in enumerate(self._articles_list):
            if idx != self._editing_index and art.get('reference', '').strip().upper() == reference.upper():
                doc_name = 'Bon de Réception' if self._mode == 'ENTREE' else ('Bon de Sortie' if self._mode == 'SORTIE' else 'Bon de Retour')
                messagebox.showwarning(
                    'Doublon Détecté',
                    f'La référence "{reference}" est déjà présente dans la liste de ce {doc_name} !\n\n'
                    'Veuillez modifier la ligne existante dans le tableau pour ajuster sa quantité.',
                    parent=self
                )
                return

        # Tenter d'associer automatiquement au produit existant en base si non fait
        if not self._produit_actuel:
            self._produit_actuel = db.find_produit_by_ref_or_last4(reference)

        # Contrôle de stock strict pour la Sortie (Bon de Sortie)
        if self._mode == 'SORTIE':
            if not self._produit_actuel:
                messagebox.showerror('Erreur Stock', 'Cet article n\'est pas disponible en stock.', parent=self)
                return

            stock_actuel = self._produit_actuel.get('quantite_stock', 0)
            if stock_actuel <= 0 or qte > stock_actuel:
                messagebox.showerror(
                    'Erreur Stock',
                    f'Cet article n\'est pas disponible en stock.\n(Stock actuel disponible : {stock_actuel})',
                    parent=self
                )
                return

        pid = self._produit_actuel['id'] if self._produit_actuel else None

        item = {
            'produit_id': pid,
            'reference': reference,
            'code_barres': reference,
            'designation': designation,
            'emplacement': self._produit_actuel.get('emplacement', '') if self._produit_actuel else '',
            'unite': unite,
            'quantite': qte,
            'utilite_ligne': lignes_str,
            'nom_machine': machine,
        }

        if self._editing_index is not None and 0 <= self._editing_index < len(self._articles_list):
            self._articles_list[self._editing_index] = item
            self._editing_index = None
        else:
            self._articles_list.append(item)

        self._refresh_tv_articles()
        self._reset_add_form()

    def _reset_add_form(self):
        self._editing_index = None
        self.var_ref.set('')
        self.var_designation.set('')
        self.var_qte.set('1')
        if hasattr(self, 'var_unite'):
            self.var_unite.set('Unité')
        self._produit_actuel = None
        self._build_fiche_vide()
        if hasattr(self, 'btn_ajouter_ligne'):
            self.btn_ajouter_ligne.configure(text='➕ Ajouter à la Liste')
        self._update_ref_status()
        self._set_focus_ref()

    def _supprimer_ligne(self):
        sel = self.tv_articles.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._articles_list):
            self._articles_list.pop(idx)
            self._editing_index = None
            if hasattr(self, 'btn_ajouter_ligne'):
                self.btn_ajouter_ligne.configure(text='➕ Ajouter à la Liste')
            self._refresh_tv_articles()

    def _refresh_tv_articles(self):
        for item in self.tv_articles.get_children():
            self.tv_articles.delete(item)

        for i, art in enumerate(self._articles_list):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tv_articles.insert('', 'end', iid=str(i), values=(
                art['reference'],
                art['designation'],
                str(art['quantite']),
                art['unite'],
                art.get('utilite_ligne', 'KHS1'),
                art.get('nom_machine', 'N/A')
            ), tags=(tag,))
        self.tv_articles.autofit_columns()

    # ── VALIDATION DU DOCUMENT ET GÉNÉRATION PDF ──
    def _valider_bon_multi(self):
        if not self._articles_list:
            doc_label = 'Bon de Sortie' if self._mode == 'SORTIE' else ('Bon de Réception' if self._mode == 'ENTREE' else 'Bon de Retour')
            messagebox.showerror('Erreur', f'Aucun produit dans le {doc_label}.', parent=self)
            return

        num_doc = self.var_num_doc.get().strip() or db.get_num_document(self._mode)

        fournisseur = ""
        service = ""
        demandeur = ""
        retourne_par = ""

        if self._mode == 'ENTREE':
            fournisseur = self.var_fournisseur_br.get().strip() if hasattr(self, 'var_fournisseur_br') else ''
            if not fournisseur or fournisseur == 'Aucun fournisseur':
                messagebox.showerror('Erreur Obligatoire', 'Le nom du Fournisseur / Livreur est obligatoire pour valider le Bon de Réception.', parent=self)
                if hasattr(self, 'cb_fournisseur_br'):
                    self.cb_fournisseur_br.focus()
                return
            service = fournisseur
        elif self._mode == 'SORTIE':
            service = self.var_service.get() if hasattr(self, 'var_service') else 'Production'
            demandeur = self.var_demandeur.get().strip() if hasattr(self, 'var_demandeur') else ''
            if not demandeur:
                messagebox.showerror('Erreur Obligatoire', 'Le Nom du Demandeur est obligatoire pour valider le Bon de Sortie.', parent=self)
                if hasattr(self, 'e_demandeur'):
                    self.e_demandeur.focus()
                return
        else:  # RETOUR
            service = self.var_service.get() if hasattr(self, 'var_service') else 'Production'
            retourne_par = self.var_retourne_par.get().strip() if hasattr(self, 'var_retourne_par') else ''
            if not retourne_par:
                messagebox.showerror('Erreur Obligatoire', 'Le champ "Retourné par" est obligatoire pour valider le Bon de Retour.', parent=self)
                if hasattr(self, 'e_retourne_par'):
                    self.e_retourne_par.focus()
                return

        motif = self.var_motif.get().strip() if hasattr(self, 'var_motif') else ''

        pdf_dir = get_config('pdf_directory', '')
        chemin_pdf = ''
        try:
            chemin_pdf = generer_bon_pdf(
                type_mvt=self._mode,
                num_doc=num_doc,
                beneficiaire=service,
                fournisseur=fournisseur,
                motif=motif,
                articles=self._articles_list,
                pdf_dir=pdf_dir or None,
                demandeur=demandeur,
                retourne_par=retourne_par
            )
        except Exception as e:
            messagebox.showerror('Erreur PDF', f'Erreur lors de la génération du PDF :\n{e}', parent=self)

        try:
            mvt_ids = db.enregistrer_mouvements_multiples(
                articles=self._articles_list,
                type_mvt=self._mode,
                beneficiaire=service,
                motif=motif,
                chemin_pdf=chemin_pdf,
                demandeur=demandeur,
                retourne_par=retourne_par,
                fournisseur_nom=fournisseur
            )
        except Exception as e:
            messagebox.showerror('Erreur Enregistrement', f'Erreur lors de l\'enregistrement en base de données :\n{e}', parent=self)
            return

        doc_title_map = {'SORTIE': 'Bon de Sortie', 'ENTREE': 'Bon de Réception', 'RETOUR': 'Bon de Retour'}
        doc_title = doc_title_map[self._mode]

        msg = f'{doc_title} {num_doc} enregistré avec {len(self._articles_list)} produit(s) !'
        show_pdf = messagebox.askyesno('✅ Document Enregistré',
                                       msg + '\n\nVoulez-vous afficher le PDF ?',
                                       parent=self)
        if show_pdf and chemin_pdf and os.path.exists(chemin_pdf):
            ouvrir_pdf_viewer(self, chemin_pdf, title=f'{doc_title} {num_doc}')

        # Réinitialisation
        self._articles_list = []
        self._refresh_tv_articles()
        self.var_num_doc.set(db.get_num_document(self._mode))
        if hasattr(self, 'var_motif'):
            self.var_motif.set('')
        if hasattr(self, 'var_demandeur'):
            self.var_demandeur.set('')
        if hasattr(self, 'var_retourne_par'):
            self.var_retourne_par.set('')
        self._update_fournisseurs_list()
        self._set_focus_ref()
