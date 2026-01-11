#!/usr/bin/env python3
"""Simple script to view database contents.

Usage:
    python view_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "network_orchestrator.db"

if not DB_PATH.exists():
    print(f"Database file not found at {DB_PATH}")
    print("Run the application first to create the database.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("NETWORK ORCHESTRATOR DATABASE CONTENTS")
print("=" * 80)

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

for table_name, in tables:
    print(f"\n{'=' * 80}")
    print(f"TABLE: {table_name}")
    print('=' * 80)
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"Total rows: {count}\n")
    
    if count == 0:
        print("(No data)")
        continue
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Get all data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Print header
    print(" | ".join(f"{col:20}" for col in columns))
    print("-" * 80)
    
    # Print rows (limit to 20 for readability)
    for row in rows[:20]:
        print(" | ".join(f"{str(val):20}" for val in row))
    
    if len(rows) > 20:
        print(f"\n... and {len(rows) - 20} more rows")

conn.close()
