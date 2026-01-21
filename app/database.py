"""
Database Configuration
SQLite database with Vercel-compatible path handling.
Includes schema with support for AI-generated photos and background removal.
"""
import sqlite3
import os

# Use /tmp for Vercel (only writable directory in serverless)
# Use local database.db for local development
IS_VERCEL = os.environ.get("VERCEL", False)
DB_NAME = "/tmp/database.db" if IS_VERCEL else "database.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      employee_name TEXT NOT NULL,
      id_nickname TEXT,
      id_number TEXT NOT NULL,
      position TEXT NOT NULL,
      department TEXT NOT NULL,
      email TEXT,
      personal_number TEXT,
      photo_path TEXT NOT NULL,
      photo_url TEXT,
      new_photo INTEGER DEFAULT 1,
      new_photo_url TEXT,
      nobg_photo_url TEXT,
      signature_path TEXT,
      signature_url TEXT,
      status TEXT DEFAULT 'Reviewing',
      date_last_modified TEXT,
      id_generated INTEGER DEFAULT 0,
      render_url TEXT,
      emergency_name TEXT,
      emergency_contact TEXT,
      emergency_address TEXT
    )
    """)
    
    # Add new_photo_url column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN new_photo_url TEXT")
        conn.commit()
    except:
        pass  # Column already exists
    
    # Add nobg_photo_url column if it doesn't exist (for background-removed photos)
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN nobg_photo_url TEXT")
        conn.commit()
    except:
        pass  # Column already exists
    
    # Add emergency contact fields (for ID card backside)
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN emergency_name TEXT")
        conn.commit()
    except:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN emergency_contact TEXT")
        conn.commit()
    except:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN emergency_address TEXT")
        conn.commit()
    except:
        pass  # Column already exists

    conn.commit()
    conn.close()
