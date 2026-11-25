"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/outillage.py
Écran de gestion des Outillages avec filtres, indicateurs de statut vert/rouge et modale dynamique.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from ui.theme import COLORS, FONTS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_danger_button, make_secondary_button, make_success_button,
                         make_input, SearchBar, SeparatorLine, DatePickerInput,
                         AutocompleteOutillageInput)
from ui.pdf_viewer import ouvrir_pdf_viewer
from services.pdf_generator import generer_bon_decharge_pdf
import database.db_manager as db


class OutillageFrame(ctk.CTkFrame):
    """Écran complet de gestion des Outillages (Magasin / En dehors du magasin)."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._search_term = ""
        self._statut_filter = "Tous"
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text="🔧  Gestion des Outillages",
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        self.badge_total = ctk.CTkLabel(
            header, text='0 outillage(s)',
            font=FONTS['body_bold'],
            text_color=COLORS['text_secondary']
        )
        self.badge_total.pack(side='left', padx=12, pady=(4, 0))

        btn_frame = ctk.CTkFrame(header, fg_color='transparent')
        btn_frame.pack(side='right')

        make_danger_button(
            btn_frame, '📤 Sortie Outil', command=self._open_sortie_modal, width=130
        ).pack(side='left', padx=3)

        make_success_button(
            btn_frame, '📥 Retour Outil', command=self._open_retour_modal, width=130
        ).pack(side='left', padx=3)

        ctk.CTkButton(
            btn_frame, text='📑 Décharge', command=self._open_decharge_modal,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_dark'],
            text_color='white', font=FONTS['body_bold'], corner_radius=8,
            height=42, width=130
        ).pack(side='left', padx=3)

        make_secondary_button(
            btn_frame, '📋 Historique Prêts', command=self._open_historique_modal, width=145
        ).pack(side='left', padx=3)

        make_primary_button(
            btn_frame, 'Nouvel Outillage', command=self._open_add_modal,
            icon='＋', width=150
        ).pack(side='left', padx=3)

        SeparatorLine(self).pack(fill='x', padx=24)

        # ── Cards Statistiques KPI (Stock Total, Dans le magasin, En dehors, Sorties) ──────
        kpi_frame = ctk.CTkFrame(self, fg_color='transparent')
        kpi_frame.pack(fill='x', padx=24, pady=(10, 4))

        def create_kpi_box(parent, title, icon, color):
            card = ctk.CTkFrame(parent, fg_color=COLORS['bg_card'], corner_radius=12, border_width=1, border_color=COLORS['border'])
            inner = ctk.CTkFrame(card, fg_color='transparent')
            inner.pack(fill='both', expand=True, padx=14, pady=10)
            
            icon_lbl = ctk.CTkLabel(inner, text=icon, font=('Segoe UI Emoji', 22), text_color=color)
            icon_lbl.pack(side='left', padx=(0, 10))

            txt_box = ctk.CTkFrame(inner, fg_color='transparent')
            txt_box.pack(side='left', fill='both', expand=True)

            val_lbl = ctk.CTkLabel(txt_box, text="0", font=('Segoe UI', 18, 'bold'), text_color=color, anchor='w')
            val_lbl.pack(fill='x')

            title_lbl = ctk.CTkLabel(txt_box, text=title, font=FONTS['small_bold'], text_color=COLORS['text_secondary'], anchor='w')
            title_lbl.pack(fill='x')

            return card, val_lbl

        self.card_total, self.lbl_kpi_total = create_kpi_box(kpi_frame, "Stock Total Cumulé", "🧰", COLORS['primary'])
        self.card_total.pack(side='left', fill='both', expand=True, padx=(0, 6))

        self.card_dans, self.lbl_kpi_dans = create_kpi_box(kpi_frame, "Dans le Magasin", "🟢", COLORS['success'])
        self.card_dans.pack(side='left', fill='both', expand=True, padx=6)

        self.card_dehors, self.lbl_kpi_dehors = create_kpi_box(kpi_frame, "En Dehors du Magasin", "🔴", COLORS['danger'])
        self.card_dehors.pack(side='left', fill='both', expand=True, padx=6)

        self.card_sorties, self.lbl_kpi_sorties = create_kpi_box(kpi_frame, "Prêts En Cours", "📋", '#9333EA')
        self.card_sorties.pack(side='left', fill='both', expand=True, padx=(6, 0))

        # ── Barre de recherche + Filtre Statut + Actions Édition/Suppression ────────
        filter_row = ctk.CTkFrame(self, fg_color='transparent')
        filter_row.pack(fill='x', padx=24, pady=12)

        SearchBar(
            filter_row,
            placeholder='Rechercher par Numéro, Désignation, Marque...',
            on_change=self._on_search, width=320
        ).pack(side='left', padx=(0, 12))

        # Switcher Statut Outillage
        filter_type_frame = ctk.CTkFrame(
            filter_row, fg_color=COLORS['bg_card'],
            corner_radius=8, border_width=1, border_color=COLORS['border']
        )
        filter_type_frame.pack(side='left')

        self.btn_f_tous = ctk.CTkButton(
            filter_type_frame, text='Tous les Outillages',
            command=lambda: self._set_statut_filter('Tous'),
            fg_color=COLORS['primary'], text_color='white',
            font=FONTS['body_bold'], corner_radius=6, height=36, width=130
        )
        self.btn_f_tous.pack(side='left', padx=2, pady=2)

        self.btn_f_dans = ctk.CTkButton(
            filter_type_frame, text='🟢 Dans le magasin',
            command=lambda: self._set_statut_filter('Dans le magasin'),
            fg_color='transparent', text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'], corner_radius=6, height=36, width=150
        )
        self.btn_f_dans.pack(side='left', padx=2, pady=2)

        self.btn_f_dehors = ctk.CTkButton(
            filter_type_frame, text='🔴 En dehors du magasin',
            command=lambda: self._set_statut_filter('En dehors du magasin'),
            fg_color='transparent', text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'], corner_radius=6, height=36, width=165
        )
        self.btn_f_dehors.pack(side='left', padx=2, pady=2)

        # Boutons d'édition et de suppression dans la barre d'outils (très visibles)
        edit_del_frame = ctk.CTkFrame(filter_row, fg_color='transparent')
        edit_del_frame.pack(side='right')

        self.btn_edit = make_secondary_button(
            edit_del_frame, '✏️ Modifier', command=self._open_edit_modal, width=115
        )
        self.btn_edit.pack(side='left', padx=3)

        self.btn_del = make_danger_button(
            edit_del_frame, '🗑️ Supprimer', command=self._delete_selected, width=120
        )
        self.btn_del.pack(side='left', padx=3)

        # ── Tableau Outillages ──────────────────────────────────────────
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
            columns=['statut', 'numero', 'designation', 'marque', 'quantite', 'date_ajout'],
            headings=['Statut Emplacement', "N° Outillage", 'Désignation', 'Marque', 'Quantité', "Date d'Ajout"],
            col_widths=[180, 140, 260, 140, 90, 130]
        )
        self.tv.pack(side='left', fill='both', expand=True)
        self.tv.bind('<Double-1>', lambda e: self._open_edit_modal())
        add_scrollbar(inner, self.tv)

        # Context Menu (Clic droit sur tableau)
        self.context_menu = tk.Menu(self, tearoff=0, bg=COLORS['bg_card'], fg=COLORS['text_primary'], activebackground=COLORS['primary'], activeforeground='white')
        self.context_menu.add_command(label="📑  Décharge d'outillage", command=self._open_decharge_from_selection)
        self.context_menu.add_command(label="📤  Sortie d'outillage", command=self._open_sortie_modal)
        self.context_menu.add_command(label="📥  Retour d'outillage (Restitution)", command=self._open_retour_modal)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✏️  Modifier l'outillage", command=self._open_edit_modal)
        self.context_menu.add_command(label="🗑️  Supprimer l'outillage", command=self._delete_selected)
        self.tv.bind('<Button-3>', self._show_context_menu)

    def _show_context_menu(self, event):
        item = self.tv.identify_row(event.y)
        if item:
            self.tv.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _set_statut_filter(self, s_filter: str):
        self._statut_filter = s_filter
        for sf, btn in [('Tous', self.btn_f_tous), ('Dans le magasin', self.btn_f_dans), ('En dehors du magasin', self.btn_f_dehors)]:
            if sf == s_filter:
                btn.configure(fg_color=COLORS['primary'], text_color='white')
            else:
                btn.configure(fg_color='transparent', text_color=COLORS['text_secondary'])
        self.refresh()

    def _on_search(self, term: str):
        self._search_term = term.strip()
        self.refresh()

    def refresh(self):
        for item in self.tv.get_children():
            self.tv.delete(item)

        outillages = db.get_all_outillages(search=self._search_term, statut_filter=self._statut_filter)
        self.badge_total.configure(text=f'{len(outillages)} outillage(s)')

        stats = db.get_outillage_stats()
        self.lbl_kpi_total.configure(text=f"{stats['total_quantite']} unité(s)")
        self.lbl_kpi_dans.configure(text=f"{stats['quantite_magasin']} unité(s)")
        self.lbl_kpi_dehors.configure(text=f"{stats['quantite_dehors']} unité(s)")
        self.lbl_kpi_sorties.configure(text=f"{stats['nb_sorties_en_cours']} prêt(s)")

        for i, o in enumerate(outillages):
            statut_val = o.get('statut', 'Dans le magasin')
            q_stock = o.get('quantite', 0) or 0
            q_dehors = o.get('quantite_dehors_actuelle', 0) or 0

            if self._statut_filter == "En dehors du magasin":
                statut_display = '🔴 En dehors du magasin'
                tag = 'en_dehors'
                qte_display = str(q_dehors) if q_dehors > 0 else str(max(q_stock, 1))
            elif self._statut_filter == "Dans le magasin":
                statut_display = '🟢 Dans le magasin'
                tag = 'dans_magasin'
                qte_display = str(q_stock)
            else:
                if q_dehors > 0 or statut_val != 'Dans le magasin' or q_stock <= 0:
                    statut_display = '🔴 En dehors du magasin'
                    tag = 'en_dehors'
                    qte_display = str(q_dehors) if q_dehors > 0 else str(max(q_stock, 1))
                else:
                    statut_display = '🟢 Dans le magasin'
                    tag = 'dans_magasin'
                    qte_display = str(q_stock)

            date_str = o.get('date_ajout', '')
            if date_str and len(date_str) >= 10:
                date_str = date_str[:10]

            try:
                self.tv.insert('', 'end', iid=str(o['id']), values=(
                    statut_display,
                    o.get('numero_outillage', ''),
                    o.get('designation', ''),
                    o.get('marque') or '-',
                    qte_display,
                    date_str
                ), tags=(tag,))
            except Exception:
                pass
        self.tv.autofit_columns()


    def _get_selected_id(self) -> int | None:
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez sélectionner un outillage.', parent=self)
            return None
        return int(sel[0])

    def _set_selected_status(self, new_status: str):
        oid = self._get_selected_id()
        if oid is None:
            return
        db.changer_statut_outillage(oid, new_status)
        self.refresh()

    def _open_add_modal(self):
        OutillageModal(self, mode='add', on_save=self.refresh)

    def _open_sortie_modal(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showwarning('Sélection', 'Veuillez d\'abord sélectionner un outillage dans le tableau pour effectuer une sortie.', parent=self)
            return
        tool_id = int(sel[0])
        tool = db.get_outillage_by_id(tool_id)
        if not tool:
            messagebox.showerror("Erreur", "L'outil sélectionné n'existe pas.", parent=self)
            return
        if tool.get('statut') == 'En dehors du magasin' or tool['quantite'] <= 0:
            messagebox.showwarning(
                "Sortie Impossible",
                f"L'outillage '{tool['designation']}' (N° {tool['numero_outillage']}) est actuellement marqué 'En dehors du magasin' (Stock disponible: 0).\n\n"
                "Impossible d'effectuer une nouvelle sortie tant qu'il n'est pas restitué et réintégré au magasin.",
                parent=self
            )
            return
        SortieOutillageModal(self, tool=tool, on_save=self.refresh)

    def _open_decharge_from_selection(self):
        sel = self.tv.selection()
        tool = None
        if sel:
            try:
                tool = db.get_outillage_by_id(int(sel[0]))
            except Exception:
                tool = None
        self._open_decharge_modal(tool=tool)

    def _open_decharge_modal(self, tool: dict = None):
        """Ouvre la fenêtre de formulaire de Décharge d'outillage."""
        if tool is None:
            sel = self.tv.selection()
            if sel:
                try:
                    tool = db.get_outillage_by_id(int(sel[0]))
                except Exception:
                    tool = None
        DechargeOutillageModal(self, tool=tool, on_save=self.refresh)

    def _open_retour_modal(self):
        sel = self.tv.selection()
        tool_id = int(sel[0]) if sel else None

        sorties_en_cours = db.get_sorties_outillage_en_cours(tool_id)
        if not sorties_en_cours:
            if tool_id is not None:
                # Réessayer globalement si l'outil spécifique n'a pas de sortie en cours
                sorties_en_cours = db.get_sorties_outillage_en_cours(None)

            if not sorties_en_cours:
                messagebox.showwarning(
                    "Retour impossible",
                    "Aucune sortie d'outillage en cours à retourner.\n\n"
                    "L'outillage n'a fait l'objet d'aucune sortie ou toutes les sorties ont déjà été totalement restituées.",
                    parent=self
                )
                return

        RetourOutillageModal(self, sorties=sorties_en_cours, on_save=self.refresh)

    def _open_historique_modal(self):
        HistoriqueSortiesOutillageModal(self)

    def _open_edit_modal(self):
        oid = self._get_selected_id()
        if oid is None:
            return
        outillage = db.get_outillage_by_id(oid)
        if outillage:
            OutillageModal(self, mode='edit', outillage=outillage, on_save=self.refresh)

    def _delete_selected(self):
        oid = self._get_selected_id()
        if oid is None:
            return
        outillage = db.get_outillage_by_id(oid)
        if not outillage:
            return
        confirm = messagebox.askyesno(
            'Confirmer la suppression',
            f'Voulez-vous vraiment supprimer cet outillage :\n\n  {outillage["designation"]} (N° {outillage["numero_outillage"]}) ?\n\n'
            'Cette action est irréversible.',
            parent=self
        )
        if confirm:
            db.supprimer_outillage(oid)
            self.refresh()


# ─────────────────────── Modale Outillage ──────────────────────────────────

class OutillageModal(ctk.CTkToplevel):
    """Fenêtre modale pour ajouter ou modifier un outillage avec sélection statut Vert / Rouge."""

    def __init__(self, parent, mode: str = 'add', outillage: dict = None, on_save=None):
        super().__init__(parent)
        self.mode = mode
        self.outillage = outillage or {}
        self.on_save = on_save

        self.title('➕ Nouveau Outillage' if mode == 'add' else '✏️ Modifier Outillage')
        self.geometry('600x560')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self._build_ui()
        if mode == 'edit' and outillage:
            self._fill_fields()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text='➕  Saisie Nouveau Outillage' if self.mode == 'add' else '✏️  Modifier Outillage',
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(18, 4), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 10))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24)

        # Désignation
        frame_des = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_des.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_des, text='Désignation *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_designation = make_input(frame_des, placeholder="Ex: Clé dynamométrique 1/2''", width=280)
        self.e_designation.pack(side='left')

        # Marque (Non obligatoire)
        frame_marque = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_marque.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_marque, text='La Marque (Optionnel)', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_marque = make_input(frame_marque, placeholder='Ex: Facom, Bosch, Makita...', width=280)
        self.e_marque.pack(side='left')

        # Numéro d'outillage
        frame_num = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_num.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_num, text="Numéro d'outillage *", font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_numero = make_input(frame_num, placeholder='Ex: OUT-2024-001', width=280)
        self.e_numero.pack(side='left')

        # Quantité
        frame_qte = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_qte.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_qte, text='La Quantité *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_quantite = make_input(frame_qte, placeholder='1', width=280)
        self.e_quantite.pack(side='left')

        # Statut Emplacement (Bouton Vert "Dans le magasin" & Bouton Rouge "En dehors de magasin")
        frame_statut = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_statut.pack(fill='x', pady=12)
        ctk.CTkLabel(frame_statut, text='Statut Emplacement *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')

        self.var_statut = tk.StringVar(value='Dans le magasin')

        statut_btns_frame = ctk.CTkFrame(frame_statut, fg_color='transparent')
        statut_btns_frame.pack(side='left')

        self.btn_statut_dans = ctk.CTkButton(
            statut_btns_frame,
            text='🟢  Dans le magasin',
            command=lambda: self._select_statut('Dans le magasin'),
            fg_color=COLORS['success'],
            hover_color='#16A34A',
            text_color='white',
            font=FONTS['body_bold'],
            corner_radius=8,
            height=38, width=150
        )
        self.btn_statut_dans.pack(side='left', padx=(0, 10))

        self.btn_statut_dehors = ctk.CTkButton(
            statut_btns_frame,
            text='🔴  En dehors du magasin',
            command=lambda: self._select_statut('En dehors du magasin'),
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['danger'],
            text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'],
            corner_radius=8,
            height=38, width=175
        )
        self.btn_statut_dehors.pack(side='left')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(12, 0))
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=24, pady=12)

        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=120).pack(side='right', padx=(6, 0))
        make_primary_button(
            btn_frame, 'Enregistrer' if self.mode == 'add' else 'Sauvegarder',
            command=self._save, icon='💾', width=180
        ).pack(side='right')

    def _select_statut(self, statut: str):
        self.var_statut.set(statut)
        if statut == 'Dans le magasin':
            self.btn_statut_dans.configure(fg_color=COLORS['success'], text_color='white')
            self.btn_statut_dehors.configure(fg_color=COLORS['bg_hover'], text_color=COLORS['text_secondary'])
        else:
            self.btn_statut_dehors.configure(fg_color=COLORS['danger'], text_color='white')
            self.btn_statut_dans.configure(fg_color=COLORS['bg_hover'], text_color=COLORS['text_secondary'])

    def _fill_fields(self):
        o = self.outillage
        self.e_designation.insert(0, o.get('designation', ''))
        self.e_marque.insert(0, o.get('marque', ''))
        self.e_numero.insert(0, o.get('numero_outillage', ''))
        self.e_quantite.insert(0, str(o.get('quantite', 1)))
        
        statut = o.get('statut', 'Dans le magasin')
        self._select_statut(statut)

    def _save(self):
        designation = self.e_designation.get().strip()
        numero = self.e_numero.get().strip()
        marque = self.e_marque.get().strip()

        if not designation:
            messagebox.showerror('Erreur', 'La Désignation est obligatoire.', parent=self)
            return
        if not numero:
            messagebox.showerror('Erreur', 'Le Numéro d\'outillage est obligatoire.', parent=self)
            return

        try:
            qte = int(self.e_quantite.get().strip() or 1)
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Erreur', 'La quantité doit être un nombre entier positif.', parent=self)
            return

        data = {
            'designation':      designation,
            'marque':           marque,
            'numero_outillage': numero,
            'quantite':         qte,
            'statut':           self.var_statut.get()
        }

        try:
            if self.mode == 'add':
                db.ajouter_outillage(data)
                messagebox.showinfo('Succès', f'Outillage "{designation}" ajouté avec succès !', parent=self)
            else:
                db.modifier_outillage(self.outillage['id'], data)
                messagebox.showinfo('Succès', f'Outillage "{designation}" mis à jour !', parent=self)

            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer :\n{e}', parent=self)


# ─────────────────────── Modale Sortie Outillage ──────────────────────────────────

class SortieOutillageModal(ctk.CTkToplevel):
    """Fenêtre modale pour enregistrer la sortie d'un outil avec nom du demandeur et quantité prise."""

    def __init__(self, parent, tool: dict, on_save=None):
        super().__init__(parent)
        self.tool = tool
        self.on_save = on_save

        self.title("📤 Sortie d'Outillage")
        self.geometry('560x530')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="📤  Sortie d'Outillage",
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(18, 4), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 10))

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=24)

        # Récapitulatif Outil
        frame_tool_info = ctk.CTkFrame(scroll, fg_color=COLORS['bg_card'], corner_radius=8, border_width=1, border_color=COLORS['border'])
        frame_tool_info.pack(fill='x', pady=8, padx=2)

        info_inner = ctk.CTkFrame(frame_tool_info, fg_color='transparent')
        info_inner.pack(fill='x', padx=14, pady=12)

        ctk.CTkLabel(info_inner, text=f"🔧  {self.tool['designation']}", font=FONTS['subtitle'], text_color=COLORS['primary'], anchor='w').pack(fill='x')
        ctk.CTkLabel(info_inner, text=f"N° Outillage : {self.tool['numero_outillage']}   |   Marque : {self.tool.get('marque') or '-'}", font=FONTS['body'], text_color=COLORS['text_secondary'], anchor='w').pack(fill='x', pady=(2, 0))
        ctk.CTkLabel(info_inner, text=f"Stock actuellement disponible : {self.tool['quantite']} unité(s)", font=FONTS['body_bold'], text_color=COLORS['success'], anchor='w').pack(fill='x', pady=(4, 0))

        # Demandeur *
        frame_dem = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_dem.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_dem, text='Nom du Demandeur *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_demandeur = make_input(frame_dem, placeholder="Ex: Jean Dupont, Service Maintenance", width=280)
        self.e_demandeur.pack(side='left')

        # Quantité Prise *
        frame_qte = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_qte.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_qte, text='Quantité Prise *', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_quantite = make_input(frame_qte, placeholder='1', width=280)
        self.e_quantite.pack(side='left')
        self.e_quantite.insert(0, "1")

        # Motif / Remarque (Optionnel)
        frame_motif = ctk.CTkFrame(scroll, fg_color='transparent')
        frame_motif.pack(fill='x', pady=8)
        ctk.CTkLabel(frame_motif, text='Motif / Remarque', font=FONTS['body_bold'],
                     text_color=COLORS['text_secondary'], width=165, anchor='w').pack(side='left')
        self.e_motif = make_input(frame_motif, placeholder="Ex: Intervention Ligne 2 (Optionnel)", width=280)
        self.e_motif.pack(side='left')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(12, 0))
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=24, pady=12)

        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=120).pack(side='right', padx=(6, 0))
        make_danger_button(
            btn_frame, 'Confirmer la Sortie',
            command=self._save, width=190
        ).pack(side='right')

    def _save(self):
        demandeur = self.e_demandeur.get().strip()
        motif = self.e_motif.get().strip()

        if not demandeur:
            messagebox.showerror('Champ obligatoire', 'Veuillez saisir le nom du demandeur.', parent=self)
            return

        try:
            qte = int(self.e_quantite.get().strip())
            if qte <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Erreur', 'La quantité prise doit être un nombre entier positif.', parent=self)
            return

        try:
            db.enregistrer_sortie_outillage(self.tool['id'], demandeur, qte, motif)
            messagebox.showinfo(
                'Sortie Enregistrée',
                f'Sortie de {qte}x "{self.tool["designation"]}" pour "{demandeur}" enregistrée avec succès !\n\n'
                f'Le stock disponible de cet outillage a été mis à jour.',
                parent=self
            )
            if self.on_save:
                self.on_save()
            self.destroy()
        except ValueError as ve:
            messagebox.showwarning('Validation', str(ve), parent=self)
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer la sortie :\n{e}', parent=self)


# ─────────────────────── Modale Retour Outillage (Ultra-Fluide) ───────────────────────

class RetourOutillageModal(ctk.CTkToplevel):
    """Fenêtre modale ultra-fluide : chaque sortie a son propre bouton Retourner + spinner."""

    def __init__(self, parent, sorties: list, on_save=None):
        super().__init__(parent)
        self.sorties = sorties
        self.on_save = on_save

        self.title("📥 Retour d'Outillage")
        self.geometry('760x580')
        self.resizable(True, True)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self._build_ui()

    def _build_ui(self):
        # En-tête
        ctk.CTkLabel(
            self, text="📥  Retour d'Outillage — Restitution au Magasin",
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(16, 2), padx=24, anchor='w')

        ctk.CTkLabel(
            self,
            text=f"{len(self.sorties)} sortie(s) en cours · Ajustez la quantité et cliquez sur 🔙 Retourner",
            font=FONTS['body'], text_color=COLORS['text_secondary']
        ).pack(pady=(0, 6), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(2, 10))

        # Zone scrollable pour les cartes de sorties
        self.scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        self.scroll.pack(fill='both', expand=True, padx=20, pady=(0, 8))

        self._render_sorties()

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 0))
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', padx=24, pady=10)
        make_secondary_button(btn_frame, '✖ Fermer', command=self.destroy, width=130).pack(side='right')

    def _render_sorties(self):
        # Nettoyer l'ancienne liste
        for w in self.scroll.winfo_children():
            w.destroy()

        if not self.sorties:
            ctk.CTkLabel(
                self.scroll,
                text="✅  Toutes les sorties ont été restituées au magasin.",
                font=FONTS['body_bold'], text_color=COLORS['success']
            ).pack(pady=40)
            return

        for s in self.sorties:
            self._make_sortie_card(self.scroll, s)

    def _make_sortie_card(self, parent, s: dict):
        """Crée une carte inline pour une sortie avec spinner et bouton Retourner."""
        card = ctk.CTkFrame(
            parent, fg_color=COLORS['bg_card'],
            corner_radius=10, border_width=1, border_color=COLORS['border']
        )
        card.pack(fill='x', pady=5, padx=2)

        # Ligne 1 : infos outil
        row1 = ctk.CTkFrame(card, fg_color='transparent')
        row1.pack(fill='x', padx=14, pady=(10, 4))

        ctk.CTkLabel(
            row1,
            text=f"🔧 {s['designation']}  (N° {s['numero_outillage']})",
            font=FONTS['body_bold'], text_color=COLORS['text_primary'], anchor='w'
        ).pack(side='left')

        # Badge quantité restante
        q_restante = s.get('quantite_restante', 1)
        ctk.CTkLabel(
            row1,
            text=f"  {q_restante} unité(s) à restituer",
            font=FONTS['small_bold'], text_color=COLORS['danger'], anchor='e'
        ).pack(side='right')

        # Ligne 2 : demandeur + date
        row2 = ctk.CTkFrame(card, fg_color='transparent')
        row2.pack(fill='x', padx=14, pady=(0, 8))

        ds = s.get('date_sortie', '')[:16] if s.get('date_sortie') else '-'
        ctk.CTkLabel(
            row2,
            text=f"👤 {s['demandeur']}   📅 {ds}",
            font=FONTS['small'], text_color=COLORS['text_secondary'], anchor='w'
        ).pack(side='left')

        # Ligne 3 : Spinner quantité + bouton Retourner
        row3 = ctk.CTkFrame(card, fg_color='transparent')
        row3.pack(fill='x', padx=14, pady=(0, 12))

        ctk.CTkLabel(row3, text='Quantité :', font=FONTS['body'],
                     text_color=COLORS['text_secondary']).pack(side='left', padx=(0, 6))

        # Bouton −
        qte_var = tk.IntVar(value=q_restante)

        def decrement(v=qte_var):
            if v.get() > 1:
                v.set(v.get() - 1)

        def increment(v=qte_var, max_q=q_restante):
            if v.get() < max_q:
                v.set(v.get() + 1)

        btn_minus = ctk.CTkButton(
            row3, text='−', width=32, height=32,
            command=decrement,
            fg_color=COLORS['bg_dark'], text_color=COLORS['text_primary'],
            hover_color=COLORS['border'], corner_radius=6, font=('Segoe UI', 14, 'bold')
        )
        btn_minus.pack(side='left', padx=2)

        lbl_qte = ctk.CTkLabel(
            row3, textvariable=qte_var,
            font=('Segoe UI', 14, 'bold'), text_color=COLORS['primary'],
            width=36
        )
        lbl_qte.pack(side='left', padx=4)

        btn_plus = ctk.CTkButton(
            row3, text='＋', width=32, height=32,
            command=increment,
            fg_color=COLORS['bg_dark'], text_color=COLORS['text_primary'],
            hover_color=COLORS['border'], corner_radius=6, font=('Segoe UI', 14, 'bold')
        )
        btn_plus.pack(side='left', padx=2)

        # Bouton Retourner
        def do_retour(sortie=s, v=qte_var, c=card):
            qte = v.get()
            if qte <= 0:
                return
            try:
                db.enregistrer_retour_outillage(sortie['id'], qte)
                # Supprimer la carte animée
                c.destroy()
                # Retirer de la liste
                if sortie in self.sorties:
                    self.sorties.remove(sortie)
                # Mettre à jour le compteur dans le titre
                self._update_header()
                # Rafraîchir le parent en temps réel
                if self.on_save:
                    self.on_save()
                # Si plus rien, afficher message vide
                if not self.sorties:
                    self._render_sorties()
            except Exception as e:
                messagebox.showerror('Erreur', str(e), parent=self)

        make_success_button(
            row3, '🔙 Retourner', command=do_retour, width=140
        ).pack(side='right', padx=(12, 0))

    def _update_header(self):
        """Met à jour dynamiquement le sous-titre avec le nombre de sorties restantes."""
        pass  # Le label est créé une fois, la carte disparaît visuellement



# ─────────────────────── Modale Historique Sorties ──────────────────────────────────

class HistoriqueSortiesOutillageModal(ctk.CTkToplevel):
    """Fenêtre modale d'affichage de l'historique complet des sorties et retours d'outillage."""

    def __init__(self, parent):
        super().__init__(parent)

        self.title("📋 Historique des Sorties et Retours d'Outillage")
        self.geometry('940x580')
        self.resizable(True, True)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        self._search_term = ""
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="📋  Historique des Prêts & Sorties d'Outillage",
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(18, 4), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 10))

        # Barre de recherche
        filter_row = ctk.CTkFrame(self, fg_color='transparent')
        filter_row.pack(fill='x', padx=24, pady=8)

        SearchBar(
            filter_row,
            placeholder='Rechercher par Demandeur, Désignation Outil, Statut...',
            on_change=self._on_search, width=420
        ).pack(side='left')

        # Tableau Historique
        tv_frame = ctk.CTkFrame(
            self, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1, border_color=COLORS['border']
        )
        tv_frame.pack(fill='both', expand=True, padx=24, pady=(8, 16))

        inner = ctk.CTkFrame(tv_frame, fg_color='transparent')
        inner.pack(fill='both', expand=True, padx=8, pady=8)

        self.tv = StyledTreeview(
            inner,
            columns=['statut', 'demandeur', 'numero', 'designation', 'qte_sortie', 'qte_retournee', 'qte_restante', 'date_sortie', 'date_retour'],
            headings=['Statut', 'Demandeur', 'N° Outil', 'Désignation', 'Sortie', 'Retourné', 'Restant', 'Date Sortie', 'Date Retour'],
            col_widths=[110, 140, 110, 180, 70, 80, 70, 130, 130]
        )
        self.tv.pack(side='left', fill='both', expand=True)
        add_scrollbar(inner, self.tv)

    def _on_search(self, term: str):
        self._search_term = term.strip()
        self.refresh()

    def refresh(self):
        for item in self.tv.get_children():
            self.tv.delete(item)

        sorties = db.get_historique_sorties_outillage(self._search_term)

        for i, s in enumerate(sorties):
            statut_val = s.get('statut', 'EN_COURS')
            statut_display = '🔴 EN COURS' if statut_val == 'EN_COURS' else '🟢 RETOURNÉ'
            tag = 'odd' if i % 2 != 0 else 'even'

            ds = s.get('date_sortie', '')[:16] if s.get('date_sortie') else '-'
            dr = s.get('date_retour', '')[:16] if s.get('date_retour') else '-'

            self.tv.insert('', 'end', values=(
                statut_display,
                s['demandeur'],
                s['numero_outillage'],
                s['designation'],
                str(s['quantite_sortie']),
                str(s['quantite_retournee']),
                str(s['quantite_restante']),
                ds,
                dr
            ), tags=(tag,))
        self.tv.autofit_columns()


# ─────────────────────── Modale Décharge Outillage ──────────────────────────────────

class DechargeOutillageModal(ctk.CTkToplevel):
    """
    Fenêtre modale d'enregistrement de Décharge d'Outillage et impression du bon officiel.
    Comprend 3 champs obligatoires :
      1. Nom du demandeur
      2. Nom de l'outillage (avec auto-complétion intelligente en temps réel)
      3. Date (pré-remplie à aujourd'hui, modifiable avec sélecteur de date)
    Layout adaptatif et fluide, proportionnel à toute résolution et mise à l'échelle Windows.
    """

    def __init__(self, parent, tool: dict = None, on_save=None):
        super().__init__(parent)
        self.parent_frame = parent
        self.tool = tool
        self.on_save = on_save

        self.title("📑 Bon de Décharge d'Outillage")
        self.minsize(520, 440)
        self.configure(fg_color=COLORS['bg_dark'])
        self.resizable(True, True)

        # Centrage dynamique sur l'écran
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 620, 520
        x = max(10, (sw - w) // 2)
        y = max(10, (sh - h) // 2 - 40)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.grab_set()
        self.focus()

        self._build_ui()
        if self.tool:
            self._fill_from_tool()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(18, 6))

        ctk.CTkLabel(
            header, text="📑  Bon de Décharge d'Outillage",
            font=FONTS['title_large'], text_color=COLORS['text_primary'], anchor='w'
        ).pack(fill='x')

        ctk.CTkLabel(
            header,
            text="Enregistrez la sortie de l'outillage et visualisez/imprimez le bon de décharge officiel.",
            font=FONTS['body'], text_color=COLORS['text_secondary'], anchor='w'
        ).pack(fill='x', pady=(2, 0))

        SeparatorLine(self).pack(fill='x', padx=24, pady=(6, 12))

        # ── Carte Formulaire (Layout adaptatif avec grid pondéré) ─────────────
        card = ctk.CTkFrame(
            self, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1, border_color=COLORS['border']
        )
        card.pack(fill='both', expand=True, padx=24, pady=(0, 14))

        card.grid_columnconfigure(0, weight=0, minsize=170)
        card.grid_columnconfigure(1, weight=1)

        # 1. Nom du Demandeur *
        lbl_dem = ctk.CTkLabel(
            card, text='Nom du Demandeur *',
            font=FONTS['body_bold'], text_color=COLORS['text_secondary'], anchor='w'
        )
        lbl_dem.grid(row=0, column=0, sticky='w', padx=(20, 10), pady=(18, 10))

        self.e_demandeur = make_input(
            card, placeholder="Ex: Jean Dupont, Technicien Maintenance...", width=300
        )
        self.e_demandeur.grid(row=0, column=1, sticky='ew', padx=(0, 20), pady=(18, 10))

        # 2. Nom de l'Outillage * (avec auto-complétion dynamique)
        lbl_outil = ctk.CTkLabel(
            card, text="Nom de l'Outillage *",
            font=FONTS['body_bold'], text_color=COLORS['text_secondary'], anchor='w'
        )
        lbl_outil.grid(row=1, column=0, sticky='w', padx=(20, 10), pady=10)

        self.e_outillage = AutocompleteOutillageInput(
            card, placeholder="Tapez les premières lettres de l'outil...", width=300
        )
        self.e_outillage.grid(row=1, column=1, sticky='ew', padx=(0, 20), pady=10)

        # 3. Date de Décharge * (avec sélecteur de calendrier)
        lbl_date = ctk.CTkLabel(
            card, text='Date de Décharge *',
            font=FONTS['body_bold'], text_color=COLORS['text_secondary'], anchor='w'
        )
        lbl_date.grid(row=2, column=0, sticky='w', padx=(20, 10), pady=10)

        today_str = datetime.now().strftime('%Y-%m-%d')
        self.e_date = DatePickerInput(card, initial_date=today_str, width=220)
        self.e_date.grid(row=2, column=1, sticky='w', padx=(0, 20), pady=10)

        # Note d'aide ergonomique
        info_frame = ctk.CTkFrame(card, fg_color=COLORS['bg_hover'], corner_radius=8)
        info_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=20, pady=(14, 18))

        ctk.CTkLabel(
            info_frame,
            text="💡  L'auto-complétion filtre en temps réel les outillages existants dès la première lettre tapée.\n"
                 "    Naviguez avec ↑ / ↓ et validez avec Entrée, ou cliquez sur l'outil suggéré.",
            font=FONTS['small'], text_color=COLORS['text_secondary'], justify='left', anchor='w'
        ).pack(fill='x', padx=12, pady=8)

        # Navigation clavier rapide
        self.e_demandeur.bind('<Return>', lambda e: self.e_outillage.entry.focus())

        # ── Barre d'actions inférieure ────────────────────────────────────────
        SeparatorLine(self).pack(fill='x', padx=24)

        btn_bar = ctk.CTkFrame(self, fg_color='transparent')
        btn_bar.pack(fill='x', padx=24, pady=14)

        make_secondary_button(
            btn_bar, 'Annuler', command=self.destroy, width=120
        ).pack(side='left')

        self.btn_submit = ctk.CTkButton(
            btn_bar,
            text='🖨️  Valider et imprimer',
            command=self._valider_et_imprimer,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            text_color='white',
            font=FONTS['body_bold'],
            corner_radius=8,
            height=42,
            width=210
        )
        self.btn_submit.pack(side='right')

        # Clic dans le vide de la fenêtre pour fermer la liste d'autocomplétion
        self.bind('<Button-1>', self._on_window_click)

    def _on_window_click(self, event):
        try:
            if hasattr(self, 'e_outillage'):
                widget = event.widget
                if widget != self.e_outillage.entry and widget != getattr(self.e_outillage, '_listbox', None):
                    self.e_outillage._hide_popup()
        except Exception:
            pass

    def _fill_from_tool(self):
        """Pré-remplit l'outillage si un outil a été sélectionné avant d'ouvrir la fenêtre."""
        if self.tool:
            self.e_outillage.set_selected_tool(self.tool)

    def _valider_et_imprimer(self):
        demandeur = self.e_demandeur.get().strip()
        outillage = self.e_outillage.get().strip()
        date_str = self.e_date.get().strip()

        # Validation stricte des 3 champs obligatoires
        if not demandeur:
            messagebox.showerror('Champ obligatoire', 'Veuillez saisir le nom du demandeur.', parent=self)
            self.e_demandeur.focus()
            return

        if not outillage:
            messagebox.showerror('Champ obligatoire', "Veuillez renseigner le nom de l'outillage.", parent=self)
            self.e_outillage.entry.focus()
            return

        if not date_str:
            messagebox.showerror('Champ obligatoire', 'Veuillez sélectionner ou renseigner une date valide.', parent=self)
            return

        # Récupération des métadonnées de l'outillage si existant en base
        tool_info = self.e_outillage.get_selected_tool()
        if not tool_info:
            tool_info = db.get_outillage_by_designation(outillage)

        try:
            # 1. Génération du numéro de bon de décharge séquentiel officiel
            num_bon = db.get_next_numero_decharge()

            # 2. Génération du fichier PDF corporate officiel
            pdf_path = generer_bon_decharge_pdf(
                num_bon=num_bon,
                demandeur=demandeur,
                outillage=outillage,
                date_str=date_str,
                tool_info=tool_info
            )

            # 3. Enregistrement dans la table dédiée 'decharges_outillage'
            db.enregistrer_decharge_outillage(
                demandeur=demandeur,
                outillage=outillage,
                date_str=date_str,
                numero_bon=num_bon,
                chemin_pdf=pdf_path
            )

            # 4. Rafraîchissement éventuel et fermeture de la modale
            if self.on_save:
                try:
                    self.on_save()
                except Exception:
                    pass

            parent_ref = self.parent_frame
            self.destroy()

            # 5. Ouverture instantanée de la visionneuse PDF intégrée (avec option Imprimer)
            ouvrir_pdf_viewer(parent_ref, pdf_path, title=f"Bon de Décharge {num_bon}")

        except Exception as e:
            messagebox.showerror('Erreur', f"Une erreur est survenue lors de l'enregistrement de la décharge :\n{e}", parent=self)


