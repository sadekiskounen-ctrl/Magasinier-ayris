"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: database/db_manager.py
Gère la connexion SQLite et toutes les opérations CRUD basées sur les Références produits.
"""

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path

_DB_CONNECTION = None


class SharedConnectionProxy:
    """
    Wrapper autour d'une connexion sqlite3.Connection partagée.
    Redirige toutes les opérations vers la connexion sous-jacente
    et empêche sa fermeture prématurée lors des appels à .close().
    """
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def close(self):
        # Ne rien faire : la connexion reste ouverte et réutilisable pour la durée de l'application.
        pass

    def real_close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db_path() -> str:
    """Retourne le chemin sécurisé de la base de données (AppData/Local)."""
    local_app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    app_dir = Path(local_app_data) / 'SARL_Ayris_Stock'
    app_dir.mkdir(parents=True, exist_ok=True)
    return str(app_dir / 'ayris_stock.db')


def perform_startup_backups(db_path: str):
    """
    Exécute la double sauvegarde automatique de la base SQLite avant toute migration/initialisation :
    1. Dans le même répertoire AppData (ayris_stock_backup_YYYYMMDD_HHMMSS.db).
    2. Sur le lecteur D:\\ (D:\\Sauvegardes_AYRIS\\ayris_stock_backup_YYYYMMDD_HHMMSS.db).
    Utilise shutil.copy2 pour garantir une copie binaire brute 100% exacte.
    """
    db_file = Path(db_path)
    if not db_file.exists() or db_file.stat().st_size == 0:
        print("[DB Backup] Première utilisation ou base absente : pas de sauvegarde à effectuer.")
        return

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"ayris_stock_backup_{timestamp}.db"

    # 1. Sauvegarde locale (AppData)
    try:
        local_backup_path = db_file.parent / backup_filename
        shutil.copy2(db_file, local_backup_path)
        print(f"[DB Backup] Sauvegarde locale AppData réussie : {local_backup_path}")
    except Exception as e:
        print(f"[DB Backup WARNING] Échec de la sauvegarde locale : {e}")

    # 2. Sauvegarde sur le lecteur D:\ (si présent et accessible)
    try:
        d_dir = Path("D:/Sauvegardes_AYRIS")
        d_dir.mkdir(parents=True, exist_ok=True)
        d_backup_path = d_dir / backup_filename
        shutil.copy2(db_file, d_backup_path)
        print(f"[DB Backup] Sauvegarde sur lecteur D:\\ réussie : {d_backup_path}")
    except Exception as e:
        print(f"[DB Backup WARNING] Lecteur D:\\ non accessible ou absent : {e}")


def get_connection() -> SharedConnectionProxy:
    """Retourne la connexion unique partagée au niveau du module avec le mode WAL."""
    global _DB_CONNECTION
    if _DB_CONNECTION is None:
        raw_conn = sqlite3.connect(get_db_path(), timeout=30.0, check_same_thread=False)
        raw_conn.row_factory = sqlite3.Row
        raw_conn.execute("PRAGMA foreign_keys = ON")
        raw_conn.execute("PRAGMA journal_mode = WAL")
        raw_conn.execute("PRAGMA synchronous = NORMAL")
        raw_conn.execute("PRAGMA cache_size = -20000")
        _DB_CONNECTION = SharedConnectionProxy(raw_conn)
    return _DB_CONNECTION


def initialize_database():
    """Initialise la base de données, effectue la double sauvegarde et applique les index/migrations."""
    db_path = get_db_path()

    # 0. Double sauvegarde automatique AVANT toute modification SQL
    perform_startup_backups(db_path)

    conn = get_connection()
    cursor = conn.cursor()

    # Table PRODUITS (code_barres stocke la Référence unique)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_barres TEXT UNIQUE NOT NULL,
            designation TEXT NOT NULL,
            emplacement TEXT DEFAULT '',
            quantite_stock INTEGER DEFAULT 0,
            unite TEXT DEFAULT 'Unité',
            utilite_ligne TEXT DEFAULT 'Aucune',
            nom_machine TEXT DEFAULT 'N/A',
            seuil_alerte INTEGER DEFAULT 5,
            categorie_piece TEXT DEFAULT 'Pièce de Rechange',
            fournisseur_id INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
            date_rechange_initiale TEXT DEFAULT '',
            duree_vie TEXT DEFAULT '',
            prochaine_date_rechange TEXT DEFAULT '',
            code_barres_reverse TEXT DEFAULT ''
        )
    """)

    # Table FOURNISSEURS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            numero TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migrations : ajouter les colonnes si absentes dans produits
    for col_def in [
        "categorie_piece TEXT DEFAULT 'Pièce de Rechange'",
        "fournisseur_id INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL",
        "date_rechange_initiale TEXT DEFAULT ''",
        "duree_vie TEXT DEFAULT ''",
        "prochaine_date_rechange TEXT DEFAULT ''",
        "code_barres_reverse TEXT DEFAULT ''"
    ]:
        try:
            cursor.execute(f"ALTER TABLE produits ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass

    # Remplir code_barres_reverse de manière rétroactive pour tous les produits existants
    cursor.execute("SELECT id, code_barres FROM produits WHERE code_barres_reverse IS NULL OR code_barres_reverse = '' OR length(code_barres_reverse) != length(code_barres)")
    rows_to_update = cursor.fetchall()
    for r in rows_to_update:
        pid, cb = r['id'], r['code_barres']
        if cb:
            cursor.execute("UPDATE produits SET code_barres_reverse = ? WHERE id = ?", (cb[::-1], pid))

    # ── Vérification et migration de la table mouvements ─────────────────────
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='mouvements'")
    row = cursor.fetchone()
    needs_rebuild = row and ("CHECK" in (row[0] or '').upper() or "RETOUR" not in (row[0] or ''))

    if row is None:
        cursor.execute("""
            CREATE TABLE mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produit_id INTEGER NOT NULL,
                type_mouvement TEXT NOT NULL,
                quantite INTEGER NOT NULL,
                beneficiaire_service TEXT DEFAULT '',
                motif TEXT DEFAULT '',
                date_heure DATETIME DEFAULT CURRENT_TIMESTAMP,
                chemin_pdf TEXT DEFAULT '',
                demandeur TEXT DEFAULT '',
                retourne_par TEXT DEFAULT '',
                FOREIGN KEY (produit_id) REFERENCES produits(id) ON DELETE CASCADE
            )
        """)
    elif needs_rebuild:
        conn.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mouvements_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produit_id INTEGER NOT NULL,
                type_mouvement TEXT NOT NULL,
                quantite INTEGER NOT NULL,
                beneficiaire_service TEXT DEFAULT '',
                motif TEXT DEFAULT '',
                date_heure DATETIME DEFAULT CURRENT_TIMESTAMP,
                chemin_pdf TEXT DEFAULT '',
                demandeur TEXT DEFAULT '',
                retourne_par TEXT DEFAULT '',
                FOREIGN KEY (produit_id) REFERENCES produits(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO mouvements_new
                (id, produit_id, type_mouvement, quantite, beneficiaire_service,
                 motif, date_heure, chemin_pdf,
                 demandeur, retourne_par)
            SELECT m.id, m.produit_id, m.type_mouvement, m.quantite, m.beneficiaire_service,
                   m.motif, m.date_heure, m.chemin_pdf,
                   COALESCE(m.demandeur, ''), COALESCE(m.retourne_par, '')
            FROM mouvements m
        """)
        cursor.execute("DROP TABLE mouvements")
        cursor.execute("ALTER TABLE mouvements_new RENAME TO mouvements")
        conn.execute("PRAGMA foreign_keys = ON")
    else:
        try:
            cursor.execute("ALTER TABLE mouvements ADD COLUMN demandeur TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE mouvements ADD COLUMN retourne_par TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    # Table PRODUITS ENGINS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produits_engins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_engin TEXT NOT NULL,
            reference TEXT UNIQUE NOT NULL,
            marque TEXT NOT NULL,
            designation TEXT NOT NULL,
            quantite_stock INTEGER DEFAULT 0,
            seuil_alerte INTEGER DEFAULT 5,
            date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table OUTILLAGE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outillage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            designation TEXT NOT NULL,
            marque TEXT DEFAULT '',
            numero_outillage TEXT NOT NULL,
            quantite INTEGER DEFAULT 1,
            statut TEXT DEFAULT 'Dans le magasin',
            date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table SORTIES OUTILLAGE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sorties_outillage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outillage_id INTEGER NOT NULL,
            demandeur TEXT NOT NULL,
            quantite_sortie INTEGER NOT NULL,
            quantite_retournee INTEGER DEFAULT 0,
            motif TEXT DEFAULT '',
            date_sortie DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_retour DATETIME,
            statut TEXT DEFAULT 'EN_COURS',
            FOREIGN KEY (outillage_id) REFERENCES outillage(id) ON DELETE CASCADE
        )
    """)

    # ── Indexation SQL pour performances maximales ───────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mouvements_produit_id ON mouvements(produit_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mouvements_date ON mouvements(date_heure DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mouvements_type ON mouvements(type_mouvement);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_produits_designation ON produits(designation);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_produits_utilite_ligne ON produits(utilite_ligne);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_produits_fournisseur_id ON produits(fournisseur_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_produits_code_barres ON produits(code_barres);")
    cursor.execute("DROP INDEX IF EXISTS idx_produits_code_barres_reverse;")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_produits_code_barres_reverse ON produits(code_barres_reverse COLLATE NOCASE);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outillage_numero ON outillage(numero_outillage);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outillage_designation ON outillage(designation);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sorties_outillage_outillage_id ON sorties_outillage(outillage_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sorties_outillage_statut ON sorties_outillage(statut);")

    conn.commit()
    print(f"[DB] Base de données SARL NOMADE AYRIS initialisée : {db_path}")


# ─────────────────────── PRODUITS ───────────────────────

def get_all_produits(search: str = "") -> list:
    """Retourne tous les produits avec les infos du fournisseur rattaché."""
    conn = get_connection()
    cursor = conn.cursor()
    if search:
        like = f"%{search}%"
        cursor.execute("""
            SELECT p.*, f.nom as fournisseur_nom, f.numero as fournisseur_numero
            FROM produits p
            LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
            WHERE p.code_barres LIKE ? OR p.designation LIKE ?
               OR p.utilite_ligne LIKE ? OR p.nom_machine LIKE ?
               OR p.emplacement LIKE ? OR f.nom LIKE ?
            ORDER BY p.designation
        """, (like, like, like, like, like, like))
    else:
        cursor.execute("""
            SELECT p.*, f.nom as fournisseur_nom, f.numero as fournisseur_numero
            FROM produits p
            LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
            ORDER BY p.designation
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_produit_by_ref(reference: str) -> dict | None:
    """Retourne un produit par sa Référence exacte avec infos fournisseur."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, f.nom as fournisseur_nom, f.numero as fournisseur_numero
        FROM produits p
        LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
        WHERE p.code_barres = ?
    """, (reference.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# Alias rétrocompatible
get_produit_by_barcode = get_produit_by_ref


def find_produit_by_ref_or_last4(query: str) -> dict | None:
    """
    Recherche un produit par sa Référence exacte OU par ses 4 derniers caractères.
    Utilise l'index B-tree sur code_barres_reverse pour une réponse instantanée sans scan complet.
    """
    q = query.strip()
    if not q:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Recherche exacte (utilisera l'index idx_produits_code_barres)
    cursor.execute("""
        SELECT p.*, f.nom as fournisseur_nom, f.numero as fournisseur_numero
        FROM produits p
        LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
        WHERE p.code_barres = ?
    """, (q,))
    row = cursor.fetchone()

    # 2. Recherche par suffixe (utilisera l'index idx_produits_code_barres_reverse)
    if not row:
        q_rev = q[::-1]
        cursor.execute("""
            SELECT p.*, f.nom as fournisseur_nom, f.numero as fournisseur_numero
            FROM produits p
            LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
            WHERE p.code_barres_reverse LIKE ?
        """, (f"{q_rev}%",))
        matches = cursor.fetchall()
        if len(matches) == 1:
            row = matches[0]
        elif len(matches) > 1:
            for m in matches:
                if str(m['code_barres']).endswith(q):
                    row = m
                    break
            if not row:
                row = matches[0]

    return dict(row) if row else None


# Alias rétrocompatible
find_produit_by_barcode_or_last4 = find_produit_by_ref_or_last4


def search_produits_by_designation(query: str, limit: int = 20) -> list:
    """
    Recherche des produits par leur désignation ou référence pour l'autocomplétion.
    Mets en priorité les produits dont la désignation commence par la chaîne saisie,
    puis ceux qui la contiennent.
    """
    q = query.strip()
    if not q:
        return []

    conn = get_connection()
    cursor = conn.cursor()
    like_prefix = f"{q}%"
    like_contains = f"%{q}%"

    cursor.execute("""
        SELECT p.*, f.nom as fournisseur_nom
        FROM produits p
        LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
        WHERE p.designation LIKE ? OR p.code_barres LIKE ?
        ORDER BY 
            CASE 
                WHEN p.designation LIKE ? THEN 1
                WHEN p.code_barres LIKE ? THEN 2
                ELSE 3
            END,
            p.designation ASC
        LIMIT ?
    """, (like_contains, like_contains, like_prefix, like_prefix, limit))

    rows = [dict(r) for r in cursor.fetchall()]
    return rows


def get_produit_by_id(produit_id: int) -> dict | None:
    """Retourne un produit par ID avec infos fournisseur."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, f.nom as fournisseur_nom, f.numero as fournisseur_numero
        FROM produits p
        LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
        WHERE p.id = ?
    """, (produit_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def ajouter_produit(data: dict) -> int:
    """Ajoute un nouveau produit. Si la référence existe déjà, ajoute automatiquement /1, /2..."""
    conn = get_connection()
    cursor = conn.cursor()

    base_ref = data['code_barres'].strip()

    # Chercher si la référence de base ou ses variantes /N existent déjà
    cursor.execute("SELECT code_barres FROM produits WHERE code_barres = ? OR code_barres LIKE ?",
                   (base_ref, f"{base_ref}/%"))
    existing = [row['code_barres'] for row in cursor.fetchall()]

    if existing:
        # Trouver le prochain suffixe disponible
        max_suffix = 0
        for ref in existing:
            if ref == base_ref:
                max_suffix = max(max_suffix, 0)
            elif ref.startswith(f"{base_ref}/"):
                try:
                    suffix = int(ref[len(base_ref) + 1:])
                    max_suffix = max(max_suffix, suffix)
                except ValueError:
                    pass
        data = dict(data)
        data['code_barres'] = f"{base_ref}/{max_suffix + 1}"

    cb = data.get('code_barres', '').strip()
    params = {
        'code_barres':            cb,
        'code_barres_reverse':    cb[::-1],
        'designation':            data.get('designation', '').strip(),
        'emplacement':            data.get('emplacement', ''),
        'quantite_stock':         data.get('quantite_stock', 0),
        'unite':                  data.get('unite', 'Unité'),
        'utilite_ligne':          data.get('utilite_ligne', 'Aucune'),
        'nom_machine':            data.get('nom_machine', 'N/A'),
        'seuil_alerte':           data.get('seuil_alerte', 5),
        'categorie_piece':        data.get('categorie_piece', 'Pièce de Rechange'),
        'fournisseur_id':         data.get('fournisseur_id'),
        'date_rechange_initiale': data.get('date_rechange_initiale', ''),
        'duree_vie':              data.get('duree_vie', ''),
        'prochaine_date_rechange': data.get('prochaine_date_rechange', ''),
    }

    cursor.execute("""
        INSERT INTO produits (code_barres, code_barres_reverse, designation, emplacement, quantite_stock,
                              unite, utilite_ligne, nom_machine, seuil_alerte, categorie_piece,
                              fournisseur_id, date_rechange_initiale, duree_vie, prochaine_date_rechange)
        VALUES (:code_barres, :code_barres_reverse, :designation, :emplacement, :quantite_stock,
                :unite, :utilite_ligne, :nom_machine, :seuil_alerte, :categorie_piece,
                :fournisseur_id, :date_rechange_initiale, :duree_vie, :prochaine_date_rechange)
    """, params)
    new_id = cursor.lastrowid
    conn.commit()
    return new_id


def modifier_produit(produit_id: int, data: dict):
    """Met à jour un produit existant."""
    conn = get_connection()
    cursor = conn.cursor()
    cb = data.get('code_barres', '').strip()
    params = {
        'code_barres':            cb,
        'code_barres_reverse':    cb[::-1],
        'designation':            data.get('designation', '').strip(),
        'emplacement':            data.get('emplacement', ''),
        'quantite_stock':         data.get('quantite_stock', 0),
        'unite':                  data.get('unite', 'Unité'),
        'utilite_ligne':          data.get('utilite_ligne', 'Aucune'),
        'nom_machine':            data.get('nom_machine', 'N/A'),
        'seuil_alerte':           data.get('seuil_alerte', 5),
        'categorie_piece':        data.get('categorie_piece', 'Pièce de Rechange'),
        'fournisseur_id':         data.get('fournisseur_id'),
        'date_rechange_initiale': data.get('date_rechange_initiale', ''),
        'duree_vie':              data.get('duree_vie', ''),
        'prochaine_date_rechange': data.get('prochaine_date_rechange', ''),
        'id':                     produit_id
    }
    cursor.execute("""
        UPDATE produits SET
            code_barres = :code_barres,
            code_barres_reverse = :code_barres_reverse,
            designation = :designation,
            emplacement = :emplacement,
            quantite_stock = :quantite_stock,
            unite = :unite,
            utilite_ligne = :utilite_ligne,
            nom_machine = :nom_machine,
            seuil_alerte = :seuil_alerte,
            categorie_piece = :categorie_piece,
            fournisseur_id = :fournisseur_id,
            date_rechange_initiale = :date_rechange_initiale,
            duree_vie = :duree_vie,
            prochaine_date_rechange = :prochaine_date_rechange
        WHERE id = :id
    """, params)
    conn.commit()


# ─────────────────────── FOURNISSEURS ───────────────────────

def get_all_fournisseurs(search: str = "") -> list:
    """Retourne la liste de tous les fournisseurs avec le nombre de produits rattachés."""
    conn = get_connection()
    cursor = conn.cursor()
    if search:
        like = f"%{search}%"
        cursor.execute("""
            SELECT f.*, COUNT(p.id) as nb_produits
            FROM fournisseurs f
            LEFT JOIN produits p ON p.fournisseur_id = f.id
            WHERE f.nom LIKE ? OR f.numero LIKE ? OR f.adresse LIKE ?
            GROUP BY f.id
            ORDER BY f.nom ASC
        """, (like, like, like))
    else:
        cursor.execute("""
            SELECT f.*, COUNT(p.id) as nb_produits
            FROM fournisseurs f
            LEFT JOIN produits p ON p.fournisseur_id = f.id
            GROUP BY f.id
            ORDER BY f.nom ASC
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_fournisseur_by_id(fournisseur_id: int) -> dict | None:
    """Retourne un fournisseur par son ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.*, COUNT(p.id) as nb_produits
        FROM fournisseurs f
        LEFT JOIN produits p ON p.fournisseur_id = f.id
        WHERE f.id = ?
        GROUP BY f.id
    """, (fournisseur_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def ajouter_fournisseur(data: dict) -> int:
    """Ajoute un nouveau fournisseur."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fournisseurs (nom, numero, adresse)
        VALUES (:nom, :numero, :adresse)
    """, {
        'nom': data.get('nom', '').strip(),
        'numero': data.get('numero', '').strip(),
        'adresse': data.get('adresse', '').strip()
    })
    fid = cursor.lastrowid
    conn.commit()
    conn.close()
    return fid


def modifier_fournisseur(fournisseur_id: int, data: dict):
    """Met à jour les informations d'un fournisseur."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE fournisseurs SET
            nom = :nom,
            numero = :numero,
            adresse = :adresse
        WHERE id = :id
    """, {
        'nom': data.get('nom', '').strip(),
        'numero': data.get('numero', '').strip(),
        'adresse': data.get('adresse', '').strip(),
        'id': fournisseur_id
    })
    conn.commit()
    conn.close()


def supprimer_fournisseur(fournisseur_id: int):
    """Supprime un fournisseur (les produits rattachés verront leur fournisseur_id passer à NULL)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE produits SET fournisseur_id = NULL WHERE fournisseur_id = ?", (fournisseur_id,))
    cursor.execute("DELETE FROM fournisseurs WHERE id = ?", (fournisseur_id,))
    conn.commit()
    conn.close()


def get_produits_par_fournisseur(fournisseur_id: int) -> list:
    """
    Retourne la liste des produits associés à ce fournisseur.
    Inclus la date d'ajout/dernier mouvement, désignation, quantité.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.code_barres, p.designation, p.quantite_stock, p.unite,
               COALESCE(MAX(m.date_heure), 'Enregistré') as date_derniere_livraison
        FROM produits p
        LEFT JOIN mouvements m ON m.produit_id = p.id AND m.type_mouvement = 'ENTREE'
        WHERE p.fournisseur_id = ?
        GROUP BY p.id
        ORDER BY p.designation ASC
    """, (fournisseur_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_produits_alertes_rechange() -> list:
    """
    Retourne les pièces de rechange nécessitant un remplacement ou une révision proche.
    Alerte ROUGE : prochaine_date_rechange <= aujourd'hui (jours_restants <= 0)
    Alerte ORANGE : prochaine_date_rechange dans moins de 30 jours (0 < jours_restants <= 30)
    Trie en priorité par ROUGE puis ORANGE.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, f.nom as fournisseur_nom
        FROM produits p
        LEFT JOIN fournisseurs f ON p.fournisseur_id = f.id
        WHERE p.prochaine_date_rechange IS NOT NULL 
          AND p.prochaine_date_rechange != ''
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    results = []
    today = datetime.now().date()

    for p in rows:
        date_str = p['prochaine_date_rechange'].strip()
        try:
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    if len(parts[2]) == 4:
                        dt = datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
                    else:
                        dt = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
                else:
                    continue
            else:
                dt = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        except ValueError:
            continue

        delta_days = (dt - today).days

        if delta_days <= 0:
            statut = 'ROUGE'
        elif delta_days <= 30:
            statut = 'ORANGE'
        else:
            statut = 'OK'

        if statut in ('ROUGE', 'ORANGE'):
            p['jours_restants'] = delta_days
            p['statut_alerte'] = statut
            p['date_echeance_fmt'] = dt.strftime('%d/%m/%Y')
            results.append(p)

    priority = {'ROUGE': 0, 'ORANGE': 1}
    results.sort(key=lambda x: (priority[x['statut_alerte']], x['jours_restants']))
    return results


def supprimer_produit(produit_id: int):
    """Supprime un produit et ses mouvements associés."""
    conn = get_connection()
    conn.execute("DELETE FROM produits WHERE id = ?", (produit_id,))
    conn.commit()
    conn.close()


def get_produits_en_alerte() -> list:
    """Retourne les produits dont le stock <= seuil_alerte."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM produits
        WHERE quantite_stock <= seuil_alerte
        ORDER BY quantite_stock ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_stats_dashboard() -> dict:
    """Retourne les statistiques pour le tableau de bord."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM produits")
    total_refs = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as alertes FROM produits WHERE quantite_stock <= seuil_alerte")
    nb_alertes = cursor.fetchone()['alertes']

    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) as nb FROM mouvements
        WHERE date(date_heure) = ?
    """, (today,))
    mvt_today = cursor.fetchone()['nb']

    conn.close()
    return {
        'total_refs': total_refs,
        'nb_alertes': nb_alertes,
        'mvt_today': mvt_today
    }


# ─────────────────────── MOUVEMENTS ───────────────────────

def get_derniers_mouvements(limit: int = 20) -> list:
    """Retourne les derniers mouvements avec infos produit."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, p.designation, p.code_barres, p.unite
        FROM mouvements m
        JOIN produits p ON m.produit_id = p.id
        ORDER BY m.date_heure DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_mouvements_count(type_filtre: str = None, date_debut: str = None, date_fin: str = None) -> int:
    """Retourne le nombre total de mouvements correspondant aux filtres."""
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) as total FROM mouvements m JOIN produits p ON m.produit_id = p.id WHERE 1=1"
    params = []
    if type_filtre:
        query += " AND m.type_mouvement = ?"
        params.append(type_filtre)
    if date_debut:
        query += " AND date(m.date_heure) >= ?"
        params.append(date_debut)
    if date_fin:
        query += " AND date(m.date_heure) <= ?"
        params.append(date_fin)
    cursor.execute(query, params)
    res = cursor.fetchone()
    return res['total'] if res else 0


def get_all_mouvements(type_filtre: str = None, date_debut: str = None, date_fin: str = None,
                         limit: int = None, offset: int = 0) -> list:
    """Retourne les mouvements avec filtres optionnels et pagination."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT m.*, p.designation, p.code_barres, p.unite
        FROM mouvements m
        JOIN produits p ON m.produit_id = p.id
        WHERE 1=1
    """
    params = []
    if type_filtre:
        query += " AND m.type_mouvement = ?"
        params.append(type_filtre)
    if date_debut:
        query += " AND date(m.date_heure) >= ?"
        params.append(date_debut)
    if date_fin:
        query += " AND date(m.date_heure) <= ?"
        params.append(date_fin)

    query += " ORDER BY m.date_heure DESC, m.id DESC"

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, max(0, offset)])

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    return rows


def enregistrer_mouvement(produit_id: int, type_mvt: str, quantite: int,
                          beneficiaire: str, motif: str, chemin_pdf: str = "",
                          demandeur: str = "", retourne_par: str = "") -> int:
    """
    Enregistre un mouvement (ENTREE, SORTIE, RETOUR) et met à jour le stock.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO mouvements (produit_id, type_mouvement, quantite,
                                beneficiaire_service, motif, chemin_pdf, demandeur, retourne_par)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (produit_id, type_mvt, quantite, beneficiaire, motif, chemin_pdf, demandeur, retourne_par))
    mvt_id = cursor.lastrowid

    if type_mvt in ('ENTREE', 'RETOUR'):
        cursor.execute("UPDATE produits SET quantite_stock = quantite_stock + ? WHERE id = ?",
                       (quantite, produit_id))
    elif type_mvt == 'SORTIE':
        cursor.execute("UPDATE produits SET quantite_stock = MAX(0, quantite_stock - ?) WHERE id = ?",
                       (quantite, produit_id))

    conn.commit()
    conn.close()
    return mvt_id


def enregistrer_mouvements_multiples(articles: list, type_mvt: str, beneficiaire: str,
                                      motif: str, chemin_pdf: str = "",
                                      demandeur: str = "", retourne_par: str = "",
                                      fournisseur_nom: str = "") -> list:
    """
    Enregistre plusieurs lignes de mouvements (Réception multi-lignes).
    Chaque article peut être un produit existant OU être auto-créé s'il n'existe pas encore.
    articles = [{'reference': str, 'designation': str, 'quantite': int}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    mvt_ids = []

    # Résoudre le fournisseur_id à partir du nom une seule fois
    fournisseur_id = None
    if fournisseur_nom:
        row_f = cursor.execute(
            "SELECT id FROM fournisseurs WHERE nom = ? COLLATE NOCASE", (fournisseur_nom,)
        ).fetchone()
        if row_f:
            fournisseur_id = row_f['id']

    for art in articles:
        ref = art.get('reference') or art.get('code_barres', '')
        designation = art.get('designation', 'Produit')
        qte = int(art.get('quantite', 1))

        utilite_ligne = art.get('utilite_ligne', 'Aucune')
        nom_machine = art.get('nom_machine', 'N/A')

        # Vérifier si le produit existe par référence
        cursor.execute("SELECT id FROM produits WHERE code_barres = ?", (ref,))
        row = cursor.fetchone()

        if row:
            pid = row['id']
            # Mettre à jour désignation, ligne, machine et fournisseur
            if fournisseur_id:
                cursor.execute("""
                    UPDATE produits
                    SET designation = ?, utilite_ligne = ?, nom_machine = ?, fournisseur_id = ?
                    WHERE id = ?
                """, (designation, utilite_ligne, nom_machine, fournisseur_id, pid))
            else:
                cursor.execute("""
                    UPDATE produits
                    SET designation = ?, utilite_ligne = ?, nom_machine = ?
                    WHERE id = ?
                """, (designation, utilite_ligne, nom_machine, pid))
        else:
            if type_mvt == 'SORTIE':
                raise ValueError(f"Cet article ({ref} - {designation}) n'est pas disponible en stock.")

            # Auto-créer le produit avec le fournisseur (ENTREE / RETOUR)
            cursor.execute("""
                INSERT INTO produits (code_barres, code_barres_reverse, designation, quantite_stock, unite, utilite_ligne, nom_machine, seuil_alerte, fournisseur_id)
                VALUES (?, ?, ?, 0, ?, ?, ?, 5, ?)
            """, (ref, ref[::-1], designation, art.get('unite', 'Unité'), utilite_ligne, nom_machine, fournisseur_id))
            pid = cursor.lastrowid

        cursor.execute("""
            INSERT INTO mouvements (produit_id, type_mouvement, quantite,
                                    beneficiaire_service, motif, chemin_pdf, demandeur, retourne_par)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (pid, type_mvt, qte, beneficiaire, motif, chemin_pdf, demandeur, retourne_par))
        mvt_ids.append(cursor.lastrowid)

        if type_mvt in ('ENTREE', 'RETOUR'):
            cursor.execute("UPDATE produits SET quantite_stock = quantite_stock + ? WHERE id = ?",
                           (qte, pid))
        elif type_mvt == 'SORTIE':
            cursor.execute("UPDATE produits SET quantite_stock = MAX(0, quantite_stock - ?) WHERE id = ?",
                           (qte, pid))

    conn.commit()
    conn.close()
    return mvt_ids


def update_mouvement(mvt_id: int, date_heure: str = None, quantite: int = None,
                     beneficiaire_service: str = None, motif: str = None,
                     demandeur: str = None, retourne_par: str = None,
                     chemin_pdf: str = None) -> bool:
    """
    Met à jour un mouvement existant et réajuste le stock si la quantité a été modifiée.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM mouvements WHERE id = ?", (mvt_id,))
    row = cursor.fetchone()
    if not row:
        return False

    old_mvt = dict(row)
    pid = old_mvt['produit_id']
    type_mvt = old_mvt['type_mouvement']
    old_qte = old_mvt['quantite']

    # Ajustement du stock si la quantité a changé
    if quantite is not None and quantite != old_qte:
        diff = quantite - old_qte
        if type_mvt in ('ENTREE', 'RETOUR'):
            cursor.execute("UPDATE produits SET quantite_stock = MAX(0, quantite_stock + ?) WHERE id = ?",
                           (diff, pid))
        elif type_mvt == 'SORTIE':
            cursor.execute("UPDATE produits SET quantite_stock = MAX(0, quantite_stock - ?) WHERE id = ?",
                           (diff, pid))

    updates = []
    params = []

    if date_heure is not None:
        updates.append("date_heure = ?")
        params.append(date_heure)
    if quantite is not None:
        updates.append("quantite = ?")
        params.append(quantite)
    if beneficiaire_service is not None:
        updates.append("beneficiaire_service = ?")
        params.append(beneficiaire_service)
    if motif is not None:
        updates.append("motif = ?")
        params.append(motif)
    if demandeur is not None:
        updates.append("demandeur = ?")
        params.append(demandeur)
    if retourne_par is not None:
        updates.append("retourne_par = ?")
        params.append(retourne_par)
    if chemin_pdf is not None:
        updates.append("chemin_pdf = ?")
        params.append(chemin_pdf)

    if updates:
        query = f"UPDATE mouvements SET {', '.join(updates)} WHERE id = ?"
        params.append(mvt_id)
        cursor.execute(query, params)
        conn.commit()

    return True


# ─────────────────────── PRODUITS ENGINS (CAMION & CLARCK) ───────────────────────

def _ensure_engins_table(conn: sqlite3.Connection):
    """S'assure que la table produits_engins existe."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produits_engins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_engin TEXT NOT NULL,
            reference TEXT UNIQUE NOT NULL,
            marque TEXT NOT NULL,
            designation TEXT NOT NULL,
            quantite_stock INTEGER DEFAULT 0,
            seuil_alerte INTEGER DEFAULT 5,
            date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def get_all_produits_engins(search: str = "", type_filter: str = "Tous") -> list:
    """Retourne tous les produits engins avec filtrage optionnel (Camion, Clarck)."""
    conn = get_connection()
    _ensure_engins_table(conn)
    cursor = conn.cursor()
    query = "SELECT * FROM produits_engins WHERE 1=1"
    params = []

    if type_filter and type_filter != "Tous":
        query += " AND type_engin = ?"
        params.append(type_filter)

    if search:
        like = f"%{search}%"
        query += " AND (reference LIKE ? OR designation LIKE ? OR marque LIKE ?)"
        params.extend([like, like, like])

    query += " ORDER BY designation"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_produit_engin_by_id(engin_id: int) -> dict | None:
    """Retourne un produit engin par ID."""
    conn = get_connection()
    _ensure_engins_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits_engins WHERE id = ?", (engin_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def ajouter_produit_engin(data: dict) -> int:
    """Ajoute un produit engin (Camion / Clarck)."""
    conn = get_connection()
    _ensure_engins_table(conn)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO produits_engins (type_engin, reference, marque, designation, quantite_stock, seuil_alerte)
        VALUES (:type_engin, :reference, :marque, :designation, :quantite_stock, :seuil_alerte)
    """, data)
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def modifier_produit_engin(engin_id: int, data: dict):
    """Modifie un produit engin."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE produits_engins SET
            type_engin = :type_engin,
            reference = :reference,
            marque = :marque,
            designation = :designation,
            quantite_stock = :quantite_stock,
            seuil_alerte = :seuil_alerte
        WHERE id = :id
    """, {**data, 'id': engin_id})
    conn.commit()
    conn.close()


def supprimer_produit_engin(engin_id: int):
    """Supprime un produit engin."""
    conn = get_connection()
    conn.execute("DELETE FROM produits_engins WHERE id = ?", (engin_id,))
    conn.commit()
    conn.close()


def update_chemin_pdf(mvt_id: int, chemin_pdf: str):
    """Met à jour le chemin PDF d'un mouvement."""
    conn = get_connection()
    conn.execute("UPDATE mouvements SET chemin_pdf = ? WHERE id = ?", (chemin_pdf, mvt_id))
    conn.commit()
    conn.close()


def get_num_document(type_mvt: str) -> str:
    """Génère un numéro de document unique (BS, BR, BT ou BC)."""
    conn = get_connection()
    cursor = conn.cursor()
    prefix_map = {'SORTIE': 'BS', 'ENTREE': 'BR', 'RETOUR': 'BT', 'COMMANDE': 'BC'}
    prefix = prefix_map.get(type_mvt, 'DOC')
    year = datetime.now().strftime('%Y')

    if type_mvt == 'COMMANDE':
        # Basé sur la date/heure pour unicité
        ts = datetime.now().strftime('%m%d%H%M')
        conn.close()
        return f"BC-{year}-{ts}"

    cursor.execute("""
        SELECT COUNT(*) as nb FROM mouvements
        WHERE type_mouvement = ? AND strftime('%Y', date_heure) = ?
    """, (type_mvt, year))
    nb = cursor.fetchone()['nb'] + 1
    conn.close()
    return f"{prefix}-{year}-{nb:04d}"


def get_inventaire_par_periode(date_debut: str, date_fin: str) -> list:
    """
    Retourne la liste des journées dans la plage [date_debut, date_fin].
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            date(date_heure) as jour,
            SUM(CASE WHEN type_mouvement = 'ENTREE' THEN quantite ELSE 0 END) as total_entrees,
            SUM(CASE WHEN type_mouvement = 'SORTIE' THEN quantite ELSE 0 END) as total_sorties,
            SUM(CASE WHEN type_mouvement = 'RETOUR' THEN quantite ELSE 0 END) as total_retours,
            COUNT(id) as nb_mouvements
        FROM mouvements
        WHERE date(date_heure) >= date(?) AND date(date_heure) <= date(?)
        GROUP BY date(date_heure)
        ORDER BY jour DESC
    """, (date_debut, date_fin))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_mouvements_journee(date_jour: str) -> list:
    """Retourne les détails de tous les mouvements d'une journée donnée (YYYY-MM-DD)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, p.code_barres, p.designation, p.emplacement, p.unite, p.quantite_stock
        FROM mouvements m
        JOIN produits p ON m.produit_id = p.id
        WHERE date(m.date_heure) = date(?)
        ORDER BY m.date_heure ASC
    """, (date_jour,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def backup_database(destination: str) -> bool:
    """Sauvegarde la base de données vers un fichier destination."""
    try:
        import shutil
        src = get_db_path()
        shutil.copy2(src, destination)
        return True
    except Exception as e:
        print(f"[DB] Erreur sauvegarde : {e}")
        return False


def reset_database():
    """Réinitialise complètement la base de données (supprime et recrée toutes les tables)."""
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM mouvements")
    conn.execute("DELETE FROM produits")
    conn.execute("DELETE FROM sqlite_sequence")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print("[DB] Base de données réinitialisée.")


def get_available_months_mouvements() -> list:
    """Retourne la liste des mois (YYYY-MM) ayant au moins un mouvement."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT strftime('%Y-%m', date_heure) as ym
        FROM mouvements
        WHERE date_heure IS NOT NULL
        ORDER BY ym DESC
    """)
    months = [row['ym'] for row in cursor.fetchall() if row['ym']]
    conn.close()

    current_ym = datetime.now().strftime('%Y-%m')
    if current_ym not in months:
        months.insert(0, current_ym)
    return months


def get_stats_mouvements_mois(year_month: str) -> dict:
    """Retourne les totaux quotidiens pour un mois donné (format 'YYYY-MM')."""
    import calendar
    try:
        y, m = map(int, year_month.split('-'))
        _, num_days = calendar.monthrange(y, m)
    except Exception:
        now = datetime.now()
        y, m = now.year, now.month
        _, num_days = calendar.monthrange(y, m)
        year_month = f"{y:04d}-{m:02d}"

    days_entrees = {d: 0 for d in range(1, num_days + 1)}
    days_sorties = {d: 0 for d in range(1, num_days + 1)}
    days_retours = {d: 0 for d in range(1, num_days + 1)}

    conn = get_connection()
    cursor = conn.cursor()
    # Compter le NOMBRE de mouvements (pas les quantités)
    cursor.execute("""
        SELECT CAST(strftime('%d', date_heure) AS INTEGER) as day,
               type_mouvement,
               COUNT(id) as nb_mvt
        FROM mouvements
        WHERE strftime('%Y-%m', date_heure) = ?
        GROUP BY day, type_mouvement
    """, (year_month,))

    for row in cursor.fetchall():
        d = row['day']
        t_type = row['type_mouvement']
        nb = row['nb_mvt'] or 0
        if d in days_entrees:
            if t_type == 'ENTREE':
                days_entrees[d] += nb
            elif t_type == 'SORTIE':
                days_sorties[d] += nb
            elif t_type == 'RETOUR':
                days_retours[d] += nb

    conn.close()

    return {
        'year_month': year_month,
        'num_days': num_days,
        'days': list(range(1, num_days + 1)),
        'entrees': [days_entrees[d] for d in range(1, num_days + 1)],
        'sorties': [days_sorties[d] for d in range(1, num_days + 1)],
        'retours': [days_retours[d] for d in range(1, num_days + 1)],
        'total_entrees': sum(days_entrees.values()),
        'total_sorties': sum(days_sorties.values()),
        'total_retours': sum(days_retours.values())
    }


# ─────────────────────── OUTILLAGE ───────────────────────

def _ensure_outillage_table(conn: sqlite3.Connection):
    """S'assure que la table outillage existe."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outillage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            designation TEXT NOT NULL,
            marque TEXT DEFAULT '',
            numero_outillage TEXT NOT NULL,
            quantite INTEGER DEFAULT 1,
            statut TEXT DEFAULT 'Dans le magasin',
            date_ajout DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def get_all_outillages(search: str = "", statut_filter: str = "Tous") -> list:
    """
    Retourne tous les outillages avec recherche et filtrage par statut.
    Enrichit chaque ligne avec 'quantite_dehors_actuelle' calculée dynamiquement.
    """
    conn = get_connection()
    _ensure_outillage_table(conn)
    _ensure_sorties_outillage_table(conn)
    cursor = conn.cursor()

    if statut_filter == "Dans le magasin":
        query = """
            SELECT * FROM outillage
            WHERE quantite > 0
        """
        params = []
    elif statut_filter == "En dehors du magasin":
        query = """
            SELECT DISTINCT o.* FROM outillage o
            WHERE o.statut != 'Dans le magasin'
               OR o.quantite <= 0
               OR EXISTS (
                   SELECT 1 FROM sorties_outillage s
                   WHERE s.outillage_id = o.id AND s.statut = 'EN_COURS'
               )
        """
        params = []
    else:
        query = "SELECT * FROM outillage WHERE 1=1"
        params = []

    if search:
        like = f"%{search}%"
        query += " AND (designation LIKE ? OR marque LIKE ? OR numero_outillage LIKE ?)"
        params.extend([like, like, like])

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # Enrichir chaque ligne avec quantite_dehors_actuelle
    for row in rows:
        try:
            cursor.execute("""
                SELECT COALESCE(SUM(quantite_sortie - quantite_retournee), 0) as qd
                FROM sorties_outillage
                WHERE outillage_id = ? AND statut = 'EN_COURS'
            """, (row['id'],))
            res = cursor.fetchone()
            qd = int(res['qd']) if res and res['qd'] else 0
        except Exception:
            qd = 0
        if qd == 0 and row.get('statut') != 'Dans le magasin':
            qd = max(row.get('quantite', 0), 1)
        row['quantite_dehors_actuelle'] = qd

    return rows


def get_outillage_stats() -> dict:
    """
    Retourne les statistiques calculées automatiquement pour l'outillage :
    - total_types: Nombre de références d'outils
    - total_quantite: Quantité globale cumulée
    - quantite_magasin: Quantité actuellement disponible dans le magasin
    - quantite_dehors: Quantité actuellement sortie / en dehors du magasin
    - nb_sorties_en_cours: Nombre d'emprunts actifs non restitués
    """
    conn = get_connection()
    _ensure_outillage_table(conn)
    _ensure_sorties_outillage_table(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total_types, COALESCE(SUM(quantite), 0) as total_quantite FROM outillage")
    row_total = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(quantite), 0) as dans_magasin
        FROM outillage
        WHERE statut = 'Dans le magasin' AND quantite > 0
    """)
    row_dans = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(s.quantite_sortie - s.quantite_retournee), 0) as en_dehors
        FROM sorties_outillage s
        JOIN outillage o ON s.outillage_id = o.id
        WHERE s.statut = 'EN_COURS'
    """)
    row_sorties = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(s.id) as nb_sorties
        FROM sorties_outillage s
        JOIN outillage o ON s.outillage_id = o.id
        WHERE s.statut = 'EN_COURS'
    """)
    row_nb_sorties = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(quantite), 0) as orphan_dehors
        FROM outillage
        WHERE (statut != 'Dans le magasin' OR quantite <= 0)
    """)
    row_orphan = cursor.fetchone()

    qte_dehors = max(row_sorties['en_dehors'], row_orphan['orphan_dehors'])
    qte_magasin = row_dans['dans_magasin']
    total_qte = qte_magasin + qte_dehors

    return {
        'total_types': row_total['total_types'],
        'total_quantite': max(row_total['total_quantite'], total_qte),
        'quantite_magasin': qte_magasin,
        'quantite_dehors': qte_dehors,
        'nb_sorties_en_cours': row_nb_sorties['nb_sorties']
    }


def get_outillage_by_id(tool_id: int) -> dict | None:
    """Retourne un outillage par ID."""
    conn = get_connection()
    _ensure_outillage_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM outillage WHERE id = ?", (tool_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def ajouter_outillage(data: dict) -> int:
    """Ajoute un nouvel outillage."""
    conn = get_connection()
    _ensure_outillage_table(conn)
    cursor = conn.cursor()

    params = {
        'designation':      data.get('designation', '').strip(),
        'marque':           data.get('marque', '').strip(),
        'numero_outillage': data.get('numero_outillage', '').strip(),
        'quantite':         data.get('quantite', 1),
        'statut':           data.get('statut', 'Dans le magasin')
    }

    cursor.execute("""
        INSERT INTO outillage (designation, marque, numero_outillage, quantite, statut)
        VALUES (:designation, :marque, :numero_outillage, :quantite, :statut)
    """, params)
    new_id = cursor.lastrowid
    conn.commit()
    return new_id


def modifier_outillage(tool_id: int, data: dict):
    """Met à jour un outillage existant."""
    conn = get_connection()
    _ensure_outillage_table(conn)
    cursor = conn.cursor()

    params = {
        'designation':      data.get('designation', '').strip(),
        'marque':           data.get('marque', '').strip(),
        'numero_outillage': data.get('numero_outillage', '').strip(),
        'quantite':         data.get('quantite', 1),
        'statut':           data.get('statut', 'Dans le magasin'),
        'id':               tool_id
    }

    cursor.execute("""
        UPDATE outillage SET
            designation = :designation,
            marque = :marque,
            numero_outillage = :numero_outillage,
            quantite = :quantite,
            statut = :statut
        WHERE id = :id
    """, params)
    conn.commit()


def supprimer_outillage(tool_id: int):
    """Supprime un outillage et ses éventuels mouvements d'emprunt associés."""
    conn = get_connection()
    _ensure_outillage_table(conn)
    _ensure_sorties_outillage_table(conn)
    conn.execute("DELETE FROM sorties_outillage WHERE outillage_id = ?", (tool_id,))
    conn.execute("DELETE FROM outillage WHERE id = ?", (tool_id,))
    conn.commit()


def changer_statut_outillage(tool_id: int, nouveau_statut: str):
    """Bascule le statut d'un outillage ('Dans le magasin' ou 'En dehors du magasin')."""
    conn = get_connection()
    _ensure_outillage_table(conn)
    conn.execute("UPDATE outillage SET statut = ? WHERE id = ?", (nouveau_statut, tool_id))
    conn.commit()


def _ensure_sorties_outillage_table(conn: sqlite3.Connection):
    """S'assure que la table sorties_outillage existe et nettoie les orphelins."""
    _ensure_outillage_table(conn)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sorties_outillage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outillage_id INTEGER NOT NULL,
            demandeur TEXT NOT NULL,
            quantite_sortie INTEGER NOT NULL,
            quantite_retournee INTEGER DEFAULT 0,
            motif TEXT DEFAULT '',
            date_sortie DATETIME DEFAULT CURRENT_TIMESTAMP,
            date_retour DATETIME,
            statut TEXT DEFAULT 'EN_COURS',
            FOREIGN KEY (outillage_id) REFERENCES outillage(id) ON DELETE CASCADE
        )
    """)
    conn.execute("DELETE FROM sorties_outillage WHERE outillage_id NOT IN (SELECT id FROM outillage)")
    conn.commit()


def enregistrer_sortie_outillage(tool_id: int, demandeur: str, quantite: int, motif: str = "") -> int:
    """
    Enregistre une sortie d'outillage pour un demandeur et réduit le stock de l'outillage.
    Lève ValueError si l'outil n'existe pas, s'il est en dehors du magasin ou si la quantité disponible est insuffisante.
    """
    if quantite <= 0:
        raise ValueError("La quantité sortie doit être supérieure à zéro.")
    if not demandeur.strip():
        raise ValueError("Le nom du demandeur est obligatoire.")

    conn = get_connection()
    _ensure_sorties_outillage_table(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM outillage WHERE id = ?", (tool_id,))
    tool = cursor.fetchone()
    if not tool:
        raise ValueError("L'outil sélectionné n'existe pas dans la base de données.")

    if tool['statut'] == 'En dehors du magasin':
        raise ValueError("Cet outillage est actuellement en dehors du magasin. Impossible d'effectuer une nouvelle sortie.")

    stock_actuel = tool['quantite']
    if quantite > stock_actuel:
        raise ValueError(f"Stock insuffisant : {stock_actuel} disponible(s), {quantite} demandé(s).")

    nouveau_stock = stock_actuel - quantite
    nouveau_statut = 'En dehors du magasin' if nouveau_stock == 0 else 'Dans le magasin'
    date_sortie_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        INSERT INTO sorties_outillage (outillage_id, demandeur, quantite_sortie, quantite_retournee, motif, date_sortie, statut)
        VALUES (?, ?, ?, 0, ?, ?, 'EN_COURS')
    """, (tool_id, demandeur.strip(), quantite, motif.strip(), date_sortie_local))
    sortie_id = cursor.lastrowid

    cursor.execute("""
        UPDATE outillage SET quantite = ?, statut = ? WHERE id = ?
    """, (nouveau_stock, nouveau_statut, tool_id))

    conn.commit()
    return sortie_id


def get_sorties_outillage_en_cours(tool_id: int = None) -> list:
    """
    Retourne les sorties d'outillages non encore intégralement restituées (statut = 'EN_COURS').
    Inclut également tous les outillages marqués hors magasin ou sélectionnés pour restitution.
    """
    conn = get_connection()
    _ensure_sorties_outillage_table(conn)
    cursor = conn.cursor()

    query = """
        SELECT s.*, o.designation, o.numero_outillage, o.marque,
               (s.quantite_sortie - s.quantite_retournee) as quantite_restante
        FROM sorties_outillage s
        JOIN outillage o ON s.outillage_id = o.id
        WHERE s.statut = 'EN_COURS'
    """
    params = []
    if tool_id is not None:
        query += " AND s.outillage_id = ?"
        params.append(tool_id)

    query += " ORDER BY s.date_sortie DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    active_tool_ids = {r['outillage_id'] for r in rows}

    # Récupérer les outils marqués 'En dehors' ou avec stock 0 n'ayant pas de ligne d'emprunt active
    query_orphans = "SELECT * FROM outillage WHERE (statut != 'Dans le magasin' OR statut LIKE '%dehors%' OR quantite <= 0)"
    params_orphans = []
    if tool_id is not None:
        query_orphans += " AND id = ?"
        params_orphans.append(tool_id)

    cursor.execute(query_orphans, params_orphans)
    orphans = [dict(r) for r in cursor.fetchall()]

    for o in orphans:
        if o['id'] not in active_tool_ids:
            qte = max(1, o['quantite'])
            rows.append({
                'id': f"fallback_{o['id']}",
                'outillage_id': o['id'],
                'demandeur': 'Sortie hors magasin',
                'quantite_sortie': qte,
                'quantite_retournee': 0,
                'quantite_restante': qte,
                'motif': 'Statut Hors Magasin',
                'date_sortie': o.get('date_ajout', ''),
                'date_retour': None,
                'statut': 'EN_COURS',
                'designation': o['designation'],
                'numero_outillage': o['numero_outillage'],
                'marque': o.get('marque') or '-'
            })
            active_tool_ids.add(o['id'])

    # Si un tool_id spécifique a été demandé et n'est toujours pas dans la liste, l'inclure impérativement
    if tool_id is not None and tool_id not in active_tool_ids:
        cursor.execute("SELECT * FROM outillage WHERE id = ?", (tool_id,))
        t_spec = cursor.fetchone()
        if t_spec:
            t_dict = dict(t_spec)
            qte = max(1, t_dict['quantite'])
            rows.append({
                'id': f"fallback_{t_dict['id']}",
                'outillage_id': t_dict['id'],
                'demandeur': 'Restitution manuelle',
                'quantite_sortie': qte,
                'quantite_retournee': 0,
                'quantite_restante': qte,
                'motif': 'Restitution directe',
                'date_sortie': t_dict.get('date_ajout', ''),
                'date_retour': None,
                'statut': 'EN_COURS',
                'designation': t_dict['designation'],
                'numero_outillage': t_dict['numero_outillage'],
                'marque': t_dict.get('marque') or '-'
            })

    return rows


def enregistrer_retour_outillage(sortie_id, quantite_retour: int) -> bool:
    """
    Enregistre le retour (restitution) d'un outillage sorti et réintègre la quantité au stock.
    Gère aussi bien les sorties BDD réelles que les sorties réétiquetées (fallback_ID).
    """
    if quantite_retour <= 0:
        raise ValueError("La quantité retournée doit être supérieure à zéro.")

    conn = get_connection()
    _ensure_sorties_outillage_table(conn)
    cursor = conn.cursor()

    date_actuelle = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if isinstance(sortie_id, str) and sortie_id.startswith('fallback_'):
        tool_id = int(sortie_id.replace('fallback_', ''))
        cursor.execute("SELECT * FROM outillage WHERE id = ?", (tool_id,))
        tool = cursor.fetchone()
        if not tool:
            raise ValueError("L'outillage sélectionné n'existe plus.")

        qte_actuelle = tool['quantite']
        nouveau_stock = qte_actuelle + quantite_retour

        cursor.execute("""
            INSERT INTO sorties_outillage (outillage_id, demandeur, quantite_sortie, quantite_retournee, motif, date_sortie, date_retour, statut)
            VALUES (?, 'Restitution Hors Magasin', ?, ?, 'Restitution Manuelle', ?, ?, 'RETOURNÉ')
        """, (tool_id, quantite_retour, quantite_retour, date_actuelle, date_actuelle))

        cursor.execute("UPDATE outillage SET quantite = ?, statut = 'Dans le magasin' WHERE id = ?",
                       (nouveau_stock, tool_id))
        conn.commit()
        return True

    sortie_id_int = int(sortie_id)
    cursor.execute("SELECT * FROM sorties_outillage WHERE id = ?", (sortie_id_int,))
    sortie = cursor.fetchone()
    if not sortie:
        raise ValueError("La sortie spécifiée n'existe pas.")

    if sortie['statut'] != 'EN_COURS':
        raise ValueError("Cette sortie a déjà été intégralement retournée.")

    restant = sortie['quantite_sortie'] - sortie['quantite_retournee']
    if quantite_retour > restant:
        raise ValueError(f"La quantité retournée ({quantite_retour}) dépasse la quantité restante à restituer ({restant}).")

    nouvelle_qte_retournee = sortie['quantite_retournee'] + quantite_retour
    nouveau_statut = 'RETOURNÉ' if nouvelle_qte_retournee >= sortie['quantite_sortie'] else 'EN_COURS'
    date_retour_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if nouveau_statut == 'RETOURNÉ' else sortie['date_retour']

    cursor.execute("""
        UPDATE sorties_outillage
        SET quantite_retournee = ?, statut = ?, date_retour = ?
        WHERE id = ?
    """, (nouvelle_qte_retournee, nouveau_statut, date_retour_val, sortie_id_int))

    tool_id = sortie['outillage_id']
    cursor.execute("SELECT quantite FROM outillage WHERE id = ?", (tool_id,))
    tool_row = cursor.fetchone()
    qte_actuelle = tool_row['quantite'] if tool_row else 0
    nouveau_stock = qte_actuelle + quantite_retour

    cursor.execute("UPDATE outillage SET quantite = ?, statut = 'Dans le magasin' WHERE id = ?",
                   (nouveau_stock, tool_id))

    conn.commit()
    return True


def get_historique_sorties_outillage(search: str = "") -> list:
    """
    Retourne l'historique de toutes les sorties/prêts d'outillages (en cours et retournés).
    """
    conn = get_connection()
    _ensure_sorties_outillage_table(conn)
    cursor = conn.cursor()

    query = """
        SELECT s.*, o.designation, o.numero_outillage, o.marque,
               (s.quantite_sortie - s.quantite_retournee) as quantite_restante
        FROM sorties_outillage s
        JOIN outillage o ON s.outillage_id = o.id
        WHERE 1=1
    """
    params = []
    if search:
        like = f"%{search}%"
        query += " AND (s.demandeur LIKE ? OR o.designation LIKE ? OR o.numero_outillage LIKE ? OR s.statut LIKE ?)"
        params.extend([like, like, like, like])

    query += " ORDER BY s.id DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    return rows


