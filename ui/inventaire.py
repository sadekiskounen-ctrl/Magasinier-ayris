"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/inventaire.py
Écran Inventaire avec filtres de dates interactifs (Calendrier) et export Excel.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
import os

from ui.theme import COLORS, FONTS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_secondary_button, make_input, SeparatorLine,
                         BadgeLabel, DatePickerInput)
import database.db_manager as db
from services.excel_generator import exporter_inventaire_excel


class InventaireFrame(ctk.CTkFrame):
    """Écran Inventaire & Export Excel."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._journees = []
        self._journee_selectionnee = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text='📋  Inventaire & Rapports Excel',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Barre de filtre avec DatePicker (Calendrier) ──────────────────────
        filter_bar = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=12,
                                  border_width=1, border_color=COLORS['border'])
        filter_bar.pack(fill='x', padx=24, pady=12)

        ctk.CTkLabel(filter_bar, text='📅  Période :', font=FONTS['subtitle'],
                     text_color=COLORS['text_primary']).pack(side='left', padx=(16, 12), pady=12)

        default_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        default_end = datetime.now().strftime('%Y-%m-%d')

        # Utilisation de DatePickerInput pour sélectionner la date de début
        ctk.CTkLabel(filter_bar, text='Du :', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary']).pack(side='left', padx=(0, 6))
        self.e_date_debut = DatePickerInput(filter_bar, initial_date=default_start, width=160)
        self.e_date_debut.pack(side='left', padx=(0, 16), pady=8)

        # Utilisation de DatePickerInput pour sélectionner la date de fin
        ctk.CTkLabel(filter_bar, text='Au :', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary']).pack(side='left', padx=(0, 6))
        self.e_date_fin = DatePickerInput(filter_bar, initial_date=default_end, width=160)
        self.e_date_fin.pack(side='left', padx=(0, 20), pady=8)

        make_secondary_button(filter_bar, '🔍 Filtrer', command=self.refresh, width=120).pack(side='left', padx=(0, 8))

        # Bouton Exporter Excel
        make_primary_button(
            filter_bar, '📊 Exporter en Excel', command=self._exporter_excel,
            icon='', width=200
        ).pack(side='right', padx=16, pady=12)

        # ── Corps principal (2 colonnes) ──────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=24, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # ── Panneau Gauche : Liste des Journées ──────────────────────────────
        left_panel = ctk.CTkFrame(
            body, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1,
            border_color=COLORS['border']
        )
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

        left_header = ctk.CTkFrame(left_panel, fg_color='transparent')
        left_header.pack(fill='x', padx=16, pady=(12, 8))

        ctk.CTkLabel(left_header, text='🗓️  Journées d\'Activité',
                     font=FONTS['subtitle'], text_color=COLORS['text_primary']).pack(side='left')

        self.badge_journees = BadgeLabel(left_header, '0 jour(s)', color=COLORS['primary'])
        self.badge_journees.pack(side='right')

        make_secondary_button(
            left_header, '☑ Tout sélectionner', command=self._select_all_journees, width=150
        ).pack(side='right', padx=(0, 8))

        tv_frame_left = ctk.CTkFrame(left_panel, fg_color='transparent')
        tv_frame_left.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        self.tv_journees = StyledTreeview(
            tv_frame_left,
            columns=['jour', 'mouvements', 'entrees', 'sorties', 'retours'],
            headings=['Date / Journée', 'Mvmts', 'Entrées', 'Sorties', 'Retours'],
            col_widths=[140, 70, 80, 80, 80]
        )
        self.tv_journees.pack(side='left', fill='both', expand=True)
        self.tv_journees.bind('<<TreeviewSelect>>', self._on_select_journee)
        self.tv_journees.bind('<Button-1>', self._on_journee_click)
        add_scrollbar(tv_frame_left, self.tv_journees)

        # ── Panneau Droit : Détail de la Journée Sélectionnée ──────────────
        right_panel = ctk.CTkFrame(
            body, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1,
            border_color=COLORS['border']
        )
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

        right_header = ctk.CTkFrame(right_panel, fg_color='transparent')
        right_header.pack(fill='x', padx=16, pady=(12, 8))

        self.lbl_detail_title = ctk.CTkLabel(
            right_header, text='🔎  Détail du Jour : (Sélectionnez une date)',
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        )
        self.lbl_detail_title.pack(side='left')

        tv_frame_right = ctk.CTkFrame(right_panel, fg_color='transparent')
        tv_frame_right.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        self.tv_detail = StyledTreeview(
            tv_frame_right,
            columns=['heure', 'type', 'code', 'produit', 'qte', 'service'],
            headings=['Heure', 'Type', 'Référence', 'Désignation', 'Qté', 'Service / Tiers'],
            col_widths=[70, 80, 110, 160, 60, 130]
        )
        self.tv_detail.pack(side='left', fill='both', expand=True)
        self.tv_detail.bind('<Button-1>', self._on_detail_click)
        add_scrollbar(tv_frame_right, self.tv_detail)

    def refresh(self):
        """Recharge les journées selon la période sélectionnée."""
        debut = self.e_date_debut.get()
        fin = self.e_date_fin.get()

        for item in self.tv_journees.get_children():
            self.tv_journees.delete(item)

        for item in self.tv_detail.get_children():
            self.tv_detail.delete(item)

        self.lbl_detail_title.configure(text='🔎  Détail du Jour : (Sélectionnez une date)')

        try:
            self._journees = db.get_inventaire_par_periode(debut, fin)
        except Exception as e:
            messagebox.showerror('Erreur Filtre', f'Format de date invalide (AAAA-MM-JJ) :\n{e}', parent=self)
            return

        self.badge_journees.configure(text=f"{len(self._journees)} jour(s)")

        for j in self._journees:
            self.tv_journees.insert('', 'end', iid=j['jour'], values=(
                j['jour'],
                str(j['nb_mouvements']),
                f"+{j['total_entrees'] or 0}",
                f"-{j['total_sorties'] or 0}",
                f"+{j['total_retours'] or 0}"
            ))
        self.tv_journees.autofit_columns()

    def _on_journee_click(self, event):
        """Désélectionne si clic sur zone vide."""
        item = self.tv_journees.identify_row(event.y)
        if not item:
            self.tv_journees.selection_set([])
            for i in self.tv_detail.get_children():
                self.tv_detail.delete(i)
            self.lbl_detail_title.configure(text='\U0001f50e  Détail du Jour : (Sélectionnez une date)')

    def _on_detail_click(self, event):
        """Désélectionne le détail si clic sur zone vide."""
        item = self.tv_detail.identify_row(event.y)
        if not item:
            self.tv_detail.selection_set([])

    def _select_all_journees(self):
        children = self.tv_journees.get_children()
        if children:
            self.tv_journees.selection_set(children)
            self._on_select_journee(None)

    def _on_select_journee(self, event):
        sel = self.tv_journees.selection()
        if not sel:
            return
        if len(sel) == 1:
            self._afficher_detail_journee(sel[0])
        else:
            self._afficher_detail_multiple_journees(list(sel))

    def _afficher_detail_multiple_journees(self, dates: list):
        for item in self.tv_detail.get_children():
            self.tv_detail.delete(item)

        self.lbl_detail_title.configure(text=f'🔎  Détail cumulé : {len(dates)} journées sélectionnées')

        tous_mouvements = []
        for date_jour in dates:
            mouvements = db.get_mouvements_journee(date_jour)
            tous_mouvements.extend(mouvements)

        for m in tous_mouvements:
            type_str = m['type_mouvement']
            tag = 'entree' if type_str == 'ENTREE' else ('sortie' if type_str == 'SORTIE' else 'retour')
            date_heure_str = m.get('date_heure', '')[:16]

            qte_prefix = '+' if type_str in ('ENTREE', 'RETOUR') else '-'

            self.tv_detail.insert('', 'end', values=(
                date_heure_str,
                type_str,
                m.get('code_barres', ''),
                m.get('designation', ''),
                f"{qte_prefix}{m['quantite']}",
                m.get('beneficiaire_service', '')
            ), tags=(tag,))
        self.tv_detail.autofit_columns()

    def _afficher_detail_journee(self, date_jour: str):
        for item in self.tv_detail.get_children():
            self.tv_detail.delete(item)

        self.lbl_detail_title.configure(text=f'🔎  Détail du Jour : {date_jour}')

        mouvements = db.get_mouvements_journee(date_jour)
        for m in mouvements:
            type_str = m['type_mouvement']
            tag = 'entree' if type_str == 'ENTREE' else ('sortie' if type_str == 'SORTIE' else 'retour')
            heure_str = m['date_heure'][11:16] if m.get('date_heure') else ''

            qte_prefix = '+' if type_str in ('ENTREE', 'RETOUR') else '-'

            self.tv_detail.insert('', 'end', values=(
                heure_str,
                type_str,
                m.get('code_barres', ''),
                m.get('designation', ''),
                f"{qte_prefix}{m['quantite']}",
                m.get('beneficiaire_service', '')
            ), tags=(tag,))
        self.tv_detail.autofit_columns()

    def _exporter_excel(self):
        debut = self.e_date_debut.get()
        fin = self.e_date_fin.get()

        default_filename = f"Inventaire_SARL_NOMADE_AYRIS_{debut}_au_{fin}.xlsx".replace('-', '_')
        dest = filedialog.asksaveasfilename(
            title='Exporter l\'Inventaire en Excel',
            defaultextension='.xlsx',
            initialfile=default_filename,
            filetypes=[('Fichier Excel', '*.xlsx'), ('Tous les fichiers', '*.*')],
            parent=self
        )
        if not dest:
            return

        try:
            res_path = exporter_inventaire_excel(debut, fin, dest)
            open_file = messagebox.askyesno(
                'Export Réussi',
                f'L\'inventaire a été exporté avec succès !\n\nFichier : {res_path}\n\nVoulez-vous l\'ouvrir maintenant ?',
                parent=self
            )
            if open_file and os.path.exists(res_path):
                os.startfile(res_path)
        except Exception as e:
            messagebox.showerror('Erreur Export', f'Erreur lors de la génération Excel :\n{e}', parent=self)
