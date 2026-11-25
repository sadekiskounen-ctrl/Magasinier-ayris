"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/historique.py
Historique des Bons (Sortie, Réception, Retour) avec aperçu, réimpression et filtres.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import subprocess
from datetime import datetime, date

from ui.theme import COLORS, FONTS, LIGNES, UNITES, get_machines_pour_lignes, MAGASINIERS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_secondary_button, make_success_button, SeparatorLine, make_combobox,
                         make_input, make_danger_button, MultiSelectLignesWidget, AutocompleteDesignationInput)
import database.db_manager as db
from services.pdf_generator import generer_bon_pdf
from services.config_manager import get_config
from ui.pdf_viewer import ouvrir_pdf_viewer
from ui.photo_viewer import ouvrir_photo_viewer

# Tentative d'import tkcalendar (optionnel)
try:
    from tkcalendar import DateEntry
    _HAS_CALENDAR = True
except ImportError:
    _HAS_CALENDAR = False


class HistoriqueFrame(ctk.CTkFrame):
    """Écran Historique & Documents PDF."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._all_mouvements = []
        self._page_size = 50
        self._current_offset = 0
        self._total_count = 0
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text='📄  Historique & Documents',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        filter_frame = ctk.CTkFrame(header, fg_color='transparent')
        filter_frame.pack(side='right')

        # ── Filtre type ──
        ctk.CTkLabel(
            filter_frame, text='Type :',
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(side='left', padx=(0, 4))

        self.var_filtre = tk.StringVar(value='Tous')
        self.cb_filtre = make_combobox(
            filter_frame, ['Tous', 'Bons de Sortie', 'Bons de Réception', 'Bons de Retour', 'Bons de Commande', 'Bons de Décharge'],
            width=180, variable=self.var_filtre
        )
        self.cb_filtre.pack(side='left', padx=(0, 8))
        self.cb_filtre.configure(command=self._apply_filter)

        # ── Filtre Fournisseur ──
        ctk.CTkLabel(
            filter_frame, text='Fournisseur :',
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(side='left', padx=(0, 4))

        self.var_fournisseur_filtre = tk.StringVar(value='Tous les fournisseurs')
        self.cb_fournisseur_filtre = make_combobox(
            filter_frame, ['Tous les fournisseurs'],
            width=180, variable=self.var_fournisseur_filtre
        )
        self.cb_fournisseur_filtre.pack(side='left', padx=(0, 10))
        self.cb_fournisseur_filtre.configure(command=self._apply_filter)

        # ── Filtre calendrier (date début / fin en Français) ──
        ctk.CTkLabel(
            filter_frame, text='Du :',
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(side='left', padx=(0, 4))

        if _HAS_CALENDAR:
            try:
                self.cal_debut = DateEntry(
                    filter_frame, width=10, background=COLORS['primary'],
                    foreground='white', borderwidth=2,
                    date_pattern='yyyy-MM-dd', locale='fr_FR'
                )
            except Exception:
                self.cal_debut = DateEntry(
                    filter_frame, width=10, background=COLORS['primary'],
                    foreground='white', borderwidth=2,
                    date_pattern='yyyy-MM-dd'
                )
            self.cal_debut.delete(0, 'end')
            self.cal_debut.pack(side='left', padx=(0, 6))

            ctk.CTkLabel(
                filter_frame, text='Au :',
                font=FONTS['small'], text_color=COLORS['text_secondary']
            ).pack(side='left', padx=(0, 4))

            try:
                self.cal_fin = DateEntry(
                    filter_frame, width=10, background=COLORS['primary'],
                    foreground='white', borderwidth=2,
                    date_pattern='yyyy-MM-dd', locale='fr_FR'
                )
            except Exception:
                self.cal_fin = DateEntry(
                    filter_frame, width=10, background=COLORS['primary'],
                    foreground='white', borderwidth=2,
                    date_pattern='yyyy-MM-dd'
                )
            self.cal_fin.pack(side='left', padx=(0, 6))

            make_secondary_button(
                filter_frame, '🔍 Filtrer', command=self._apply_filter, width=90
            ).pack(side='left', padx=(0, 4))
            make_secondary_button(
                filter_frame, '✖ Effacer', command=self._clear_date_filter, width=90
            ).pack(side='left', padx=(0, 8))
        else:
            # Fallback: champs texte simples
            self.e_debut = tk.Entry(filter_frame, width=11, font=('Segoe UI', 9))
            self.e_debut.pack(side='left', padx=(0, 4))
            self.e_debut.insert(0, 'AAAA-MM-JJ')

            ctk.CTkLabel(
                filter_frame, text='Au :',
                font=FONTS['small'], text_color=COLORS['text_secondary']
            ).pack(side='left', padx=(0, 4))

            self.e_fin = tk.Entry(filter_frame, width=11, font=('Segoe UI', 9))
            self.e_fin.pack(side='left', padx=(0, 6))
            self.e_fin.insert(0, 'AAAA-MM-JJ')

            make_secondary_button(
                filter_frame, '🔍 Filtrer', command=self._apply_filter, width=90
            ).pack(side='left', padx=(0, 4))
            make_secondary_button(
                filter_frame, '✖ Effacer', command=self._clear_date_filter, width=90
            ).pack(side='left', padx=(0, 8))

        make_secondary_button(
            filter_frame, '↻ Actualiser', command=self.refresh, width=110
        ).pack(side='left')

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Contenu principal (2 colonnes) ───────────────────────────────────
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=24, pady=12)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # ── Tableau des documents ─────────────────────────────────────────────
        list_panel = ctk.CTkFrame(
            body, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        list_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        ctk.CTkLabel(
            list_panel, text='📋  Liste des Documents',
            font=FONTS['subtitle'],
            text_color=COLORS['text_primary']
        ).pack(anchor='w', padx=16, pady=(12, 8))

        tv_frame = ctk.CTkFrame(list_panel, fg_color='transparent')
        tv_frame.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        self.tv = StyledTreeview(
            tv_frame,
            columns=['date', 'type', 'nb_articles', 'qte_total', 'service', 'pdf'],
            headings=['Date / Heure', 'Type', '# Articles', 'Qté Totale', 'Service / Fournisseur', 'PDF'],
            col_widths=[145, 80, 80, 80, 170, 50]
        )
        self.tv.pack(side='left', fill='both', expand=True)
        self.tv.bind('<<TreeviewSelect>>', self._on_select)
        self.tv.bind('<Double-1>', lambda e: self._ouvrir_pdf())
        add_scrollbar(tv_frame, self.tv)

        # Barre d'actions
        btns = ctk.CTkFrame(list_panel, fg_color='transparent')
        btns.pack(fill='x', padx=16, pady=(0, 12))

        make_primary_button(
            btns, 'Ouvrir PDF', command=self._ouvrir_pdf, icon='📄', width=120
        ).pack(side='left', padx=(0, 6))

        make_secondary_button(
            btns, '✏️ Modifier Bon', command=self._modifier_bon, width=130
        ).pack(side='left', padx=(0, 6))

        make_secondary_button(
            btns, '🖨️ Réimprimer', command=self._reimprimer, width=120
        ).pack(side='left', padx=(0, 6))

        make_secondary_button(
            btns, '📂 Dossier PDF', command=self._ouvrir_dossier, width=120
        ).pack(side='left', padx=(0, 6))

        make_success_button(
            btns, '📊 Exporter vers Excel', command=self._exporter_excel, width=160
        ).pack(side='left', padx=(0, 6))

        self.btn_charger_plus = make_secondary_button(
            btns, '📥 Charger plus', command=self._charger_plus, width=140
        )
        self.btn_charger_plus.pack(side='left')

        # ── Panneau de détail aperçu ──────────────────────────────────────────
        preview_panel = ctk.CTkFrame(
            body, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        preview_panel.grid(row=0, column=1, sticky='nsew', padx=(10, 0))

        ctk.CTkLabel(
            preview_panel, text='🔍  Détails du Document',
            font=FONTS['subtitle'],
            text_color=COLORS['text_primary']
        ).pack(anchor='w', padx=16, pady=(12, 8))

        SeparatorLine(preview_panel).pack(fill='x', padx=16)

        self.detail_frame = ctk.CTkScrollableFrame(
            preview_panel, fg_color='transparent'
        )
        self.detail_frame.pack(fill='both', expand=True, padx=8, pady=8)

        self._show_detail_empty()

    def _show_detail_empty(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.detail_frame, text='📄',
            font=('Segoe UI Emoji', 40),
            text_color=COLORS['text_muted']
        ).pack(pady=(30, 8))
        ctk.CTkLabel(
            self.detail_frame, text='Sélectionnez un document',
            font=FONTS['body'],
            text_color=COLORS['text_muted']
        ).pack()

    def _show_detail(self, mvt: dict):
        """Affiche le détail complet d'un document : toutes ses lignes d'articles."""
        for w in self.detail_frame.winfo_children():
            w.destroy()

        t_type = mvt['type_mouvement']
        # Pour les BC et BD : utiliser leur numéro de document direct
        if mvt.get('_source') == 'bons_commande':
            num_doc_str = mvt.get('num_bc', '—')
        elif mvt.get('_source') == 'decharges_outillage':
            num_doc_str = mvt.get('num_bon', '—')
        else:
            num_doc_str = db.extract_num_document(mvt)

        type_labels = {
            'SORTIE': f'📤 Bon de Sortie ({num_doc_str})',
            'ENTREE': f'📥 Bon de Réception ({num_doc_str})',
            'RETOUR': f'↩️ Bon de Retour ({num_doc_str})',
            'COMMANDE': f'🛒 Bon de Commande ({num_doc_str})',
            'DECHARGE': f'📑 Bon de Décharge ({num_doc_str})'
        }
        type_colors = {
            'SORTIE': COLORS['danger'],
            'ENTREE': COLORS['success'],
            'RETOUR': COLORS['warning'],
            'COMMANDE': COLORS.get('primary', '#7B5EA7'),
            'DECHARGE': '#0284C7'
        }

        ctk.CTkLabel(
            self.detail_frame, text=type_labels.get(t_type, f"{t_type} ({num_doc_str})"),
            font=FONTS['subtitle'],
            text_color=type_colors.get(t_type, COLORS['text_primary'])
        ).pack(anchor='w', padx=8, pady=(8, 4))

        SeparatorLine(self.detail_frame).pack(fill='x', padx=8, pady=4)

        def detail_row_static(icon, label, value):
            f = ctk.CTkFrame(self.detail_frame, fg_color=COLORS['bg_hover'], corner_radius=8)
            f.pack(fill='x', padx=8, pady=2)
            ctk.CTkLabel(f, text=f'{icon} {label}', font=FONTS['small_bold'],
                         text_color=COLORS['text_secondary'], width=110, anchor='w').pack(side='left', padx=10, pady=6)
            ctk.CTkLabel(f, text=str(value or '—'), font=FONTS['body_bold'],
                         text_color=COLORS['text_primary'], wraplength=160, justify='left').pack(side='left', padx=4)

        detail_row_static('🏷️', 'N° Document', num_doc_str)

        # ── En-tête du document ──
        raw_dt = mvt.get('date_heure', '') or ''
        try:
            dt_disp = datetime.strptime(raw_dt[:19], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y  %H:%M')
        except Exception:
            dt_disp = raw_dt[:16] if raw_dt else '—'

        detail_row_static('📅', 'Date & Heure', dt_disp)

        service_fourn = mvt.get('beneficiaire_service', '') or mvt.get('fournisseur_nom', '')
        if service_fourn:
            detail_row_static('🏢', 'Service / Fourn.', service_fourn)
        if mvt.get('motif'):
            detail_row_static('📝', 'Motif', mvt.get('motif'))
        if mvt.get('demandeur'):
            detail_row_static('👤', 'Demandeur', mvt.get('demandeur'))
        if mvt.get('retourne_par'):
            detail_row_static('👤', 'Retourné par', mvt.get('retourne_par'))
        if mvt.get('magasinier'):
            detail_row_static('👷', 'Magasinier', mvt.get('magasinier'))

        # ── Statut PDF ──
        chemin_pdf = mvt.get('chemin_pdf', '')
        pdf_ok = bool(chemin_pdf and os.path.exists(chemin_pdf))
        pdf_label = '✅ Disponible' if pdf_ok else '❌ Introuvable'
        pdf_color = COLORS['success'] if pdf_ok else COLORS['danger']
        pdf_frame = ctk.CTkFrame(self.detail_frame, fg_color=COLORS['bg_hover'], corner_radius=8)
        pdf_frame.pack(fill='x', padx=8, pady=2)
        ctk.CTkLabel(pdf_frame, text='📄 PDF', font=FONTS['small_bold'],
                     text_color=COLORS['text_secondary'], width=110, anchor='w').pack(side='left', padx=10, pady=6)
        ctk.CTkLabel(pdf_frame, text=pdf_label, font=FONTS['body_bold'],
                     text_color=pdf_color).pack(side='left', padx=4)

        SeparatorLine(self.detail_frame).pack(fill='x', padx=8, pady=(8, 4))

        # ── Tableau des articles du bon ──
        ctk.CTkLabel(
            self.detail_frame,
            text=f"📦  Articles du Bon  ({mvt.get('nb_articles', '?')} article(s))",
            font=FONTS['small_bold'],
            text_color=COLORS['text_secondary']
        ).pack(anchor='w', padx=8, pady=(0, 4))

        # Récupérer les articles détaillés depuis la BD
        articles = []
        if mvt.get('_source') == 'bons_commande':
            # BC autonome : lire depuis bons_commande par num_bc
            try:
                articles = db.get_articles_bon_commande(mvt.get('num_bc', ''))
                # Normaliser les clés pour l'affichage
                for a in articles:
                    a.setdefault('designation', a.get('designation', '—'))
                    a.setdefault('quantite', 0)
                    a.setdefault('unite', '')
            except Exception:
                articles = []
        elif mvt.get('_source') == 'decharges_outillage':
            # BD autonome : afficher l'outillage déchargé
            articles = [{
                'code_barres': '—',
                'designation': mvt.get('outillage', '—'),
                'quantite': 1,
                'unite': 'Unité'
            }]
        elif chemin_pdf:
            try:
                articles = db.get_articles_document(chemin_pdf)
            except Exception:
                articles = []

        # Si pas de chemin PDF, on affiche les designations groupées
        if articles:
            for i, art in enumerate(articles):
                row_color = COLORS['bg_hover'] if i % 2 == 0 else COLORS.get('bg_card', COLORS['bg_hover'])
                art_f = ctk.CTkFrame(self.detail_frame, fg_color=row_color, corner_radius=6)
                art_f.pack(fill='x', padx=8, pady=1)

                # Numéro de ligne
                ctk.CTkLabel(
                    art_f, text=f"{i+1:02d}",
                    font=FONTS['small_bold'],
                    text_color=COLORS['text_muted'], width=24
                ).pack(side='left', padx=(8, 4), pady=5)

                # Désignation
                lbl_des = ctk.CTkLabel(
                    art_f, text=art.get('designation', '—'),
                    font=FONTS['body'],
                    text_color=COLORS['text_primary'],
                    anchor='w'
                )
                lbl_des.pack(side='left', padx=4, fill='x', expand=True)

                # Si l'article possède une référence, vérifier si photo disponible
                art_ref = art.get('code_barres') or art.get('reference')
                if art_ref and db.has_photo_piece_by_ref(art_ref):
                    btn_art_photo = ctk.CTkButton(
                        art_f, text='📷', width=28, height=24,
                        fg_color=COLORS['primary'], hover_color=COLORS['primary_dark'],
                        font=FONTS['small_bold'], corner_radius=6,
                        command=lambda r=art_ref: ouvrir_photo_viewer(self, code_barres=r)
                    )
                    btn_art_photo.pack(side='right', padx=(2, 4))

                # Quantité
                ctk.CTkLabel(
                    art_f, text=f"x{art.get('quantite', 0)}",
                    font=FONTS['small_bold'],
                    text_color=type_colors.get(t_type, COLORS['text_primary']),
                    width=50
                ).pack(side='right', padx=(4, 8))

                # Unité
                ctk.CTkLabel(
                    art_f, text=str(art.get('unite', '')),
                    font=FONTS['small'],
                    text_color=COLORS['text_secondary'],
                    width=50
                ).pack(side='right', padx=2)
        else:
            # Fallback: afficher les désignations groupées
            designations_str = mvt.get('designations', '') or ''
            for i, des in enumerate(designations_str.split(' | ')):
                if not des.strip():
                    continue
                row_color = COLORS['bg_hover'] if i % 2 == 0 else COLORS.get('bg_card', COLORS['bg_hover'])
                art_f = ctk.CTkFrame(self.detail_frame, fg_color=row_color, corner_radius=6)
                art_f.pack(fill='x', padx=8, pady=1)
                ctk.CTkLabel(
                    art_f, text=f"{i+1:02d}  {des.strip()}",
                    font=FONTS['body'],
                    text_color=COLORS['text_primary'],
                    anchor='w'
                ).pack(side='left', padx=8, pady=5, fill='x', expand=True)

        # ── Boutons d'action ──
        SeparatorLine(self.detail_frame).pack(fill='x', padx=8, pady=(8, 4))

        # Bouton Voir Photo pour les pièces du bon
        # Si le bon contient une ou plusieurs pièces, permettre de voir / choisir la photo
        def _ouvrir_photo_bon():
            # Chercher le premier article qui possède une photo ou le premier article tout court
            target_piece_id = None
            target_ref = None
            if articles:
                for a in articles:
                    ref_c = a.get('code_barres') or a.get('reference')
                    if ref_c:
                        p_db = db.find_produit_by_ref_or_last4(ref_c)
                        if p_db and db.has_photo_piece(p_db['id']):
                            target_piece_id = p_db['id']
                            break
                        elif not target_piece_id and p_db:
                            target_piece_id = p_db['id']
            if not target_piece_id and mvt.get('produit_id'):
                target_piece_id = mvt.get('produit_id')

            if target_piece_id:
                ouvrir_photo_viewer(self, piece_id=target_piece_id)
            elif articles and (articles[0].get('code_barres') or articles[0].get('reference')):
                ouvrir_photo_viewer(self, code_barres=articles[0].get('code_barres') or articles[0].get('reference'))
            else:
                messagebox.showinfo("Photo", "Aucune pièce associée identifiée pour ce document.", parent=self)

        # Vérifier si au moins un article du document a une photo
        has_any_photo = False
        if articles:
            for a in articles:
                ref_c = a.get('code_barres') or a.get('reference')
                if ref_c and db.has_photo_piece_by_ref(ref_c):
                    has_any_photo = True
                    break
        elif mvt.get('produit_id') and db.has_photo_piece(mvt.get('produit_id')):
            has_any_photo = True

        btn_photo_text = '📷 Voir photo de la pièce' if has_any_photo else '📷 Aucune photo'
        btn_photo = make_secondary_button(
            self.detail_frame, btn_photo_text,
            command=_ouvrir_photo_bon,
            width=220
        )
        btn_photo.pack(pady=(2, 4))
        if not has_any_photo:
            btn_photo.configure(state='disabled')

        make_secondary_button(
            self.detail_frame, '✏️ Modifier le Bon',
            command=lambda m=mvt: self._modifier_bon(m),
            width=220
        ).pack(pady=(2, 4))

        if pdf_ok:
            make_primary_button(
                self.detail_frame, '📄 Afficher le PDF',
                command=lambda p=chemin_pdf: ouvrir_pdf_viewer(self, p, title='Document PDF'),
                icon='', width=220
            ).pack(pady=(2, 6))

    def _modifier_bon(self, mvt: dict = None):
        """Ouvre la modale pour modifier le Bon sélectionné (données et quantités)."""
        if mvt is None or not isinstance(mvt, dict):
            mvt = self._get_selected_mvt()
        if not mvt:
            return
        EditDocumentModal(self, mvt=mvt, on_save=self.refresh)

    def _update_fournisseurs_filter(self):
        """Recharge dynamiquement la liste des fournisseurs dans le filtre déroulant d'historique."""
        try:
            fournisseurs = db.get_all_fournisseurs()
            noms = [f['nom'] for f in fournisseurs if f.get('nom')]
            options = ['Tous les fournisseurs'] + noms
            current = self.var_fournisseur_filtre.get()
            self.cb_fournisseur_filtre.configure(values=options)
            if current not in options:
                self.var_fournisseur_filtre.set('Tous les fournisseurs')
        except Exception:
            pass

    def refresh(self):
        self._update_fournisseurs_filter()
        self._current_offset = 0
        self._load_page(reset=True)

    def _charger_plus(self):
        self._current_offset += self._page_size
        self._load_page(reset=False)

    def _get_date_filter(self):
        """Retourne (date_debut_str, date_fin_str) ou (None, None) si pas de filtre."""
        d_debut = None
        d_fin   = None
        if _HAS_CALENDAR:
            try:
                raw_debut = self.cal_debut.get_date()
                raw_fin   = self.cal_fin.get_date()
                # get_date() retourne un objet date ou une string selon la version
                if isinstance(raw_debut, date):
                    d_debut = raw_debut.strftime('%Y-%m-%d')
                elif raw_debut:
                    d_debut = str(raw_debut)[:10]
                if isinstance(raw_fin, date):
                    d_fin = raw_fin.strftime('%Y-%m-%d')
                elif raw_fin:
                    d_fin = str(raw_fin)[:10]
            except Exception:
                pass
        else:
            v1 = getattr(self, 'e_debut', None)
            v2 = getattr(self, 'e_fin', None)
            if v1 and v2:
                s1 = v1.get().strip()
                s2 = v2.get().strip()
                if len(s1) == 10 and s1 != 'AAAA-MM-JJ':
                    d_debut = s1
                if len(s2) == 10 and s2 != 'AAAA-MM-JJ':
                    d_fin = s2
        return d_debut, d_fin

    def _clear_date_filter(self):
        """Efface le filtre de date, type et fournisseur puis réaffiche tout."""
        self.var_filtre.set('Tous')
        if hasattr(self, 'var_fournisseur_filtre'):
            self.var_fournisseur_filtre.set('Tous les fournisseurs')

        if _HAS_CALENDAR:
            try:
                self.cal_debut.set_date(date.today())
                self.cal_fin.set_date(date.today())
                # Vider manuellement pour signifier "pas de filtre"
                self.cal_debut.delete(0, 'end')
                self.cal_fin.delete(0, 'end')
            except Exception:
                pass
        else:
            for attr in ('e_debut', 'e_fin'):
                widget = getattr(self, attr, None)
                if widget:
                    widget.delete(0, 'end')
                    widget.insert(0, 'AAAA-MM-JJ')
        self._apply_filter()

    def _apply_filter(self, value: str = None):
        self._current_offset = 0
        self._load_page(reset=True)

    def _load_page(self, reset: bool = True):
        value = self.var_filtre.get()
        fourn_val = self.var_fournisseur_filtre.get() if hasattr(self, 'var_fournisseur_filtre') else None
        if fourn_val == 'Tous les fournisseurs':
            fourn_val = None

        d_debut, d_fin = self._get_date_filter()

        filtre_map = {
            'Bons de Sortie': 'SORTIE',
            'Bons de Réception': 'ENTREE',
            'Bons de Retour': 'RETOUR',
            'Bons de Commande': 'COMMANDE',
            'Bons de Décharge': 'DECHARGE'
        }
        filtre_type = filtre_map.get(value)

        # ── Charger les mouvements stock (SORTIE / ENTREE / RETOUR) ──────────
        # Exclure COMMANDE et DECHARGE de la table mouvements (tables dédiées)
        mvt_filtre = filtre_type if filtre_type not in ('COMMANDE', 'DECHARGE') else None
        load_mvts = filtre_type not in ('COMMANDE', 'DECHARGE')
        load_bc   = (filtre_type == 'COMMANDE' or filtre_type is None)
        load_bd   = (filtre_type == 'DECHARGE' or filtre_type is None)

        if load_mvts:
            count_mvts = db.get_mouvements_count(
                type_filtre=mvt_filtre,
                date_debut=d_debut,
                date_fin=d_fin,
                fournisseur_filtre=fourn_val
            )
            new_mvts = db.get_all_mouvements(
                type_filtre=mvt_filtre,
                date_debut=d_debut,
                date_fin=d_fin,
                limit=self._page_size,
                offset=self._current_offset,
                fournisseur_filtre=fourn_val
            )
        else:
            count_mvts = 0
            new_mvts = []

        # ── Charger les Bons de Commande depuis table dédiée ─────────────────
        if load_bc:
            count_bc = db.get_bons_commande_count(
                date_debut=d_debut,
                date_fin=d_fin,
                fournisseur_filtre=fourn_val
            )
            new_bc = db.get_all_bons_commande(
                date_debut=d_debut,
                date_fin=d_fin,
                limit=self._page_size,
                offset=self._current_offset if filtre_type == 'COMMANDE' else 0,
                fournisseur_filtre=fourn_val
            )
        else:
            count_bc = 0
            new_bc = []

        # ── Charger les Bons de Décharge depuis table dédiée ─────────────────
        if load_bd:
            count_bd = db.get_decharges_count(date_debut=d_debut, date_fin=d_fin)
            new_bd = db.get_all_decharges_pour_historique(
                date_debut=d_debut,
                date_fin=d_fin,
                limit=self._page_size,
                offset=self._current_offset if filtre_type == 'DECHARGE' else 0
            )
        else:
            count_bd = 0
            new_bd = []

        self._total_count = count_mvts + count_bc + count_bd

        # Fusionner et trier par date décroissante
        combined = list(new_mvts) + list(new_bc) + list(new_bd)
        combined.sort(key=lambda m: m.get('date_heure', '') or '', reverse=True)

        # Utiliser un id unique pour les BC (préfixe 'bc_') pour éviter collision
        if reset:
            self._all_mouvements = []
            for item in self.tv.get_children():
                self.tv.delete(item)
        
        self._all_mouvements.extend(combined)

        for m in combined:
            t_type = m['type_mouvement']
            tag_map = {'SORTIE': 'sortie', 'ENTREE': 'entree', 'RETOUR': 'retour', 'COMMANDE': 'even', 'DECHARGE': 'even'}
            tag = tag_map.get(t_type, 'even')

            raw_dt = m.get('date_heure', '') or ''
            try:
                dt_obj = datetime.strptime(raw_dt[:19], '%Y-%m-%d %H:%M:%S')
                date_str = dt_obj.strftime('%Y-%m-%d  %H:%M')
            except Exception:
                date_str = raw_dt[:16] if raw_dt else ''

            # Numéro de document
            if t_type == 'COMMANDE' and m.get('_source') == 'bons_commande':
                num_doc_str = m.get('num_bc', '—')
            elif m.get('_source') == 'decharges_outillage':
                num_doc_str = m.get('num_bon', '—')
            else:
                num_doc_str = db.extract_num_document(m)

            type_base = {'SORTIE': '📤 BS', 'ENTREE': '📥 BR', 'RETOUR': '↩️ BT', 'COMMANDE': '🛒 BC', 'DECHARGE': '📑 BD'}.get(t_type, t_type)
            type_str = f"{type_base}  {num_doc_str}"
            pdf_str = '✅' if (m.get('chemin_pdf') and os.path.exists(m.get('chemin_pdf', ''))) else '❌'

            service_display = m.get('beneficiaire_service', '') or m.get('fournisseur_nom', '') or ''
            nb_articles = m.get('nb_articles', 1)
            total_qte = m.get('total_quantite', m.get('quantite', 0)) or 0

            # iid unique : BC → 'bc_N', BD → 'bd_N', mouvements → str(id)
            if m.get('_source') == 'bons_commande':
                iid = f"bc_{m['id']}"
            elif m.get('_source') == 'decharges_outillage':
                iid = f"bd_{m['id']}"
            else:
                iid = str(m['id'])

            self.tv.insert('', 'end', iid=iid, values=(
                date_str,
                type_str,
                str(nb_articles),
                str(total_qte),
                service_display,
                pdf_str
            ), tags=(tag,))

        self.tv.autofit_columns()
        if reset:
            self._show_detail_empty()

        loaded = len(self._all_mouvements)
        if hasattr(self, 'btn_charger_plus'):
            if loaded < self._total_count:
                self.btn_charger_plus.configure(text=f'📥 Charger plus ({loaded}/{self._total_count})', state='normal')
            else:
                self.btn_charger_plus.configure(text=f'✓ Tous affichés ({loaded}/{self._total_count})', state='disabled')

    def _on_select(self, event):
        sel = self.tv.selection()
        if not sel:
            return
        iid = sel[0]
        mvt = self._find_mvt_by_iid(iid)
        if mvt:
            self._show_detail(mvt)

    def _find_mvt_by_iid(self, iid: str) -> dict | None:
        """Retrouve un mouvement, BC ou BD depuis son iid."""
        if iid.startswith('bd_'):
            bd_id = int(iid[3:])
            return next((m for m in self._all_mouvements
                         if m.get('_source') == 'decharges_outillage' and m['id'] == bd_id), None)
        elif iid.startswith('bc_'):
            bc_id = int(iid[3:])
            return next((m for m in self._all_mouvements
                         if m.get('_source') == 'bons_commande' and m['id'] == bc_id), None)
        else:
            mvt_id = int(iid)
            return next((m for m in self._all_mouvements
                         if m.get('_source') not in ('bons_commande', 'decharges_outillage') and m['id'] == mvt_id), None)

    def _get_selected_mvt(self) -> dict | None:
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner un document.', parent=self)
            return None
        return self._find_mvt_by_iid(sel[0])

    def _ouvrir_pdf(self):
        mvt = self._get_selected_mvt()
        if not mvt:
            return
        chemin = mvt.get('chemin_pdf', '')
        if chemin and os.path.exists(chemin):
            t_type = mvt.get('type_mouvement', '')
            label_map = {'SORTIE': 'Bon de Sortie', 'ENTREE': 'Bon de Réception',
                         'RETOUR': 'Bon de Retour', 'COMMANDE': 'Bon de Commande',
                         'DECHARGE': 'Bon de Décharge'}
            ouvrir_pdf_viewer(self, chemin, title=label_map.get(t_type, 'Document PDF'))
        else:
            messagebox.showerror('PDF Introuvable', f'Fichier introuvable :\n{chemin}', parent=self)

    def _reimprimer(self):
        """Réimprime le document sélectionné avec tous ses articles."""
        mvt = self._get_selected_mvt()
        if not mvt:
            return

        # ── Cas Bon de Décharge : régénérer via generer_bon_decharge_pdf ──────
        if mvt.get('_source') == 'decharges_outillage':
            from services.pdf_generator import generer_bon_decharge_pdf
            num_reimp = (mvt.get('num_bon', 'BD-REIMP') or 'BD-REIMP') + '-REIMP'
            try:
                pdf_dir = get_config('pdf_directory', '')
                chemin_pdf = generer_bon_decharge_pdf(
                    num_bon=num_reimp,
                    demandeur=mvt.get('demandeur', ''),
                    outillage=mvt.get('outillage', ''),
                    date_str=mvt.get('date', ''),
                    pdf_dir=pdf_dir or None
                )
                messagebox.showinfo('PDF Régénéré', 'Bon de Décharge réimprimé avec succès !', parent=self)
                ouvrir_pdf_viewer(self, chemin_pdf, title=f"Bon de Décharge {mvt.get('num_bon', '')}")
            except Exception as e:
                messagebox.showerror('Erreur', f'Impossible de réimprimer :\n{e}', parent=self)
            return

        # ── Cas Bon de Commande : régénérer via generer_bon_commande_pdf ──────
        if mvt.get('_source') == 'bons_commande':
            from services.pdf_generator import generer_bon_commande_pdf
            num_bc = mvt.get('num_bc', '')
            num_reimp = (num_bc or 'BC-REIMP') + '-REIMP'
            articles = db.get_articles_bon_commande(num_bc)
            if not articles:
                articles = [{
                    'reference': '',
                    'designation': mvt.get('designations', '') or '',
                    'quantite': mvt.get('total_quantite', 1) or 1,
                    'unite': 'Unité',
                    'observation': ''
                }]
            try:
                pdf_dir = get_config('pdf_directory', '')
                chemin_pdf = generer_bon_commande_pdf(
                    num_bc=num_reimp,
                    fournisseur=mvt.get('fournisseur_nom', '') or mvt.get('beneficiaire_service', ''),
                    articles=articles,
                    motif='Réimpression',
                    pdf_dir=pdf_dir or None
                )
                messagebox.showinfo('PDF Régénéré', f'Bon de Commande réimprimé avec succès !\n{len(articles)} article(s) inclus.', parent=self)
                ouvrir_pdf_viewer(self, chemin_pdf, title=f"Bon de Commande {num_bc}")
            except Exception as e:
                messagebox.showerror('Erreur', f'Impossible de réimprimer :\n{e}', parent=self)
            return

        num_doc = db.get_num_document(mvt['type_mouvement']) + '-REIMP'

        # Récupérer tous les articles du document
        chemin_pdf_src = mvt.get('chemin_pdf', '')
        articles_detail = []
        if chemin_pdf_src:
            try:
                articles_detail = db.get_articles_document(chemin_pdf_src)
            except Exception:
                articles_detail = []

        if articles_detail:
            articles = [
                {
                    'reference': a.get('code_barres', ''),
                    'designation': a.get('designation', ''),
                    'emplacement': '',
                    'unite': a.get('unite', 'Unité'),
                    'quantite': a.get('quantite', 0),
                }
                for a in articles_detail
            ]
        else:
            # Fallback: un seul article depuis les données groupées
            articles = [{
                'reference': '',
                'designation': mvt.get('designations', '') or '',
                'emplacement': '',
                'unite': '',
                'quantite': mvt.get('total_quantite', 0) or 0,
            }]

        pdf_dir = get_config('pdf_directory', '')
        try:
            chemin_pdf = generer_bon_pdf(
                type_mvt=mvt['type_mouvement'],
                num_doc=num_doc,
                beneficiaire=mvt.get('beneficiaire_service', ''),
                fournisseur=mvt.get('fournisseur_nom', ''),
                motif=mvt.get('motif', ''),
                articles=articles,
                pdf_dir=pdf_dir or None,
                demandeur=mvt.get('demandeur', ''),
                retourne_par=mvt.get('retourne_par', ''),
                magasinier=mvt.get('magasinier', '')
            )
            messagebox.showinfo('PDF Régénéré', f'PDF réimprimé avec succès !\n{len(articles)} article(s) inclus.', parent=self)
            ouvrir_pdf_viewer(self, chemin_pdf, title='Réimpression')
        except Exception as e:
            messagebox.showerror('Erreur', f'Impossible de réimprimer :\n{e}', parent=self)

    def _ouvrir_dossier(self):
        pdf_dir = get_config('pdf_directory', '')
        if not pdf_dir:
            from pathlib import Path
            pdf_dir = str(Path.home() / 'Documents' / 'SARL_Ayris_PDF')
        os.makedirs(pdf_dir, exist_ok=True)
        subprocess.run(['explorer', pdf_dir], shell=True)

    def _exporter_excel(self):
        """Exporte l'ensemble des mouvements actuellement filtrés vers un fichier Excel (.xlsx)."""
        from services.excel_generator import exporter_historique_excel
        from tkinter import filedialog

        value = self.var_filtre.get()
        fourn_val = self.var_fournisseur_filtre.get() if hasattr(self, 'var_fournisseur_filtre') else None
        if fourn_val == 'Tous les fournisseurs':
            fourn_val = None

        d_debut, d_fin = self._get_date_filter()

        filtre_map = {
            'Bons de Sortie': 'SORTIE',
            'Bons de Réception': 'ENTREE',
            'Bons de Retour': 'RETOUR',
            'Bons de Commande': 'COMMANDE',
            'Bons de Décharge': 'DECHARGE'
        }
        filtre_type = filtre_map.get(value)

        # Récupérer tous les documents groupés selon les filtres (sans pagination)
        mvts = db.get_all_mouvements(
            type_filtre=filtre_type if filtre_type not in ('COMMANDE', 'DECHARGE') else None,
            date_debut=d_debut,
            date_fin=d_fin,
            limit=None,
            fournisseur_filtre=fourn_val
        )

        if not mvts:
            messagebox.showwarning('Export Excel', 'Aucun document à exporter pour les filtres sélectionnés.', parent=self)
            return

        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        default_filename = f"Export_Historique_AYRIS_{date_str}.xlsx"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Enregistrer l'export Excel de l'Historique",
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx")]
        )

        if not file_path:
            return

        try:
            exporter_historique_excel(mvts, file_path)
            messagebox.showinfo(
                '✅ Export Réussi',
                f'L\'historique de {len(mvts)} document(s) a été exporté avec succès !\n\nFichier : {file_path}',
                parent=self
            )
            if messagebox.askyesno('Ouvrir Excel', 'Voulez-vous ouvrir le fichier Excel généré ?', parent=self):
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror('Erreur Export', f'Échec de la génération du fichier Excel :\n{e}', parent=self)


# ────────────────────── Modale Modification de Bon ───────────────────────────

# ────────────────────── Modale Modification de Bon ───────────────────────────

class EditDocumentModal(ctk.CTkToplevel):
    """Fenêtre modale complète pour modifier les métadonnées, ajouter ou supprimer des articles d'un Bon."""

    def __init__(self, parent, mvt: dict, on_save=None):
        super().__init__(parent)
        self.mvt = mvt
        self.on_save = on_save

        t_type = mvt.get('type_mouvement', '')
        type_names = {
            'SORTIE': 'Bon de Sortie',
            'ENTREE': 'Bon de Réception',
            'RETOUR': 'Bon de Retour',
            'COMMANDE': 'Bon de Commande'
        }
        self.type_title = type_names.get(t_type, 'Document')
        if mvt.get('_source') == 'bons_commande':
            self.num_doc = mvt.get('num_bc', '') or db.extract_num_document(mvt)
        else:
            self.num_doc = db.extract_num_document(mvt)

        self.title(f'✏️  Modifier {self.type_title} ({self.num_doc})')
        self.geometry('780x820')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self.update_idletasks()
        w, h = 780, 820
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

        chemin_pdf = mvt.get('chemin_pdf', '')
        raw_articles = []
        if mvt.get('_source') == 'bons_commande':
            try:
                raw_articles = db.get_articles_bon_commande(self.num_doc)
            except Exception:
                raw_articles = []
        elif chemin_pdf:
            try:
                raw_articles = db.get_articles_document(chemin_pdf)
            except Exception:
                raw_articles = [mvt]
        else:
            raw_articles = [mvt]

        if not raw_articles:
            raw_articles = [mvt]

        # Structure interne des articles du bon
        self.articles_list = []
        for art in raw_articles:
            self.articles_list.append({
                'id': art.get('id'),
                'reference': art.get('code_barres', '') or art.get('reference', ''),
                'code_barres': art.get('code_barres', '') or art.get('reference', ''),
                'designation': art.get('designation', ''),
                'quantite': art.get('quantite', 1),
                'unite': art.get('unite', 'Unité'),
                'utilite_ligne': art.get('utilite_ligne', 'Aucune'),
                'nom_machine': art.get('nom_machine', 'N/A'),
                'is_new': False
            })

        self.deleted_articles = []
        self._build_ui()

    def _build_ui(self):
        # ── BOUTONS FIXES EN BAS ──
        btn_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], height=60, border_width=1, border_color=COLORS['border'])
        btn_frame.pack(side='bottom', fill='x', padx=0, pady=0)

        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=130).pack(side='right', padx=16, pady=10)
        make_success_button(
            btn_frame, '💾 Enregistrer & Régénérer PDF',
            command=self._save, width=240
        ).pack(side='right', padx=(0, 8), pady=10)

        # ── En-tête de la modale ──
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(16, 2))

        ctk.CTkLabel(
            header, text=f'✏️  Modifier {self.type_title} — {self.num_doc}',
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(side='left')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(6, 10))

        # ── Zone Scrollable au centre ──
        self.scroll = ctk.CTkScrollableFrame(self, fg_color='transparent', scrollbar_button_color=COLORS['primary'])
        self.scroll.pack(side='top', fill='both', expand=True, padx=24, pady=(0, 6))

        def row_input(label_text, initial_val, placeholder=''):
            f = ctk.CTkFrame(self.scroll, fg_color=COLORS['bg_hover'], corner_radius=8)
            f.pack(fill='x', pady=3)
            ctk.CTkLabel(f, text=label_text, font=FONTS['small_bold'],
                         text_color=COLORS['text_secondary'], width=150, anchor='w').pack(side='left', padx=10, pady=6)
            var = tk.StringVar(value=str(initial_val if initial_val is not None else ''))
            entry = ctk.CTkEntry(
                f, textvariable=var,
                fg_color=COLORS['bg_input'], border_color=COLORS['border'],
                border_width=1, text_color=COLORS['text_primary'],
                font=FONTS['body'], height=32, placeholder_text=placeholder
            )
            entry.pack(side='left', fill='x', expand=True, padx=(4, 8), pady=4)
            return entry

        t_type = self.mvt.get('type_mouvement', '')
        raw_dt = self.mvt.get('date_heure', '') or ''
        self.e_date = row_input('📅 Date & Heure', raw_dt, 'AAAA-MM-JJ HH:MM:SS')

        service_init = self.mvt.get('beneficiaire_service', '') or self.mvt.get('fournisseur_nom', '')
        self.e_service = row_input('🏢 Service / Fourn.', service_init, 'Service ou Fournisseur')
        self.e_motif = row_input('📝 Motif', self.mvt.get('motif', ''), 'Motif du mouvement')

        if t_type == 'SORTIE' or self.mvt.get('demandeur'):
            self.e_demandeur = row_input('👤 Demandeur', self.mvt.get('demandeur', ''), 'Nom du demandeur')
        if t_type == 'RETOUR' or self.mvt.get('retourne_par'):
            self.e_retourne = row_input('👤 Retourné par', self.mvt.get('retourne_par', ''), 'Nom du remettant')

        mag_initial = self.mvt.get('magasinier', '') or MAGASINIERS[0]
        self.e_magasinier = row_input('👷 Magasinier', mag_initial, 'Nom du magasinier')

        SeparatorLine(self.scroll).pack(fill='x', pady=12)

        # ── FORMULAIRE AJOUT D'ARTICLE AU BON (Exactement comme à la création) ──
        add_card = ctk.CTkFrame(self.scroll, fg_color=COLORS['bg_card'], corner_radius=10, border_width=1, border_color=COLORS['primary'])
        add_card.pack(fill='x', pady=(0, 12))

        ctk.CTkLabel(
            add_card, text='➕  Ajouter un Article à ce Bon (Réf, Désignation, Qté, Unité, Utilité, Machine)',
            font=FONTS['subtitle'], text_color=COLORS['primary']
        ).pack(anchor='w', padx=12, pady=(10, 4))
        SeparatorLine(add_card).pack(fill='x', padx=12, pady=(0, 8))

        grid_add = ctk.CTkFrame(add_card, fg_color='transparent')
        grid_add.pack(fill='x', padx=12, pady=(0, 8))

        # Référence avec Bouton Auto-Génération
        ctk.CTkLabel(grid_add, text='Réf * :', font=FONTS['small_bold'], text_color=COLORS['text_secondary']).grid(row=0, column=0, padx=4, pady=4, sticky='w')
        f_ref = ctk.CTkFrame(grid_add, fg_color='transparent')
        f_ref.grid(row=0, column=1, padx=4, pady=4, sticky='w')

        self.var_add_ref = tk.StringVar()
        self.e_add_ref = make_input(f_ref, placeholder='Ex: REF-1234', textvariable=self.var_add_ref, width=130)
        self.e_add_ref.pack(side='left', padx=(0, 4))
        self.var_add_ref.trace_add('write', self._on_add_ref_change)

        def _auto_gen_edit():
            existing = [art.get('code_barres', '') or art.get('reference', '') for art in self.articles_list if art]
            self.var_add_ref.set(db.generer_reference_unique(excluded_refs=existing))

        make_secondary_button(
            f_ref, '⚡ Auto Réf',
            command=_auto_gen_edit,
            width=95, height=32
        ).pack(side='left')

        # Désignation (Autocomplétion)
        ctk.CTkLabel(grid_add, text='Désignation * :', font=FONTS['small_bold'], text_color=COLORS['text_secondary']).grid(row=0, column=2, padx=4, pady=4, sticky='w')
        self.var_add_designation = tk.StringVar()
        self.e_add_designation = AutocompleteDesignationInput(
            grid_add, placeholder='Taper pour rechercher...',
            textvariable=self.var_add_designation,
            on_select=self._on_add_autocomplete_select
        )
        self.e_add_designation.grid(row=0, column=3, padx=4, pady=4, sticky='ew')

        # Quantité & Unité
        ctk.CTkLabel(grid_add, text='Qté * :', font=FONTS['small_bold'], text_color=COLORS['text_secondary']).grid(row=1, column=0, padx=4, pady=4, sticky='w')
        self.var_add_qte = tk.StringVar(value='1')
        self.e_add_qte = make_input(grid_add, placeholder='1', textvariable=self.var_add_qte, width=80)
        self.e_add_qte.grid(row=1, column=1, padx=4, pady=4, sticky='w')

        ctk.CTkLabel(grid_add, text='Unité * :', font=FONTS['small_bold'], text_color=COLORS['text_secondary']).grid(row=1, column=2, padx=4, pady=4, sticky='w')
        self.var_add_unite = tk.StringVar(value='Unité')
        self.cb_add_unite = make_combobox(grid_add, UNITES, variable=self.var_add_unite, width=120)
        self.cb_add_unite.grid(row=1, column=3, padx=4, pady=4, sticky='w')

        # Utilité Ligne & Machine
        ctk.CTkLabel(grid_add, text='Utilité / Ligne * :', font=FONTS['small_bold'], text_color=COLORS['text_secondary']).grid(row=2, column=0, padx=4, pady=4, sticky='w')
        self.widget_add_lignes = MultiSelectLignesWidget(grid_add, options=LIGNES, default_selected=['KHS1'], on_change=self._on_add_lignes_change)
        self.widget_add_lignes.grid(row=2, column=1, columnspan=3, padx=4, pady=4, sticky='ew')

        ctk.CTkLabel(grid_add, text='Machine * :', font=FONTS['small_bold'], text_color=COLORS['text_secondary']).grid(row=3, column=0, padx=4, pady=4, sticky='w')
        self.var_add_machine = tk.StringVar(value='Blomax')
        self.cb_add_machine = make_combobox(grid_add, get_machines_pour_lignes(['KHS1']), variable=self.var_add_machine, width=180)
        self.cb_add_machine.grid(row=3, column=1, columnspan=2, padx=4, pady=4, sticky='w')

        make_primary_button(
            grid_add, '➕ Ajouter l\'Article à ce Bon',
            command=self._ajouter_article_au_bon, icon='', width=200
        ).grid(row=3, column=3, padx=4, pady=6, sticky='e')

        grid_add.grid_columnconfigure(3, weight=1)

        # ── ZONE LISTE DES ARTICLES DU BON ──
        self.lbl_articles_title = ctk.CTkLabel(
            self.scroll,
            text='',
            font=FONTS['subtitle'], text_color=COLORS['primary']
        )
        self.lbl_articles_title.pack(anchor='w', pady=(4, 6))

        self.articles_container = ctk.CTkFrame(self.scroll, fg_color='transparent')
        self.articles_container.pack(fill='x', pady=0)

        self._render_articles_list()

    def _on_add_ref_change(self, *_):
        code = self.var_add_ref.get().strip()
        if len(code) >= 4:
            p = db.find_produit_by_ref_or_last4(code)
            if p:
                self.var_add_designation.set(p.get('designation', ''))
                if p.get('unite'): self.var_add_unite.set(p['unite'])
                if p.get('utilite_ligne'):
                    self.widget_add_lignes.set_selected([l.strip() for l in p['utilite_ligne'].split(',') if l.strip()])
                if p.get('nom_machine'): self.var_add_machine.set(p['nom_machine'])

    def _on_add_autocomplete_select(self, p: dict):
        if p and p.get('code_barres'):
            self.var_add_ref.set(p['code_barres'])
            self._on_add_ref_change()

    def _on_add_lignes_change(self, selected_lignes: list):
        machines = get_machines_pour_lignes(selected_lignes)
        self.cb_add_machine.configure(values=machines)
        if self.var_add_machine.get() not in machines:
            self.var_add_machine.set(machines[0])

    def _ajouter_article_au_bon(self):
        ref = self.var_add_ref.get().strip()
        desig = self.var_add_designation.get().strip()
        unite = self.var_add_unite.get()
        lignes = ", ".join(self.widget_add_lignes.get_selected())
        machine = self.var_add_machine.get()

        if not ref:
            messagebox.showerror('Erreur', 'La référence est obligatoire.', parent=self)
            return
        if not desig:
            messagebox.showerror('Erreur', 'La désignation est obligatoire.', parent=self)
            return
        try:
            qte = int(self.var_add_qte.get().strip())
            if qte <= 0: raise ValueError
        except ValueError:
            messagebox.showerror('Erreur', 'La quantité doit être un entier positif.', parent=self)
            return

        # Ajouter à la liste
        self.articles_list.append({
            'id': None,
            'reference': ref,
            'code_barres': ref,
            'designation': desig,
            'quantite': qte,
            'unite': unite,
            'utilite_ligne': lignes,
            'nom_machine': machine,
            'is_new': True
        })

        # Réinitialiser le mini-formulaire
        self.var_add_ref.set('')
        self.var_add_designation.set('')
        self.var_add_qte.set('1')
        self._render_articles_list()

    def _supprimer_article_bon(self, index: int):
        if 0 <= index < len(self.articles_list):
            item = self.articles_list.pop(index)
            if item.get('id'):
                self.deleted_articles.append(item)
            self._render_articles_list()

    def _render_articles_list(self):
        for w in self.articles_container.winfo_children():
            w.destroy()

        self.lbl_articles_title.configure(
            text=f"📦  Articles de ce Bon ({len(self.articles_list)} ligne(s)) — Modifier Quantités ou Supprimer :"
        )
        self.article_entries = []

        for i, art in enumerate(self.articles_list):
            art_f = ctk.CTkFrame(self.articles_container, fg_color=COLORS['bg_card'], corner_radius=8, border_width=1, border_color=COLORS['border'])
            art_f.pack(fill='x', pady=4)

            top_line = ctk.CTkFrame(art_f, fg_color='transparent')
            top_line.pack(fill='x', padx=8, pady=(6, 2))

            new_badge = " [NOUVEAU]" if art.get('is_new') else ""
            ctk.CTkLabel(
                top_line, text=f"{i+1:02d}.  {art.get('designation', '—')}{new_badge}",
                font=FONTS['body_bold'], text_color=COLORS['primary'] if art.get('is_new') else COLORS['text_primary'], anchor='w'
            ).pack(side='left', fill='x', expand=True)

            ctk.CTkLabel(
                top_line, text=f"Réf: {art.get('code_barres', '—')}",
                font=FONTS['small'], text_color=COLORS['text_secondary']
            ).pack(side='right', padx=8)

            make_danger_button(
                top_line, '🗑️', command=lambda idx=i: self._supprimer_article_bon(idx), width=35
            ).pack(side='right', padx=4)

            qte_line = ctk.CTkFrame(art_f, fg_color='transparent')
            qte_line.pack(fill='x', padx=8, pady=(2, 6))

            ctk.CTkLabel(
                qte_line, text="Quantité :", font=FONTS['small_bold'],
                text_color=COLORS['text_secondary']
            ).pack(side='left', padx=(0, 6))

            var_qte = tk.StringVar(value=str(art.get('quantite', 1)))
            e_qte = ctk.CTkEntry(
                qte_line, textvariable=var_qte,
                fg_color=COLORS['bg_input'], border_color=COLORS['border'],
                border_width=1, text_color=COLORS['text_primary'],
                font=FONTS['body_bold'], width=80, height=28
            )
            e_qte.pack(side='left', padx=(0, 6))

            ctk.CTkLabel(
                qte_line, text=f"{art.get('unite', 'Unité')}  |  Ligne: {art.get('utilite_ligne', 'N/A')}  |  Machine: {art.get('nom_machine', 'N/A')}",
                font=FONTS['small'], text_color=COLORS['text_secondary']
            ).pack(side='left', padx=6)

            self.article_entries.append((art, e_qte))

    def _save(self):
        new_date = self.e_date.get().strip()
        new_service = self.e_service.get().strip()
        new_motif = self.e_motif.get().strip()
        new_demandeur = self.e_demandeur.get().strip() if hasattr(self, 'e_demandeur') else ''
        new_retourne = self.e_retourne.get().strip() if hasattr(self, 'e_retourne') else ''
        new_magasinier = self.e_magasinier.get().strip() if hasattr(self, 'e_magasinier') else ''

        if not self.articles_list:
            messagebox.showerror('Erreur Bon', 'Le bon doit contenir au moins un article.', parent=self)
            return

        # 1. Valider toutes les quantités
        updated_items = []
        for art, entry in self.article_entries:
            try:
                qte = int(entry.get().strip())
                if qte <= 0: raise ValueError
            except ValueError:
                messagebox.showerror('Erreur Quantité', f'Quantité invalide pour "{art.get("designation")}" (entier > 0 requis).', parent=self)
                return
            art['quantite'] = qte
            updated_items.append(art)

        # ── CAS PARTICULIER : BON DE COMMANDE ──
        if self.mvt.get('_source') == 'bons_commande':
            from services.pdf_generator import generer_bon_commande_pdf
            pdf_dir = get_config('pdf_directory', '')
            bc_articles = []
            for item in updated_items:
                bc_articles.append({
                    'reference': item.get('code_barres', '') or item.get('reference', ''),
                    'designation': item.get('designation', ''),
                    'quantite': item['quantite'],
                    'unite': item.get('unite', 'Unité'),
                    'observation': item.get('observation', '')
                })

            new_pdf_path = ''
            try:
                new_pdf_path = generer_bon_commande_pdf(
                    num_bc=self.num_doc,
                    fournisseur=new_service,
                    articles=bc_articles,
                    motif=new_motif,
                    pdf_dir=pdf_dir or None
                )
            except Exception as e:
                messagebox.showerror('Erreur PDF', f'Erreur lors de la régénération du Bon de Commande :\n{e}', parent=self)
                return

            try:
                db.enregistrer_bon_commande(
                    num_bc=self.num_doc,
                    fournisseur=new_service,
                    articles=bc_articles,
                    chemin_pdf=new_pdf_path,
                    date_heure=new_date if new_date else None
                )
            except Exception as e:
                messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer la commande en base :\n{e}', parent=self)
                return

            messagebox.showinfo('✅ Modifications Enregistrées',
                                f'Le Bon de Commande ({self.num_doc}) a été mis à jour avec succès !\n({len(updated_items)} article(s) enregistrés)',
                                parent=self)
            if self.on_save:
                self.on_save()
            if new_pdf_path and os.path.exists(new_pdf_path):
                ouvrir_pdf_viewer(self.master, new_pdf_path, title=f'Bon de Commande {self.num_doc}')
            self.destroy()
            return

        # 2. Supprimer les articles retirés du bon en BDD
        try:
            for item in self.deleted_articles:
                if item.get('id'):
                    db.update_mouvement(item['id'], quantite=0)
                    conn = db.get_connection()
                    conn.execute("DELETE FROM mouvements WHERE id = ?", (item['id'],))
                    conn.commit()
                    conn.close()
        except Exception as e:
            print(f"[DB Delete Warning] {e}")

        # 3. Enregistrer les nouveaux articles ajoutés au bon
        new_articles_to_save = [item for item in updated_items if item.get('is_new')]
        if new_articles_to_save:
            try:
                db.enregistrer_mouvements_multiples(
                    articles=new_articles_to_save,
                    type_mvt=self.mvt['type_mouvement'],
                    beneficiaire=new_service,
                    motif=new_motif,
                    demandeur=new_demandeur,
                    retourne_par=new_retourne,
                    fournisseur_nom=new_service if self.mvt['type_mouvement'] == 'ENTREE' else '',
                    date_heure=new_date if new_date else None,
                    magasinier=new_magasinier
                )
            except Exception as e:
                messagebox.showerror('Erreur Ajout Articles', f'Impossible d\'ajouter les nouveaux articles :\n{e}', parent=self)
                return

        # 4. Mettre à jour les articles existants
        existing_items = [item for item in updated_items if not item.get('is_new') and item.get('id')]
        try:
            for item in existing_items:
                db.update_mouvement(
                    mvt_id=item['id'],
                    date_heure=new_date if new_date else None,
                    quantite=item['quantite'],
                    beneficiaire_service=new_service,
                    motif=new_motif,
                    demandeur=new_demandeur,
                    retourne_par=new_retourne,
                    magasinier=new_magasinier
                )
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible de mettre à jour le bon :\n{e}', parent=self)
            return

        # 5. Régénérer le document PDF avec l'ensemble des articles du bon
        pdf_articles = []
        for item in updated_items:
            pdf_articles.append({
                'reference': item.get('code_barres', '') or item.get('reference', ''),
                'designation': item.get('designation', ''),
                'quantite': item['quantite'],
                'unite': item.get('unite', 'Unité'),
                'utilite_ligne': item.get('utilite_ligne', 'Aucune'),
                'nom_machine': item.get('nom_machine', 'N/A')
            })

        pdf_dir = get_config('pdf_directory', '')
        new_pdf_path = ''
        try:
            new_pdf_path = generer_bon_pdf(
                type_mvt=self.mvt['type_mouvement'],
                num_doc=self.num_doc,
                beneficiaire=new_service,
                fournisseur=new_service,
                motif=new_motif if self.mvt['type_mouvement'] != 'ENTREE' else '',
                articles=pdf_articles,
                pdf_dir=pdf_dir or None,
                demandeur=new_demandeur,
                retourne_par=new_retourne,
                magasinier=new_magasinier
            )
            # Mettre à jour le chemin PDF dans l'ensemble des mouvements du bon
            if new_pdf_path:
                for item in updated_items:
                    if item.get('id'):
                        db.update_mouvement(item['id'], chemin_pdf=new_pdf_path)
        except Exception as e:
            messagebox.showerror('Erreur PDF', f'Erreur lors de la régénération du PDF :\n{e}', parent=self)

        messagebox.showinfo('✅ Modifications Enregistrées',
                            f'Le {self.type_title} ({self.num_doc}) a été mis à jour avec succès !\n({len(updated_items)} article(s) enregistrés)',
                            parent=self)

        if self.on_save:
            self.on_save()

        if new_pdf_path and os.path.exists(new_pdf_path):
            ouvrir_pdf_viewer(self.master, new_pdf_path, title=f'Document {self.num_doc}')

        self.destroy()

