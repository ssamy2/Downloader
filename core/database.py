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
DB_PATH = "data/bot_database.db"

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
                    can_download INTEGER DEFAULT 1,
                    can_use_quality INTEGER DEFAULT 1,
                    can_download_audio INTEGER DEFAULT 1,
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
                    channel_id INTEGER,
                    channel_title TEXT,
                    is_private INTEGER DEFAULT 0,
                    is_valid INTEGER DEFAULT 1,
                    added_by INTEGER,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_checked TEXT,
                    invite_link TEXT
                )
            """)
            
            # Auto-migrate: add columns if they don't exist (for existing old databases)
            await self._auto_migrate_permissions()
            await self._auto_migrate_channels()
            
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
            
            # File Cache table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    platform TEXT,
                    quality TEXT,
                    file_id TEXT,
                    file_type TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(url, quality)
                )
            """)
            
            # Cookies table
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    status TEXT DEFAULT 'testing',
                    uses INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    last_used TEXT,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self._connection.commit()
    
    async def _auto_migrate_permissions(self) -> None:
        """Auto-migrate database to add permission columns if missing"""
        try:
            # Check if columns exist
            cursor = await self._connection.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            # Add missing permission columns
            if 'can_download' not in columns:
                await self._connection.execute("ALTER TABLE users ADD COLUMN can_download INTEGER DEFAULT 1")
                logger.info("Added 'can_download' column to users table")
            
            if 'can_use_quality' not in columns:
                await self._connection.execute("ALTER TABLE users ADD COLUMN can_use_quality INTEGER DEFAULT 1")
                logger.info("Added 'can_use_quality' column to users table")
            
            if 'can_download_audio' not in columns:
                await self._connection.execute("ALTER TABLE users ADD COLUMN can_download_audio INTEGER DEFAULT 1")
                logger.info("Added 'can_download_audio' column to users table")
            
            await self._connection.commit()
        except Exception as e:
            logger.error(f"Error during permissions migration: {e}")
    
    async def _auto_migrate_channels(self) -> None:
        """Auto-migrate database to add channel columns if missing"""
        try:
            # Check if columns exist in required_channels table
            cursor = await self._connection.execute("PRAGMA table_info(required_channels)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            # Add missing channel columns
            if 'channel_id' not in columns:
                await self._connection.execute("ALTER TABLE required_channels ADD COLUMN channel_id INTEGER")
                logger.info("Added 'channel_id' column to required_channels table")
            
            if 'is_private' not in columns:
                await self._connection.execute("ALTER TABLE required_channels ADD COLUMN is_private INTEGER DEFAULT 0")
                logger.info("Added 'is_private' column to required_channels table")
            
            if 'is_valid' not in columns:
                await self._connection.execute("ALTER TABLE required_channels ADD COLUMN is_valid INTEGER DEFAULT 1")
                logger.info("Added 'is_valid' column to required_channels table")
            
            if 'last_checked' not in columns:
                await self._connection.execute("ALTER TABLE required_channels ADD COLUMN last_checked TEXT")
                logger.info("Added 'last_checked' column to required_channels table")
            
            if 'invite_link' not in columns:
                await self._connection.execute("ALTER TABLE required_channels ADD COLUMN invite_link TEXT")
                logger.info("Added 'invite_link' column to required_channels table")
                
            # Update existing channels to be valid by default
            if 'is_valid' in columns:
                await self._connection.execute(
                    "UPDATE required_channels SET is_valid = 1 WHERE is_valid IS NULL"
                )
                
        except Exception as e:
            logger.error(f"Error during channels migration: {e}")
    
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
    
    async def set_user_permission(self, user_id: int, permission: str, value: bool) -> bool:
        """Set user permission (can_download, can_use_quality, can_download_audio)"""
        valid_permissions = ['can_download', 'can_use_quality', 'can_download_audio']
        if permission not in valid_permissions:
            return False
        return await self.update_user(user_id, **{permission: int(value)})
    
    async def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """Get user permissions"""
        user = await self.get_user(user_id)
        if not user:
            return {'can_download': True, 'can_use_quality': True, 'can_download_audio': True}
        
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT can_download, can_use_quality, can_download_audio FROM users WHERE user_id = ?", 
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'can_download': bool(row['can_download']),
                    'can_use_quality': bool(row['can_use_quality']),
                    'can_download_audio': bool(row['can_download_audio'])
                }
            return {'can_download': True, 'can_use_quality': True, 'can_download_audio': True}
    
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
                                   channel_title: str, added_by: int,
                                   channel_id: int = None, is_private: bool = False,
                                   invite_link: str = None) -> bool:
        """Add a required channel"""
        async with self._lock:
            try:
                await self._connection.execute("""
                    INSERT OR REPLACE INTO required_channels 
                    (channel_username, channel_id, channel_title, is_private, is_valid, added_by, added_at, last_checked, invite_link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (channel_username, channel_id, channel_title, int(is_private), 1, added_by, datetime.now().isoformat(), datetime.now().isoformat(), invite_link))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding channel: {e}")
                return False
    
    async def remove_required_channel(self, channel_id: int) -> bool:
        """Remove a required channel by channel_id"""
        async with self._lock:
            try:
                await self._connection.execute(
                    "DELETE FROM required_channels WHERE channel_id = ?",
                    (channel_id,)
                )
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error removing channel: {e}")
                return False
    
    async def get_channel_by_id(self, channel_id: int) -> Optional[Dict[str, any]]:
        """Get channel info by ID"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT channel_username, channel_id, channel_title, is_private, is_valid FROM required_channels WHERE channel_id = ?",
                (channel_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'username': row[0],
                    'channel_id': row[1],
                    'title': row[2],
                    'is_private': bool(row[3]),
                    'is_valid': bool(row[4])
                }
            return None
    
    async def get_required_channels(self) -> List[Dict[str, any]]:
        """Get all required channels"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT channel_username, channel_id, channel_title, is_private, is_valid, invite_link FROM required_channels"
            )
            rows = await cursor.fetchall()
            return [{
                'username': row[0], 
                'channel_id': row[1],
                'title': row[2],
                'is_private': bool(row[3]),
                'is_valid': bool(row[4]),
                'invite_link': row[5]
            } for row in rows]
    
    async def update_channel_status(self, channel_username: str, 
                                   channel_id: int = None,
                                   is_private: bool = None,
                                   is_valid: bool = None) -> bool:
        """Update channel status (private/public, valid/invalid)"""
        async with self._lock:
            try:
                updates = []
                params = []
                
                if channel_id is not None:
                    updates.append("channel_id = ?")
                    params.append(channel_id)
                
                if is_private is not None:
                    updates.append("is_private = ?")
                    params.append(int(is_private))
                
                if is_valid is not None:
                    updates.append("is_valid = ?")
                    params.append(int(is_valid))
                
                updates.append("last_checked = ?")
                params.append(datetime.now().isoformat())
                
                params.append(channel_username)
                
                query = f"UPDATE required_channels SET {', '.join(updates)} WHERE channel_username = ?"
                await self._connection.execute(query, params)
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error updating channel status: {e}")
                return False
    
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

    # ==================== File Cache ====================
    
    async def get_cached_file(self, url: str, quality: str) -> Optional[Dict[str, str]]:
        """Get cached file_id and file_type for a URL and quality"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT file_id, file_type FROM file_cache WHERE url = ? AND quality = ?",
                (url, quality)
            )
            row = await cursor.fetchone()
            if row:
                return {'file_id': row[0], 'file_type': row[1]}
            return None
            
    async def cache_file(self, url: str, platform: str, quality: str, file_id: str, file_type: str = 'video') -> bool:
        """Cache a file_id for future use"""
        async with self._lock:
            try:
                await self._connection.execute("""
                    INSERT OR REPLACE INTO file_cache (url, platform, quality, file_id, file_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (url, platform, quality, file_id, file_type, datetime.now().isoformat()))
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error caching file: {e}")
                return False

    # ==================== Cookies Management ====================
    
    async def add_cookie(self, file_path: str) -> bool:
        """Add a new cookie file to database"""
        async with self._lock:
            try:
                await self._connection.execute(
                    "INSERT OR IGNORE INTO cookies (file_path, status) VALUES (?, 'testing')",
                    (file_path,)
                )
                await self._connection.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding cookie: {e}")
                return False
                
    async def get_working_cookie(self) -> Optional[str]:
        """Get the least recently used working cookie"""
        async with self._lock:
            cursor = await self._connection.execute(
                "SELECT file_path FROM cookies WHERE status = 'working' ORDER BY last_used ASC NULLS FIRST LIMIT 1"
            )
            row = await cursor.fetchone()
            return row['file_path'] if row else None
            
    async def update_cookie_status(self, file_path: str, status: str) -> None:
        """Update cookie status (working, burned)"""
        async with self._lock:
            await self._connection.execute(
                "UPDATE cookies SET status = ? WHERE file_path = ?",
                (status, file_path)
            )
            await self._connection.commit()
            
    async def report_cookie_usage(self, file_path: str, success: bool) -> None:
        """Report success/failure for a cookie"""
        async with self._lock:
            now = datetime.now().isoformat()
            if success:
                await self._connection.execute("""
                    UPDATE cookies SET 
                        uses = uses + 1, 
                        failures = 0, 
                        last_used = ?,
                        status = 'working'
                    WHERE file_path = ?
                """, (now, file_path))
            else:
                await self._connection.execute("""
                    UPDATE cookies SET 
                        failures = failures + 1,
                        last_used = ?
                    WHERE file_path = ?
                """, (now, file_path))
                
                # Burn if too many failures
                await self._connection.execute(
                    "UPDATE cookies SET status = 'burned' WHERE file_path = ? AND failures >= 3",
                    (file_path,)
                )
            await self._connection.commit()
            
    async def get_cookies_stats(self) -> Dict[str, int]:
        """Get statistics about cookies"""
        async with self._lock:
            cursor = await self._connection.execute("SELECT status, COUNT(*) as count FROM cookies GROUP BY status")
            rows = await cursor.fetchall()
            stats = {'working': 0, 'burned': 0, 'testing': 0, 'total': 0}
            for row in rows:
                stats[row['status']] = row['count']
                stats['total'] += row['count']
            return stats
            
    async def delete_burned_cookies(self) -> List[str]:
        """Remove burned cookies from DB and return paths to delete files"""
        async with self._lock:
            cursor = await self._connection.execute("SELECT file_path FROM cookies WHERE status = 'burned'")
            paths = [row['file_path'] for row in await cursor.fetchall()]
            
            await self._connection.execute("DELETE FROM cookies WHERE status = 'burned'")
            await self._connection.commit()
            return paths

# Global database instance
db = Database()
