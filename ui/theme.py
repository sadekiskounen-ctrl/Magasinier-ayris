"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: ui/theme.py
Palette de couleurs officielle AYRIS (Thème Clair ERP & SaaS Moderne) avec polices agrandies.
"""

# ─── Palette officielle AYRIS ────────────────────────────────────────────────
COLORS = {
    # Backgrounds & Cards (Clair & Épuré)
    'bg_darkest':   '#F1F5F9',   # Gris ardoise très clair
    'bg_dark':      '#F8FAFC',   # Blanc cassé épuré
    'bg_card':      '#FFFFFF',   # Blanc pur (Cartes et Panneaux)
    'bg_sidebar':   '#0B2E6B',   # Bleu marine profond AYRIS (sidebar)
    'bg_hover':     '#F1F5F9',   # Gris-bleu très doux au survol
    'bg_input':     '#FFFFFF',   # Blanc pur pour les champs de saisie
    'bg_selected':  '#004899',   # Bleu Royal AYRIS sélectionné

    # Brand Couleurs AYRIS (extraites du logo)
    'primary':      '#004899',   # Bleu Royal AYRIS
    'primary_dark': '#003366',
    'primary_light':'#0074D9',
    'accent':       '#0096D6',   # Cyan source vibrant
    'accent_light': '#00B5EC',

    # États & Statuts (Textes lisibles & Fond doux)
    'success':      '#059669',   # Vert émeraude
    'success_bg':   '#D1FAE5',   # Vert menthe très doux
    'warning':      '#D97706',   # Ambre
    'warning_bg':   '#FEF3C7',   # Ambre très doux
    'danger':       '#DC2626',   # Rouge vif
    'danger_bg':    '#FEE2E2',   # Rouge très doux
    'info':         '#0096D6',

    # Textes Haute Lisibilité (Contraste maximal)
    'text_primary':   '#0F172A',   # Noir ardoise profond (lisibilité 100%)
    'text_secondary': '#475569',   # Gris ardoise moyen
    'text_muted':     '#94A3B8',   # Gris doux
    'text_white':     '#FFFFFF',

    # Bordures nettes
    'border':       '#CBD5E1',   # Gris ardoise clair
    'border_light': '#E2E8F0',

    # Sidebar
    'sidebar_text':        '#CBD5E1',
    'sidebar_text_active': '#FFFFFF',
    'sidebar_active_bg':   '#004899',
    'sidebar_icon':        '#00B5EC',
}

# ─── Typographie Segoe UI — Lisibilité & Ergonomie Maximale ─────────────────
FONTS = {
    'title_large':  ('Segoe UI', 22, 'bold'),
    'title':        ('Segoe UI', 18, 'bold'),
    'subtitle':     ('Segoe UI', 15, 'bold'),
    'body':         ('Segoe UI', 13),
    'body_bold':    ('Segoe UI', 13, 'bold'),
    'small':        ('Segoe UI', 11),
    'small_bold':   ('Segoe UI', 11, 'bold'),
    'mono':         ('Consolas', 12, 'bold'),
    'icon':         ('Segoe UI Emoji', 16),
}

# Mapping des onglets sidebar
SIDEBAR_ITEMS = [
    {'key': 'dashboard',   'icon': '📊', 'label': 'Tableau de Bord'},
    {'key': 'fournisseurs','icon': '🏭', 'label': 'Fournisseurs'},
    {'key': 'catalogue',   'icon': '📦', 'label': 'Produit Pièce de Rechange'},
    {'key': 'engins',      'icon': '🚜', 'label': "Produit d'Engins"},
    {'key': 'outillage',   'icon': '🔧', 'label': 'Outillage'},
    {'key': 'saisie',      'icon': '🔄', 'label': 'Mouvements & Bons'},
    {'key': 'achat',       'icon': '🛒', 'label': 'Bon de Commande'},
    {'key': 'inventaire',  'icon': '📋', 'label': 'Inventaire & Excel'},
    {'key': 'historique',  'icon': '📄', 'label': 'Historique & PDF'},
    {'key': 'options',     'icon': '⚙️',  'label': 'Configuration'},
]

# Lignes de production & utilités
LIGNES = ['KHS1', 'KHS2', 'UROLA', 'ADUE', 'Convoyeur', 'Compresseur', 'Aucune (Matériel Général)']

# Option de sous-lignes pour Convoyeur et Compresseur
SOUS_LIGNES_CONVOYEUR = ['KHS1', 'KHS2', 'UROLA']
SOUS_LIGNES_COMPRESSEUR = ['KHS1', 'KHS2', 'UROLA', '7 BAR']

# Machines selon la ligne sélectionnée
MACHINES_SPECIFIQUES = {
    'KHS1':  ['Blomax', 'Remplisseuse', 'Étiqueteuse', 'Fardeleuse', 'Poignéeuse', 'Palettiseur', 'Robopack', 'CIP'],
    'KHS2':  ['Blomax', 'Remplisseuse', 'Étiqueteuse', 'Fardeleuse', 'Poignéeuse', 'Palettiseur', 'Robopack', 'paramix'],
    'UROLA': ['Souffleuse', 'Remplisseuse', 'Étiqueteuse', 'Poignéeuse', 'Palettiseur', 'Robopack', 'Compresseur'],
    'ADUE':  ['N/A'],
    'Convoyeur': ['N/A'],
    'Compresseur': ['N/A'],
    'Aucune (Matériel Général)': ['N/A'],
}


def get_machines_pour_lignes(lignes_selectionnees: list) -> list:
    """Retourne la liste dédoublonnée des machines selon les lignes sélectionnées."""
    if not lignes_selectionnees or ('Aucune (Matériel Général)' in lignes_selectionnees and len(lignes_selectionnees) == 1):
        return ['N/A']
    machines = []
    for ligne in lignes_selectionnees:
        if ligne in MACHINES_SPECIFIQUES:
            for m in MACHINES_SPECIFIQUES[ligne]:
                if m not in machines:
                    machines.append(m)
    return machines if machines else ['N/A']


UNITES = ['Unité', 'Pièce', 'kg', 'L', 'm', 'Boîte', 'Rouleau', 'Carton', 'Paquet', 'Bidon']

SERVICES = [
    'Production', 'Maintenance', 'Qualité', 'Direction', 'Logistique',
    'Commercial', 'Administratif', 'Fournisseur Externe', 'Autre'
]
