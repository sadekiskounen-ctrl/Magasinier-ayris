"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/widgets.py
Composants UI réutilisables — Design Premium ERP Mondial avec scrollbars horizontales.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from ui.theme import COLORS, FONTS

try:
    from tkcalendar import DateEntry, Calendar
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False


def make_card(parent, title: str = "", width: int = 200, height: int = 120) -> ctk.CTkFrame:
    """Crée une carte stylisée épurée."""
    return ctk.CTkFrame(
        parent,
        fg_color=COLORS['bg_card'],
        corner_radius=10,
        border_width=1,
        border_color=COLORS['border'],
        width=width,
        height=height
    )


def make_stat_card(parent, title: str, value: str, icon: str,
                   color: str, bg_color: str = None) -> ctk.CTkFrame:
    """Carte statistique KPI grand format ultra-lisible."""
    frame = ctk.CTkFrame(
        parent,
        fg_color=COLORS['bg_card'],
        corner_radius=16,
        border_width=1,
        border_color=COLORS['border'],
    )

    icon_frame = ctk.CTkFrame(
        frame,
        fg_color=bg_color or COLORS['bg_hover'],
        corner_radius=12,
        width=60,
        height=60
    )
    icon_frame.pack(side='left', padx=18, pady=18)
    icon_frame.pack_propagate(False)

    ctk.CTkLabel(
        icon_frame,
        text=icon,
        font=('Segoe UI Emoji', 28),
        text_color=color
    ).place(relx=0.5, rely=0.5, anchor='center')

    text_frame = ctk.CTkFrame(frame, fg_color='transparent')
    text_frame.pack(side='left', pady=16, fill='y', expand=True)

    ctk.CTkLabel(
        text_frame,
        text=value,
        font=('Segoe UI', 28, 'bold'),
        text_color=color
    ).pack(anchor='w')

    ctk.CTkLabel(
        text_frame,
        text=title,
        font=FONTS['body_bold'],
        text_color=COLORS['text_secondary']
    ).pack(anchor='w')

    return frame


def make_section_header(parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
    """Crée un en-tête de section."""
    frame = ctk.CTkFrame(parent, fg_color='transparent')
    ctk.CTkLabel(
        frame, text=title,
        font=FONTS['title'],
        text_color=COLORS['text_primary']
    ).pack(side='left')

    if subtitle:
        ctk.CTkLabel(
            frame, text=f"  {subtitle}",
            font=FONTS['small'],
            text_color=COLORS['text_secondary']
        ).pack(side='left', pady=(4, 0))

    return frame


def make_primary_button(parent, text: str, command=None, icon: str = "",
                         width: int = 170, height: int = 42) -> ctk.CTkButton:
    """Bouton principal bleu royal."""
    return ctk.CTkButton(
        parent,
        text=f"{icon}  {text}" if icon else text,
        command=command,
        fg_color=COLORS['primary'],
        hover_color=COLORS['primary_dark'],
        text_color=COLORS['text_white'],
        font=FONTS['body_bold'],
        corner_radius=10,
        height=height,
        width=width
    )


def make_danger_button(parent, text: str, command=None, width: int = 140, height: int = 42) -> ctk.CTkButton:
    """Bouton danger rouge."""
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=COLORS['danger_bg'],
        hover_color=COLORS['danger'],
        text_color=COLORS['danger'],
        border_color=COLORS['danger'],
        border_width=1,
        font=FONTS['body_bold'],
        corner_radius=10,
        height=42,
        width=width
    )


def make_success_button(parent, text: str, command=None, width: int = 170) -> ctk.CTkButton:
    """Bouton succès vert."""
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=COLORS['success'],
        hover_color='#047857',
        text_color=COLORS['text_white'],
        font=FONTS['body_bold'],
        corner_radius=10,
        height=42,
        width=width
    )


def make_secondary_button(parent, text: str, command=None, width: int = 140, height: int = 42) -> ctk.CTkButton:
    """Bouton secondaire neutre."""
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=COLORS['bg_hover'],
        hover_color=COLORS['border'],
        text_color=COLORS['text_primary'],
        border_color=COLORS['border'],
        border_width=1,
        font=FONTS['body_bold'],
        corner_radius=10,
        height=height,
        width=width
    )


def make_input(parent, placeholder: str = "", width: int = 220,
               textvariable=None) -> ctk.CTkEntry:
    """Champ de saisie avec fond blanc pur et écriture agrandie."""
    return ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        fg_color=COLORS['bg_input'],
        border_color=COLORS['border'],
        border_width=1,
        text_color=COLORS['text_primary'],
        placeholder_text_color=COLORS['text_muted'],
        font=FONTS['body'],
        corner_radius=8,
        height=42,
        width=width,
        textvariable=textvariable
    )


def make_label(parent, text: str, style: str = 'body',
               color: str = None) -> ctk.CTkLabel:
    """Label stylisé."""
    return ctk.CTkLabel(
        parent,
        text=text,
        font=FONTS.get(style, FONTS['body']),
        text_color=color or COLORS['text_primary']
    )


def make_combobox(parent, values: list, width: int = 220,
                  variable=None) -> ctk.CTkComboBox:
    """Menu déroulant stylisé."""
    return ctk.CTkComboBox(
        parent,
        values=values,
        fg_color=COLORS['bg_input'],
        border_color=COLORS['border'],
        border_width=1,
        button_color=COLORS['primary'],
        button_hover_color=COLORS['primary_dark'],
        dropdown_fg_color=COLORS['bg_card'],
        dropdown_hover_color=COLORS['bg_hover'],
        dropdown_text_color=COLORS['text_primary'],
        text_color=COLORS['text_primary'],
        font=FONTS['body'],
        corner_radius=8,
        width=width,
        height=42,
        variable=variable
    )


# ─── WIDGET DATEPICKER INTERACTIF / CALENDRIER ────────────────────────────────
class DatePickerInput(ctk.CTkFrame):
    """Champ de saisie de date avec un bouton calendrier interactif."""

    def __init__(self, parent, initial_date: str = "", width: int = 160, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_input'], corner_radius=8,
                         border_width=1, border_color=COLORS['border'], **kwargs)

        self.var_date = tk.StringVar(value=initial_date)

        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.var_date,
            placeholder_text='AAAA-MM-JJ',
            fg_color='transparent',
            border_width=0,
            text_color=COLORS['text_primary'],
            font=FONTS['body_bold'],
            width=width - 48,
            height=40
        )
        self.entry.pack(side='left', padx=(8, 2))

        btn_cal = ctk.CTkButton(
            self,
            text='📅',
            width=36,
            height=34,
            command=self._open_calendar_popup,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_dark'],
            corner_radius=6,
            font=('Segoe UI Emoji', 14)
        )
        btn_cal.pack(side='right', padx=3, pady=3)

    def get(self) -> str:
        return self.var_date.get().strip()

    def set(self, val: str):
        self.var_date.set(val)

    def _open_calendar_popup(self):
        """Ouvre une fenêtre modale avec calendrier interactif."""
        popup = ctk.CTkToplevel(self)
        popup.title('Sélectionner une date')
        popup.geometry('360x380')
        popup.resizable(False, False)
        popup.configure(fg_color=COLORS['bg_dark'])
        popup.grab_set()
        popup.focus()

        ctk.CTkLabel(popup, text='📅 Choisir une journée', font=FONTS['subtitle'],
                     text_color=COLORS['text_primary']).pack(pady=(12, 6))

        if HAS_TKCALENDAR:
            cal_frame = tk.Frame(popup, bg=COLORS['bg_dark'])
            cal_frame.pack(padx=16, pady=8, fill='both', expand=True)

            cal = Calendar(
                cal_frame,
                selectmode='day',
                date_pattern='yyyy-mm-dd',
                background=COLORS['primary'],
                foreground=COLORS['text_white'],
                headersbackground=COLORS['bg_darkest'],
                headersforeground=COLORS['primary'],
                selectbackground=COLORS['accent'],
                selectforeground=COLORS['text_white'],
                normalbackground=COLORS['bg_card'],
                normalforeground=COLORS['text_primary'],
                weekendbackground=COLORS['bg_hover'],
                weekendforeground=COLORS['text_secondary'],
                font=('Segoe UI', 10)
            )
            cal.pack(fill='both', expand=True)

            def select_and_close():
                self.var_date.set(cal.get_date())
                popup.destroy()

        else:
            ctk.CTkLabel(popup, text='Saisissez la date (AAAA-MM-JJ) :', font=FONTS['body'],
                         text_color=COLORS['text_secondary']).pack(pady=10)
            e_fallback = make_input(popup, placeholder='AAAA-MM-JJ', width=200)
            e_fallback.insert(0, self.var_date.get())
            e_fallback.pack(pady=10)

            def select_and_close():
                self.var_date.set(e_fallback.get())
                popup.destroy()

        btn_box = ctk.CTkFrame(popup, fg_color='transparent')
        btn_box.pack(fill='x', padx=16, pady=12)

        make_secondary_button(btn_box, 'Annuler', command=popup.destroy, width=100).pack(side='left')
        make_primary_button(btn_box, 'Valider', command=select_and_close, width=140).pack(side='right')


# ─── TABLEAU STYLISÉ GRAND FORMAT AVEC SCROLL HORIZONTAL ─────────────────────
class StyledTreeview(ttk.Treeview):
    """
    Treeview entreprise claire grand format (style SAP / Dynamics / Salesforce).
    Avec défilement horizontal ET vertical intégré.
    """

    def __init__(self, parent, columns: list, headings: list,
                 col_widths: list = None, stretch_cols: bool = True, **kwargs):
        style = ttk.Style()
        style.theme_use('clam')

        # Style des lignes et cellules
        style.configure('Dark.Treeview',
                         background='#FFFFFF',
                         foreground='#0F172A',
                         fieldbackground='#FFFFFF',
                         rowheight=38,
                         font=('Segoe UI', 11),
                         borderwidth=0,
                         relief='flat')

        # Style des en-têtes
        style.configure('Dark.Treeview.Heading',
                         background='#004899',
                         foreground='#FFFFFF',
                         font=('Segoe UI', 11, 'bold'),
                         borderwidth=0,
                         relief='flat',
                         padding=(6, 8))

        style.map('Dark.Treeview',
                  background=[('selected', '#1D4ED8')],
                  foreground=[('selected', '#FFFFFF')])
        style.map('Dark.Treeview.Heading',
                  background=[('active', '#003380')])

        super().__init__(
            parent,
            columns=columns,
            show='headings',
            style='Dark.Treeview',
            **kwargs
        )

        for i, (col, heading) in enumerate(zip(columns, headings)):
            self.heading(col, text=heading)
            width = col_widths[i] if col_widths and i < len(col_widths) else 130
            anchor = 'center' if width <= 90 or col in ('stock', 'seuil', 'qte', 'unite', 'type', 'alerte') else 'w'
            is_flex = stretch_cols and (col in ('designation', 'machine', 'utilite_ligne', 'emplacement', 'categorie', 'produit') or (i == len(columns) - 1))
            min_w = max(40, int(width * 0.4))
            self.column(col, width=width, anchor=anchor, minwidth=min_w, stretch=is_flex)

        # Tags couleurs
        self.tag_configure('alert',   background='#FEE2E2', foreground='#991B1B')
        self.tag_configure('warning', background='#FEF3C7', foreground='#92400E')
        self.tag_configure('entree',  background='#D1FAE5', foreground='#065F46')
        self.tag_configure('sortie',  background='#FEE2E2', foreground='#991B1B')
        self.tag_configure('retour',  background='#FEF3C7', foreground='#92400E')
        self.tag_configure('even',    background='#FFFFFF', foreground='#0F172A')
        self.tag_configure('odd',     background='#F8FAFC', foreground='#0F172A')
        self.tag_configure('dans_magasin', background='#E6F4EA', foreground='#137333')
        self.tag_configure('en_dehors',     background='#FCE8E6', foreground='#C5221F')

        # Support du défilement horizontal à la molette (Shift + Molette)
        self.bind('<Shift-MouseWheel>', self._on_shift_mousewheel)

    def autofit_columns(self, padding: int = 24, min_col_w: int = 60, max_col_w: int = 500):
        """
        Ajuste dynamiquement la largeur de chaque colonne selon le texte le plus long.
        Examine les 30 premières lignes pour une rapidité maximale sans blocage GUI.
        """
        try:
            import tkinter.font as tkfont
            f_body = tkfont.Font(family='Segoe UI', size=11)
            f_head = tkfont.Font(family='Segoe UI', size=11, weight='bold')

            children = list(self.get_children()[:30])

            for col in self['columns']:
                # Width of header
                heading_text = str(self.heading(col, 'text') or '')
                max_w = f_head.measure(heading_text) + padding

                # Width of cell values (échantillon rapide)
                for item in children:
                    val = str(self.set(item, col) or '')
                    if val:
                        w_val = f_body.measure(val) + padding
                        if w_val > max_w:
                            max_w = w_val

                # Clamp width between min and max
                final_w = min(max(max_w, min_col_w), max_col_w)
                anchor = self.column(col, 'anchor')
                stretch = self.column(col, 'stretch')

                self.column(col, width=final_w, minwidth=final_w, anchor=anchor, stretch=stretch)
        except Exception:
            pass

    def _on_shift_mousewheel(self, event):
        if event.delta:
            self.xview_scroll(int(-1 * (event.delta / 120)), "units")


def add_scrollbar(parent, widget, side='right') -> tuple:
    """
    Ajoute barres de défilement verticale ET horizontale au tableau.
    Retourne (scrollbar_vertical, scrollbar_horizontal).
    """
    style = ttk.Style()

    # Dépacker temporairement pour réordonner correctement
    try:
        widget.pack_forget()
    except Exception:
        pass

    # Style scrollbar verticale
    style.configure('Dark.Vertical.TScrollbar',
                     background=COLORS['bg_hover'],
                     troughcolor='#F1F5F9',
                     arrowcolor=COLORS['primary'],
                     bordercolor=COLORS['border'],
                     width=12)

    # Style scrollbar horizontale
    style.configure('Dark.Horizontal.TScrollbar',
                     background=COLORS['bg_hover'],
                     troughcolor='#F1F5F9',
                     arrowcolor=COLORS['primary'],
                     bordercolor=COLORS['border'],
                     width=12)

    # Scrollbar horizontale en bas d'abord (prend toute la largeur du bas)
    sb_h = ttk.Scrollbar(parent, orient='horizontal', command=widget.xview,
                          style='Dark.Horizontal.TScrollbar')
    sb_h.pack(side='bottom', fill='x')

    # Scrollbar verticale à droite ensuite (prend toute la hauteur restante à droite)
    sb_v = ttk.Scrollbar(parent, orient='vertical', command=widget.yview,
                          style='Dark.Vertical.TScrollbar')
    sb_v.pack(side='right', fill='y')

    widget.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
    widget.pack(side='left', fill='both', expand=True)

    return sb_v, sb_h


class SearchBar(ctk.CTkFrame):
    """Barre de recherche claire avec icône."""

    def __init__(self, parent, placeholder: str = "Rechercher par Référence...",
                 on_change=None, width: int = 340, **kwargs):
        super().__init__(parent, fg_color=COLORS['bg_input'],
                         corner_radius=10, border_width=1,
                         border_color=COLORS['border'], **kwargs)

        ctk.CTkLabel(self, text='🔍', font=('Segoe UI Emoji', 16),
                     text_color=COLORS['text_secondary'],
                     fg_color='transparent').pack(side='left', padx=(12, 4))

        self.var = tk.StringVar()
        self.entry = ctk.CTkEntry(
            self, textvariable=self.var,
            placeholder_text=placeholder,
            fg_color='transparent',
            border_width=0,
            text_color=COLORS['text_primary'],
            placeholder_text_color=COLORS['text_muted'],
            font=FONTS['body'],
            width=width - 50,
            height=40
        )
        self.entry.pack(side='left', fill='x', expand=True)

        if on_change:
            self.var.trace_add('write', lambda *_: on_change(self.var.get()))

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)

    def focus(self):
        self.entry.focus()


class MultiSelectLignesWidget(ctk.CTkFrame):
    """Widget de sélection multiple des lignes (KHS1, KHS2, UROLA, ADUE, Aucune) — grille lisible."""

    def __init__(self, parent, options: list, default_selected: list = None,
                 on_change=None, **kwargs):
        super().__init__(parent, fg_color='transparent', **kwargs)
        self.options = options
        self.on_change = on_change
        self.check_vars = {}

        self.grid_columnconfigure(0, weight=1, minsize=130)
        self.grid_columnconfigure(1, weight=1, minsize=130)

        if default_selected is None:
            default_selected = [options[0]] if options else []

        curr_row = 0
        curr_col = 0
        for opt in options:
            var = tk.BooleanVar(value=(opt in default_selected))
            self.check_vars[opt] = var

            chk = ctk.CTkCheckBox(
                self,
                text=opt,
                variable=var,
                command=lambda o=opt: self._on_checkbox_click(o),
                fg_color=COLORS['primary'],
                hover_color=COLORS['primary_dark'],
                text_color=COLORS['text_primary'],
                font=FONTS['body_bold'],
                corner_radius=4,
                checkbox_width=20,
                checkbox_height=20
            )

            # Si l'option est longue (ex: "Aucune (Matériel Général)" ou "Groupe Électrogène"), elle prend toute la largeur
            if len(opt) > 10:
                if curr_col == 1:
                    curr_row += 1
                    curr_col = 0
                chk.grid(row=curr_row, column=0, columnspan=2, sticky='w', padx=(4, 6), pady=4)
                curr_row += 1
                curr_col = 0
            else:
                chk.grid(row=curr_row, column=curr_col, sticky='w', padx=(4, 6), pady=4)
                if curr_col == 1:
                    curr_row += 1
                    curr_col = 0
                else:
                    curr_col = 1

    def _on_checkbox_click(self, clicked_opt: str):
        if clicked_opt in ('Groupe Électrogène', 'Aucune (Matériel Général)') and self.check_vars[clicked_opt].get():
            # Décocher les autres options pour isoler Groupe Électrogène / Matériel Général
            for opt, var in self.check_vars.items():
                if opt != clicked_opt:
                    var.set(False)
        elif self.check_vars.get(clicked_opt) and self.check_vars[clicked_opt].get():
            # Décocher Groupe Électrogène et Aucune si une ligne de production est cochée
            for special in ('Groupe Électrogène', 'Aucune (Matériel Général)'):
                if special in self.check_vars:
                    self.check_vars[special].set(False)
        self._on_toggle()

    def _on_toggle(self):
        if self.on_change:
            self.on_change(self.get_selected())

    def get_selected(self) -> list:
        selected = [opt for opt, var in self.check_vars.items() if var.get()]
        return selected if selected else ['Aucune (Matériel Général)']

    def set_selected(self, selected_list: list):
        for opt, var in self.check_vars.items():
            var.set(opt in selected_list)
        if self.on_change:
            self.on_change(self.get_selected())


_BADGE_BG_MAP = {
    COLORS['danger']:  COLORS['danger_bg'],
    COLORS['warning']: COLORS['warning_bg'],
    COLORS['success']: COLORS['success_bg'],
    COLORS['primary']: COLORS['bg_hover'],
    COLORS['info']:    '#E0F2FE',
}


class BadgeLabel(ctk.CTkLabel):
    """Badge coloré haute lisibilité."""

    def __init__(self, parent, text: str, color: str = None, **kwargs):
        fg_color = color or COLORS['primary']
        bg = _BADGE_BG_MAP.get(fg_color, COLORS['bg_hover'])
        super().__init__(
            parent, text=text,
            fg_color=bg,
            text_color=fg_color,
            corner_radius=6,
            font=FONTS['small_bold'],
            **kwargs
        )


class SeparatorLine(ctk.CTkFrame):
    """Ligne séparatrice horizontale."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            height=1,
            fg_color=COLORS['border'],
            **kwargs
        )


class AutocompleteDesignationInput(ctk.CTkFrame):
    """
    Champ de recherche avec autocomplétion dynamique et fenêtre de suggestions haute visibilité.
    Affiche la liste des pièces correspondantes dès la première lettre saisie.
    Lors du choix d'une pièce, déclenche le callback on_select(produit).
    """

    def __init__(self, parent, placeholder: str = "Désignation...",
                 textvariable=None, on_select=None, width: int = 220, **kwargs):
        super().__init__(parent, fg_color='transparent', **kwargs)
        self.on_select_callback = on_select
        self.var_text = textvariable if textvariable is not None else tk.StringVar()
        self._results = []
        self._popup = None
        self._search_timer = None
        self._selecting = False  # flag pour bloquer la recherche lors d'une sélection

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            fg_color=COLORS['bg_input'],
            border_color=COLORS['border'],
            border_width=1,
            text_color=COLORS['text_primary'],
            placeholder_text_color=COLORS['text_muted'],
            font=FONTS['body'],
            corner_radius=8,
            height=42,
            width=width,
            textvariable=self.var_text
        )
        self.entry.pack(fill='x', expand=True)

        self.var_text.trace_add('write', self._on_text_change)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        self.entry.bind('<Escape>', lambda e: self._hide_popup())

    def _on_text_change(self, *_):
        # Ne pas lancer une recherche si on est en train de sélectionner un élément
        if self._selecting:
            return
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
        self._search_timer = self.after(150, self._do_search)

    def _do_search(self):
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None
        query = self.var_text.get().strip()
        if not query:
            self._hide_popup()
            return

        import database.db_manager as db
        self._results = db.search_produits_by_designation(query, limit=15)
        if self._results:
            self._show_popup()
        else:
            self._hide_popup()

    def _show_popup(self):
        if self._popup is None or not self._popup.winfo_exists():
            self._popup = ctk.CTkToplevel(self)
            self._popup.overrideredirect(True)
            self._popup.attributes('-topmost', True)
            self._popup.configure(fg_color=COLORS['bg_card'])

        self.update_idletasks()
        entry_w = self.entry.winfo_width()
        w = max(entry_w, 360)
        h = min(len(self._results) * 56 + 16, 260)

        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2

        # Prévenir le débordement à droite de l'écran
        sw = self.winfo_screenwidth()
        if x + w > sw - 20:
            x = max(10, sw - w - 20)

        self._popup.geometry(f"{w}x{h}+{x}+{y}")

        for child in self._popup.winfo_children():
            child.destroy()

        scroll_frame = ctk.CTkScrollableFrame(
            self._popup, fg_color=COLORS['bg_card'],
            border_width=2, border_color=COLORS['primary']
        )
        scroll_frame.pack(fill='both', expand=True)

        for prod in self._results:
            ref = prod.get('code_barres', '')
            des = prod.get('designation', '')
            stk = prod.get('quantite_stock', 0)
            unite = prod.get('unite', '')

            item_btn = ctk.CTkButton(
                scroll_frame,
                text=f"[{ref}]  {des}\n↳ Stock : {stk} {unite}",
                anchor='w',
                fg_color=COLORS['bg_hover'],
                hover_color=COLORS['bg_selected'],
                text_color=COLORS['text_primary'],
                font=FONTS['body_bold'],
                height=48,
                corner_radius=6,
                command=lambda p=prod: self._select_produit(p)
            )
            item_btn.pack(fill='x', padx=4, pady=3)

    def _select_produit(self, prod: dict):
        self._selecting = True  # bloquer le déclenchement de recherche
        self._hide_popup()
        try:
            self.var_text.set(prod.get('designation', ''))
            if self.on_select_callback:
                self.on_select_callback(prod)
        finally:
            self._selecting = False

    def _hide_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None

    def _on_focus_out(self, event):
        # Délai court pour permettre le clic sur un bouton de la popup avant de la fermer
        self.after(200, self._hide_popup_if_not_selecting)

    def _hide_popup_if_not_selecting(self):
        if not self._selecting:
            self._hide_popup()


# ─── AUTOCOMPLÉTION OUTILLAGE DYNAMIQUE (COMMENCE PAR, INSENSIBLE CASSE/ACCENT) ───

class AutocompleteOutillageInput(ctk.CTkFrame):
    """
    Champ de saisie pour l'Outillage avec autocomplétion dynamique et menu déroulant sous le champ :
    - Filtrage 'commence par', insensible à la casse et aux accents.
    - Suggestions lues dynamiquement depuis la table SQLite 'outillage' (lecture seule).
    - Clavier (flèches Haut/Bas puis Entrée pour sélectionner, Échap pour fermer).
    - Souris (survol fluide et clic pour sélectionner).
    - Focus maintenu dans le champ de saisie pendant l'affichage des suggestions.
    - Largeur de la liste exactement identique à celle du champ de saisie.
    - Environ 8 suggestions visibles max avec barre de défilement si > 8.
    - Si vide ou aucun résultat : liste masquée et saisie libre autorisée.
    - Fermeture automatique par Échap ou clic en dehors.
    """

    def __init__(self, parent, placeholder: str = "Nom de l'outillage...",
                 textvariable=None, on_select=None, width: int = 280, **kwargs):
        super().__init__(parent, fg_color='transparent', **kwargs)
        self.on_select_callback = on_select
        self.var_text = textvariable if textvariable is not None else tk.StringVar()
        self._suggestions = []
        self._selected_tool = None
        self._popup = None
        self._listbox = None
        self._scrollbar = None
        self._container = None
        self._selecting = False
        self._search_timer = None

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            fg_color=COLORS['bg_input'],
            border_color=COLORS['border'],
            border_width=1,
            text_color=COLORS['text_primary'],
            placeholder_text_color=COLORS['text_muted'],
            font=FONTS['body'],
            corner_radius=8,
            height=42,
            width=width,
            textvariable=self.var_text
        )
        self.entry.pack(fill='x', expand=True)

        # Écoutes d'événements
        self.var_text.trace_add('write', self._on_text_change)
        self.entry.bind('<Down>', self._on_key_down)
        self.entry.bind('<Up>', self._on_key_up)
        self.entry.bind('<Return>', self._on_key_enter)
        self.entry.bind('<KP_Enter>', self._on_key_enter)
        self.entry.bind('<Escape>', self._on_key_escape)
        self.entry.bind('<FocusOut>', self._on_focus_out)

    def _on_text_change(self, *_):
        if self._selecting:
            return
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
        self._search_timer = self.after(30, self._do_search)

    def _do_search(self):
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None
        query = self.var_text.get()
        if not query or not query.strip():
            self._hide_popup()
            self._selected_tool = None
            return

        import database.db_manager as db
        self._suggestions = db.get_suggestions_outillage(query)
        if self._suggestions:
            self._show_popup()
        else:
            self._hide_popup()

    def _show_popup(self):
        if not self._suggestions:
            self._hide_popup()
            return

        top = self.winfo_toplevel()
        if self._popup is None or not self._popup.winfo_exists():
            self._popup = tk.Toplevel(top)
            self._popup.overrideredirect(True)
            self._popup.attributes('-topmost', True)
            self._popup.configure(bg=COLORS['primary'])

            self._container = tk.Frame(self._popup, bg=COLORS['bg_card'], bd=1, relief='solid')
            self._container.pack(fill='both', expand=True)

            self._listbox = tk.Listbox(
                self._container,
                font=('Segoe UI', 11),
                bg=COLORS['bg_card'],
                fg=COLORS['text_primary'],
                selectbackground=COLORS['primary'],
                selectforeground='white',
                activestyle='none',
                exportselection=False,
                bd=0,
                highlightthickness=0,
                cursor='hand2'
            )

            self._scrollbar = ttk.Scrollbar(self._container, orient='vertical', command=self._listbox.yview)
            self._listbox.configure(yscrollcommand=self._scrollbar.set)

            self._listbox.bind('<ButtonRelease-1>', self._on_listbox_click)
            self._listbox.bind('<Motion>', self._on_listbox_motion)

        # Remplir les suggestions
        self._listbox.delete(0, tk.END)
        for item in self._suggestions:
            des = item.get('designation', '')
            num = item.get('numero_outillage', '')
            mrq = item.get('marque', '')

            extra = []
            if num:
                extra.append(f"N° {num}")
            if mrq:
                extra.append(mrq)

            if extra:
                label = f"{des}   ({', '.join(extra)})"
            else:
                label = des
            self._listbox.insert(tk.END, f"  {label}")

        n = len(self._suggestions)
        vis = min(n, 8)
        self._listbox.configure(height=vis)

        if n > 8:
            self._scrollbar.pack(side='right', fill='y')
        else:
            self._scrollbar.pack_forget()

        self._listbox.pack(side='left', fill='both', expand=True)

        # Positionnement et dimensionnement précis (même largeur que le champ)
        self.update_idletasks()
        self.entry.update_idletasks()

        w = self.entry.winfo_width()
        if w < 100:
            w = self.winfo_width()
        if w < 100:
            w = 320

        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 1

        self._popup.update_idletasks()
        h = self._popup.winfo_reqheight()

        # Protection contre débordements écran (résolutions variées, DPI scaling)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        if x + w > screen_w - 10:
            x = max(10, screen_w - w - 10)

        if y + h > screen_h - 10:
            # Afficher au-dessus si l'espace inférieur est insuffisant
            y = max(10, self.entry.winfo_rooty() - h - 1)

        self._popup.geometry(f"{w}x{h}+{x}+{y}")
        self._popup.deiconify()
        self._popup.lift()

    def _on_key_down(self, event):
        if not self._is_popup_visible():
            self._do_search()
            return 'break'
        size = self._listbox.size()
        if size == 0:
            return 'break'
        sel = self._listbox.curselection()
        idx = (sel[0] + 1) if sel else 0
        if idx >= size:
            idx = size - 1
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(idx)
        self._listbox.activate(idx)
        self._listbox.see(idx)
        return 'break'

    def _on_key_up(self, event):
        if not self._is_popup_visible():
            return 'break'
        size = self._listbox.size()
        if size == 0:
            return 'break'
        sel = self._listbox.curselection()
        idx = (sel[0] - 1) if sel else 0
        if idx < 0:
            idx = 0
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(idx)
        self._listbox.activate(idx)
        self._listbox.see(idx)
        return 'break'

    def _on_key_enter(self, event):
        if self._is_popup_visible():
            sel = self._listbox.curselection()
            if sel:
                self._select_index(sel[0])
                return 'break'
            else:
                self._hide_popup()

    def _on_key_escape(self, event):
        if self._is_popup_visible():
            self._hide_popup()
            return 'break'

    def _on_listbox_motion(self, event):
        if self._listbox and self._listbox.winfo_exists():
            idx = self._listbox.nearest(event.y)
            if 0 <= idx < len(self._suggestions):
                self._listbox.selection_clear(0, tk.END)
                self._listbox.selection_set(idx)
                self._listbox.activate(idx)

    def _on_listbox_click(self, event):
        if self._listbox and self._listbox.winfo_exists():
            idx = self._listbox.nearest(event.y)
            if 0 <= idx < len(self._suggestions):
                self._select_index(idx)

    def _select_index(self, idx: int):
        if 0 <= idx < len(self._suggestions):
            item = self._suggestions[idx]
            self._selected_tool = item
            self._selecting = True
            self._hide_popup()
            try:
                self.var_text.set(item.get('designation', ''))
                self.entry.icursor(tk.END)
                if self.on_select_callback:
                    self.on_select_callback(item)
            finally:
                self._selecting = False

    def _on_focus_out(self, event):
        self.after(180, self._check_focus_out)

    def _check_focus_out(self):
        if self._selecting:
            return
        try:
            focused = self.focus_get()
            if self._popup and self._popup.winfo_exists():
                if focused not in (self.entry, self._listbox, self._scrollbar, self._popup):
                    self._hide_popup()
        except Exception:
            self._hide_popup()

    def _is_popup_visible(self) -> bool:
        return self._popup is not None and self._popup.winfo_exists() and self._popup.winfo_viewable()

    def _hide_popup(self):
        if self._search_timer:
            try:
                self.after_cancel(self._search_timer)
            except Exception:
                pass
            self._search_timer = None
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            self._listbox = None
            self._scrollbar = None
            self._container = None

    def get(self) -> str:
        """Retourne la valeur saisie dans le champ."""
        return self.var_text.get().strip()

    def set(self, val: str):
        """Définit la valeur du champ sans déclencher la recherche popup."""
        self._selecting = True
        try:
            self.var_text.set(val)
        finally:
            self._selecting = False

    def get_selected_tool(self) -> dict | None:
        """Retourne l'objet outillage sélectionné depuis la liste s'il existe."""
        return self._selected_tool

    def set_selected_tool(self, tool: dict):
        """Présélectionne un outil (nom et métadonnées)."""
        self._selected_tool = tool
        if tool:
            self.set(tool.get('designation', ''))


