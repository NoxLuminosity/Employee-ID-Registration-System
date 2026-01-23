"""
Database Configuration - Supabase PostgreSQL
Persistent database for Vercel deployment using Supabase.

Environment Variables Required:
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_KEY: Your Supabase anon/service key

For local development without Supabase, falls back to SQLite.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if Supabase credentials are available
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Fallback to SQLite for local development
IS_VERCEL = os.environ.get("VERCEL", "0") == "1" or os.environ.get("VERCEL_ENV") is not None
SQLITE_DB = "/tmp/database.db" if IS_VERCEL else "database.db"

logger.info(f"Database config: USE_SUPABASE={USE_SUPABASE}, IS_VERCEL={IS_VERCEL}")

# Initialize Supabase client if available
supabase_client = None
if USE_SUPABASE:
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        USE_SUPABASE = False


# =============================================================================
# SQLite Fallback (for local development)
# =============================================================================
def get_sqlite_connection():
    """Get SQLite connection for local development"""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    """Initialize SQLite database schema"""
    import sqlite3
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_name TEXT NOT NULL,
        first_name TEXT,
        middle_initial TEXT,
        last_name TEXT,
        id_nickname TEXT,
        id_number TEXT NOT NULL,
        position TEXT NOT NULL,
        department TEXT,
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
    
    # Migration for existing SQLite databases
    migrations = [
        "ALTER TABLE employees ADD COLUMN new_photo_url TEXT",
        "ALTER TABLE employees ADD COLUMN nobg_photo_url TEXT",
        "ALTER TABLE employees ADD COLUMN emergency_name TEXT",
        "ALTER TABLE employees ADD COLUMN emergency_contact TEXT",
        "ALTER TABLE employees ADD COLUMN emergency_address TEXT",
        "ALTER TABLE employees ADD COLUMN first_name TEXT",
        "ALTER TABLE employees ADD COLUMN middle_initial TEXT",
        "ALTER TABLE employees ADD COLUMN last_name TEXT"
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
        except:
            pass  # Column already exists
    
    conn.commit()
    conn.close()


# =============================================================================
# Supabase Database Operations
# =============================================================================
def init_db():
    """Initialize database - creates table if using SQLite or verifies Supabase"""
    if USE_SUPABASE:
        # Supabase table should be created via SQL Editor in dashboard
        try:
            result = supabase_client.table("employees").select("id").limit(1).execute()
            logger.info("Supabase employees table verified")
        except Exception as e:
            logger.error(f"Supabase table check failed: {e}")
            logger.info("Please create the 'employees' table in Supabase Dashboard")
    else:
        init_sqlite_db()
        logger.info("SQLite database initialized")


def get_connection():
    """Get database connection - returns SQLite connection or None for Supabase"""
    if USE_SUPABASE:
        return None  # Supabase uses client directly
    return get_sqlite_connection()


# =============================================================================
# Employee CRUD Operations
# =============================================================================
def insert_employee(data: Dict[str, Any]) -> Optional[int]:
    """Insert a new employee record"""
    if USE_SUPABASE:
        try:
            # Remove id if present (auto-generated)
            insert_data = {k: v for k, v in data.items() if k != 'id'}
            # Convert boolean fields
            if 'new_photo' in insert_data:
                insert_data['new_photo'] = bool(insert_data['new_photo'])
            if 'id_generated' in insert_data:
                insert_data['id_generated'] = bool(insert_data['id_generated'])
            
            result = supabase_client.table("employees").insert(insert_data).execute()
            if result.data:
                return result.data[0].get('id')
            return None
        except Exception as e:
            logger.error(f"Supabase insert error: {e}")
            return None
    else:
        # SQLite fallback
        import sqlite3
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        
        cursor.execute(f"INSERT INTO employees ({columns}) VALUES ({placeholders})", values)
        employee_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return employee_id


def get_all_employees() -> List[Dict[str, Any]]:
    """Get all employees ordered by date"""
    if USE_SUPABASE:
        try:
            result = supabase_client.table("employees").select("*").order("date_last_modified", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Supabase fetch error: {e}")
            return []
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees ORDER BY date_last_modified DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


def get_employee_by_id(employee_id: int) -> Optional[Dict[str, Any]]:
    """Get a single employee by ID"""
    if USE_SUPABASE:
        try:
            result = supabase_client.table("employees").select("*").eq("id", employee_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Supabase fetch by ID error: {e}")
            return None
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


def update_employee(employee_id: int, data: Dict[str, Any]) -> bool:
    """Update an employee record"""
    if USE_SUPABASE:
        try:
            # Convert boolean fields
            update_data = data.copy()
            if 'new_photo' in update_data:
                update_data['new_photo'] = bool(update_data['new_photo'])
            if 'id_generated' in update_data:
                update_data['id_generated'] = bool(update_data['id_generated'])
            
            result = supabase_client.table("employees").update(update_data).eq("id", employee_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Supabase update error: {e}")
            return False
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        values = tuple(data.values()) + (employee_id,)
        
        cursor.execute(f"UPDATE employees SET {set_clause} WHERE id = ?", values)
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


def delete_employee(employee_id: int) -> bool:
    """Delete an employee record"""
    if USE_SUPABASE:
        try:
            result = supabase_client.table("employees").delete().eq("id", employee_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Supabase delete error: {e}")
            return False
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


def table_exists() -> bool:
    """Check if employees table exists"""
    if USE_SUPABASE:
        try:
            supabase_client.table("employees").select("id").limit(1).execute()
            return True
        except:
            return False
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        result = cursor.fetchone()
        conn.close()
        return result is not None


def get_employee_count() -> int:
    """Get total employee count"""
    if USE_SUPABASE:
        try:
            result = supabase_client.table("employees").select("id", count="exact").execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"Supabase count error: {e}")
            return 0
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM employees")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0


def get_status_breakdown() -> Dict[str, int]:
    """Get employee count by status"""
    if USE_SUPABASE:
        try:
            # Supabase doesn't have GROUP BY in REST API, so we fetch all and count
            result = supabase_client.table("employees").select("status").execute()
            counts = {}
            for row in result.data or []:
                status = row.get('status') or 'Reviewing'
                counts[status] = counts.get(status, 0) + 1
            return counts
        except Exception as e:
            logger.error(f"Supabase status breakdown error: {e}")
            return {}
    else:
        # SQLite fallback
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) as count FROM employees GROUP BY status")
        rows = cursor.fetchall()
        conn.close()
        return {row[0] or 'Reviewing': row[1] for row in rows}


# =============================================================================
# Legacy compatibility
# =============================================================================
def get_db_connection():
    """Legacy function for backward compatibility"""
    if USE_SUPABASE:
        logger.warning("get_db_connection() called but using Supabase - returning None")
        return None
    return get_sqlite_connection()


# Export for backward compatibility
DB_NAME = SQLITE_DB if not USE_SUPABASE else "supabase"
