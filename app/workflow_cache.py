"""
Workflow Cache - Efficient Result Caching for Multi-Step Workflows
===================================================================
Caches intermediate results (Cloudinary URLs, generated images, etc.) so that
when a later API step fails and retries, previously completed work is reused
instead of being re-executed.

Supports:
- In-memory cache with TTL expiration (for serverless short-lived instances)
- Supabase-backed persistent cache (for production durability across cold starts)
- SQLite-backed cache (for local development)

Cache Keys Convention:
- "photo_{id_number}" → Cloudinary photo URL
- "signature_{id_number}" → Cloudinary signature URL
- "ai_headshot_{id_number}" → AI-generated headshot URL
- "nobg_{id_number}" → Background-removed image URL
- "seedream_{hash}" → Seedream generation result URL
- "lark_append_{id_number}" → Lark Bitable record ID

TTL (Time-To-Live):
- Default: 1 hour for intermediate results
- Extended: 24 hours for expensive operations (AI generation)
- Short: 10 minutes for temporary uploads
"""
import logging
import time
import hashlib
import json
from typing import Any, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Default TTLs in seconds
TTL_DEFAULT = 3600    # 1 hour - standard intermediate results
TTL_EXTENDED = 86400  # 24 hours - expensive AI generation results


class WorkflowCache:
    """
    Multi-layer cache for workflow intermediate results.
    
    Layer 1: In-memory dict (fastest, lost on cold start)
    Layer 2: Database-backed (persistent, survives cold starts)
    
    Thread-safe for single-process use (adequate for serverless).
    """
    
    # In-memory cache: {key: {"value": Any, "expires_at": float, "created_at": float}}
    _memory_cache: Dict[str, Dict] = {}
    
    # Max in-memory entries to prevent unbounded growth
    _max_memory_entries = 500
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """
        Get a cached value by key. Checks memory first, then database.
        
        Args:
            key: Cache key string
            
        Returns:
            Cached value if found and not expired, None otherwise.
        """
        # Layer 1: Check in-memory cache
        entry = cls._memory_cache.get(key)
        if entry:
            if time.time() < entry["expires_at"]:
                logger.debug(f"Cache HIT (memory): {key}")
                return entry["value"]
            else:
                # Expired - remove from memory
                del cls._memory_cache[key]
                logger.debug(f"Cache EXPIRED (memory): {key}")
        
        # Layer 2: Check database cache
        try:
            db_value = cls._get_from_db(key)
            if db_value is not None:
                # Promote to memory cache for faster subsequent access
                cls._memory_cache[key] = {
                    "value": db_value,
                    "expires_at": time.time() + TTL_DEFAULT,
                    "created_at": time.time(),
                }
                logger.debug(f"Cache HIT (database): {key}")
                return db_value
        except Exception as e:
            logger.warning(f"Cache DB lookup failed for '{key}': {e}")
        
        logger.debug(f"Cache MISS: {key}")
        return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = TTL_DEFAULT) -> bool:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key string
            value: Value to cache (must be JSON-serializable for DB layer)
            ttl: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            True if cached successfully.
        """
        now = time.time()
        
        # Evict oldest entries if memory cache is too large
        if len(cls._memory_cache) >= cls._max_memory_entries:
            cls._evict_memory()
        
        # Layer 1: Store in memory
        cls._memory_cache[key] = {
            "value": value,
            "expires_at": now + ttl,
            "created_at": now,
        }
        
        # Layer 2: Store in database (for persistence across cold starts)
        try:
            cls._set_in_db(key, value, ttl)
        except Exception as e:
            logger.warning(f"Cache DB store failed for '{key}': {e}")
        
        logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
        return True
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """Remove a cached value."""
        # Remove from memory
        cls._memory_cache.pop(key, None)
        
        # Remove from database
        try:
            cls._delete_from_db(key)
        except Exception as e:
            logger.warning(f"Cache DB delete failed for '{key}': {e}")
        
        logger.debug(f"Cache DELETE: {key}")
        return True
    
    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """
        Delete all cache entries matching a key prefix.
        
        Args:
            pattern: Key prefix to match (e.g., "photo_EMP001" deletes
                     "photo_EMP001_v1", "photo_EMP001_v2", etc.)
        
        Returns:
            Number of entries deleted.
        """
        count = 0
        # Memory cache
        keys_to_delete = [k for k in cls._memory_cache if k.startswith(pattern)]
        for k in keys_to_delete:
            del cls._memory_cache[k]
            count += 1
        
        # Database cache
        try:
            count += cls._delete_pattern_from_db(pattern)
        except Exception as e:
            logger.warning(f"Cache DB pattern delete failed for '{pattern}': {e}")
        
        logger.debug(f"Cache DELETE_PATTERN: {pattern} ({count} entries)")
        return count
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        valid = sum(1 for e in cls._memory_cache.values() if now < e["expires_at"])
        expired = len(cls._memory_cache) - valid
        return {
            "memory_entries": len(cls._memory_cache),
            "memory_valid": valid,
            "memory_expired": expired,
        }
    
    @classmethod
    def clear_expired(cls) -> int:
        """Remove all expired entries from memory and database."""
        now = time.time()
        expired_keys = [k for k, v in cls._memory_cache.items() if now >= v["expires_at"]]
        for k in expired_keys:
            del cls._memory_cache[k]
        
        # Also clean database
        try:
            cls._cleanup_db()
        except Exception as e:
            logger.warning(f"Cache DB cleanup failed: {e}")
        
        return len(expired_keys)
    
    @classmethod
    def clear_all(cls) -> None:
        """Clear all cache entries (memory and database)."""
        cls._memory_cache.clear()
        try:
            cls._clear_all_db()
        except Exception as e:
            logger.warning(f"Cache DB clear failed: {e}")
        logger.info("Cache cleared (all layers)")
    
    # =========================================================================
    # Internal: Memory eviction
    # =========================================================================
    
    @classmethod
    def _evict_memory(cls):
        """Evict expired entries first, then oldest entries if still over limit."""
        now = time.time()
        
        # First pass: remove expired
        expired = [k for k, v in cls._memory_cache.items() if now >= v["expires_at"]]
        for k in expired:
            del cls._memory_cache[k]
        
        # If still over limit, remove oldest 20%
        if len(cls._memory_cache) >= cls._max_memory_entries:
            sorted_keys = sorted(
                cls._memory_cache.keys(),
                key=lambda k: cls._memory_cache[k]["created_at"]
            )
            evict_count = max(1, len(sorted_keys) // 5)
            for k in sorted_keys[:evict_count]:
                del cls._memory_cache[k]
    
    # =========================================================================
    # Internal: Database-backed cache (Supabase or SQLite)
    # =========================================================================
    
    @classmethod
    def _get_from_db(cls, key: str) -> Optional[Any]:
        """Retrieve from database cache layer."""
        from app.database import USE_SUPABASE, supabase_client, get_sqlite_connection
        
        if USE_SUPABASE:
            try:
                result = (
                    supabase_client.table("workflow_cache")
                    .select("cache_value, expires_at")
                    .eq("cache_key", key)
                    .single()
                    .execute()
                )
                if result.data:
                    expires_str = result.data.get("expires_at", "")
                    if expires_str:
                        from datetime import datetime, timezone
                        # Parse ISO timestamp robustly
                        try:
                            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                            if expires_dt.timestamp() < time.time():
                                # Expired - delete it
                                cls._delete_from_db(key)
                                return None
                        except (ValueError, AttributeError):
                            pass
                    raw = result.data.get("cache_value")
                    return json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                return None
        else:
            try:
                cls._init_cache_sqlite()
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cache_value FROM workflow_cache WHERE cache_key = ? AND expires_at > datetime('now')",
                    (key,)
                )
                row = cursor.fetchone()
                conn.close()
                if row:
                    return json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except Exception:
                return None
        
        return None
    
    @classmethod
    def _set_in_db(cls, key: str, value: Any, ttl: int):
        """Store in database cache layer."""
        from app.database import USE_SUPABASE, supabase_client, get_sqlite_connection
        
        json_value = json.dumps(value) if not isinstance(value, str) else json.dumps(value)
        
        if USE_SUPABASE:
            try:
                data = {
                    "cache_key": key,
                    "cache_value": json_value,
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": datetime.utcfromtimestamp(time.time() + ttl).isoformat(),
                    "ttl_seconds": ttl,
                }
                # Upsert (insert or update on conflict)
                supabase_client.table("workflow_cache").upsert(
                    data, on_conflict="cache_key"
                ).execute()
            except Exception as e:
                logger.debug(f"Supabase cache set failed: {e}")
        else:
            try:
                cls._init_cache_sqlite()
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO workflow_cache 
                       (cache_key, cache_value, created_at, expires_at, ttl_seconds) 
                       VALUES (?, ?, datetime('now'), datetime('now', '+' || ? || ' seconds'), ?)""",
                    (key, json_value, ttl, ttl)
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"SQLite cache set failed: {e}")
    
    @classmethod
    def _delete_from_db(cls, key: str):
        """Delete from database cache layer."""
        from app.database import USE_SUPABASE, supabase_client, get_sqlite_connection
        
        if USE_SUPABASE:
            try:
                supabase_client.table("workflow_cache").delete().eq("cache_key", key).execute()
            except Exception:
                pass
        else:
            try:
                cls._init_cache_sqlite()
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflow_cache WHERE cache_key = ?", (key,))
                conn.commit()
                conn.close()
            except Exception:
                pass
    
    @classmethod
    def _delete_pattern_from_db(cls, pattern: str) -> int:
        """Delete matching entries from database cache."""
        from app.database import USE_SUPABASE, supabase_client, get_sqlite_connection
        
        if USE_SUPABASE:
            try:
                result = (
                    supabase_client.table("workflow_cache")
                    .delete()
                    .like("cache_key", f"{pattern}%")
                    .execute()
                )
                return len(result.data) if result.data else 0
            except Exception:
                return 0
        else:
            try:
                cls._init_cache_sqlite()
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflow_cache WHERE cache_key LIKE ?", (f"{pattern}%",))
                count = cursor.rowcount
                conn.commit()
                conn.close()
                return count
            except Exception:
                return 0
    
    @classmethod
    def _cleanup_db(cls):
        """Remove expired entries from database."""
        from app.database import USE_SUPABASE, supabase_client, get_sqlite_connection
        
        if USE_SUPABASE:
            try:
                supabase_client.table("workflow_cache").delete().lt(
                    "expires_at", datetime.utcnow().isoformat()
                ).execute()
            except Exception:
                pass
        else:
            try:
                cls._init_cache_sqlite()
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflow_cache WHERE expires_at < datetime('now')")
                conn.commit()
                conn.close()
            except Exception:
                pass
    
    @classmethod
    def _clear_all_db(cls):
        """Clear all database cache entries."""
        from app.database import USE_SUPABASE, supabase_client, get_sqlite_connection
        
        if USE_SUPABASE:
            try:
                supabase_client.table("workflow_cache").delete().neq(
                    "cache_key", "___IMPOSSIBLE___"
                ).execute()
            except Exception:
                pass
        else:
            try:
                cls._init_cache_sqlite()
                conn = get_sqlite_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflow_cache")
                conn.commit()
                conn.close()
            except Exception:
                pass
    
    # SQLite table initialization
    _sqlite_initialized = False
    
    @classmethod
    def _init_cache_sqlite(cls):
        """Create workflow_cache table in SQLite if it doesn't exist."""
        if cls._sqlite_initialized:
            return
        
        from app.database import get_sqlite_connection
        try:
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    expires_at TEXT NOT NULL,
                    ttl_seconds INTEGER DEFAULT 3600
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_cache_expires ON workflow_cache(expires_at)"
            )
            conn.commit()
            conn.close()
            cls._sqlite_initialized = True
        except Exception as e:
            logger.warning(f"Failed to init SQLite cache table: {e}")


def make_cache_key(*parts: str) -> str:
    """
    Create a deterministic cache key from multiple parts.
    
    Example:
        make_cache_key("photo", "EMP-001") -> "photo_EMP-001"
        make_cache_key("seedream", url, prompt) -> "seedream_<hash>"
    """
    # For short parts, join directly
    joined = "_".join(str(p) for p in parts if p)
    if len(joined) <= 128:
        return joined
    
    # For long parts, hash them
    hash_val = hashlib.sha256(joined.encode()).hexdigest()[:16]
    prefix = str(parts[0]) if parts else "cache"
    return f"{prefix}_{hash_val}"
