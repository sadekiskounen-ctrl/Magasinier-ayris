"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: services/excel_generator.py
Génère un export Excel (.xlsx) de l'inventaire par période avec en-tête officiel SARL NOMADE AYRIS.
"""

import os
from datetime import datetime
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as OpenpyxlImage
import database.db_manager as db

LOGO_PATH = str(Path(__file__).parent.parent / 'assets' / 'logo_nomade_ayris.png')


def exporter_inventaire_excel(date_debut: str, date_fin: str, destination_path: str) -> str:
    """
    Génère un fichier Excel (.xlsx) structuré par journée sur la plage [date_debut, date_fin].
    Contient l'en-tête officiel SARL NOMADE AYRIS et le détail complet des mouvements.
    """
    wb = openpyxl.Workbook()

    COLOR_NAVY = "1A3A5C"
    COLOR_BLUE = "2563EB"
    COLOR_GRAY = "CBD5E1"

    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Segoe UI", size=10, bold=True, color="DCE6F1")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=9)

    fill_navy = PatternFill(start_color=COLOR_NAVY, end_color=COLOR_NAVY, fill_type="solid")
    fill_blue = PatternFill(start_color=COLOR_BLUE, end_color=COLOR_BLUE, fill_type="solid")
    fill_row_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=COLOR_GRAY),
        right=Side(style='thin', color=COLOR_GRAY),
        top=Side(style='thin', color=COLOR_GRAY),
        bottom=Side(style='thin', color=COLOR_GRAY)
    )

    # ── FEUILLE 1 : RÉCAPITULATIF ──
    ws_recap = wb.active
    ws_recap.title = "Récapitulatif Inventaire"
    ws_recap.views.sheetView[0].showGridLines = True

    # En-tête SARL NOMADE AYRIS
    ws_recap.merge_cells("A1:F2")
    cell_title = ws_recap["A1"]
    cell_title.value = "SARL NOMADE AYRIS — RAPPORT D'INVENTAIRE & LOGISTIQUE"
    cell_title.font = font_title
    cell_title.fill = fill_navy
    cell_title.alignment = Alignment(horizontal="center", vertical="center")

    ws_recap.merge_cells("A3:F3")
    cell_sub = ws_recap["A3"]
    cell_sub.value = f"Période du {date_debut} au {date_fin} | Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    cell_sub.font = font_subtitle
    cell_sub.fill = fill_blue
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")

    headers_recap = ["Date / Journée", "Nombre Mouvements", "Total Entrées", "Total Sorties", "Total Retours", "Solde Net"]
    ws_recap.append([])  # Ligne 4 vide

    ws_recap.append(headers_recap)  # Ligne 5
    for col_num in range(1, 7):
        c = ws_recap.cell(row=5, column=col_num)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    journees = db.get_inventaire_par_periode(date_debut, date_fin)
    row_idx = 6
    for j in journees:
        entrees = j['total_entrees'] or 0
        sorties = j['total_sorties'] or 0
        retours = j['total_retours'] or 0
        solde = (entrees + retours) - sorties

        row = [j['jour'], j['nb_mouvements'], entrees, sorties, retours, solde]
        ws_recap.append(row)

        fill_curr = fill_row_alt if row_idx % 2 == 0 else PatternFill(fill_type=None)
        for col_num in range(1, 7):
            c = ws_recap.cell(row=row_idx, column=col_num)
            c.font = font_data
            c.border = thin_border
            if fill_curr.fill_type:
                c.fill = fill_curr
            c.alignment = Alignment(horizontal="center" if col_num != 1 else "left", vertical="center")
        row_idx += 1

    # ── FEUILLE 2 : DÉTAIL DES MOUVEMENTS ──
    ws_detail = wb.create_sheet(title="Détail des Mouvements")
    ws_detail.views.sheetView[0].showGridLines = True

    ws_detail.merge_cells("A1:H2")
    c_det = ws_detail["A1"]
    c_det.value = "SARL NOMADE AYRIS — DÉTAIL CHRONOLOGIQUE DES MOUVEMENTS"
    c_det.font = font_title
    c_det.fill = fill_navy
    c_det.alignment = Alignment(horizontal="center", vertical="center")

    headers_detail = ["Date & Heure", "N° Doc / Type", "Référence Produit", "Désignation Produit", "Quantité", "Service / Tiers", "Motif", "Fichier PDF"]
    ws_detail.append([])  # Ligne 3 vide
    ws_detail.append(headers_detail)  # Ligne 4

    for col_num in range(1, 9):
        c = ws_detail.cell(row=4, column=col_num)
        c.font = font_header
        c.fill = fill_blue
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    row_idx = 5
    for j in journees:
        mouvements = db.get_mouvements_journee(j['jour'])
        for m in mouvements:
            type_str = m['type_mouvement']
            qte_prefix = "+" if type_str in ('ENTREE', 'RETOUR') else "-"
            pdf_name = os.path.basename(m.get('chemin_pdf', '')) if m.get('chemin_pdf') else "N/A"

            row = [
                m['date_heure'][:16] if m.get('date_heure') else '',
                type_str,
                m.get('code_barres', ''),
                m.get('designation', ''),
                f"{qte_prefix}{m['quantite']} {m.get('unite', '')}",
                m.get('beneficiaire_service', ''),
                m.get('motif', ''),
                pdf_name
            ]
            ws_detail.append(row)

            fill_curr = fill_row_alt if row_idx % 2 == 0 else PatternFill(fill_type=None)
            for col_num in range(1, 9):
                c = ws_detail.cell(row=row_idx, column=col_num)
                c.font = font_data
                c.border = thin_border
                if fill_curr.fill_type:
                    c.fill = fill_curr
                if col_num in (1, 2, 3, 5):
                    c.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")
            row_idx += 1

    # Active les filtres automatiques Excel sur les deux feuilles
    ws_recap.auto_filter.ref = f"A5:F{max(5, ws_recap.max_row)}"
    ws_detail.auto_filter.ref = f"A4:H{max(4, ws_detail.max_row)}"

    # Ajustement des largeurs de colonnes
    for ws in [ws_recap, ws_detail]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if cell.row in (1, 2, 3):
                    continue
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(destination_path)
    return destination_path


def exporter_historique_excel(mouvements: list, destination_path: str) -> str:
    """
    Génère un fichier Excel (.xlsx) pour l'Historique & Documents avec filtres automatiques Excel activés.
    """
    wb = openpyxl.Workbook()

    COLOR_NAVY = "1A3A5C"
    COLOR_BLUE = "2563EB"
    COLOR_GRAY = "CBD5E1"

    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Segoe UI", size=10, bold=True, color="DCE6F1")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=9)

    fill_navy = PatternFill(start_color=COLOR_NAVY, end_color=COLOR_NAVY, fill_type="solid")
    fill_blue = PatternFill(start_color=COLOR_BLUE, end_color=COLOR_BLUE, fill_type="solid")
    fill_row_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=COLOR_GRAY),
        right=Side(style='thin', color=COLOR_GRAY),
        top=Side(style='thin', color=COLOR_GRAY),
        bottom=Side(style='thin', color=COLOR_GRAY)
    )

    ws = wb.active
    ws.title = "Historique & Documents"
    ws.views.sheetView[0].showGridLines = True

    # En-tête SARL NOMADE AYRIS
    ws.merge_cells("A1:I2")
    cell_title = ws["A1"]
    cell_title.value = "SARL NOMADE AYRIS — HISTORIQUE DES DOCUMENTS ET MOUVEMENTS"
    cell_title.font = font_title
    cell_title.fill = fill_navy
    cell_title.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:I3")
    cell_sub = ws["A3"]
    cell_sub.value = f"Export effectué le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Total : {len(mouvements)} document(s)"
    cell_sub.font = font_subtitle
    cell_sub.fill = fill_blue
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")

    headers = [
        "Date & Heure", "Type Mouvement", "Référence Produit", "Désignation Produit",
        "Quantité", "Service / Tiers", "Demandeur / Remettant", "Motif", "Fichier PDF"
    ]
    ws.append([])  # Ligne 4 vide

    ws.append(headers)  # Ligne 5
    for col_num in range(1, 10):
        c = ws.cell(row=5, column=col_num)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    row_idx = 6
    for m in mouvements:
        t_type = m.get('type_mouvement', '')
        type_str = {'SORTIE': 'Bon de Sortie', 'ENTREE': 'Bon de Réception', 'RETOUR': 'Bon de Retour', 'COMMANDE': 'Bon de Commande'}.get(t_type, t_type)
        personne = m.get('demandeur') or m.get('retourne_par') or ''
        pdf_name = os.path.basename(m.get('chemin_pdf', '')) if m.get('chemin_pdf') else "Non disponible"

        row = [
            m.get('date_heure', '')[:19],
            type_str,
            m.get('code_barres', ''),
            m.get('designation', ''),
            f"{m.get('quantite', 0)} {m.get('unite', '')}".strip(),
            m.get('beneficiaire_service', ''),
            personne,
            m.get('motif', ''),
            pdf_name
        ]
        ws.append(row)

        fill_curr = fill_row_alt if row_idx % 2 == 0 else PatternFill(fill_type=None)
        for col_num in range(1, 10):
            c = ws.cell(row=row_idx, column=col_num)
            c.font = font_data
            c.border = thin_border
            if fill_curr.fill_type:
                c.fill = fill_curr
            if col_num in (1, 2, 3, 5, 9):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        row_idx += 1

    # Active les filtres automatiques Excel
    max_row = max(5, ws.max_row)
    ws.auto_filter.ref = f"A5:I{max_row}"

    # Ajustement des largeurs de colonnes
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if cell.row in (1, 2, 3):
                continue
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(destination_path)
    return destination_path


def exporter_catalogue_excel(produits: list, destination_path: str) -> str:
    """
    Génère un fichier Excel (.xlsx) pour le Catalogue des Pièces de Rechange (filtré par machine, ligne, catégorie, etc.).
    Contient l'en-tête officiel SARL NOMADE AYRIS et les filtres automatiques Excel activés.
    """
    wb = openpyxl.Workbook()

    COLOR_NAVY = "1A3A5C"
    COLOR_BLUE = "2563EB"
    COLOR_GRAY = "CBD5E1"
    COLOR_ALERT_BG = "FEE2E2"

    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Segoe UI", size=10, bold=True, color="DCE6F1")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=9)
    font_alert = Font(name="Segoe UI", size=9, bold=True, color="DC2626")

    fill_navy = PatternFill(start_color=COLOR_NAVY, end_color=COLOR_NAVY, fill_type="solid")
    fill_blue = PatternFill(start_color=COLOR_BLUE, end_color=COLOR_BLUE, fill_type="solid")
    fill_row_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_alert = PatternFill(start_color=COLOR_ALERT_BG, end_color=COLOR_ALERT_BG, fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=COLOR_GRAY),
        right=Side(style='thin', color=COLOR_GRAY),
        top=Side(style='thin', color=COLOR_GRAY),
        bottom=Side(style='thin', color=COLOR_GRAY)
    )

    ws = wb.active
    ws.title = "Pièces de Rechange"
    ws.views.sheetView[0].showGridLines = True

    # En-tête SARL NOMADE AYRIS
    ws.merge_cells("A1:M2")
    cell_title = ws["A1"]
    cell_title.value = "SARL NOMADE AYRIS — CATALOGUE DES PIÈCES DE RECHANGE"
    cell_title.font = font_title
    cell_title.fill = fill_navy
    cell_title.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:M3")
    cell_sub = ws["A3"]
    cell_sub.value = f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Total : {len(produits)} référence(s)"
    cell_sub.font = font_subtitle
    cell_sub.fill = fill_blue
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")

    headers = [
        "Référence", "Désignation Produit", "Fournisseur", "Catégorie",
        "Emplacement", "Stock Actuel", "Unité", "Seuil d'Alerte",
        "Utilité Ligne(s)", "Nom Machine", "Date Rechange Initial",
        "Durée de Vie", "Prochaine Rechange"
    ]
    ws.append([])  # Ligne 4 vide

    ws.append(headers)  # Ligne 5
    for col_num in range(1, 14):
        c = ws.cell(row=5, column=col_num)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    row_idx = 6
    for p in produits:
        stock = p.get('quantite_stock', 0)
        seuil = p.get('seuil_alerte', 5)
        en_alerte = stock <= seuil

        row = [
            p.get('code_barres', ''),
            p.get('designation', ''),
            p.get('fournisseur_nom') or '—',
            p.get('categorie_piece') or 'Pièce de Rechange',
            p.get('emplacement') or '—',
            stock,
            p.get('unite', 'Unité'),
            seuil,
            p.get('utilite_ligne') or '—',
            p.get('nom_machine') or '—',
            p.get('date_rechange_initiale') or '—',
            p.get('duree_vie') or '—',
            p.get('prochaine_date_rechange') or '—'
        ]
        ws.append(row)

        fill_curr = fill_alert if en_alerte else (fill_row_alt if row_idx % 2 == 0 else PatternFill(fill_type=None))
        font_curr = font_alert if en_alerte else font_data

        for col_num in range(1, 14):
            c = ws.cell(row=row_idx, column=col_num)
            c.font = font_curr
            c.border = thin_border
            if fill_curr.fill_type:
                c.fill = fill_curr
            if col_num in (1, 6, 7, 8, 11, 12, 13):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        row_idx += 1

    # Active les filtres automatiques Excel
    max_row = max(5, ws.max_row)
    ws.auto_filter.ref = f"A5:M{max_row}"

    # Ajustement des largeurs de colonnes
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if cell.row in (1, 2, 3):
                continue
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(destination_path)
    return destination_path


def exporter_engins_excel(produits: list, destination_path: str) -> str:
    """
    Génère un fichier Excel (.xlsx) pour le Catalogue des Produits d'Engins (Camion / Clarck).
    Contient l'en-tête officiel SARL NOMADE AYRIS et les filtres automatiques Excel activés.
    """
    wb = openpyxl.Workbook()

    COLOR_NAVY = "1A3A5C"
    COLOR_BLUE = "2563EB"
    COLOR_GRAY = "CBD5E1"
    COLOR_ALERT_BG = "FEE2E2"

    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Segoe UI", size=10, bold=True, color="DCE6F1")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=9)
    font_alert = Font(name="Segoe UI", size=9, bold=True, color="DC2626")

    fill_navy = PatternFill(start_color=COLOR_NAVY, end_color=COLOR_NAVY, fill_type="solid")
    fill_blue = PatternFill(start_color=COLOR_BLUE, end_color=COLOR_BLUE, fill_type="solid")
    fill_row_alt = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_alert = PatternFill(start_color=COLOR_ALERT_BG, end_color=COLOR_ALERT_BG, fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=COLOR_GRAY),
        right=Side(style='thin', color=COLOR_GRAY),
        top=Side(style='thin', color=COLOR_GRAY),
        bottom=Side(style='thin', color=COLOR_GRAY)
    )

    ws = wb.active
    ws.title = "Produits Engins"
    ws.views.sheetView[0].showGridLines = True

    # En-tête SARL NOMADE AYRIS
    ws.merge_cells("A1:G2")
    cell_title = ws["A1"]
    cell_title.value = "SARL NOMADE AYRIS — CATALOGUE DES PRODUITS D'ENGINS"
    cell_title.font = font_title
    cell_title.fill = fill_navy
    cell_title.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:G3")
    cell_sub = ws["A3"]
    cell_sub.value = f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Total : {len(produits)} référence(s)"
    cell_sub.font = font_subtitle
    cell_sub.fill = fill_blue
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")

    headers = [
        "Type Engin", "Référence", "Marque", "Désignation Pièce",
        "Stock Actuel", "Seuil d'Alerte", "Statut Alerte"
    ]
    ws.append([])  # Ligne 4 vide

    ws.append(headers)  # Ligne 5
    for col_num in range(1, 8):
        c = ws.cell(row=5, column=col_num)
        c.font = font_header
        c.fill = fill_navy
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    row_idx = 6
    for p in produits:
        stock = p.get('quantite_stock', 0)
        seuil = p.get('seuil_alerte', 5)
        en_alerte = stock <= seuil
        statut_str = "⚠️ ALERTE STOCK" if en_alerte else "OK"

        row = [
            p.get('type_engin', ''),
            p.get('reference', ''),
            p.get('marque', ''),
            p.get('designation', ''),
            stock,
            seuil,
            statut_str
        ]
        ws.append(row)

        fill_curr = fill_alert if en_alerte else (fill_row_alt if row_idx % 2 == 0 else PatternFill(fill_type=None))
        font_curr = font_alert if en_alerte else font_data

        for col_num in range(1, 8):
            c = ws.cell(row=row_idx, column=col_num)
            c.font = font_curr
            c.border = thin_border
            if fill_curr.fill_type:
                c.fill = fill_curr
            if col_num in (1, 2, 5, 6, 7):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        row_idx += 1

    # Active les filtres automatiques Excel
    max_row = max(5, ws.max_row)
    ws.auto_filter.ref = f"A5:G{max_row}"

    # Ajustement des largeurs de colonnes
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if cell.row in (1, 2, 3):
                continue
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(destination_path)
    return destination_path


def exporter_alertes_excel(alertes: list, destination_path: str) -> str:
    """
    Génère un fichier Excel (.xlsx) dédié aux Produits en Alerte de Stock.
    """
    wb = openpyxl.Workbook()

    COLOR_NAVY = "1A3A5C"
    COLOR_RED = "DC2626"
    COLOR_GRAY = "CBD5E1"
    COLOR_ALERT_BG = "FEE2E2"

    font_title = Font(name="Segoe UI", size=16, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Segoe UI", size=10, bold=True, color="FEE2E2")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_alert = Font(name="Segoe UI", size=9, bold=True, color="DC2626")

    fill_navy = PatternFill(start_color=COLOR_NAVY, end_color=COLOR_NAVY, fill_type="solid")
    fill_red = PatternFill(start_color=COLOR_RED, end_color=COLOR_RED, fill_type="solid")
    fill_alert = PatternFill(start_color=COLOR_ALERT_BG, end_color=COLOR_ALERT_BG, fill_type="solid")
    fill_row_alt = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=COLOR_GRAY),
        right=Side(style='thin', color=COLOR_GRAY),
        top=Side(style='thin', color=COLOR_GRAY),
        bottom=Side(style='thin', color=COLOR_GRAY)
    )

    ws = wb.active
    ws.title = "Alertes Stock"
    ws.views.sheetView[0].showGridLines = True

    # En-tête SARL NOMADE AYRIS
    ws.merge_cells("A1:G2")
    cell_title = ws["A1"]
    cell_title.value = "SARL NOMADE AYRIS — RAPPORT DES PRODUITS EN ALERTE STOCK"
    cell_title.font = font_title
    cell_title.fill = fill_navy
    cell_title.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:G3")
    cell_sub = ws["A3"]
    cell_sub.value = f"Export généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Total Alertes : {len(alertes)} produit(s)"
    cell_sub.font = font_subtitle
    cell_sub.fill = fill_red
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")

    headers = [
        "Référence", "Désignation Produit", "Stock Actuel", "Unité",
        "Seuil d'Alerte", "Ligne(s)", "Machine"
    ]
    ws.append([])  # Ligne 4 vide

    ws.append(headers)  # Ligne 5
    for col_num in range(1, 8):
        c = ws.cell(row=5, column=col_num)
        c.font = font_header
        c.fill = fill_red
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    row_idx = 6
    for p in alertes:
        stock = p.get('quantite_stock', 0)
        seuil = p.get('seuil_alerte', 5)

        row = [
            p.get('code_barres', ''),
            p.get('designation', ''),
            stock,
            p.get('unite', 'Unité'),
            seuil,
            p.get('utilite_ligne') or '—',
            p.get('nom_machine') or '—'
        ]
        ws.append(row)

        fill_curr = fill_alert if row_idx % 2 == 0 else fill_row_alt

        for col_num in range(1, 8):
            c = ws.cell(row=row_idx, column=col_num)
            c.font = font_alert
            c.border = thin_border
            c.fill = fill_curr
            if col_num in (1, 3, 4, 5):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        row_idx += 1

    # Active les filtres automatiques Excel
    max_row = max(5, ws.max_row)
    ws.auto_filter.ref = f"A5:G{max_row}"

    # Ajustement des largeurs de colonnes
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if cell.row in (1, 2, 3):
                continue
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(destination_path)
    return destination_path


