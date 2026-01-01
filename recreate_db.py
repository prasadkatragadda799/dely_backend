"""
Script to recreate the database with proper SQLite-compatible types
"""
import os
import sqlite3
from app.database import Base, engine
from app.models import *

# Delete existing database if it exists
db_file = "dely.db"
if os.path.exists(db_file):
    try:
        os.remove(db_file)
        print(f"Deleted existing {db_file}")
    except Exception as e:
        print(f"Could not delete {db_file}: {e}")
        print("Please stop the server and try again")
        exit(1)

# Create all tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Database created successfully!")

# Verify tables were created
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Created tables: {', '.join(tables)}")
conn.close()

