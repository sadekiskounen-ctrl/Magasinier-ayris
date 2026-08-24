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

from ui.theme import COLORS, FONTS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_secondary_button, make_success_button, SeparatorLine, make_combobox)
import database.db_manager as db
from services.pdf_generator import generer_bon_pdf
from services.config_manager import get_config
from ui.pdf_viewer import ouvrir_pdf_viewer

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
            filter_frame, ['Tous', 'Bons de Sortie', 'Bons de Réception', 'Bons de Retour', 'Bons de Commande'],
            width=190, variable=self.var_filtre
        )
        self.cb_filtre.pack(side='left', padx=(0, 10))
        self.cb_filtre.configure(command=self._apply_filter)

        # ── Filtre calendrier (date début / fin) ──
        ctk.CTkLabel(
            filter_frame, text='Du :',
            font=FONTS['small'], text_color=COLORS['text_secondary']
        ).pack(side='left', padx=(0, 4))

        if _HAS_CALENDAR:
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
            filter_frame, '↻ Actualiser', command=self.refresh, width=120
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
            columns=['date', 'type', 'produit', 'qte', 'service', 'pdf'],
            headings=['Date / Heure', 'Type', 'Désignation', 'Qté', 'Service / Tiers', 'PDF'],
            col_widths=[145, 80, 200, 60, 130, 60]
        )
        self.tv.pack(side='left', fill='both', expand=True)
        self.tv.bind('<<TreeviewSelect>>', self._on_select)
        self.tv.bind('<Double-1>', lambda e: self._ouvrir_pdf())
        add_scrollbar(tv_frame, self.tv)

        # Barre d'actions
        btns = ctk.CTkFrame(list_panel, fg_color='transparent')
        btns.pack(fill='x', padx=16, pady=(0, 12))

        make_primary_button(
            btns, 'Ouvrir PDF', command=self._ouvrir_pdf, icon='📄', width=150
        ).pack(side='left', padx=(0, 8))

        make_secondary_button(
            btns, '🖨️ Réimprimer', command=self._reimprimer, width=140
        ).pack(side='left', padx=(0, 8))

        make_secondary_button(
            btns, '📂 Dossier PDF', command=self._ouvrir_dossier, width=140
        ).pack(side='left', padx=(0, 8))

        self.btn_charger_plus = make_secondary_button(
            btns, '📥 Charger plus', command=self._charger_plus, width=180
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
        for w in self.detail_frame.winfo_children():
            w.destroy()

        t_type = mvt['type_mouvement']
        type_labels = {'SORTIE': '📤 Bon de Sortie', 'ENTREE': '📥 Bon de Réception', 'RETOUR': '↩️ Bon de Retour'}
        type_colors = {'SORTIE': COLORS['danger'], 'ENTREE': COLORS['success'], 'RETOUR': COLORS['warning']}

        ctk.CTkLabel(
            self.detail_frame, text=type_labels.get(t_type, t_type),
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

        def detail_row_input(icon, label, initial_val, var_name):
            f = ctk.CTkFrame(self.detail_frame, fg_color=COLORS['bg_hover'], corner_radius=8)
            f.pack(fill='x', padx=8, pady=2)
            ctk.CTkLabel(f, text=f'{icon} {label}', font=FONTS['small_bold'],
                         text_color=COLORS['text_secondary'], width=110, anchor='w').pack(side='left', padx=10, pady=6)
            var = tk.StringVar(value=str(initial_val if initial_val is not None else ''))
            setattr(self, var_name, var)
            entry = ctk.CTkEntry(
                f, textvariable=var,
                fg_color=COLORS['bg_input'], border_color=COLORS['border'],
                border_width=1, text_color=COLORS['text_primary'],
                font=FONTS['body'], height=32
            )
            entry.pack(side='left', fill='x', expand=True, padx=(4, 8), pady=4)
            return entry

        raw_dt = mvt.get('date_heure', '') or ''
        detail_row_input('📅', 'Date/Heure', raw_dt, '_var_edit_date')
        detail_row_static('📦', 'Produit', mvt.get('designation', '—'))
        detail_row_static('🏷️', 'Référence', mvt.get('code_barres', '—'))
        detail_row_input('🔢', 'Quantité', mvt.get('quantite', 0), '_var_edit_qte')
        detail_row_input('🏢', 'Service/Tiers', mvt.get('beneficiaire_service', ''), '_var_edit_service')

        if t_type == 'SORTIE' or mvt.get('demandeur'):
            detail_row_input('👤', 'Demandeur', mvt.get('demandeur', ''), '_var_edit_demandeur')
        if t_type == 'RETOUR' or mvt.get('retourne_par'):
            detail_row_input('👤', 'Retourné par', mvt.get('retourne_par', ''), '_var_edit_retourne')

        detail_row_input('📝', 'Motif', mvt.get('motif', ''), '_var_edit_motif')

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

        make_success_button(
            self.detail_frame, '💾 Enregistrer & Régénérer PDF',
            command=lambda m=mvt: self._save_and_regenerate_mvt(m),
            width=220
        ).pack(pady=(12, 6))

        if pdf_ok:
            make_primary_button(
                self.detail_frame, '📄 Afficher le PDF',
                command=lambda p=chemin_pdf: ouvrir_pdf_viewer(self, p, title='Document PDF'),
                icon='', width=220
            ).pack(pady=(0, 12))

    def _save_and_regenerate_mvt(self, mvt: dict):
        """Modifie les champs du mouvement en base de données et régénère le document PDF."""
        try:
            new_qte = int(getattr(self, '_var_edit_qte').get().strip())
            if new_qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Erreur', 'Quantité invalide (entier positif requis).', parent=self)
            return

        new_date = getattr(self, '_var_edit_date').get().strip()
        new_service = getattr(self, '_var_edit_service').get().strip()
        new_motif = getattr(self, '_var_edit_motif').get().strip()
        new_demandeur = getattr(self, '_var_edit_demandeur').get().strip() if hasattr(self, '_var_edit_demandeur') else ''
        new_retourne_par = getattr(self, '_var_edit_retourne').get().strip() if hasattr(self, '_var_edit_retourne') else ''

        t_type = mvt['type_mouvement']

        # Retrouver le numéro de document
        chemin_existant = mvt.get('chemin_pdf', '')
        num_doc = ''
        if chemin_existant:
            base_name = os.path.basename(chemin_existant)
            parts = base_name.split('_')
            if len(parts) >= 3 and parts[0] in ('BR', 'BS', 'BT'):
                num_doc = f"{parts[1]}-{parts[2]}"
            elif len(parts) >= 2:
                num_doc = parts[1]
        if not num_doc:
            num_doc = f"DOC-{mvt['id']:04d}"

        # Régénérer le fichier PDF avec les nouvelles données
        article = {
            'reference': mvt.get('code_barres', ''),
            'designation': mvt.get('designation', ''),
            'quantite': new_qte,
            'unite': mvt.get('unite', 'Unité'),
            'utilite_ligne': mvt.get('utilite_ligne', 'Aucune'),
            'nom_machine': mvt.get('nom_machine', 'N/A')
        }

        pdf_dir = get_config('pdf_directory', '')
        new_chemin_pdf = ''
        try:
            new_chemin_pdf = generer_bon_pdf(
                type_mvt=t_type,
                num_doc=num_doc,
                beneficiaire=new_service,
                fournisseur=new_service,
                motif=new_motif if t_type != 'ENTREE' else '',
                articles=[article],
                pdf_dir=pdf_dir or None,
                demandeur=new_demandeur,
                retourne_par=new_retourne_par
            )
        except Exception as e:
            messagebox.showerror('Erreur PDF', f'Erreur lors de la régénération du PDF :\n{e}', parent=self)

        # Mettre à jour la base de données (y compris l'ajustement du stock)
        ok = db.update_mouvement(
            mvt_id=mvt['id'],
            date_heure=new_date if new_date else None,
            quantite=new_qte,
            beneficiaire_service=new_service,
            motif=new_motif,
            demandeur=new_demandeur,
            retourne_par=new_retourne_par,
            chemin_pdf=new_chemin_pdf if new_chemin_pdf else None
        )

        if ok:
            messagebox.showinfo('✅ Modifications Enregistrées',
                                'Les modifications ont été enregistrées et le PDF a été mis à jour avec succès !',
                                parent=self)
            self.refresh()
            if new_chemin_pdf and os.path.exists(new_chemin_pdf):
                ouvrir_pdf_viewer(self, new_chemin_pdf, title=f'Document {num_doc}')
        else:
            messagebox.showerror('Erreur', 'Échec de la mise à jour en base de données.', parent=self)

    def refresh(self):
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
        """Efface le filtre de date et réaffiche tout."""
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
        d_debut, d_fin = self._get_date_filter()

        filtre_map = {
            'Bons de Sortie': 'SORTIE',
            'Bons de Réception': 'ENTREE',
            'Bons de Retour': 'RETOUR',
            'Bons de Commande': 'COMMANDE'
        }
        filtre_type = filtre_map.get(value)

        self._total_count = db.get_mouvements_count(type_filtre=filtre_type, date_debut=d_debut, date_fin=d_fin)
        new_mvts = db.get_all_mouvements(type_filtre=filtre_type, date_debut=d_debut, date_fin=d_fin,
                                          limit=self._page_size, offset=self._current_offset)

        if reset:
            self._all_mouvements = list(new_mvts)
            for item in self.tv.get_children():
                self.tv.delete(item)
        else:
            self._all_mouvements.extend(new_mvts)

        for m in new_mvts:
            t_type = m['type_mouvement']
            tag_map = {'SORTIE': 'sortie', 'ENTREE': 'entree', 'RETOUR': 'retour', 'COMMANDE': 'even'}
            tag = tag_map.get(t_type, 'even')

            raw_dt = m.get('date_heure', '') or ''
            try:
                dt_obj = datetime.strptime(raw_dt[:19], '%Y-%m-%d %H:%M:%S')
                date_str = dt_obj.strftime('%Y-%m-%d  %H:%M')
            except Exception:
                date_str = raw_dt[:16] if raw_dt else ''

            type_str = {'SORTIE': '📤 BS', 'ENTREE': '📥 BR', 'RETOUR': '↩️ BT', 'COMMANDE': '🛒 BC'}.get(t_type, t_type)
            pdf_str = '✅' if (m.get('chemin_pdf') and os.path.exists(m.get('chemin_pdf', ''))) else '❌'

            self.tv.insert('', 'end', iid=str(m['id']), values=(
                date_str,
                type_str,
                m.get('designation', ''),
                str(m.get('quantite', '')),
                m.get('beneficiaire_service', ''),
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
        mvt_id = int(sel[0])
        mvt = next((m for m in self._all_mouvements if m['id'] == mvt_id), None)
        if mvt:
            self._show_detail(mvt)

    def _get_selected_mvt(self) -> dict | None:
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner un document.', parent=self)
            return None
        mvt_id = int(sel[0])
        return next((m for m in self._all_mouvements if m['id'] == mvt_id), None)

    def _ouvrir_pdf(self):
        mvt = self._get_selected_mvt()
        if not mvt:
            return
        chemin = mvt.get('chemin_pdf', '')
        if chemin and os.path.exists(chemin):
            t_type = mvt.get('type_mouvement', '')
            label_map = {'SORTIE': 'Bon de Sortie', 'ENTREE': 'Bon de Réception',
                         'RETOUR': 'Bon de Retour', 'COMMANDE': 'Bon de Commande'}
            ouvrir_pdf_viewer(self, chemin, title=label_map.get(t_type, 'Document PDF'))
        else:
            messagebox.showerror('PDF Introuvable', f'Fichier introuvable :\n{chemin}', parent=self)

    def _reimprimer(self):
        mvt = self._get_selected_mvt()
        if not mvt:
            return

        num_doc = db.get_num_document(mvt['type_mouvement']) + '-REIMP'
        article = {
            'reference': mvt.get('code_barres', ''),
            'designation': mvt.get('designation', ''),
            'emplacement': '',
            'unite': mvt.get('unite', 'Unité'),
            'quantite': mvt.get('quantite', 0),
        }
        pdf_dir = get_config('pdf_directory', '')
        try:
            chemin_pdf = generer_bon_pdf(
                type_mvt=mvt['type_mouvement'],
                num_doc=num_doc,
                beneficiaire=mvt.get('beneficiaire_service', ''),
                motif=mvt.get('motif', ''),
                articles=[article],
                pdf_dir=pdf_dir or None
            )
            messagebox.showinfo('PDF Régénéré', f'PDF réimprimé avec succès !', parent=self)
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
