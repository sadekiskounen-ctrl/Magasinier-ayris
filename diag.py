import sys
sys.path.insert(0, '.')
from database.db_manager import get_connection, _ensure_outillage_table, _ensure_sorties_outillage_table

conn = get_connection()
_ensure_outillage_table(conn)
_ensure_sorties_outillage_table(conn)
cursor = conn.cursor()

print("=== TOUS LES OUTILLAGES ===")
cursor.execute("SELECT id, designation, statut, quantite FROM outillage")
for r in cursor.fetchall():
    print(dict(r))

print()
print("=== SORTIES EN COURS ===")
cursor.execute("SELECT outillage_id, demandeur, quantite_sortie, quantite_retournee, statut FROM sorties_outillage WHERE statut='EN_COURS'")
for r in cursor.fetchall():
    print(dict(r))

print()
print("=== FILTRE EN DEHORS (actuel) ===")
cursor.execute("SELECT id, designation, statut, quantite FROM outillage WHERE NOT (statut = 'Dans le magasin' AND quantite > 0)")
for r in cursor.fetchall():
    print(dict(r))

print()
print("=== FILTRE LARGE (avec EXISTS) ===")
cursor.execute("""
    SELECT id, designation, statut, quantite FROM outillage
    WHERE (statut != 'Dans le magasin' OR quantite <= 0
           OR EXISTS (SELECT 1 FROM sorties_outillage s WHERE s.outillage_id = outillage.id AND s.statut = 'EN_COURS'))
""")
for r in cursor.fetchall():
    print(dict(r))
