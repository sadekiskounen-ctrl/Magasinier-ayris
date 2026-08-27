import sys
sys.path.insert(0, '.')
from database.db_manager import get_all_outillages, get_outillage_stats

print("=== get_all_outillages(statut_filter='Tous') ===")
rows = get_all_outillages(statut_filter='Tous')
for r in rows:
    print(r)

print()
print("=== get_all_outillages(statut_filter='En dehors du magasin') ===")
rows = get_all_outillages(statut_filter='En dehors du magasin')
for r in rows:
    print(r)

print()
print("=== get_outillage_stats() ===")
stats = get_outillage_stats()
print(stats)
