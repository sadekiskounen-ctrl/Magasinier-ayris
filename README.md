# 📦 SARL AYRIS — Gestionnaire de Stock

Application de gestion de magasin/stock pour **SARL AYRIS**, développée en Python avec CustomTkinter et SQLite.

---

## 🚀 Lancement Rapide

### 1. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 2. Lancer l'application
```bash
python main.py
```

---

## 📂 Structure du Projet

```
Magasinier/
│
├── main.py                    # Point d'entrée principal
├── build.py                   # Script de compilation PyInstaller (.exe)
├── requirements.txt           # Dépendances Python
│
├── database/
│   ├── __init__.py
│   └── db_manager.py          # Gestion SQLite (CRUD, stats, mouvements)
│
├── ui/
│   ├── __init__.py
│   ├── theme.py               # Palette de couleurs, polices, constantes
│   ├── widgets.py             # Composants réutilisables (cartes, tableaux...)
│   ├── main_window.py         # Fenêtre principale + sidebar de navigation
│   ├── dashboard.py           # Tableau de bord (KPIs, alertes, mouvements)
│   ├── catalogue.py           # Catalogue produits (CRUD complet)
│   ├── saisie.py              # Saisie rapide Entrées/Sorties (scanner)
│   ├── historique.py          # Historique & documents PDF
│   └── options.py             # Configuration (imprimante, PDF, sauvegarde)
│
└── services/
    ├── __init__.py
    ├── pdf_generator.py       # Génération PDF (BS/BR) avec ReportLab
    └── config_manager.py      # Configuration persistante (JSON)
```

---

## 🗄️ Emplacement de la Base de Données

La base de données SQLite est stockée à l'emplacement sécurisé Windows :
```
C:\Users\<Utilisateur>\AppData\Local\SARL_Ayris_Stock\ayris_stock.db
```
Elle est créée automatiquement au premier lancement.

---

## 📋 Fonctionnalités

| Écran | Fonctionnalités |
|---|---|
| 📊 **Dashboard** | KPIs en temps réel, alertes de stock, derniers mouvements |
| 📦 **Catalogue** | CRUD produits, recherche, menu dépendant ligne/machine |
| 🔄 **Saisie** | Focus auto scanner, fiche produit instantanée, génération PDF |
| 📄 **Historique** | Tous les bons BS/BR, aperçu, réimpression, ouverture PDF |
| ⚙️ **Options** | Dossier PDF, imprimante, sauvegarde .db |

---

## 🔨 Compilation en .EXE

Pour générer un exécutable Windows autonome :
```bash
pip install pyinstaller
python build.py
```
Le fichier `SARL_Ayris_Stock.exe` sera généré dans `dist/`.

---

## 📦 Dépendances

| Paquet | Rôle |
|---|---|
| `customtkinter` | Interface graphique moderne |
| `reportlab` | Génération PDF professionnelle |
| `Pillow` | Traitement d'images |
| `pyinstaller` | Compilation .exe (optionnel) |

---

## 🏗️ Schéma Base de Données

### Table `produits`
| Champ | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifiant unique |
| code_barres | TEXT UNIQUE | Code-barres/scanner |
| designation | TEXT | Nom du produit |
| emplacement | TEXT | Localisation en magasin |
| quantite_stock | INTEGER | Quantité disponible |
| unite | TEXT | Unité de mesure |
| utilite_ligne | TEXT | Ligne de production |
| nom_machine | TEXT | Machine associée |
| seuil_alerte | INTEGER | Seuil d'alerte stock |

### Table `mouvements`
| Champ | Type | Description |
|---|---|---|
| id | INTEGER PK | Identifiant unique |
| produit_id | INTEGER FK | Référence produit |
| type_mouvement | TEXT | ENTREE ou SORTIE |
| quantite | INTEGER | Quantité déplacée |
| beneficiaire_service | TEXT | Service destinataire |
| motif | TEXT | Motif du mouvement |
| date_heure | DATETIME | Horodatage automatique |
| chemin_pdf | TEXT | Chemin du bon PDF généré |

---

*© 2024 SARL AYRIS — Application développée avec Python 3.10+*
