"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/dashboard.py
Tableau de bord principal avec KPIs, alertes de stock et mouvements récents.
"""

import customtkinter as ctk
import tkinter as tk
from ui.theme import COLORS, FONTS
from ui.widgets import (make_stat_card, make_section_header, StyledTreeview,
                         add_scrollbar, SeparatorLine, BadgeLabel, make_success_button)
import database.db_manager as db


class DashboardFrame(ctk.CTkFrame):
    """Écran Tableau de Bord avec statistiques et graphique mensuel."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_dark'], **kwargs)

        self.month_map = {}
        self.selected_month = None

        # Conteneur défilable
        self.scroll = ctk.CTkScrollableFrame(self, fg_color='transparent', corner_radius=0)
        self.scroll.pack(fill='both', expand=True)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # ── En-tête ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self.scroll, fg_color='transparent')
        header.pack(fill='x', padx=24, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text='Tableau de Bord — SARL NOMADE AYRIS',
            font=FONTS['title_large'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        self.lbl_time = ctk.CTkLabel(
            header, text='',
            font=FONTS['body'],
            text_color=COLORS['text_secondary']
        )
        self.lbl_time.pack(side='right', pady=(6, 0))
        self._update_clock()

        ctk.CTkButton(
            header, text='↻ Actualiser',
            command=self.refresh,
            fg_color=COLORS['bg_hover'],
            hover_color=COLORS['bg_selected'],
            text_color=COLORS['text_secondary'],
            font=FONTS['body_bold'],
            corner_radius=8,
            height=34, width=120
        ).pack(side='right', padx=(0, 10))

        SeparatorLine(self.scroll).pack(fill='x', padx=24)

        # ── KPI Cards ──────────────────────────────────────────────────────
        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color='transparent')
        self.kpi_frame.pack(fill='x', padx=24, pady=16)

        # ── Zone principale (2 colonnes : Alertes + Mouvements) ───────────
        main_area = ctk.CTkFrame(self.scroll, fg_color='transparent')
        main_area.pack(fill='x', padx=24, pady=(0, 16))
        main_area.grid_columnconfigure(0, weight=3)
        main_area.grid_columnconfigure(1, weight=2)

        # ── Tableau alertes ───────────────────────────────────────────────
        alert_panel = ctk.CTkFrame(
            main_area, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1,
            border_color=COLORS['border']
        )
        alert_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

        alert_header = ctk.CTkFrame(alert_panel, fg_color='transparent')
        alert_header.pack(fill='x', padx=16, pady=(12, 8))

        ctk.CTkLabel(
            alert_header, text='🚨  Produits en Alerte de Stock',
            font=FONTS['subtitle'],
            text_color=COLORS['danger']
        ).pack(side='left')
        self.badge_alerts = BadgeLabel(alert_header, '0', color=COLORS['danger'])
        self.badge_alerts.pack(side='left', padx=8)

        make_success_button(
            alert_header, '📊 Exporter Excel', command=self._exporter_alertes_excel, width=140
        ).pack(side='right')

        tv_frame_alert = ctk.CTkFrame(alert_panel, fg_color='transparent', height=260)
        tv_frame_alert.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        tv_frame_alert.pack_propagate(False)

        self.tv_alerts = StyledTreeview(
            tv_frame_alert,
            columns=['ref', 'designation', 'stock', 'seuil', 'ligne', 'machine'],
            headings=['Référence', 'Désignation', 'Stock', 'Seuil', 'Ligne(s)', 'Machine'],
            col_widths=[110, 180, 75, 55, 80, 110]
        )
        add_scrollbar(tv_frame_alert, self.tv_alerts)

        # ── Derniers mouvements ───────────────────────────────────────────
        mvt_panel = ctk.CTkFrame(
            main_area, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1,
            border_color=COLORS['border']
        )
        mvt_panel.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

        mvt_header = ctk.CTkFrame(mvt_panel, fg_color='transparent')
        mvt_header.pack(fill='x', padx=16, pady=(12, 8))
        ctk.CTkLabel(
            mvt_header, text='🕒  Derniers Mouvements',
            font=FONTS['subtitle'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        tv_frame_mvt = ctk.CTkFrame(mvt_panel, fg_color='transparent', height=260)
        tv_frame_mvt.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        tv_frame_mvt.pack_propagate(False)

        self.tv_mvts = StyledTreeview(
            tv_frame_mvt,
            columns=['date', 'type', 'produit', 'qte'],
            headings=['Date / Heure', 'Type', 'Produit', 'Qté'],
            col_widths=[130, 95, 140, 55]
        )
        add_scrollbar(tv_frame_mvt, self.tv_mvts)

        # ── Widget Suivi & Alertes Pièces de Rechange (Rouge / Orange) ─────
        rechange_panel = ctk.CTkFrame(
            self.scroll, fg_color=COLORS['bg_card'],
            corner_radius=12, border_width=1,
            border_color=COLORS['border']
        )
        rechange_panel.pack(fill='x', padx=24, pady=(0, 16))

        rechange_header = ctk.CTkFrame(rechange_panel, fg_color='transparent')
        rechange_header.pack(fill='x', padx=16, pady=(12, 8))

        ctk.CTkLabel(
            rechange_header, text='⏱️  Suivi & Alertes Échéances Pièces de Rechange',
            font=FONTS['subtitle'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        self.badge_rechange_rouge = ctk.CTkLabel(
            rechange_header, text='🔴 0 Urgent',
            font=FONTS['body_bold'], text_color=COLORS['danger'],
            fg_color=COLORS['danger_bg'], corner_radius=6, padx=10, pady=4
        )
        self.badge_rechange_rouge.pack(side='left', padx=6)

        self.badge_rechange_orange = ctk.CTkLabel(
            rechange_header, text='🟠 0 À anticiper',
            font=FONTS['body_bold'], text_color=COLORS['warning'],
            fg_color=COLORS['warning_bg'], corner_radius=6, padx=10, pady=4
        )
        self.badge_rechange_orange.pack(side='left', padx=4)

        tv_frame_rechange = ctk.CTkFrame(rechange_panel, fg_color='transparent', height=200)
        tv_frame_rechange.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        tv_frame_rechange.pack_propagate(False)

        self.tv_rechange = StyledTreeview(
            tv_frame_rechange,
            columns=['statut', 'ref', 'designation', 'fournisseur', 'echeance', 'delai'],
            headings=['Échéance Statut', 'Référence', 'Désignation', 'Fournisseur', 'Date Échéance', 'Délai Restant'],
            col_widths=[140, 110, 220, 140, 120, 110]
        )
        add_scrollbar(tv_frame_rechange, self.tv_rechange)

        # ── Graphique Camembert des Mouvements ────────────────────────────
        graph_panel = ctk.CTkFrame(
            self.scroll, fg_color=COLORS['bg_card'],
            corner_radius=14, border_width=1,
            border_color=COLORS['border']
        )
        graph_panel.pack(fill='x', padx=24, pady=(0, 24))

        graph_header = ctk.CTkFrame(graph_panel, fg_color='transparent')
        graph_header.pack(fill='x', padx=16, pady=(14, 10))

        ctk.CTkLabel(
            graph_header, text='📊  Répartition des Mouvements Mensuels',
            font=FONTS['subtitle'],
            text_color=COLORS['text_primary']
        ).pack(side='left')

        # Sélecteur de mois
        self.var_month = tk.StringVar()
        self.opt_month = ctk.CTkOptionMenu(
            graph_header,
            variable=self.var_month,
            values=['Chargement...'],
            command=self._on_month_selected,
            fg_color=COLORS['primary'],
            button_color=COLORS['primary_dark'],
            font=FONTS['body_bold'],
            dropdown_font=FONTS['body'],
            corner_radius=8,
            width=180
        )
        self.opt_month.pack(side='left', padx=16)

        # Badges résumés mensuels (Encadrement fixe anti-clipping)
        badges_frame = ctk.CTkFrame(graph_header, fg_color='transparent')
        badges_frame.pack(side='right')

        self.lbl_sum_entrees = ctk.CTkLabel(
            badges_frame, text='▲ Entrées: 0 mvt',
            font=FONTS['body_bold'], text_color='#10B981',
            fg_color='#D1FAE5', corner_radius=8, padx=14, pady=5, width=160
        )
        self.lbl_sum_entrees.pack(side='left', padx=(6, 4))

        self.lbl_sum_sorties = ctk.CTkLabel(
            badges_frame, text='▼ Sorties: 0 mvt',
            font=FONTS['body_bold'], text_color='#EF4444',
            fg_color='#FEE2E2', corner_radius=8, padx=14, pady=5, width=160
        )
        self.lbl_sum_sorties.pack(side='left', padx=4)

        self.lbl_sum_retours = ctk.CTkLabel(
            badges_frame, text='↩ Retours: 0 mvt',
            font=FONTS['body_bold'], text_color='#D97706',
            fg_color='#FEF3C7', corner_radius=8, padx=14, pady=5, width=160
        )
        self.lbl_sum_retours.pack(side='left', padx=(4, 6))
        self._chart_data = None

        # Zone du Canvas pour le graphique camembert
        self.chart_canvas = tk.Canvas(
            graph_panel, bg='#F8FAFC', highlightthickness=0, height=340
        )
        self.chart_canvas.pack(fill='x', padx=16, pady=(0, 16))
        self.chart_canvas.bind('<Configure>', lambda e: self._update_graph())
        self._tooltip_id = None
        self._tooltip_window = None
        self.chart_canvas.bind('<Motion>', self._on_pie_hover)
        self.chart_canvas.bind('<Leave>', self._on_pie_leave)

    def _update_clock(self):
        from datetime import datetime
        now_dt = datetime.now()
        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        mois = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        
        jour_str = jours[now_dt.weekday()]
        mois_str = mois[now_dt.month - 1]
        
        now = f"  📅  {jour_str} {now_dt.day} {mois_str} {now_dt.year}   🕐  {now_dt.strftime('%H:%M:%S')}"
        self.lbl_time.configure(text=now)
        self.after(1000, self._update_clock)

    def _format_month_fr(self, ym: str) -> str:
        """Convertit 'YYYY-MM' en 'Mois YYYY' (ex: '2026-07' -> 'Juillet 2026')."""
        try:
            y, m = ym.split('-')
            mois = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
            return f"{mois[int(m)-1]} {y}"
        except Exception:
            return ym

    def _on_month_selected(self, choice: str):
        ym = self.month_map.get(choice)
        if ym:
            self.selected_month = ym
            self._update_graph()

    def _on_pie_hover(self, event):
        """Affiche un tooltip au survol des parts du camembert."""
        if not self._pie_slices:
            return
        import math
        cx = getattr(self, '_pie_cx', 0)
        cy = getattr(self, '_pie_cy', 0)
        r = getattr(self, '_pie_r', 0)
        if r == 0:
            return
        dx = event.x - cx
        dy = event.y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        inner_r = r * 0.35
        if dist > r or dist < inner_r:
            self._hide_pie_tooltip()
            return

        # Angle en degrés [0, 360) dans le sens anti-horaire depuis l'Est (3h)
        angle = math.degrees(math.atan2(-dy, dx)) % 360

        for (start, extent, label, value, pct, color) in self._pie_slices:
            # Un angle A appartient au secteur (start, extent) ssi (A - start) % 360 <= extent
            if (angle - start) % 360 <= extent:
                if getattr(self, '_current_tip_label', None) == label and self._tooltip_window:
                    return  # Déjà affiché pour cette part
                self._hide_pie_tooltip()
                tip = tk.Toplevel(self.chart_canvas)
                tip.wm_overrideredirect(True)
                tip.configure(bg='#1E293B')
                tip.wm_geometry(f"+{event.x_root + 14}+{event.y_root - 50}")
                f = tk.Frame(tip, bg='#1E293B', padx=12, pady=8)
                f.pack()
                dot = tk.Frame(f, bg=color, width=12, height=12)
                dot.grid(row=0, column=0, padx=(0, 6), pady=2)
                tk.Label(f, text=label, bg='#1E293B', fg='#FFFFFF',
                         font=('Segoe UI', 10, 'bold')).grid(row=0, column=1, sticky='w')
                tk.Label(f, text=f"{value} mouvement(s)", bg='#1E293B', fg='#94A3B8',
                         font=('Segoe UI', 9)).grid(row=1, column=0, columnspan=2, sticky='w')
                tk.Label(f, text=f"{pct:.1f}%", bg='#1E293B', fg=color,
                         font=('Segoe UI', 14, 'bold')).grid(row=2, column=0, columnspan=2, sticky='w')
                self._tooltip_window = tip
                self._current_tip_label = label
                return
        self._hide_pie_tooltip()

    def _hide_pie_tooltip(self):
        if self._tooltip_window:
            try:
                self._tooltip_window.destroy()
            except Exception:
                pass
            self._tooltip_window = None
        self._current_tip_label = None

    def _on_pie_leave(self, event):
        self._hide_pie_tooltip()

    def _update_graph(self):
        if not self.selected_month:
            return

        import math

        stats = db.get_stats_mouvements_mois(self.selected_month)
        self._chart_data = stats

        total_e = stats['total_entrees']
        total_s = stats['total_sorties']
        total_r = stats['total_retours']
        total   = total_e + total_s + total_r

        # Mettre à jour les badges
        self.lbl_sum_entrees.configure(text=f"▲ Entrées: {total_e} mvt")
        self.lbl_sum_sorties.configure(text=f"▼ Sorties: {total_s} mvt")
        self.lbl_sum_retours.configure(text=f"↩ Retours: {total_r} mvt")

        canvas = self.chart_canvas
        canvas.delete("all")
        self._pie_slices = []

        width  = canvas.winfo_width() or 900
        height = 340

        # ── Fond dégradé subtil (rectangles empilés du blanc au gris très clair) ──
        for i in range(height):
            ratio  = i / height
            r_ch   = int(0xF8 + ratio * (0xF1 - 0xF8))
            g_ch   = int(0xFA + ratio * (0xF5 - 0xFA))
            b_ch   = int(0xFC + ratio * (0xF9 - 0xFC))
            col_bg = f'#{r_ch:02x}{g_ch:02x}{b_ch:02x}'
            canvas.create_line(0, i, width, i, fill=col_bg)

        # ── Données du camembert ────────────────────────────────────────────
        PIE_COLORS = [
            ('#0EA5E9', '#0284C7', 'Entrées',  total_e),  # Bleu ciel
            ('#EF4444', '#DC2626', 'Sorties',  total_s),  # Rouge
            ('#F59E0B', '#D97706', 'Retours',  total_r),  # Ambre
        ]

        # Centrer le camembert sur la moitié gauche, légende à droite
        pie_size   = min(height - 40, 280)
        pie_r      = pie_size // 2
        cx         = width // 3
        cy         = height // 2
        self._pie_cx = cx
        self._pie_cy = cy
        self._pie_r  = pie_r

        if total == 0:
            # Aucune donnée
            canvas.create_oval(cx - pie_r, cy - pie_r, cx + pie_r, cy + pie_r,
                               fill='#E2E8F0', outline='#CBD5E1', width=2)
            canvas.create_text(cx, cy, text='Aucun\nmouvement',
                               font=('Segoe UI', 14, 'bold'), fill='#94A3B8', justify='center')
            canvas.create_text(width * 2 // 3, cy,
                               text=f'Mois : {self._format_month_fr(self.selected_month)}\n\nAucun mouvement enregistré.',
                               font=('Segoe UI', 13), fill='#64748B', justify='center')
            return

        # ── Ombre du disque ────────────────────────────────────────────────
        for sh in range(8, 0, -1):
            alpha_val = int(0xE0 + sh * 2)
            sh_col = f'#{alpha_val:02x}{alpha_val:02x}{alpha_val:02x}'
            canvas.create_oval(cx - pie_r + sh, cy - pie_r + sh,
                               cx + pie_r + sh, cy + pie_r + sh,
                               fill=sh_col, outline='')

        # ── Dessiner les parts ───────────────────────────────────────────────
        start_angle = 90.0  # Démarrer à 12h
        slices_drawn = []

        for (col_main, col_dark, label, value) in PIE_COLORS:
            if value == 0:
                continue
            pct    = value / total * 100
            extent = value / total * 360.0

            # Part principale
            canvas.create_arc(
                cx - pie_r, cy - pie_r, cx + pie_r, cy + pie_r,
                start=start_angle, extent=extent,
                fill=col_main, outline='#FFFFFF', width=3,
                style='pieslice'
            )

            # Stocker pour le hover (start_angle % 360 correspond directement au système d'angle Tkinter)
            slices_drawn.append((start_angle % 360, extent, label, value, pct, col_main))

            # Label pourcentage si part suffisamment grande
            mid_angle = start_angle + extent / 2
            rad = math.radians(mid_angle)
            label_r = pie_r * 0.62
            lx = cx + label_r * math.cos(rad)
            ly = cy - label_r * math.sin(rad)

            if pct >= 5:
                canvas.create_text(lx, ly, text=f'{pct:.0f}%',
                                   font=('Segoe UI', 13, 'bold'),
                                   fill='#FFFFFF')

            start_angle += extent

        self._pie_slices = slices_drawn

        # ── Cercle blanc central (effet donut) ────────────────────────────────
        inner_r = pie_r * 0.35
        canvas.create_oval(
            cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
            fill='#FFFFFF', outline='#F1F5F9', width=2
        )
        # Texte total au centre
        canvas.create_text(cx, cy - 10, text=str(total),
                           font=('Segoe UI', 20, 'bold'), fill='#1E293B')
        canvas.create_text(cx, cy + 12, text='mouvements',
                           font=('Segoe UI', 9), fill='#64748B')

        # ── Légende à droite ───────────────────────────────────────────────
        legend_x  = cx + pie_r + 60
        legend_y0 = cy - (len([v for _,_,_,v in PIE_COLORS if v > 0]) * 56) // 2

        legend_items = [(c, d, lbl, val) for (c, d, lbl, val) in PIE_COLORS if val > 0]
        for i, (col_main, col_dark, label, value) in enumerate(legend_items):
            ly = legend_y0 + i * 60
            pct = value / total * 100

            # Carré couleur arrondi
            canvas.create_rectangle(legend_x, ly, legend_x + 22, ly + 22,
                                    fill=col_main, outline=col_dark, width=1)

            # Label + valeur
            canvas.create_text(legend_x + 32, ly + 4, text=label,
                               font=('Segoe UI', 13, 'bold'), fill='#1E293B', anchor='w')
            canvas.create_text(legend_x + 32, ly + 22,
                               text=f'{value} mvt  —  {pct:.1f}%',
                               font=('Segoe UI', 11), fill='#64748B', anchor='w')

            # Barre de progression horizontale
            bar_w_max = min(220, width - legend_x - 40)
            bar_filled = int(bar_w_max * pct / 100)
            bar_y = ly + 40
            # Fond
            canvas.create_rectangle(legend_x, bar_y, legend_x + bar_w_max, bar_y + 8,
                                    fill='#E2E8F0', outline='', width=0)
            # Remplie
            if bar_filled > 0:
                canvas.create_rectangle(legend_x, bar_y, legend_x + bar_filled, bar_y + 8,
                                        fill=col_main, outline='', width=0)

    def refresh(self):
        stats = db.get_stats_dashboard()

        for w in self.kpi_frame.winfo_children():
            w.destroy()

        kpi_data = [
            {
                'title': 'Total Références',
                'value': str(stats['total_refs']),
                'icon': '📦',
                'color': COLORS['primary'],
                'bg': COLORS['bg_hover']
            },
            {
                'title': 'Alertes Stock',
                'value': str(stats['nb_alertes']),
                'icon': '🚨',
                'color': COLORS['danger'],
                'bg': COLORS['danger_bg']
            },
            {
                'title': 'Mouvements Aujourd\'hui',
                'value': str(stats['mvt_today']),
                'icon': '🔄',
                'color': COLORS['success'],
                'bg': COLORS['success_bg']
            },
        ]

        for i, kpi in enumerate(kpi_data):
            card = make_stat_card(
                self.kpi_frame,
                title=kpi['title'],
                value=kpi['value'],
                icon=kpi['icon'],
                color=kpi['color'],
                bg_color=kpi['bg']
            )
            card.grid(row=0, column=i, padx=6, sticky='ew')
            self.kpi_frame.grid_columnconfigure(i, weight=1)

        # Alertes
        for item in self.tv_alerts.get_children():
            self.tv_alerts.delete(item)

        alertes = db.get_produits_en_alerte()
        self.badge_alerts.configure(text=str(len(alertes)))

        for p in alertes:
            tag = 'alert' if p['quantite_stock'] == 0 else 'warning'
            self.tv_alerts.insert('', 'end', values=(
                p['code_barres'],
                p['designation'],
                f"{p['quantite_stock']} {p['unite']}",
                str(p['seuil_alerte']),
                p['utilite_ligne'] or '—',
                p['nom_machine'] or '—'
            ), tags=(tag,))
        self.tv_alerts.autofit_columns()

        # Derniers mouvements
        for item in self.tv_mvts.get_children():
            self.tv_mvts.delete(item)

        mvts = db.get_derniers_mouvements(15)
        for m in mvts:
            t_type = m['type_mouvement']
            tag_map = {'ENTREE': 'entree', 'SORTIE': 'sortie', 'RETOUR': 'retour'}
            tag = tag_map.get(t_type, 'even')

            prefix_map = {'ENTREE': '▲ ENTRÉE', 'SORTIE': '▼ SORTIE', 'RETOUR': '↩ RETOUR'}
            qte_prefix = '+' if t_type in ('ENTREE', 'RETOUR') else '-'

            raw_dt = m.get('date_heure', '') or ''
            date_str = raw_dt[:16] if len(raw_dt) >= 16 else raw_dt
            self.tv_mvts.insert('', 'end', values=(
                date_str,
                prefix_map.get(t_type, t_type),
                m.get('designation', ''),
                f"{qte_prefix}{m['quantite']}"
            ), tags=(tag,))
        self.tv_mvts.autofit_columns()

        # Suivi & Alertes Pièces de Rechange (Rouge / Orange)
        for item in self.tv_rechange.get_children():
            self.tv_rechange.delete(item)

        alertes_rechange = db.get_produits_alertes_rechange()
        nb_rouge = sum(1 for a in alertes_rechange if a['statut_alerte'] == 'ROUGE')
        nb_orange = sum(1 for a in alertes_rechange if a['statut_alerte'] == 'ORANGE')

        self.badge_rechange_rouge.configure(text=f'🔴 {nb_rouge} Urgent')
        self.badge_rechange_orange.configure(text=f'🟠 {nb_orange} À anticiper')

        for a in alertes_rechange:
            st = a['statut_alerte']
            days = a['jours_restants']
            if st == 'ROUGE':
                statut_str = '🔴 ROUGE (Échue)' if days < 0 else '🔴 ROUGE (Aujourd\'hui)'
                tag = 'alert'
                delai_str = f"Dépassé ({abs(days)} j)" if days < 0 else "Aujourd'hui !"
            else:
                statut_str = '🟠 ORANGE (Proche)'
                tag = 'warning'
                delai_str = f"Dans {days} jour(s)"

            self.tv_rechange.insert('', 'end', values=(
                statut_str,
                a['code_barres'],
                a['designation'],
                a.get('fournisseur_nom') or '—',
                a.get('date_echeance_fmt') or a.get('prochaine_date_rechange'),
                delai_str
            ), tags=(tag,))
        self.tv_rechange.autofit_columns()

        # Charger la liste des mois disponibles pour le graphique
        available_months = db.get_available_months_mouvements()
        self.month_map = {self._format_month_fr(ym): ym for ym in available_months}
        month_labels = list(self.month_map.keys())

        if month_labels:
            self.opt_month.configure(values=month_labels)
            if not self.selected_month or self.selected_month not in self.month_map.values():
                self.selected_month = available_months[0]
                self.var_month.set(month_labels[0])
            self._update_graph()

    def _exporter_alertes_excel(self):
        """Exporte l'ensemble des produits en alerte de stock vers un fichier Excel (.xlsx)."""
        from tkinter import filedialog, messagebox
        from datetime import datetime
        import os
        from services.excel_generator import exporter_alertes_excel

        alertes = db.get_produits_en_alerte()
        if not alertes:
            messagebox.showinfo('Export Excel', 'Aucun produit n\'est actuellement sous le seuil d\'alerte.', parent=self)
            return

        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        default_filename = f"Export_Alertes_Stock_AYRIS_{date_str}.xlsx"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Enregistrer l'export Excel des Alertes de Stock",
            initialfile=default_filename,
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx")]
        )

        if not file_path:
            return

        try:
            exporter_alertes_excel(alertes, file_path)
            messagebox.showinfo(
                '✅ Export Réussi',
                f'La liste des {len(alertes)} produit(s) en alerte de stock a été exportée avec succès !\n\nFichier : {file_path}',
                parent=self
            )
            if messagebox.askyesno('Ouvrir Excel', 'Voulez-vous ouvrir le fichier Excel généré ?', parent=self):
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror('Erreur Export', f'Échec de la génération du fichier Excel :\n{e}', parent=self)
