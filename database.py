"""
Asynchronous Database handlers using aiosqlite
"""
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"


@dataclass
class User:
    """User data model"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    language_code: Optional[str]
    is_banned: bool
    is_admin: bool
    is_secondary_owner: bool
    downloads_today: int
    total_downloads: int
    last_download: Optional[datetime]
    last_activity: datetime
    created_at: datetime


class Database:
    """Async database manager"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """Initialize database connection and create tables"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info("Database connected successfully")
    
    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    async def _create_tables(self) -> None:
        """Create all required tables"""
        async with self._lock:
            # Users table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language_code TEXT DEFAULT 'en',
                    is_banned INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    is_secondary_owner INTEGER DEFAULT 0,
                    downloads_today INTEGER DEFAULT 0,
                    total_downloads INTEGER DEFAULT 0,
                    last_download TEXT,
                    last_activity TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Downloads log table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    platform TEXT,
                    quality TEXT,
                    file_size INTEGER,
                    status TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Settings table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Required channels table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS required_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_username TEXT UNIQUE,
                    channel_title TEXT,
                    added_by INTEGER,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Error logs table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    traceback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self._connection.commit()
    
    # ==================== User Management ====================
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return User(
                    user_id=row['user_id'],
                    username=row['username'],
                    first_name=row['first_name'],
                    language_code=row['language_code'],
                    is_banned=bool(row['is_banned']),
                    is_admin=bool(row['is_admin']),
                    is_secondary_owner=bool(row['is_secondary_owner']),
                    downloads_today=row['downloads_today'],
                    total_downloads=row['total_downloads'],
                    last_download=datetime.fromisoformat(row['last_download']) if row['last_download'] else None,
                    last_activity=datetime.fromisoformat(row['last_activity']) if row['last_activity'] else datetime.now(),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                )
            return None
    
    async def add_user(self, user_id: int, username: str = None, 
                       first_name: str = None, language_code: str = 'en') -> bool:
        """Add new user to database"""
        async with self._lock:
            try:
                now = datetime.now().isoformat()
                await self._connection.execute("""
                    INSERT OR IGNORE INTO users 
                    (user_id, username, first_name, language_code, last_activity, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, language_code, now, now))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding user: {e}")
                return False
    
    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        if not kwargs:
            return False
        
        async with self._lock:
            try:
                fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values()) + [user_id]
                await self._connection.execute(
                    f"UPDATE users SET {fields} WHERE user_id = ?", values
                )
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error updating user: {e}")
                return False
    
    async def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        return await self.update_user(user_id, is_banned=1)
    
    async def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        return await self.update_user(user_id, is_banned=0)
    
    async def set_admin(self, user_id: int, is_admin: bool = True) -> bool:
        """Set user as admin"""
        return await self.update_user(user_id, is_admin=int(is_admin))
    
    async def set_secondary_owner(self, user_id: int, is_owner: bool = True) -> bool:
        """Set user as secondary owner"""
        return await self.update_user(user_id, is_secondary_owner=int(is_owner))
    
    async def get_all_users(self) -> List[int]:
        """Get all user IDs"""
        async with self._lock:
            cursor = await self._connection.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [row['user_id'] for row in rows]
    
    async def get_active_users(self) -> List[int]:
        """Get non-banned user IDs"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT user_id FROM users WHERE is_banned = 0"
            )
            rows = await cursor.fetchall()
            return [row['user_id'] for row in rows]
    
    async def get_admins(self) -> List[int]:
        """Get all admin user IDs"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT user_id FROM users WHERE is_admin = 1 OR is_secondary_owner = 1"
            )
            rows = await cursor.fetchall()
            return [row['user_id'] for row in rows]
    
    # ==================== Download Limits ====================
    
    async def check_daily_limit(self, user_id: int, limit: int = 15) -> Dict[str, Any]:
        """Check if user has reached daily download limit"""
        user = await self.get_user(user_id)
        if not user:
            return {'allowed': True, 'remaining': limit, 'reset_time': None}
        
        # Check if we need to reset (new day)
        if user.last_download:
            last_download_date = user.last_download.date()
            if last_download_date < datetime.now().date():
                await self.reset_user_limit(user_id)
                return {'allowed': True, 'remaining': limit, 'reset_time': None}
        
        remaining = limit - user.downloads_today
        if remaining <= 0:
            # Calculate reset time (midnight)
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            reset_time = tomorrow - datetime.now()
            return {
                'allowed': False, 
                'remaining': 0, 
                'reset_time': str(reset_time).split('.')[0]
            }
        
        return {'allowed': True, 'remaining': remaining, 'reset_time': None}
    
    async def increment_download(self, user_id: int) -> bool:
        """Increment user's download count"""
        async with self._lock:
            try:
                now = datetime.now().isoformat()
                await self._connection.execute("""
                    UPDATE users SET 
                        downloads_today = downloads_today + 1,
                        total_downloads = total_downloads + 1,
                        last_download = ?,
                        last_activity = ?
                    WHERE user_id = ?
                """, (now, now, user_id))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error incrementing download: {e}")
                return False
    
    async def reset_user_limit(self, user_id: int) -> bool:
        """Reset user's daily download count"""
        return await self.update_user(user_id, downloads_today=0)
    
    async def reset_all_daily_limits(self) -> bool:
        """Reset all users' daily limits"""
        async with self._lock:
            try:
                await self._connection.execute("UPDATE users SET downloads_today = 0")
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error resetting limits: {e}")
                return False
    
    # ==================== Cooldown Management ====================
    
    async def check_cooldown(self, user_id: int, cooldown_seconds: int = 5) -> Dict[str, Any]:
        """Check if user is in cooldown period"""
        user = await self.get_user(user_id)
        if not user or not user.last_download:
            return {'in_cooldown': False, 'remaining': 0}
        
        elapsed = (datetime.now() - user.last_download).total_seconds()
        if elapsed < cooldown_seconds:
            remaining = int(cooldown_seconds - elapsed)
            return {'in_cooldown': True, 'remaining': remaining}
        
        return {'in_cooldown': False, 'remaining': 0}
    
    # ==================== Download Logging ====================
    
    async def log_download(self, user_id: int, url: str, platform: str,
                          quality: str, file_size: int = 0, 
                          status: str = 'success', error_message: str = None) -> bool:
        """Log a download attempt"""
        async with self._lock:
            try:
                await self._connection.execute("""
                    INSERT INTO downloads 
                    (user_id, url, platform, quality, file_size, status, error_message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, url, platform, quality, file_size, status, 
                      error_message, datetime.now().isoformat()))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error logging download: {e}")
                return False
    
    async def log_error(self, user_id: int, url: str, error_type: str,
                       error_message: str, traceback: str = None) -> int:
        """Log an error and return the error ID"""
        async with self._lock:
            try:
                cursor = await self._connection.execute("""
                    INSERT INTO error_logs 
                    (user_id, url, error_type, error_message, traceback, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, url, error_type, error_message, traceback,
                      datetime.now().isoformat()))
                await self._connection.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Error logging error: {e}")
                return 0
    
    # ==================== Statistics ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        async with self._lock:
            stats = {}
            
            # Total users
            cursor = await self._connection.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = (await cursor.fetchone())[0]
            
            # New users today
            today = datetime.now().date().isoformat()
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?", (today,)
            )
            stats['new_users_today'] = (await cursor.fetchone())[0]
            
            # Downloads today
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM downloads WHERE DATE(created_at) = ? AND status = 'success'",
                (today,)
            )
            stats['downloads_today'] = (await cursor.fetchone())[0]
            
            # Total downloads
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM downloads WHERE status = 'success'"
            )
            stats['total_downloads'] = (await cursor.fetchone())[0]
            
            # Active users (last 24h)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor = await self._connection.execute(
                "SELECT COUNT(*) FROM users WHERE last_activity > ?", (yesterday,)
            )
            stats['active_users_24h'] = (await cursor.fetchone())[0]
            
            return stats
    
    # ==================== Required Channels ====================
    
    async def add_required_channel(self, channel_username: str, 
                                   channel_title: str, added_by: int) -> bool:
        """Add a required channel"""
        async with self._lock:
            try:
                await self._connection.execute("""
                    INSERT OR REPLACE INTO required_channels 
                    (channel_username, channel_title, added_by, added_at)
                    VALUES (?, ?, ?, ?)
                """, (channel_username, channel_title, added_by, datetime.now().isoformat()))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding channel: {e}")
                return False
    
    async def remove_required_channel(self, channel_username: str) -> bool:
        """Remove a required channel"""
        async with self._lock:
            try:
                await self._connection.execute(
                    "DELETE FROM required_channels WHERE channel_username = ?",
                    (channel_username,)
                )
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error removing channel: {e}")
                return False
    
    async def get_required_channels(self) -> List[Dict[str, str]]:
        """Get all required channels"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT channel_username, channel_title FROM required_channels"
            )
            rows = await cursor.fetchall()
            return [{'username': row[0], 'title': row[1]} for row in rows]
    
    # ==================== Settings ====================
    
    async def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else default
    
    async def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value"""
        async with self._lock:
            try:
                await self._connection.execute("""
                    INSERT OR REPLACE INTO settings (key, value)
                    VALUES (?, ?)
                """, (key, value))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error setting value: {e}")
                return False
    
    async def get_bot_settings(self) -> Dict[str, Any]:
        """Get all bot settings as dictionary"""
        async with self._lock:
            cursor = await self._connection.execute("SELECT key, value FROM settings")
            rows = await cursor.fetchall()
            settings = {}
            for row in rows:
                key, value = row[0], row[1]
                if value.lower() in ('true', 'false'):
                    settings[key] = value.lower() == 'true'
                elif value.isdigit():
                    settings[key] = int(value)
                else:
                    settings[key] = value
            return settings
    
    async def update_bot_settings(self, settings: Dict[str, Any]) -> bool:
        """Update multiple bot settings"""
        async with self._lock:
            try:
                for key, value in settings.items():
                    await self._connection.execute("""
                        INSERT OR REPLACE INTO settings (key, value)
                        VALUES (?, ?)
                    """, (key, str(value)))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error updating settings: {e}")
                return False


# Global database instance
db = Database()
