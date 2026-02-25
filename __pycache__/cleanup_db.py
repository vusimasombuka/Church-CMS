import sqlite3
import os

db_path = os.path.join("instance", "cms.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Current tables:")
for t in tables:
    print(f"  - {t[0]}")

# Delete the leftover temporary table
print("\nDeleting _alembic_tmp_check_in...")
cursor.execute("DROP TABLE IF EXISTS _alembic_tmp_check_in")

# Also check for other temp tables
for temp_table in ['_alembic_tmp_services', '_alembic_tmp_member', '_alembic_tmp_visitor', '_alembic_tmp_giving']:
    cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
    print(f"Dropped {temp_table} if it existed")

conn.commit()
conn.close()
print("\nCleanup complete!")