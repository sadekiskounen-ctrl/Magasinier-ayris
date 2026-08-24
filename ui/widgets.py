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

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

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
                command=self._on_toggle,
                fg_color=COLORS['primary'],
                hover_color=COLORS['primary_dark'],
                text_color=COLORS['text_primary'],
                font=FONTS['body_bold'],
                corner_radius=4,
                checkbox_width=20,
                checkbox_height=20
            )

            # Si l'option est longue (ex: "Aucune (Matériel Général)" ou "Compresseur"), elle prend toute la largeur
            if len(opt) > 12:
                if curr_col == 1:
                    curr_row += 1
                    curr_col = 0
                chk.grid(row=curr_row, column=0, columnspan=2, sticky='w', padx=(4, 8), pady=5)
                curr_row += 1
                curr_col = 0
            else:
                chk.grid(row=curr_row, column=curr_col, sticky='w', padx=(4, 8), pady=5)
                if curr_col == 1:
                    curr_row += 1
                    curr_col = 0
                else:
                    curr_col = 1

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
