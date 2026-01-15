#!/usr/bin/env python3
"""Simple script to view database contents.

Usage:
    python3 view_db.py                          # View all tables
    python3 view_db.py --table deployments      # View deployments table
    python3 view_db.py -t nodes                 # View nodes table
    python3 view_db.py -t telemetry_samples     # View telemetry_samples table
    python3 view_db.py -t events                # View events table
    python3 view_db.py --list                   # List all available tables
"""

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "network_orchestrator.db"


def list_tables(cursor):
    """List all available tables."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print("Available tables:")
    for table_name, in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name} ({count} rows)")


def view_table(cursor, table_name):
    """View contents of a specific table."""
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        print(f"Error: Table '{table_name}' not found.")
        print("\nAvailable tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for name, in cursor.fetchall():
            print(f"  - {name}")
        return
    
    print("=" * 80)
    print(f"TABLE: {table_name}")
    print("=" * 80)
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"Total rows: {count}\n")
    
    if count == 0:
        print("(No data)")
        return
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Get all data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Print header
    print(" | ".join(f"{col:20}" for col in columns))
    print("-" * 80)
    
    # Print rows (limit to 50 for readability)
    for row in rows[:50]:
        print(" | ".join(f"{str(val):20}" for val in row))
    
    if len(rows) > 50:
        print(f"\n... and {len(rows) - 50} more rows")


def main():
    parser = argparse.ArgumentParser(
        description="View database contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 view_db.py                          # View all tables
  python3 view_db.py --table deployments      # View deployments table
  python3 view_db.py -t nodes                  # View nodes table
  python3 view_db.py -t telemetry_samples     # View telemetry_samples table
  python3 view_db.py -t events                # View events table
  python3 view_db.py --list                   # List all available tables
        """
    )
    parser.add_argument(
        "-t", "--table",
        help="View a specific table (e.g., deployments, nodes, telemetry_samples, events)"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all available tables"
    )
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print(f"Database file not found at {DB_PATH}")
        print("Run the application first to create the database.")
        exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if args.list:
        list_tables(cursor)
    elif args.table:
        view_table(cursor, args.table)
    else:
        # View all tables
        print("=" * 80)
        print("NETWORK ORCHESTRATOR DATABASE CONTENTS")
        print("=" * 80)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for table_name, in tables:
            view_table(cursor, table_name)
            print()  # Empty line between tables
    
    conn.close()


if __name__ == "__main__":
    main()
