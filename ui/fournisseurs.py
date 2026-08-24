"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/fournisseurs.py
Écran de Gestion des Fournisseurs (Liste, Fiche détaillée avec produits rattachés & modale d'ajout/édition).
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from ui.theme import COLORS, FONTS
from ui.widgets import (StyledTreeview, add_scrollbar, make_primary_button,
                         make_danger_button, make_secondary_button,
                         make_input, SearchBar, SeparatorLine)
import database.db_manager as db


class FournisseursFrame(ctk.CTkFrame):
    """Écran Gestion des Fournisseurs avec vue Liste et Fiche Détaillée."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)
        self._search_term = ""
        self._selected_fournisseur_id = None

        self._search_timer = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header, text='🏭  Gestion des Fournisseurs',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        self.badge_total = ctk.CTkLabel(
            header, text='0 fournisseur(s)',
            font=FONTS['body_bold'],
            text_color=COLORS['text_secondary']
        )
        self.badge_total.pack(side='left', padx=12, pady=(4, 0))

        btn_frame = ctk.CTkFrame(header, fg_color='transparent')
        btn_frame.pack(side='right')

        make_primary_button(
            btn_frame, 'Nouveau Fournisseur', command=self._open_add_modal,
            icon='＋', width=190
        ).pack(side='left', padx=4)

        SeparatorLine(self).pack(fill='x', padx=24, pady=(0, 10))

        # ── Zone Contenu Split (Gauche: Liste Fournisseurs | Droite: Fiche Détaillée) ──
        main_split = ctk.CTkFrame(self, fg_color='transparent')
        main_split.pack(fill='both', expand=True, padx=24, pady=(0, 16))
        main_split.grid_columnconfigure(0, weight=4)
        main_split.grid_columnconfigure(1, weight=5)
        main_split.grid_rowconfigure(0, weight=1)

        # ── PANNEAU GAUCHE : LISTE DES FOURNISSEURS ──────────────────────────
        left_panel = ctk.CTkFrame(
            main_split, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1, border_color=COLORS['border']
        )
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        left_panel.grid_rowconfigure(2, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        # En-tête gauche + Recherche
        left_header = ctk.CTkFrame(left_panel, fg_color='transparent')
        left_header.grid(row=0, column=0, sticky='ew', padx=16, pady=(12, 6))

        ctk.CTkLabel(
            left_header, text='📋  Liste des Fournisseurs',
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(side='left')

        search_frame = ctk.CTkFrame(left_panel, fg_color='transparent')
        search_frame.grid(row=1, column=0, sticky='ew', padx=16, pady=(0, 8))

        SearchBar(
            search_frame,
            placeholder='Rechercher nom, numéro, adresse...',
            on_change=self._on_search, width=280
        ).pack(fill='x')

        # Treeview liste fournisseurs
        tv_frame_f = ctk.CTkFrame(left_panel, fg_color='transparent')
        tv_frame_f.grid(row=2, column=0, sticky='nsew', padx=8, pady=(0, 12))

        self.tv_fournisseurs = StyledTreeview(
            tv_frame_f,
            columns=['nom', 'numero', 'adresse', 'nb_prod'],
            headings=['Nom Fournisseur', 'Numéro / Tél', 'Adresse', 'Produits'],
            col_widths=[140, 110, 150, 65],
            stretch_cols=True
        )
        self.tv_fournisseurs.pack(side='left', fill='both', expand=True)
        self.tv_fournisseurs.bind('<<TreeviewSelect>>', self._on_select_fournisseur)
        add_scrollbar(tv_frame_f, self.tv_fournisseurs)

        # ── PANNEAU DROIT : FICHE DÉTAILLÉE FOURNISSEUR ──────────────────────
        self.right_panel = ctk.CTkFrame(
            main_split, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1, border_color=COLORS['border']
        )
        self.right_panel.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

        self._build_fiche_empty()

    def _build_fiche_empty(self):
        """Affiche un état vide lorsque aucun fournisseur n'est sélectionné."""
        for w in self.right_panel.winfo_children():
            w.destroy()

        empty_box = ctk.CTkFrame(self.right_panel, fg_color='transparent')
        empty_box.place(relx=0.5, rely=0.5, anchor='center')

        ctk.CTkLabel(
            empty_box, text='🏭', font=('Segoe UI Emoji', 48),
            text_color=COLORS['text_muted']
        ).pack(pady=4)

        ctk.CTkLabel(
            empty_box, text='Sélectionnez un fournisseur',
            font=FONTS['subtitle'], text_color=COLORS['text_secondary']
        ).pack()

        ctk.CTkLabel(
            empty_box,
            text='Cliquez sur un fournisseur dans la liste pour consulter\nsa fiche détaillée et ses produits rattachés.',
            font=FONTS['small'], text_color=COLORS['text_muted'], justify='center'
        ).pack(pady=4)

    def refresh(self):
        """Rafraîchit la liste des fournisseurs."""
        for item in self.tv_fournisseurs.get_children():
            self.tv_fournisseurs.delete(item)

        fournisseurs = db.get_all_fournisseurs(self._search_term)
        self.badge_total.configure(text=f'{len(fournisseurs)} fournisseur(s)')

        for i, f in enumerate(fournisseurs):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tv_fournisseurs.insert('', 'end', iid=str(f['id']), values=(
                f['nom'],
                f['numero'] or '—',
                f['adresse'] or '—',
                str(f['nb_produits'])
            ), tags=(tag,))

        # Si un fournisseur était sélectionné, recharger sa fiche
        if self._selected_fournisseur_id:
            fourn = db.get_fournisseur_by_id(self._selected_fournisseur_id)
            if fourn:
                self._show_fiche_fournisseur(fourn)
            else:
                self._selected_fournisseur_id = None
                self._build_fiche_empty()

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

    def _on_select_fournisseur(self, event):
        sel = self.tv_fournisseurs.selection()
        if not sel:
            return
        fid = int(sel[0])
        self._selected_fournisseur_id = fid
        fournisseur = db.get_fournisseur_by_id(fid)
        if fournisseur:
            self._show_fiche_fournisseur(fournisseur)

    def _show_fiche_fournisseur(self, fournisseur: dict):
        """Affiche la fiche détaillée complète du fournisseur sélectionné."""
        for w in self.right_panel.winfo_children():
            w.destroy()

        # En-tête de la fiche fournisseur
        header = ctk.CTkFrame(self.right_panel, fg_color='transparent')
        header.pack(fill='x', padx=20, pady=(16, 10))

        info_box = ctk.CTkFrame(header, fg_color='transparent')
        info_box.pack(side='left')

        ctk.CTkLabel(
            info_box, text=f"🏭  {fournisseur['nom']}",
            font=FONTS['title'], text_color=COLORS['primary']
        ).pack(anchor='w')

        num = fournisseur.get('numero') or 'Non renseigné'
        adr = fournisseur.get('adresse') or 'Non renseignée'
        ctk.CTkLabel(
            info_box, text=f"📞 {num}   |   📍 {adr}",
            font=FONTS['body'], text_color=COLORS['text_secondary']
        ).pack(anchor='w', pady=(2, 0))

        # Boutons d'action fournisseur
        act_box = ctk.CTkFrame(header, fg_color='transparent')
        act_box.pack(side='right')

        make_secondary_button(
            act_box, '✏️ Modifier',
            command=lambda: self._open_edit_modal(fournisseur), width=100
        ).pack(side='left', padx=4)

        make_danger_button(
            act_box, '🗑️ Supprimer',
            command=lambda: self._delete_fournisseur(fournisseur), width=110
        ).pack(side='left', padx=4)

        SeparatorLine(self.right_panel).pack(fill='x', padx=20, pady=6)

        # Bar de titre de la liste de produits associés + Bouton d'ajout
        prod_title_frame = ctk.CTkFrame(self.right_panel, fg_color='transparent')
        prod_title_frame.pack(fill='x', padx=20, pady=(8, 8))

        ctk.CTkLabel(
            prod_title_frame,
            text=f"📦 Produits associés ({fournisseur.get('nb_produits', 0)})",
            font=FONTS['subtitle'], text_color=COLORS['text_primary']
        ).pack(side='left')

        make_primary_button(
            prod_title_frame, '＋ Nouveau Produit',
            command=lambda: self._add_product_for_fournisseur(fournisseur),
            width=180, height=36
        ).pack(side='right')

        # Tableau des produits rattachés (sans emplacement, conformément à la demande)
        tv_frame_p = ctk.CTkFrame(self.right_panel, fg_color='transparent')
        tv_frame_p.pack(fill='both', expand=True, padx=12, pady=(0, 16))

        tv_prods = StyledTreeview(
            tv_frame_p,
            columns=['date', 'code', 'designation', 'stock', 'unite'],
            headings=['Date (Livraison/Création)', 'Référence', 'Désignation', 'Stock', 'Unité'],
            col_widths=[140, 110, 200, 70, 70],
            stretch_cols=True
        )
        tv_prods.pack(side='left', fill='both', expand=True)
        add_scrollbar(tv_frame_p, tv_prods)

        # Remplir les produits rattachés
        produits = db.get_produits_par_fournisseur(fournisseur['id'])
        for i, p in enumerate(produits):
            tag = 'even' if i % 2 == 0 else 'odd'
            tv_prods.insert('', 'end', values=(
                p['date_derniere_livraison'],
                p['code_barres'],
                p['designation'],
                str(p['quantite_stock']),
                p['unite']
            ), tags=(tag,))

    def _open_add_modal(self):
        FournisseurModal(self, mode='add', on_save=self.refresh)

    def _open_edit_modal(self, fournisseur: dict):
        FournisseurModal(self, mode='edit', fournisseur=fournisseur, on_save=self.refresh)

    def _delete_fournisseur(self, fournisseur: dict):
        confirm = messagebox.askyesno(
            'Confirmer la suppression',
            f"Voulez-vous vraiment supprimer le fournisseur :\n\n  {fournisseur['nom']} ?\n\n"
            "Les produits rattachés ne seront pas supprimés, mais n'auront plus de fournisseur.",
            parent=self
        )
        if confirm:
            db.supprimer_fournisseur(fournisseur['id'])
            self._selected_fournisseur_id = None
            self._build_fiche_empty()
            self.refresh()

    def _add_product_for_fournisseur(self, fournisseur: dict):
        ProduitRapideModal(self, fournisseur=fournisseur, on_save=self.refresh)


# ─────────────────────── Modale Fournisseur ───────────────────────────────────

class FournisseurModal(ctk.CTkToplevel):
    """Formulaire modale d'ajout ou de modification d'un fournisseur."""

    def __init__(self, parent, mode: str = 'add', fournisseur: dict = None, on_save=None):
        super().__init__(parent)
        self.mode = mode
        self.fournisseur = fournisseur or {}
        self.on_save = on_save

        self.title('➕  Nouveau Fournisseur' if mode == 'add' else '✏️  Modifier le Fournisseur')
        self.geometry('500x380')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        # Centrer la fenêtre
        self.update_idletasks()
        w, h = 500, 380
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

        self._build_ui()
        if mode == 'edit' and fournisseur:
            self._fill_fields()

    def _build_ui(self):
        # Boutons fixes en bas
        btn_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], height=60, border_width=1, border_color=COLORS['border'])
        btn_frame.pack(side='bottom', fill='x')

        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=110).pack(side='right', padx=16, pady=12)
        make_primary_button(
            btn_frame, 'Enregistrer' if self.mode == 'add' else 'Sauvegarder',
            command=self._save, icon='💾', width=160
        ).pack(side='right', padx=(0, 8), pady=12)

        # En-tête
        ctk.CTkLabel(
            self, text='➕  Nouveau Fournisseur' if self.mode == 'add' else '✏️  Modifier le Fournisseur',
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(20, 4), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 16))

        # Champs du formulaire
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=24)

        def row(label_text, placeholder):
            frame = ctk.CTkFrame(body, fg_color='transparent')
            frame.pack(fill='x', pady=6)
            ctk.CTkLabel(
                frame, text=label_text, font=FONTS['body_bold'],
                text_color=COLORS['text_secondary'], width=150, anchor='w'
            ).pack(side='left')
            inp = make_input(frame, placeholder=placeholder)
            inp.pack(side='left', fill='x', expand=True)
            return inp

        self.e_nom = row('Nom du fournisseur *', 'Ex: SARL HydroTech / Bosch')
        self.e_num = row('Numéro / Téléphone', 'Ex: 021 55 44 33')
        self.e_adr = row('Adresse', 'Ex: Zone Industrielle, Alger')

    def _fill_fields(self):
        f = self.fournisseur
        self.e_nom.insert(0, f.get('nom', ''))
        self.e_num.insert(0, f.get('numero', ''))
        self.e_adr.insert(0, f.get('adresse', ''))

    def _save(self):
        nom = self.e_nom.get().strip()
        if not nom:
            messagebox.showerror('Erreur', 'Le nom du fournisseur est obligatoire.', parent=self)
            return

        data = {
            'nom': nom,
            'numero': self.e_num.get().strip(),
            'adresse': self.e_adr.get().strip()
        }

        try:
            if self.mode == 'add':
                db.ajouter_fournisseur(data)
                messagebox.showinfo('Succès', f'Fournisseur "{nom}" créé avec succès !', parent=self)
            else:
                db.modifier_fournisseur(self.fournisseur['id'], data)
                messagebox.showinfo('Succès', f'Fournisseur "{nom}" mis à jour !', parent=self)

            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer :\n{e}', parent=self)


# ─────────────────────── Modale Produit Rapide (depuis Fournisseur) ────────────

class ProduitRapideModal(ctk.CTkToplevel):
    """Formulaire simplifié pour ajouter un produit directement depuis la fiche fournisseur.
    Champs : Date de livraison, Désignation, Quantité (+ Référence auto-suggérée)."""

    def __init__(self, parent, fournisseur: dict, on_save=None):
        super().__init__(parent)
        self.fournisseur = fournisseur
        self.on_save = on_save

        titre = f"➕  Nouveau Produit — {fournisseur.get('nom', '')}"
        self.title(titre)
        self.geometry('520x440')
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.grab_set()
        self.focus()

        # Centrer la fenêtre
        self.update_idletasks()
        w, h = 520, 440
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}')

        self._build_ui()

    def _build_ui(self):
        # Boutons fixes en bas
        btn_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], height=60,
                                 border_width=1, border_color=COLORS['border'])
        btn_frame.pack(side='bottom', fill='x')
        make_secondary_button(btn_frame, 'Annuler', command=self.destroy, width=120).pack(side='right', padx=16, pady=12)
        make_primary_button(btn_frame, 'Enregistrer', command=self._save, icon='💾', width=170).pack(side='right', padx=(0, 8), pady=12)

        # En-tête
        ctk.CTkLabel(
            self,
            text=f"➕  Nouveau Produit",
            font=FONTS['title_large'], text_color=COLORS['text_primary']
        ).pack(pady=(18, 2), padx=24, anchor='w')

        ctk.CTkLabel(
            self,
            text=f"🏭  Fournisseur : {self.fournisseur.get('nom', '')}",
            font=FONTS['body_bold'], text_color=COLORS['primary']
        ).pack(pady=(0, 4), padx=24, anchor='w')

        SeparatorLine(self).pack(fill='x', padx=24, pady=(4, 14))

        # Zone des champs
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=24)

        def row(label_text, placeholder, required=False):
            frame = ctk.CTkFrame(body, fg_color='transparent')
            frame.pack(fill='x', pady=8)
            lbl = label_text + (' *' if required else '')
            ctk.CTkLabel(
                frame, text=lbl, font=FONTS['body_bold'],
                text_color=COLORS['text_secondary'], width=175, anchor='w'
            ).pack(side='left')
            inp = make_input(frame, placeholder=placeholder)
            inp.pack(side='left', fill='x', expand=True)
            return inp

        # 1. Date de livraison (avec bouton Aujourd'hui)
        frame_date = ctk.CTkFrame(body, fg_color='transparent')
        frame_date.pack(fill='x', pady=8)
        ctk.CTkLabel(
            frame_date, text='Date de livraison', font=FONTS['body_bold'],
            text_color=COLORS['text_secondary'], width=175, anchor='w'
        ).pack(side='left')
        self.e_date = make_input(frame_date, placeholder='AAAA-MM-JJ  (ex: 2026-08-12)')
        self.e_date.pack(side='left', fill='x', expand=True, padx=(0, 6))

        def _today():
            from datetime import datetime
            self.e_date.delete(0, 'end')
            self.e_date.insert(0, datetime.now().strftime('%Y-%m-%d'))

        make_secondary_button(frame_date, "Aujourd'hui", command=_today, width=105, height=36).pack(side='left')

        # 2. Désignation
        self.e_design = row('Désignation', 'Nom du produit / pièce', required=True)

        # 3. Référence (auto-suggérée, modifiable)
        frame_ref = ctk.CTkFrame(body, fg_color='transparent')
        frame_ref.pack(fill='x', pady=8)
        ctk.CTkLabel(
            frame_ref, text='Référence *', font=FONTS['body_bold'],
            text_color=COLORS['text_secondary'], width=175, anchor='w'
        ).pack(side='left')
        self.e_ref = make_input(frame_ref, placeholder='Ex: REF-0001 (auto-suggérée)')
        self.e_ref.pack(side='left', fill='x', expand=True, padx=(0, 6))

        make_secondary_button(
            frame_ref, '⚡ Suggérer', command=self._suggest_ref, width=105, height=36
        ).pack(side='left')

        # 4. Quantité
        self.e_qte = row('Quantité', '0')

        # Infobulle
        ctk.CTkLabel(
            body,
            text='ℹ️  Les autres détails du produit peuvent être complétés\n    dans la section "Pièces de Rechange" du catalogue.',
            font=FONTS['small'], text_color=COLORS['text_muted'],
            justify='left'
        ).pack(anchor='w', pady=(10, 0))

    def _suggest_ref(self):
        """Génère une référence suggérée à partir de la désignation et du nom fournisseur."""
        design = self.e_design.get().strip()
        fourn_name = self.fournisseur.get('nom', 'FOURN')
        prefix = ''.join(c for c in fourn_name[:4].upper() if c.isalpha())
        suffix = ''.join(c for c in design[:4].upper() if c.isalnum())
        import random
        num = random.randint(1000, 9999)
        suggested = f"{prefix}-{suffix}-{num}" if suffix else f"{prefix}-{num}"
        self.e_ref.delete(0, 'end')
        self.e_ref.insert(0, suggested)

    def _save(self):
        designation = self.e_design.get().strip()
        ref = self.e_ref.get().strip()

        if not designation:
            messagebox.showerror('Erreur', 'La désignation est obligatoire.', parent=self)
            return
        if not ref:
            messagebox.showerror('Erreur', 'La référence est obligatoire.\nCliquez sur "⚡ Suggérer" pour en générer une automatiquement.', parent=self)
            return

        try:
            qte = int(self.e_qte.get().strip() or '0')
        except ValueError:
            messagebox.showerror('Erreur', 'La quantité doit être un nombre entier.', parent=self)
            return

        data = {
            'code_barres':            ref,
            'designation':            designation,
            'emplacement':            '',
            'quantite_stock':         qte,
            'unite':                  'Unité',
            'utilite_ligne':          'Aucune',
            'nom_machine':            'N/A',
            'seuil_alerte':           5,
            'categorie_piece':        'Pièce de Rechange',
            'fournisseur_id':         self.fournisseur.get('id'),
            'date_rechange_initiale': self.e_date.get().strip(),
            'duree_vie':              '',
            'prochaine_date_rechange': ''
        }

        try:
            new_id = db.ajouter_produit(data)
            # Enregistrer aussi un mouvement d'entrée si date renseignée
            date_val = self.e_date.get().strip()
            if date_val:
                try:
                    import database.db_manager as db2
                    conn = db2.get_connection()
                    conn.execute(
                        "INSERT INTO mouvements (produit_id, type_mouvement, quantite, date_heure, commentaire) VALUES (?, 'ENTREE', ?, ?, ?)",
                        (new_id, qte, date_val, f"Livraison fournisseur {self.fournisseur.get('nom','')}")
                    )
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

            messagebox.showinfo(
                'Succès',
                f'Produit "{designation}" ajouté avec succès !\nRéférence : {ref}',
                parent=self
            )
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror('Erreur BDD', f'Impossible d\'enregistrer :\n{e}', parent=self)
