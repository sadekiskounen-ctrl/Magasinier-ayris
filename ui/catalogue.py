"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/catalogue.py
Catalogue produits avec filtres multi-sélection Ligne/Machine, triangle d'alerte et auto-suffixe référence.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from ui.theme import (COLORS, FONTS, LIGNES, UNITES, MACHINES_SPECIFIQUES,
                      get_machines_pour_lignes, SOUS_LIGNES_CONVOYEUR, SOUS_LIGNES_COMPRESSEUR)
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_danger_button, make_secondary_button,
                         make_input, make_combobox, SearchBar, SeparatorLine,
                         MultiSelectLignesWidget)
import database.db_manager as db


class CatalogueFrame(ctk.CTkFrame):
    """Écran Catalogue Produits avec filtres multi-sélection et alertes visuelles."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._search_term = ""
        self._selected_lignes = set()       # vide = Toutes
        self._selected_machines = set()     # vide = Toutes
        self._selected_categories = set()   # vide = Toutes
        self._search_timer = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text='📦  Produit Pièce de Rechange',
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
            btn_frame, 'Nouveau Produit', command=self._open_add_modal,
            icon='＋', width=180
        ).pack(side='left', padx=4)

        self.btn_edit = make_secondary_button(
            btn_frame, '✏️ Modifier', command=self._open_edit_modal, width=120
        )
        self.btn_edit.pack(side='left', padx=4)

        self.btn_del = make_danger_button(
            btn_frame, '🗑️ Supprimer', command=self._delete_selected, width=120
        )
        self.btn_del.pack(side='left', padx=4)

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Barre de recherche + Filtres multi-sélection ──────────────────────
        filter_row = ctk.CTkFrame(self, fg_color='transparent')
        filter_row.pack(fill='x', padx=24, pady=12)

        SearchBar(
            filter_row,
            placeholder='Rechercher par Référence, Désignation, Ligne, Machine...',
            on_change=self._on_search, width=320
        ).pack(side='left', padx=(0, 10))

        # Bouton filtre Catégorie (multi-sélection via popup)
        self.btn_filter_cat = ctk.CTkButton(
            filter_row,
            text='🏷️ Catégorie : Toutes ▾',
            command=self._open_cat_filter_popup,
            fg_color=COLORS['bg_input'],
            hover_color=COLORS['bg_hover'],
            text_color=COLORS['text_primary'],
            border_color=COLORS['border'],
            border_width=1,
            font=FONTS['body_bold'],
            corner_radius=8, height=40, width=190
        )
        self.btn_filter_cat.pack(side='left', padx=(0, 8))

        # Bouton filtre Ligne (multi-sélection via popup)
        self.btn_filter_ligne = ctk.CTkButton(
            filter_row,
            text='🏭 Ligne : Toutes ▾',
            command=self._open_ligne_filter_popup,
            fg_color=COLORS['bg_input'],
            hover_color=COLORS['bg_hover'],
            text_color=COLORS['text_primary'],
            border_color=COLORS['border'],
            border_width=1,
            font=FONTS['body_bold'],
            corner_radius=8, height=40, width=180
        )
        self.btn_filter_ligne.pack(side='left', padx=(0, 8))

        # Bouton filtre Machine (multi-sélection via popup)
        self.btn_filter_machine = ctk.CTkButton(
            filter_row,
            text='⚙️ Machine : Toutes ▾',
            command=self._open_machine_filter_popup,
            fg_color=COLORS['bg_input'],
            hover_color=COLORS['bg_hover'],
            text_color=COLORS['text_primary'],
            border_color=COLORS['border'],
            border_width=1,
            font=FONTS['body_bold'],
            corner_radius=8, height=40, width=190
        )
        self.btn_filter_machine.pack(side='left', padx=(0, 8))

        make_secondary_button(
            filter_row, '✖ Réinitialiser', command=self._reset_filters, width=130
        ).pack(side='left')

        # ── Tableau produits (occupant 100% de la largeur dynamiquement) ─────
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
            columns=['alerte', 'code', 'designation', 'fournisseur', 'categorie', 'emplacement', 'stock',
                     'unite', 'seuil', 'ligne', 'machine', 'rechange'],
            headings=['⚠️', 'Référence', 'Désignation', 'Fournisseur', 'Catégorie', 'Emplacement', 'Stock',
                      'Unité', 'Seuil', 'Ligne(s)', 'Machine', 'Prochaine Rechange'],
            col_widths=[36, 120, 220, 140, 140, 120, 65, 65, 55, 120, 120, 130],
            stretch_cols=True
        )
        self.tv.pack(side='left', fill='both', expand=True)
        self.tv.bind('<Double-1>', lambda e: self._open_edit_modal())
        add_scrollbar(inner, self.tv)

    # ── Popup Filtre Catégorie (multi-sélection) ──────────────────────────────
    def _open_cat_filter_popup(self):
        cats = ['Pièce de Rechange', "Pièce d'Usure"]
        self._show_multi_filter_popup(
            title='Filtrer par Catégorie',
            options=cats,
            selected_set=self._selected_categories,
            on_apply=self._apply_cat_filter,
            anchor_widget=self.btn_filter_cat
        )

    def _apply_cat_filter(self, selected: set):
        self._selected_categories = selected
        if selected:
            label = ', '.join(sorted(selected))
            if len(label) > 18:
                label = f'{len(selected)} catégorie(s)'
            self.btn_filter_cat.configure(text=f'🏷️ {label} ▾', fg_color=COLORS['primary'],
                                          text_color=COLORS['text_white'])
        else:
            self.btn_filter_cat.configure(text='🏷️ Catégorie : Toutes ▾',
                                          fg_color=COLORS['bg_input'], text_color=COLORS['text_primary'])
        self.refresh()

    # ── Popup Filtre Ligne (multi-sélection) ──────────────────────────────────
    def _open_ligne_filter_popup(self):
        self._show_multi_filter_popup(
            title='Filtrer par Ligne(s)',
            options=LIGNES,
            selected_set=self._selected_lignes,
            on_apply=self._apply_ligne_filter,
            anchor_widget=self.btn_filter_ligne
        )

    def _apply_ligne_filter(self, selected: set):
        self._selected_lignes = selected
        if selected:
            label = ', '.join(sorted(selected))
            if len(label) > 20:
                label = f'{len(selected)} ligne(s)'
            self.btn_filter_ligne.configure(text=f'🏭 {label} ▾', fg_color=COLORS['primary'],
                                            text_color=COLORS['text_white'])
        else:
            self.btn_filter_ligne.configure(text='🏭 Ligne : Toutes ▾',
                                            fg_color=COLORS['bg_input'], text_color=COLORS['text_primary'])
        self.refresh()

    # ── Popup Filtre Machine (multi-sélection) ────────────────────────────────
    def _open_machine_filter_popup(self):
        all_machines = []
        seen = set()
        for machines in MACHINES_SPECIFIQUES.values():
            for m in machines:
                if m not in seen and m != 'N/A':
                    all_machines.append(m)
                    seen.add(m)
        self._show_multi_filter_popup(
            title='Filtrer par Machine(s)',
            options=sorted(all_machines),
            selected_set=self._selected_machines,
            on_apply=self._apply_machine_filter,
            anchor_widget=self.btn_filter_machine
        )

    def _apply_machine_filter(self, selected: set):
        self._selected_machines = selected
        if selected:
            label = ', '.join(sorted(selected))
            if len(label) > 22:
                label = f'{len(selected)} machine(s)'
            self.btn_filter_machine.configure(text=f'⚙️ {label} ▾', fg_color=COLORS['primary'],
                                              text_color=COLORS['text_white'])
        else:
            self.btn_filter_machine.configure(text='⚙️ Machine : Toutes ▾',
                                              fg_color=COLORS['bg_input'], text_color=COLORS['text_primary'])
        self.refresh()

    def _show_multi_filter_popup(self, title: str, options: list,
                                  selected_set: set, on_apply, anchor_widget):
        """Affiche un popup de sélection multiple ancré sous le bouton avec boutons toujours visibles."""
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.configure(fg_color=COLORS['bg_card'])
        popup.resizable(False, False)
        popup.grab_set()

        desired_height = min(max(320, 110 + len(options) * 36), 460)
        desired_width = 300

        popup.update_idletasks()
        x = anchor_widget.winfo_rootx()
        y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 4
        popup.geometry(f'{desired_width}x{desired_height}+{x}+{y}')

        ctk.CTkLabel(popup, text=title, font=FONTS['subtitle'],
                     text_color=COLORS['text_primary']).pack(padx=14, pady=(12, 6), anchor='w')

        SeparatorLine(popup).pack(fill='x', padx=12, pady=(0, 4))

        btn_row = ctk.CTkFrame(popup, fg_color=COLORS['bg_hover'], height=52)
        btn_row.pack(side='bottom', fill='x', padx=8, pady=8)

        scroll = ctk.CTkScrollableFrame(popup, fg_color='transparent')
        scroll.pack(side='top', fill='both', expand=True, padx=8, pady=4)

        check_vars = {}
        for opt in options:
            var = tk.BooleanVar(value=(opt in selected_set))
            check_vars[opt] = var
            chk = ctk.CTkCheckBox(
                scroll, text=opt, variable=var,
                fg_color=COLORS['primary'], hover_color=COLORS['primary_dark'],
                text_color=COLORS['text_primary'], font=FONTS['body_bold'],
                corner_radius=4, checkbox_width=20, checkbox_height=20
            )
            chk.pack(anchor='w', padx=8, pady=5)

        def apply():
            result = {opt for opt, var in check_vars.items() if var.get()}
            on_apply(result)
            popup.destroy()

        def clear():
            for var in check_vars.values():
                var.set(False)
            apply()

        make_secondary_button(btn_row, 'Effacer tout', command=clear, width=110).pack(side='left', padx=8, pady=8)
        make_primary_button(btn_row, '✓ Appliquer', command=apply, width=130).pack(side='right', padx=8, pady=8)

    def _reset_filters(self):
        self._selected_lignes = set()
        self._selected_machines = set()
        self._selected_categories = set()
        self.btn_filter_cat.configure(text='🏷️ Catégorie : Toutes ▾',
                                      fg_color=COLORS['bg_input'], text_color=COLORS['text_primary'])
        self.btn_filter_ligne.configure(text='🏭 Ligne : Toutes ▾',
                                        fg_color=COLORS['bg_input'], text_color=COLORS['text_primary'])
        self.btn_filter_machine.configure(text='⚙️ Machine : Toutes ▾',
                                          fg_color=COLORS['bg_input'], text_color=COLORS['text_primary'])
        self.refresh()

    def _on_search(self, term: str):
        if hasattr(self, '_search_timer') and self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None

        self._search_timer = self.after(250, lambda: self._do_debounced_search(term))

    def _do_debounced_search(self, term: str):
        self._search_timer = None
        self._search_term = term.strip()
        self.refresh()

    def refresh(self):
        for item in self.tv.get_children():
            self.tv.delete(item)

        if self._search_term and len(self._search_term) <= 4:
            matched = db.find_produit_by_ref_or_last4(self._search_term)
            produits = [matched] if matched else db.get_all_produits(self._search_term)
        else:
            produits = db.get_all_produits(self._search_term)

        # Filtres multi-sélection Catégorie
        if self._selected_categories:
            produits = [p for p in produits if (p.get('categorie_piece') or 'Pièce de Rechange') in self._selected_categories]

        # Filtres multi-sélection Ligne
        if self._selected_lignes:
            produits = [p for p in produits if any(
                l in (p.get('utilite_ligne') or '') for l in self._selected_lignes
            )]

        # Filtres multi-sélection Machine
        if self._selected_machines:
            produits = [p for p in produits if (p.get('nom_machine') or '') in self._selected_machines]

        nb_alerts = sum(1 for p in produits if p['quantite_stock'] <= p['seuil_alerte'])
        self.badge_total.configure(text=f'{len(produits)} référence(s)')
        self.badge_alerts.configure(
            text=f'  ⚠️ {nb_alerts} alerte(s) de stock  ' if nb_alerts > 0 else ''
        )

        for i, p in enumerate(produits):
            en_alerte = p['quantite_stock'] <= p['seuil_alerte']
            tag = 'alert' if en_alerte else ('even' if i % 2 == 0 else 'odd')
            self.tv.insert('', 'end', iid=str(p['id']), values=(
                '⚠️' if en_alerte else '',
                p['code_barres'],
                p['designation'],
                p.get('fournisseur_nom') or '—',
                p.get('categorie_piece') or 'Pièce de Rechange',
                p['emplacement'] or '—',
                f"{p['quantite_stock']}",
                p['unite'],
                str(p['seuil_alerte']),
                p['utilite_ligne'] or '—',
                p['nom_machine'] or '—',
                p.get('prochaine_date_rechange') or '—'
            ), tags=(tag,))
        self.tv.autofit_columns()

    def _get_selected_id(self) -> int | None:
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner un produit.', parent=self)
            return None
        return int(sel[0])

    def _open_add_modal(self):
        ProductModal(self, mode='add', on_save=self.refresh)

    def _open_edit_modal(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        produit = db.get_produit_by_id(pid)
        if produit:
            ProductModal(self, mode='edit', produit=produit, on_save=self.refresh)

    def _delete_selected(self):
        pid = self._get_selected_id()
        if pid is None:
            return
        produit = db.get_produit_by_id(pid)
        if not produit:
            return
        confirm = messagebox.askyesno(
            'Confirmer la suppression',
            f'Supprimer le produit :\n\n  {produit["designation"]} ({produit["code_barres"]}) ?\n\n'
            'Cette action est irréversible.',
            parent=self
        )
        if confirm:
            db.supprimer_produit(pid)
            self.refresh()


# ─────────────────────── Modale Produit ───────────────────────────────────────

class ProductModal(ctk.CTkToplevel):
    """Fenêtre modale pour ajouter ou modifier un produit (Ergonomique avec boutons fixes)."""

    def __init__(self, parent, mode: str = 'add', produit: dict = None, on_save=None, preselect_fournisseur_id: int = None):
        super().__init__(parent)
        self.mode = mode
        self.produit = produit or {}
        self.on_save = on_save
        self.preselect_fournisseur_id = preselect_fournisseur_id

        self.title('➕  Nouveau Produit' if mode == 'add' else '✏️  Modifier le Produit')
        self.geometry('720x760')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        # Centrer la fenêtre modale sur l'écran
        self.update_idletasks()
        w, h = 720, 760
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

        self._build_ui()
        if mode == 'edit' and produit:
            self._fill_fields()
        elif mode == 'add' and preselect_fournisseur_id:
            self._preselect_fournisseur(preselect_fournisseur_id)

    def _build_ui(self):
        # ── BOUTONS EN BAS EN PREMIER (Fixes et toujours visibles) ─
        btn_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], height=60, border_width=1, border_color=COLORS['border'])
        btn_frame.pack(side='bottom', fill='x', padx=0, pady=0)

        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=130).pack(side='right', padx=16, pady=10)
        make_primary_button(
            btn_frame, 'Enregistrer' if self.mode == 'add' else 'Sauvegarder',
            command=self._save, icon='💾', width=190
        ).pack(side='right', padx=(0, 8), pady=10)

        # ── En-tête de la modale ─────────────────────────────────────────────
        ctk.CTkLabel(
            self, text='➕  Nouveau Produit' if self.mode == 'add' else '✏️  Modifier le Produit',
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(16, 2), padx=24, anchor='w')

        if self.mode == 'add':
            ctk.CTkLabel(
                self,
                text='ℹ️  Si la référence existe déjà, un suffixe /1, /2... sera ajouté automatiquement.',
                font=FONTS['small'], text_color=COLORS['text_secondary'],
                fg_color=COLORS['bg_hover'], corner_radius=6
            ).pack(fill='x', padx=24, pady=(0, 4))

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 10))

        # ── Zone Scrollable au centre pour tous les champs ────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent', scrollbar_button_color=COLORS['primary'])
        scroll.pack(side='top', fill='both', expand=True, padx=24, pady=(0, 6))

        def row(label_text, widget_fn, *args, **kwargs):
            frame = ctk.CTkFrame(scroll, fg_color='transparent')
            frame.pack(fill='x', pady=5)
            ctk.CTkLabel(frame, text=label_text, font=FONTS['body_bold'],
                         text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
            w = widget_fn(frame, *args, **kwargs)
            w.pack(side='left', fill='x', expand=True)
            return w

        # Champ Fournisseur
        frame_fourn = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_fourn.pack(fill='x', pady=5)
        ctk.CTkLabel(frame_fourn, text='Fournisseur', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')

        self.fournisseurs_list = db.get_all_fournisseurs()
        self.fourn_map = {f["nom"]: f["id"] for f in self.fournisseurs_list}
        fourn_names = ["Aucun (Non spécifié)"] + list(self.fourn_map.keys())

        self.var_fournisseur = tk.StringVar(value="Aucun (Non spécifié)")
        self.cb_fournisseur = make_combobox(frame_fourn, fourn_names, width=280, variable=self.var_fournisseur)
        self.cb_fournisseur.pack(side='left', padx=(0, 8))

        make_secondary_button(frame_fourn, '＋ Nouveau', command=self._quick_add_fournisseur, width=100, height=36).pack(side='left')

        self.e_code    = row('Référence *',     make_input, placeholder='Ex: REF-8820')
        self.e_design  = row('Désignation *',   make_input, placeholder='Nom du produit')

        # Champ Catégorie Pièce
        frame_cat = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_cat.pack(fill='x', pady=5)
        ctk.CTkLabel(frame_cat, text='Catégorie Pièce *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.var_categorie = tk.StringVar(value='Pièce de Rechange')
        make_combobox(frame_cat,
                      ['Pièce de Rechange', "Pièce d'Usure"],
                      width=280, variable=self.var_categorie).pack(side='left')

        self.e_emplace = row('Emplacement',     make_input, placeholder='Ex: Allée A - Rayon 3')
        self.e_qte     = row('Quantité Stock',  make_input, placeholder='0')
        self.e_seuil   = row("Seuil d'Alerte", make_input, placeholder='5')

        # Unité
        frame_unite = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_unite.pack(fill='x', pady=5)
        ctk.CTkLabel(frame_unite, text='Unité', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.var_unite = tk.StringVar(value='Unité')
        make_combobox(frame_unite, UNITES, width=220, variable=self.var_unite).pack(side='left')

        # Multi-Sélection Ligne(s)
        frame_lignes = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_lignes.pack(fill='x', pady=5)
        ctk.CTkLabel(frame_lignes, text='Utilité / Ligne(s) *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='nw').pack(side='left', anchor='n', pady=4)
        self.widget_lignes = MultiSelectLignesWidget(
            frame_lignes, options=LIGNES, default_selected=['KHS1'],
            on_change=self._on_lignes_changed
        )
        self.widget_lignes.pack(side='left', fill='x', expand=True, pady=4)

        # Sous-choix Convoyeur (dynamique)
        self.frame_sub_convoyeur = ctk.CTkFrame(scroll, fg_color='transparent')
        ctk.CTkLabel(self.frame_sub_convoyeur, text='Ligne Convoyeur *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.var_sub_convoyeur = tk.StringVar(value='KHS1')
        make_combobox(self.frame_sub_convoyeur, SOUS_LIGNES_CONVOYEUR, width=280, variable=self.var_sub_convoyeur).pack(side='left')

        # Sous-choix Compresseur (dynamique)
        self.frame_sub_compresseur = ctk.CTkFrame(scroll, fg_color='transparent')
        ctk.CTkLabel(self.frame_sub_compresseur, text='Type Compresseur *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.var_sub_compresseur = tk.StringVar(value='KHS1')
        make_combobox(self.frame_sub_compresseur, SOUS_LIGNES_COMPRESSEUR, width=280, variable=self.var_sub_compresseur).pack(side='left')

        # Nom Machine
        self.frame_machine = ctk.CTkFrame(scroll, fg_color='transparent')
        self.frame_machine.pack(fill='x', pady=5)
        ctk.CTkLabel(self.frame_machine, text='Nom Machine *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.var_machine = tk.StringVar(value='Blomax')
        self.cb_machine = make_combobox(self.frame_machine, get_machines_pour_lignes(['KHS1']),
                                        width=280, variable=self.var_machine)
        self.cb_machine.pack(side='left')
        self._on_lignes_changed(self.widget_lignes.get_selected())

        # ── SECTION OPTIONNELLE : SUIVI ET ÉCHÉANCE PIÈCE DE RECHANGE ───────
        SeparatorLine(scroll).pack(fill='x', pady=12)

        sec_title = ctk.CTkFrame(scroll, fg_color='transparent')
        sec_title.pack(fill='x', pady=(0, 6))
        ctk.CTkLabel(
            sec_title, text='📅  Suivi & Échéance Pièce de Rechange (Optionnel)',
            font=FONTS['subtitle'], text_color=COLORS['primary']
        ).pack(side='left')

        # 1. Date de rechange initiale
        frame_date_init = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_date_init.pack(fill='x', pady=4)
        ctk.CTkLabel(frame_date_init, text='Date rechange initiale', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_date_init = make_input(frame_date_init, placeholder='AAAA-MM-JJ (ex: 2026-08-12)')
        self.e_date_init.pack(side='left', fill='x', expand=True, padx=(0, 6))

        def _set_today_init():
            from datetime import datetime
            self.e_date_init.delete(0, 'end')
            self.e_date_init.insert(0, datetime.now().strftime('%Y-%m-%d'))
            self._try_auto_calc_prochaine_date()

        make_secondary_button(frame_date_init, 'Aujourd\'hui', command=_set_today_init, width=100, height=36).pack(side='left')

        # 2. Durée de vie (saisie libre par le magasinier)
        self.e_duree_vie = row('Durée de vie', make_input, placeholder='Ex: 6 mois / 90 jours / 30')
        self.e_duree_vie.bind('<KeyRelease>', lambda e: self._try_auto_calc_prochaine_date())

        # 3. Prochaine date de rechange (saisie manuelle avec calcul d'aide)
        frame_date_proch = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_date_proch.pack(fill='x', pady=4)
        ctk.CTkLabel(frame_date_proch, text='Prochaine date rechange', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_date_proch = make_input(frame_date_proch, placeholder='AAAA-MM-JJ (ex: 2027-02-12)')
        self.e_date_proch.pack(side='left', fill='x', expand=True, padx=(0, 6))

        make_secondary_button(frame_date_proch, '⚡ Calculer', command=self._try_auto_calc_prochaine_date, width=100, height=36).pack(side='left')

    def _quick_add_fournisseur(self):
        """Ouvre une modale rapide pour ajouter un nouveau fournisseur sans quitter la création de produit."""
        from ui.fournisseurs import FournisseurModal
        def _on_created():
            self.fournisseurs_list = db.get_all_fournisseurs()
            self.fourn_map = {f["nom"]: f["id"] for f in self.fournisseurs_list}
            fourn_names = ["Aucun (Non spécifié)"] + list(self.fourn_map.keys())
            self.cb_fournisseur.configure(values=fourn_names)
            if self.fournisseurs_list:
                latest = self.fournisseurs_list[-1]
                self.var_fournisseur.set(latest['nom'])
        FournisseurModal(self, mode='add', on_save=_on_created)

    def _preselect_fournisseur(self, fid: int):
        for nom, supplier_id in self.fourn_map.items():
            if supplier_id == fid:
                self.var_fournisseur.set(nom)
                break

    def _try_auto_calc_prochaine_date(self):
        """Tente d'additionner automatiquement la durée de vie à la date initiale si analysable."""
        date_init_str = self.e_date_init.get().strip()
        duree_str = self.e_duree_vie.get().strip()

        if not date_init_str or not duree_str:
            return

        from datetime import datetime
        try:
            dt = datetime.strptime(date_init_str, '%Y-%m-%d')
        except ValueError:
            return

        # Tenter d'extraire un nombre de la durée de vie
        import re
        numbers = re.findall(r'\d+', duree_str)
        if not numbers:
            return
        val = int(numbers[0])

        is_days = 'jour' in duree_str.lower() or 'day' in duree_str.lower()
        from datetime import timedelta

        if is_days:
            next_date = dt + timedelta(days=val)
        else:
            # Par défaut considérer en mois si non spécifié ou si 'mois'
            year = dt.year + (dt.month + val - 1) // 12
            month = (dt.month + val - 1) % 12 + 1
            day = min(dt.day, 28)  # Sécurité fin de mois
            next_date = datetime(year, month, day)

        self.e_date_proch.delete(0, 'end')
        self.e_date_proch.insert(0, next_date.strftime('%Y-%m-%d'))

    def _on_lignes_changed(self, selected_lignes: list):
        if 'Convoyeur' in selected_lignes:
            self.frame_sub_convoyeur.pack(fill='x', pady=5, before=self.frame_machine)
        else:
            self.frame_sub_convoyeur.pack_forget()

        if 'Compresseur' in selected_lignes:
            self.frame_sub_compresseur.pack(fill='x', pady=5, before=self.frame_machine)
        else:
            self.frame_sub_compresseur.pack_forget()

        machines = get_machines_pour_lignes(selected_lignes)
        self.cb_machine.configure(values=machines)
        if self.var_machine.get() not in machines:
            self.var_machine.set(machines[0])

    def _fill_fields(self):
        p = self.produit
        self.e_code.insert(0, p.get('code_barres', ''))
        self.e_design.insert(0, p.get('designation', ''))
        self.e_emplace.insert(0, p.get('emplacement', ''))
        self.e_qte.insert(0, str(p.get('quantite_stock', 0)))
        self.e_seuil.insert(0, str(p.get('seuil_alerte', 5)))

        # Fournisseur
        fid = p.get('fournisseur_id')
        if fid:
            self._preselect_fournisseur(fid)
        else:
            self.var_fournisseur.set("Aucun (Non spécifié)")

        # Dates rechange
        self.e_date_init.insert(0, p.get('date_rechange_initiale', ''))
        self.e_duree_vie.insert(0, p.get('duree_vie', ''))
        self.e_date_proch.insert(0, p.get('prochaine_date_rechange', ''))

        unite = p.get('unite', 'Unité')
        if unite in UNITES:
            self.var_unite.set(unite)
        lignes_list = [l.strip() for l in (p.get('utilite_ligne', 'KHS1') or 'KHS1').split(',')]
        self.widget_lignes.set_selected(lignes_list)
        self.var_machine.set(p.get('nom_machine', 'N/A'))
        cat = p.get('categorie_piece', 'Pièce de Rechange')
        self.var_categorie.set(cat if cat in ['Pièce de Rechange', "Pièce d'Usure"] else 'Pièce de Rechange')

    def _save(self):
        code = self.e_code.get().strip()
        designation = self.e_design.get().strip()

        if not code:
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

        fourn_nom = self.var_fournisseur.get()
        fourn_id = self.fourn_map.get(fourn_nom) if fourn_nom in self.fourn_map else None

        selected_lignes = self.widget_lignes.get_selected()
        data = {
            'code_barres':            code,
            'designation':            designation,
            'emplacement':            self.e_emplace.get().strip(),
            'quantite_stock':         qte,
            'unite':                  self.var_unite.get(),
            'utilite_ligne':          ', '.join(selected_lignes),
            'nom_machine':            self.var_machine.get(),
            'seuil_alerte':           seuil,
            'categorie_piece':        self.var_categorie.get(),
            'fournisseur_id':         fourn_id,
            'date_rechange_initiale': self.e_date_init.get().strip(),
            'duree_vie':              self.e_duree_vie.get().strip(),
            'prochaine_date_rechange': self.e_date_proch.get().strip()
        }

        try:
            if self.mode == 'add':
                new_id = db.ajouter_produit(data)
                added = db.get_produit_by_id(new_id)
                final_ref = added['code_barres'] if added else code
                messagebox.showinfo('Succès', f'Produit "{designation}" ajouté !\nRéférence : {final_ref}', parent=self)
            else:
                db.modifier_produit(self.produit['id'], data)
                messagebox.showinfo('Succès', f'Produit "{designation}" mis à jour !', parent=self)

            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer :\n{e}', parent=self)
