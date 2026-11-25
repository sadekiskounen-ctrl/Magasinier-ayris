"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/engins.py
Écran de gestion des Produits d'Engins (Camion & Clarck) avec filtres, recherche et modale dynamique.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from ui.theme import COLORS, FONTS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_danger_button, make_secondary_button,
                         make_input, make_combobox, SearchBar, SeparatorLine)
import database.db_manager as db

MARQUES_CAMION = ['Renault', 'Hyundai', 'JAC', 'JMC']
MARQUES_CLARCK = ['Hyster', 'Hili', 'Tirsam', 'Linde', 'Hyundai', 'Toyota']


class EnginsFrame(ctk.CTkFrame):
    """Écran Produit d'Engins avec filtrage Camion / Clarck, alertes de stock et export Excel."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._search_term = ""
        self._type_filter = "Tous"
        self._filter_stock_alerte = False
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text="🚜  Produit d'Engins",
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        self.badge_total = ctk.CTkLabel(
            header, text='0 référence(s)',
            font=FONTS['body_bold'],
            text_color=COLORS['text_secondary']
        )
        self.badge_total.pack(side='left', padx=12, pady=(4, 0))

        self.badge_alerts = ctk.CTkLabel(
            header, text='',
            font=FONTS['body_bold'],
            text_color=COLORS['danger'],
            fg_color=COLORS['danger_bg'],
            corner_radius=6
        )
        self.badge_alerts.pack(side='left', padx=4, pady=(4, 0))

        btn_frame = ctk.CTkFrame(header, fg_color='transparent')
        btn_frame.pack(side='right')

        make_primary_button(
            btn_frame, 'Nouveau Produit Engin', command=self._open_add_modal,
            icon='＋', width=210
        ).pack(side='left', padx=4)

        self.btn_edit = make_secondary_button(
            btn_frame, '✏️ Modifier', command=self._open_edit_modal, width=120
        )
        self.btn_edit.pack(side='left', padx=4)

        self.btn_del = make_danger_button(
            btn_frame, '🗑️ Supprimer', command=self._delete_selected, width=120
        )
        self.btn_del.pack(side='left', padx=4)

        make_success_button(
            btn_frame, '📊 Exporter vers Excel', command=self._exporter_excel, width=170
        ).pack(side='left', padx=4)

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Barre de recherche + Filtre Type Engin + Filtre Stock Alerte ──────
        filter_row = ctk.CTkFrame(self, fg_color='transparent')
        filter_row.pack(fill='x', padx=24, pady=12)

        SearchBar(
            filter_row,
            placeholder='Rechercher par Référence, Désignation, Marque...',
            on_change=self._on_search, width=320
        ).pack(side='left', padx=(0, 12))

        # Switcher Type Engin
        filter_type_frame = ctk.CTkFrame(
            filter_row, fg_color=COLORS['bg_card'],
            corner_radius=8, border_width=1, border_color=COLORS['border']
        )
        filter_type_frame.pack(side='left', padx=(0, 10))

        self.btn_f_tous = ctk.CTkButton(
            filter_type_frame, text='Tous les Engins',
            command=lambda: self._set_type_filter('Tous'),
            fg_color=COLORS['primary'], text_color='white',
            font=FONTS['body_bold'], corner_radius=6, height=36, width=130
        )
        self.btn_f_tous.pack(side='left', padx=2, pady=2)

        self.btn_f_camion = ctk.CTkButton(
            filter_type_frame, text='🚛 Camion',
            command=lambda: self._set_type_filter('Camion'),
            fg_color='transparent', text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'], corner_radius=6, height=36, width=110
        )
        self.btn_f_camion.pack(side='left', padx=2, pady=2)

        self.btn_f_clarck = ctk.CTkButton(
            filter_type_frame, text='🚜 Clarck',
            command=lambda: self._set_type_filter('Clarck'),
            fg_color='transparent', text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'], corner_radius=6, height=36, width=110
        )
        self.btn_f_clarck.pack(side='left', padx=2, pady=2)

        # Bouton filtre Stock Alerte
        self.btn_filter_alerte = ctk.CTkButton(
            filter_row,
            text='⚠️ Stock Alerte : Tous ▾',
            command=self._toggle_stock_alerte_filter,
            fg_color=COLORS['bg_input'],
            hover_color=COLORS['bg_hover'],
            text_color=COLORS['text_primary'],
            border_color=COLORS['border'],
            border_width=1,
            font=FONTS['body_bold'],
            corner_radius=8, height=40, width=170
        )
        self.btn_filter_alerte.pack(side='left', padx=(0, 8))

        make_secondary_button(
            filter_row, '✖ Réinitialiser', command=self._reset_filters, width=130
        ).pack(side='left')

        # ── Tableau Produits Engins ──────────────────────────────────────────
        tv_frame = ctk.CTkFrame(
            self, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1,
            border_color=COLORS['border']
        )
        tv_frame.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        inner = ctk.CTkFrame(tv_frame, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=8, pady=8)

        self.tv = StyledTreeview(
            inner,
            columns=['alerte', 'type', 'reference', 'marque', 'designation', 'stock', 'seuil'],
            headings=['⚠', 'Type Engin', 'Référence', 'Marque', 'Désignation Pièce', 'Stock', 'Seuil'],
            col_widths=[36, 120, 150, 130, 240, 80, 70]
        )
        self.tv.pack(side='left', fill='both', expand=True)
        self.tv.bind('<Double-1>', lambda e: self._open_edit_modal())
        add_scrollbar(inner, self.tv)

    def _set_type_filter(self, t_filter: str):
        self._type_filter = t_filter
        for tf, btn in [('Tous', self.btn_f_tous), ('Camion', self.btn_f_camion), ('Clarck', self.btn_f_clarck)]:
            if tf == t_filter:
                btn.configure(fg_color=COLORS['primary'], text_color='white')
            else:
                btn.configure(fg_color='transparent', text_color=COLORS['text_secondary'])
        self.refresh()

    def _toggle_stock_alerte_filter(self):
        """Bascule le filtre Stock Alerte pour les engins."""
        self._filter_stock_alerte = not self._filter_stock_alerte
        if self._filter_stock_alerte:
            self.btn_filter_alerte.configure(
                text='⚠️ Stock Alerte : Oui',
                fg_color=COLORS['danger'],
                text_color=COLORS['text_white'],
                hover_color=COLORS['danger']
            )
        else:
            self.btn_filter_alerte.configure(
                text='⚠️ Stock Alerte : Tous ▾',
                fg_color=COLORS['bg_input'],
                text_color=COLORS['text_primary'],
                hover_color=COLORS['bg_hover']
            )
        self.refresh()

    def _reset_filters(self):
        self._type_filter = "Tous"
        self._filter_stock_alerte = False
        self._set_type_filter("Tous")
        self.btn_filter_alerte.configure(
            text='⚠️ Stock Alerte : Tous ▾',
            fg_color=COLORS['bg_input'],
            text_color=COLORS['text_primary'],
            hover_color=COLORS['bg_hover']
        )
        self.refresh()

    def _on_search(self, term: str):
        self._search_term = term.strip()
        self.refresh()

    def _get_filtered_produits(self) -> list:
        produits = db.get_all_produits_engins(search=self._search_term, type_filter=self._type_filter)
        if self._filter_stock_alerte:
            produits = [p for p in produits if p.get('quantite_stock', 0) <= p.get('seuil_alerte', 5)]
        return produits

    def refresh(self):
        for item in self.tv.get_children():
            self.tv.delete(item)

        produits = self._get_filtered_produits()
        nb_alerts = sum(1 for p in produits if p['quantite_stock'] <= p['seuil_alerte'])
        self.badge_total.configure(text=f'{len(produits)} référence(s)')
        self.badge_alerts.configure(
            text=f'  ⚠️ {nb_alerts} alerte(s) de stock  ' if nb_alerts > 0 else ''
        )

        for i, p in enumerate(produits):
            en_alerte = p['quantite_stock'] <= p['seuil_alerte']
            tag = 'alert' if en_alerte else ('even' if i % 2 == 0 else 'odd')
            type_str = '🚛 Camion' if p['type_engin'] == 'Camion' else '🚜 Clarck'
            self.tv.insert('', 'end', iid=str(p['id']), values=(
                '⚠️' if en_alerte else '',
                type_str,
                p['reference'],
                p['marque'],
                p['designation'],
                str(p['quantite_stock']),
                str(p['seuil_alerte'])
            ), tags=(tag,))
        self.tv.autofit_columns()

    def _exporter_excel(self):
        """Exporte les pièces engins actuellement filtrées vers un fichier Excel (.xlsx)."""
        from tkinter import filedialog
        from datetime import datetime
        import os
        from services.excel_generator import exporter_engins_excel

        produits = self._get_filtered_produits()
        if not produits:
            messagebox.showwarning('Export Excel', 'Aucune pièce engin ne correspond aux filtres actuels.', parent=self)
            return

        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        if self._filter_stock_alerte:
            default_filename = f"Export_Engins_Alerte_Stock_AYRIS_{date_str}.xlsx"
            dialog_title = "Enregistrer l'export Excel des Produits Engins en Alerte Stock"
        else:
            default_filename = f"Export_Produits_Engins_AYRIS_{date_str}.xlsx"
            dialog_title = "Enregistrer l'export Excel des Produits d'Engins"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title=dialog_title,
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx")]
        )

        if not file_path:
            return

        try:
            exporter_engins_excel(produits, file_path)
            export_msg = (
                f'La liste de {len(produits)} produit(s) engin(s) en alerte de stock a été exportée avec succès !'
                if self._filter_stock_alerte else
                f'Le catalogue de {len(produits)} produit(s) d\'engin(s) a été exporté avec succès !'
            )
            messagebox.showinfo(
                '✅ Export Réussi',
                f'{export_msg}\n\nFichier : {file_path}',
                parent=self
            )
            if messagebox.askyesno('Ouvrir Excel', 'Voulez-vous ouvrir le fichier Excel généré ?', parent=self):
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror('Erreur Export', f'Échec de la génération du fichier Excel :\n{e}', parent=self)

    def _get_selected_id(self) -> int | None:
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner un produit engin.', parent=self)
            return None
        return int(sel[0])

    def _open_add_modal(self):
        EnginProductModal(self, mode='add', on_save=self.refresh)

    def _open_edit_modal(self):
        eid = self._get_selected_id()
        if eid is None:
            return
        produit = db.get_produit_engin_by_id(eid)
        if produit:
            EnginProductModal(self, mode='edit', produit=produit, on_save=self.refresh)

    def _delete_selected(self):
        eid = self._get_selected_id()
        if eid is None:
            return
        produit = db.get_produit_engin_by_id(eid)
        if not produit:
            return
        confirm = messagebox.askyesno(
            'Confirmer la suppression',
            f'Supprimer la pièce engin :\n\n  {produit["designation"]} ({produit["reference"]}) ?\n\n'
            'Cette action est irréversible.',
            parent=self
        )
        if confirm:
            db.supprimer_produit_engin(eid)
            self.refresh()


# ─────────────────────── Modale Produit Engin ──────────────────────────────────

class EnginProductModal(ctk.CTkToplevel):
    """Fenêtre modale pour ajouter ou modifier un produit d'engin (Camion / Clarck)."""

    def __init__(self, parent, mode: str = 'add', produit: dict = None, on_save=None):
        super().__init__(parent)
        self.mode = mode
        self.produit = produit or {}
        self.on_save = on_save

        self.title('➕ Nouveau Produit Engin' if mode == 'add' else '✏️ Modifier Produit Engin')
        self.geometry('600x580')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self._build_ui()
        if mode == 'edit' and produit:
            self._fill_fields()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text='➕  Nouveau Produit Engin' if self.mode == 'add' else '✏️  Modifier Produit Engin',
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(18, 4), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 10))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24)

        # Type Engin (Camion / Clarck)
        frame_type = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_type.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_type, text='Type Engin *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')

        self.var_type = tk.StringVar(value='Camion')
        rb_camion = ctk.CTkRadioButton(
            frame_type, text='🚛 Camion', variable=self.var_type, value='Camion',
            command=self._on_type_changed, font=FONTS['body_bold'],
            fg_color=COLORS['primary'], text_color=COLORS['text_primary']
        )
        rb_camion.pack(side='left', padx=(0, 20))

        rb_clarck = ctk.CTkRadioButton(
            frame_type, text='🚜 Clarck', variable=self.var_type, value='Clarck',
            command=self._on_type_changed, font=FONTS['body_bold'],
            fg_color=COLORS['primary'], text_color=COLORS['text_primary']
        )
        rb_clarck.pack(side='left')

        # Marque (Dynamique)
        frame_marque = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_marque.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_marque, text='Marque *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.var_marque = tk.StringVar(value=MARQUES_CAMION[0])
        self.cb_marque = make_combobox(frame_marque, MARQUES_CAMION, width=280, variable=self.var_marque)
        self.cb_marque.pack(side='left')

        # Référence
        frame_ref = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_ref.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_ref, text='Référence *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_ref = make_input(frame_ref, placeholder='Ex: REF-CAM-101', width=280)
        self.e_ref.pack(side='left')

        # Désignation de la pièce
        frame_des = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_des.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_des, text='Désignation Pièce *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_design = make_input(frame_des, placeholder='Désignation de la pièce...', width=280)
        self.e_design.pack(side='left')

        # Quantité
        frame_qte = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_qte.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_qte, text='Quantité Stock *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_qte = make_input(frame_qte, placeholder='0', width=280)
        self.e_qte.pack(side='left')

        # Seuil d'Alerte
        frame_seuil = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_seuil.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_seuil, text="Seuil d'Alerte", font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_seuil = make_input(frame_seuil, placeholder='5', width=280)
        self.e_seuil.pack(side='left')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(12, 0))
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=24, pady=12)

        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=120).pack(side='right', padx=(6, 0))
        make_primary_button(
            btn_frame, 'Enregistrer' if self.mode == 'add' else 'Sauvegarder',
            command=self._save, icon='💾', width=180
        ).pack(side='right')

    def _on_type_changed(self):
        t_type = self.var_type.get()
        marques = MARQUES_CAMION if t_type == 'Camion' else MARQUES_CLARCK
        self.cb_marque.configure(values=marques)
        self.var_marque.set(marques[0])

    def _fill_fields(self):
        p = self.produit
        self.var_type.set(p.get('type_engin', 'Camion'))
        self._on_type_changed()

        marque = p.get('marque', '')
        if marque:
            self.var_marque.set(marque)

        self.e_ref.insert(0, p.get('reference', ''))
        self.e_design.insert(0, p.get('designation', ''))
        self.e_qte.insert(0, str(p.get('quantite_stock', 0)))
        self.e_seuil.insert(0, str(p.get('seuil_alerte', 5)))

    def _save(self):
        reference = self.e_ref.get().strip()
        designation = self.e_design.get().strip()

        if not reference:
            messagebox.showerror('Erreur', 'La Référence est obligatoire.', parent=self)
            return
        if not designation:
            messagebox.showerror('Erreur', 'La Désignation est obligatoire.', parent=self)
            return
        try:
            qte = int(self.e_qte.get() or 0)
            seuil = int(self.e_seuil.get() or 5)
        except ValueError:
            messagebox.showerror('Erreur', 'La quantité et le seuil doivent être des entiers.', parent=self)
            return

        data = {
            'type_engin':     self.var_type.get(),
            'reference':      reference,
            'marque':         self.var_marque.get(),
            'designation':    designation,
            'quantite_stock': qte,
            'seuil_alerte':   seuil
        }

        try:
            if self.mode == 'add':
                db.ajouter_produit_engin(data)
                messagebox.showinfo('Succès', f'Pièce engin "{designation}" ajoutée !', parent=self)
            else:
                db.modifier_produit_engin(self.produit['id'], data)
                messagebox.showinfo('Succès', f'Pièce engin "{designation}" mise à jour !', parent=self)

            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer :\n{e}', parent=self)
