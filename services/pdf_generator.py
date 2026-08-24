"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: services/pdf_generator.py
Génère des PDF d'entreprise de classe internationale (style SAP / Oracle / IBM) pour BS, BR, BT et BC.
Footer ancré à la fin de la page A4.
"""

import os
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, Image)
from reportlab.lib.colors import HexColor

# ─── Palette Entreprise Internationale AYRIS ──────────────────────────────────
COLOR_NAVY     = HexColor('#0B2E6B')   # Bleu marine officiel AYRIS
COLOR_ROYAL    = HexColor('#004899')   # Bleu royal
COLOR_CYAN     = HexColor('#0096D6')   # Cyan source
COLOR_LIGHT_BG = HexColor('#F8FAFC')   # Ardoise claire
COLOR_BORDER   = HexColor('#CBD5E1')   # Bordure fine
COLOR_TEXT_DARK= HexColor('#0F172A')   # Noir ardoise
COLOR_TEXT_MUT = HexColor('#0F172A')   # Noir (anciennement gris - rendu noir gras)
COLOR_ROW_ALT  = HexColor('#F1F5F9')   # Ligne alternée
COLOR_WHITE    = colors.white

BASE_DIR = Path(__file__).parent.parent
LOGO_PATH = str(BASE_DIR / 'assets' / 'logo_nomade_ayris.png')


def get_default_pdf_dir() -> str:
    try:
        from services.config_manager import get_config
        pdf_dir = get_config('pdf_directory', '')
        if pdf_dir and os.path.isdir(pdf_dir):
            return pdf_dir
    except Exception:
        pass
    docs = Path.home() / 'Documents' / 'SARL_Ayris_PDF'
    docs.mkdir(parents=True, exist_ok=True)
    return str(docs)


def _get_header_logo() -> Image | None:
    """Retourne l'image du logo officielle sans déformation (ratio 1.28)."""
    if os.path.exists(LOGO_PATH):
        try:
            return Image(LOGO_PATH, width=4.2*cm, height=3.28*cm)
        except Exception:
            pass
    return None


def _build_corporate_header(doc_type: str, num_doc: str, date_str: str,
                           beneficiaire: str, fournisseur: str = "",
                           demandeur: str = "", retourne_par: str = "") -> list:
    """En-tête PDF Entreprise Internationale (Layout 2 colonnes avec logo et cartouche)."""
    elements = []

    logo_img = _get_header_logo()
    if logo_img:
        logo_cell = logo_img
    else:
        logo_cell = Paragraph(
            '<b><font color="#0B2E6B" size="18">SARL NOMADE AYRIS</font></b><br/>'
            '<font color="#0096D6" size="9">EAU DE SOURCE NATURELLE</font>',
            ParagraphStyle('logo_fall', fontName='Helvetica-Bold', leading=18)
        )

    # Cartouche de droite (Titre + N° Document)
    doc_title_style = ParagraphStyle(
        'doctitle', fontName='Helvetica-Bold', fontSize=14,
        textColor=COLOR_WHITE, alignment=TA_CENTER
    )

    right_cartouche_data = [
        [Paragraph(f"<b>{doc_type}</b>", doc_title_style)],
        [Paragraph(f'N° Document : <b><font color="#004899">{num_doc}</font></b>',
                   ParagraphStyle('numd', fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER))],
        [Paragraph(f'<b>Date : {date_str}</b>',
                   ParagraphStyle('dtd', fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER, textColor=COLOR_TEXT_DARK))]
    ]
    cartouche_table = Table(right_cartouche_data, colWidths=[9*cm])
    cartouche_table.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  COLOR_NAVY),
        ('BACKGROUND',   (0, 1), (-1, -1), COLOR_LIGHT_BG),
        ('GRID',         (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
    ]))

    header_table = Table([[logo_cell, cartouche_table]], colWidths=[9*cm, 9*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',  (0, 0), (0, 0),   'LEFT'),
        ('ALIGN',  (1, 0), (1, 0),   'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*cm))

    # Ligne de séparation corporate
    elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_ROYAL, spaceAfter=8))

    # Bloc informations complémentaires (Bénéficiaire / Fournisseur / Demandeur / Retourné par)
    if fournisseur or 'RÉCEPTION' in doc_type or 'COMMANDE' in doc_type:
        col3_label = 'Fournisseur / Livreur'
        col3_val = f'<b>{fournisseur or beneficiaire or "Non spécifié"}</b>'
    elif 'SORTIE' in doc_type:
        col3_label = 'Service & Demandeur'
        col3_val = f'<b>{beneficiaire or "Non spécifié"}</b>'
        if demandeur:
            col3_val += f'<br/><b>Demandeur : {demandeur}</b>'
    elif 'RETOUR' in doc_type:
        col3_label = 'Service & Retourné par'
        col3_val = f'<b>{beneficiaire or "Non spécifié"}</b>'
        if retourne_par:
            col3_val += f'<br/><b>Retourné par : {retourne_par}</b>'
    else:
        col3_label = 'Service / Bénéficiaire'
        col3_val = f'<b>{beneficiaire or "Non spécifié"}</b>'

    info_data = [
        [
            Paragraph('<b>Société Émettrice</b>', ParagraphStyle('l1', fontName='Helvetica-Bold', fontSize=8, textColor=COLOR_TEXT_DARK)),
            Paragraph(f'<b>{col3_label}</b>', ParagraphStyle('l2', fontName='Helvetica-Bold', fontSize=8, textColor=COLOR_TEXT_DARK)),
            Paragraph('<b>Statut Document</b>', ParagraphStyle('l3', fontName='Helvetica-Bold', fontSize=8, textColor=COLOR_TEXT_DARK)),
        ],
        [
            Paragraph('<b>SARL NOMADE AYRIS</b><br/><b>Eau de Source Naturelle</b>',
                      ParagraphStyle('v1', fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_TEXT_DARK)),
            Paragraph(col3_val,
                      ParagraphStyle('v2', fontName='Helvetica-Bold', fontSize=10, textColor=COLOR_ROYAL)),
            Paragraph('<b>DOCUMENT OFFICIEL</b><br/><b>Validé & Enregistré</b>',
                      ParagraphStyle('v3', fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_TEXT_DARK)),
        ]
    ]
    info_table = Table(info_data, colWidths=[6*cm, 6.5*cm, 5.5*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('GRID',         (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))
    return elements


def _build_corporate_table(articles: list, type_mvt: str) -> list:
    """Tableau de données style SAP / Oracle ERP."""
    elements = []

    col_header_style = ParagraphStyle('ch', fontName='Helvetica-Bold', fontSize=9,
                                       textColor=COLOR_WHITE, alignment=TA_CENTER)
    headers = [
        Paragraph('N°', col_header_style),
        Paragraph('Référence', col_header_style),
        Paragraph('Désignation Article', col_header_style),
        Paragraph('Ligne / Machine', col_header_style),
        Paragraph('Qté', col_header_style),
        Paragraph('Unité', col_header_style),
    ]

    cell_style  = ParagraphStyle('cell',  fontName='Helvetica', fontSize=9, textColor=COLOR_TEXT_DARK)
    cell_center = ParagraphStyle('cellc', fontName='Helvetica', fontSize=9, textColor=COLOR_TEXT_DARK, alignment=TA_CENTER)
    cell_bold   = ParagraphStyle('cellb', fontName='Helvetica-Bold', fontSize=10, textColor=COLOR_ROYAL, alignment=TA_CENTER)

    data = [headers]
    for i, art in enumerate(articles, 1):
        ref = art.get('reference') or art.get('code_barres', '')
        ligne = art.get('utilite_ligne', '') or art.get('emplacement', '—')
        machine = art.get('nom_machine', '')
        ligne_machine = f"{ligne} / {machine}" if machine else ligne

        data.append([
            Paragraph(str(i), cell_center),
            Paragraph(str(ref), cell_style),
            Paragraph(str(art.get('designation', '')), cell_style),
            Paragraph(str(ligne_machine), cell_center),
            Paragraph(str(art.get('quantite', '')), cell_bold),
            Paragraph(str(art.get('unite', 'Unité')), cell_center),
        ])

    total_qty = sum(int(a.get('quantite', 0)) for a in articles)
    data.append([
        Paragraph('', cell_style),
        Paragraph('', cell_style),
        Paragraph('<b>TOTAL ARTICLES</b>', ParagraphStyle('tot', fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_TEXT_DARK, alignment=TA_RIGHT)),
        Paragraph('', cell_style),
        Paragraph(f'<b>{total_qty}</b>', ParagraphStyle('totv', fontName='Helvetica-Bold', fontSize=11, textColor=COLOR_ROYAL, alignment=TA_CENTER)),
        Paragraph('', cell_style),
    ])

    table = Table(data, colWidths=[1*cm, 3.5*cm, 6.5*cm, 4*cm, 1.5*cm, 1.5*cm])
    ts = [
        ('BACKGROUND',    (0, 0), (-1, 0),  COLOR_NAVY),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  COLOR_WHITE),
        ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, 0),  8),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  8),
        ('GRID',          (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('TOPPADDING',    (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
        ('BACKGROUND',    (0, -1), (-1, -1), COLOR_LIGHT_BG),
        ('LINEABOVE',     (0, -1), (-1, -1), 1.5, COLOR_ROYAL),
    ]
    for i in range(1, len(data) - 1):
        if i % 2 == 0:
            ts.append(('BACKGROUND', (0, i), (-1, i), COLOR_ROW_ALT))

    table.setStyle(TableStyle(ts))
    elements.append(table)
    return elements


def _build_signatures_block(motif: str, type_mvt: str, demandeur: str = "", retourne_par: str = "") -> list:
    """Bloc de signatures ajusté selon la demande (Magasinier / Livreur / Demandeur / Agent Remettant)."""
    elements = []
    elements.append(Spacer(1, 0.4*cm))

    if motif:
        motif_style = ParagraphStyle('motif', fontName='Helvetica', fontSize=9, textColor=COLOR_TEXT_DARK)
        motif_box = Table([[Paragraph(f'<b>Remarques / Motif :</b> {motif}', motif_style)]], colWidths=[18*cm])
        motif_box.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, -1), HexColor('#FEF3C7')),
            ('GRID',         (0, 0), (-1, -1), 0.5, HexColor('#F59E0B')),
            ('LEFTPADDING',  (0, 0), (-1, -1), 10),
            ('TOPPADDING',   (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
        ]))
        elements.append(motif_box)
        elements.append(Spacer(1, 0.4*cm))

    sig_label = ParagraphStyle('sigl', fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_WHITE, alignment=TA_CENTER)

    if type_mvt == 'SORTIE':
        left_title = "Le Magasinier"
        right_title = f"Le Demandeur : {demandeur}" if demandeur else "Le Service Récipiendaire / Demandeur"
    elif type_mvt == 'ENTREE':
        left_title = "Le Magasinier (Réception)"
        right_title = "Le Livreur / Fournisseur"
    elif type_mvt == 'COMMANDE':
        left_title = "Le Magasinier"
        right_title = "Le Fournisseur / Destinataire"
    else:
        left_title = "Le Magasinier"
        right_title = f"Retourné par : {retourne_par}" if retourne_par else "L'Agent Remettant (Retour)"

    sig_data = [
        [Paragraph(left_title, sig_label), Paragraph(right_title, sig_label)],
        [
            Paragraph('\n\n\n\n<b>Signature & Cachet Officiel</b>',
                      ParagraphStyle('s1', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=COLOR_TEXT_DARK)),
            Paragraph('\n\n\n\n<b>Signature & Cachet Officiel</b>',
                      ParagraphStyle('s2', fontName='Helvetica-Bold', fontSize=8, alignment=TA_CENTER, textColor=COLOR_TEXT_DARK)),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[8.8*cm, 8.8*cm])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  COLOR_ROYAL),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  COLOR_WHITE),
        ('GRID',         (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (0, 0), (-1, 0),  6),
        ('BOTTOMPADDING',(0, 0), (-1, 0),  6),
        ('TOPPADDING',   (0, 1), (-1, 1),  30),
        ('BOTTOMPADDING',(0, 1), (-1, 1),  10),
    ]))
    elements.append(sig_table)
    return elements


def _draw_footer(canvas, doc, num_doc: str):
    """Dessine le pied de page ancré à la toute fin de la page A4."""
    canvas.saveState()

    # Ligne séparatrice au bas de la page
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(1)
    canvas.line(1.5 * cm, 1.5 * cm, 19.5 * cm, 1.5 * cm)

    # Texte du pied de page
    now_str = datetime.now().strftime('%d/%m/%Y à %H:%M')
    footer_text = f'SARL NOMADE AYRIS — Document Officiel Réf. {num_doc} — Édité le {now_str} — Page {doc.page}'

    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(COLOR_TEXT_DARK)
    canvas.drawCentredString(10.5 * cm, 1.0 * cm, footer_text)

    canvas.restoreState()


# ─────────────────── GÉNÉRATEUR BONS DE STOCK (BS / BR / BT) ─────────────────

def generer_bon_pdf(
    type_mvt: str,
    num_doc: str,
    beneficiaire: str = "",
    fournisseur: str = "",
    motif: str = "",
    articles: list = None,
    pdf_dir: str = None,
    demandeur: str = "",
    retourne_par: str = ""
) -> str:
    """Génère un PDF officiel avec footer ancré en bas de page A4."""
    if articles is None:
        articles = []
    if pdf_dir is None:
        pdf_dir = get_default_pdf_dir()

    Path(pdf_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    prefix = {'SORTIE': 'BS', 'ENTREE': 'BR', 'RETOUR': 'BT'}.get(type_mvt, 'DOC')
    filename = f"{prefix}_{num_doc.replace('-','_')}_{timestamp}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc_type_label = {
        'SORTIE': "BON DE SORTIE",
        'ENTREE': "BON DE RÉCEPTION",
        'RETOUR': "BON DE RETOUR"
    }.get(type_mvt, "DOCUMENT")

    date_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.2*cm, bottomMargin=2.2*cm,
        title=f"SARL NOMADE AYRIS — {doc_type_label} {num_doc}",
        author="SARL NOMADE AYRIS Enterprise System",
    )

    story = []
    story.extend(_build_corporate_header(doc_type_label, num_doc, date_str, beneficiaire, fournisseur, demandeur, retourne_par))
    story.extend(_build_corporate_table(articles, type_mvt))
    story.extend(_build_signatures_block(motif, type_mvt, demandeur, retourne_par))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_footer(c, d, num_doc),
        onLaterPages=lambda c, d: _draw_footer(c, d, num_doc)
    )
    print(f"[PDF] Document corporate généré : {filepath}")
    return filepath


# ─────────────────── GÉNÉRATEUR BON DE COMMANDE ──────────────────────────────

def generer_bon_commande_pdf(
    num_bc: str,
    fournisseur: str = "",
    articles: list = None,
    motif: str = "",
    pdf_dir: str = None
) -> str:
    """Génère un Bon de Commande (BC) PDF officiel de classe internationale."""
    if articles is None:
        articles = []
    if pdf_dir is None:
        pdf_dir = get_default_pdf_dir()

    Path(pdf_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"BC_{num_bc.replace('-','_')}_{timestamp}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    date_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.2*cm, bottomMargin=2.2*cm,
        title=f"SARL NOMADE AYRIS — BON DE COMMANDE {num_bc}",
        author="SARL NOMADE AYRIS Enterprise System",
    )

    story = []
    story.extend(_build_corporate_header("BON DE COMMANDE", num_bc, date_str, "", fournisseur))
    story.extend(_build_corporate_table(articles, 'COMMANDE'))
    story.extend(_build_signatures_block(motif, 'COMMANDE'))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_footer(c, d, num_bc),
        onLaterPages=lambda c, d: _draw_footer(c, d, num_bc)
    )
    print(f"[PDF] Bon de commande corporate généré : {filepath}")
    return filepath
