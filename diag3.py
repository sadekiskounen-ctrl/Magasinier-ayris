import sys
sys.path.insert(0, '.')
from database.db_manager import get_connection, _ensure_outillage_table, _ensure_sorties_outillage_table

conn = get_connection()
_ensure_outillage_table(conn)
_ensure_sorties_outillage_table(conn)
cursor = conn.cursor()

print("=== OUTILLAGES AVEC SORTIES EN COURS OU DÉCLARÉS DEHORS ===")
cursor.execute("""
    SELECT DISTINCT o.* FROM outillage o
    WHERE o.statut != 'Dans le magasin'
       OR o.quantite <= 0
       OR EXISTS (
           SELECT 1 FROM sorties_outillage s
           WHERE s.outillage_id = o.id AND s.statut = 'EN_COURS'
       )
""")
for r in cursor.fetchall():
    d = dict(r)
    # Calculate exact quantity outside
    cursor.execute("""
        SELECT COALESCE(SUM(quantite_sortie - quantite_retournee), 0) as qd
        FROM sorties_outillage
        WHERE outillage_id = ? AND statut = 'EN_COURS'
    """, (d['id'],))
    res = cursor.fetchone()
    qd = res['qd'] if res else 0
    if qd == 0 and d['statut'] != 'Dans le magasin':
        qd = max(d['quantite'], 1)
    d['quantite_dehors_actuelle'] = qd
    print(d)
