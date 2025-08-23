#!/usr/bin/env python3
"""
Pi Monitor - Authentication Database
Handles user accounts and WebAuthn credentials storage
"""

import sqlite3
import json
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class AuthDatabase:
    """SQLite database for storing user authentication data"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Use the same database as metrics
            import os
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(backend_dir, 'pi_monitor.db')
        else:
            self.db_path = db_path
        self.init_auth_tables()
    
    def _connect(self):
        """Create a SQLite connection with performance optimizations"""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            conn.execute('PRAGMA foreign_keys=ON;')
            conn.execute('PRAGMA journal_mode=WAL;')
        except Exception:
            pass
        return conn
    
    def init_auth_tables(self):
        """Initialize authentication tables"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        display_name TEXT,
                        email TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                ''')
                
                # WebAuthn credentials table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS webauthn_credentials (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        credential_id TEXT UNIQUE NOT NULL,
                        public_key TEXT NOT NULL,
                        sign_count INTEGER DEFAULT 0,
                        device_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # User sessions table (for JWT tokens)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        token_hash TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_agent TEXT,
                        ip_address TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # WebAuthn challenges table (for multi-process support)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS webauthn_challenges (
                        id TEXT PRIMARY KEY,
                        challenge TEXT UNIQUE NOT NULL,
                        user_id TEXT,
                        challenge_type TEXT NOT NULL, -- 'registration' or 'authentication'
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT, -- JSON for additional data
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credentials_user_id ON webauthn_credentials(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_credentials_credential_id ON webauthn_credentials(credential_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON user_sessions(token_hash)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_challenges_challenge ON webauthn_challenges(challenge)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_challenges_expires_at ON webauthn_challenges(expires_at)')
                
                conn.commit()
                logger.info("Authentication database tables initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize authentication database: {e}")
            raise
    
    # User Management
    def create_user(self, username: str, display_name: str = None, email: str = None) -> Optional[str]:
        """Create a new user and return user ID"""
        try:
            user_id = str(uuid.uuid4())
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (id, username, display_name, email)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, display_name or username, email))
                conn.commit()
                logger.info(f"Created new user: {username} (ID: {user_id})")
                return user_id
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None
    
    def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id}: {e}")
    
    # WebAuthn Credentials Management
    def store_credential(self, user_id: str, credential_id: str, public_key: str, 
                        device_name: str = None) -> Optional[str]:
        """Store a WebAuthn credential"""
        try:
            cred_id = str(uuid.uuid4())
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO webauthn_credentials 
                    (id, user_id, credential_id, public_key, device_name)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cred_id, user_id, credential_id, public_key, device_name))
                conn.commit()
                logger.info(f"Stored credential for user {user_id}: {device_name or 'Unknown Device'}")
                return cred_id
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            return None
    
    def get_user_credentials(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active credentials for a user"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM webauthn_credentials 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get credentials for user {user_id}: {e}")
            return []
    
    def get_credential_by_id(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Get credential by credential ID"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM webauthn_credentials 
                    WHERE credential_id = ? AND is_active = 1
                ''', (credential_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get credential {credential_id}: {e}")
            return None
    
    def update_credential_usage(self, credential_id: str, sign_count: int):
        """Update credential sign count and last used timestamp"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE webauthn_credentials 
                    SET sign_count = ?, last_used = CURRENT_TIMESTAMP
                    WHERE credential_id = ?
                ''', (sign_count, credential_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update credential usage: {e}")
    
    # Session Management
    def create_session(self, user_id: str, token_hash: str, expires_at: datetime,
                      user_agent: str = None, ip_address: str = None) -> Optional[str]:
        """Create a new user session"""
        try:
            session_id = str(uuid.uuid4())
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_sessions 
                    (id, user_id, token_hash, expires_at, user_agent, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session_id, user_id, token_hash, expires_at, user_agent, ip_address))
                conn.commit()
                return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    def get_session_by_token(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get session by token hash"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.*, u.username, u.display_name 
                    FROM user_sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.token_hash = ? AND s.is_active = 1 AND s.expires_at > CURRENT_TIMESTAMP
                ''', (token_hash,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def update_session_activity(self, token_hash: str):
        """Update session last activity"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_sessions 
                    SET last_active = CURRENT_TIMESTAMP
                    WHERE token_hash = ?
                ''', (token_hash,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    def invalidate_session(self, token_hash: str):
        """Invalidate a session"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0
                    WHERE token_hash = ?
                ''', (token_hash,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP')
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired sessions")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    # Admin functions
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin function)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.*, COUNT(c.id) as credential_count
                    FROM users u
                    LEFT JOIN webauthn_credentials c ON u.id = c.user_id AND c.is_active = 1
                    WHERE u.is_active = 1
                    GROUP BY u.id
                    ORDER BY u.created_at DESC
                ''')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Get user count
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
                user_count = cursor.fetchone()[0]
                
                # Get credential count
                cursor.execute('SELECT COUNT(*) FROM webauthn_credentials WHERE is_active = 1')
                credential_count = cursor.fetchone()[0]
                
                # Get active session count
                cursor.execute('SELECT COUNT(*) FROM user_sessions WHERE is_active = 1 AND expires_at > CURRENT_TIMESTAMP')
                active_sessions = cursor.fetchone()[0]
                
                return {
                    'total_users': user_count,
                    'total_credentials': credential_count,
                    'active_sessions': active_sessions
                }
        except Exception as e:
            logger.error(f"Failed to get auth stats: {e}")
            return {}
    
    # WebAuthn challenge management methods
    def store_challenge(self, challenge: str, user_id: str = None, challenge_type: str = 'authentication', 
                       metadata: dict = None, expires_in: int = 600) -> bool:
        """Store a WebAuthn challenge in the database"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT OR REPLACE INTO webauthn_challenges 
                    (id, challenge, user_id, challenge_type, expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (str(uuid.uuid4()), challenge, user_id, challenge_type, expires_at, metadata_json))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to store challenge: {e}")
            return False
    
    def get_challenge(self, challenge: str) -> Optional[Dict[str, Any]]:
        """Retrieve a WebAuthn challenge from the database"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM webauthn_challenges 
                    WHERE challenge = ? AND expires_at > CURRENT_TIMESTAMP
                ''', (challenge,))
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    if result.get('metadata'):
                        try:
                            result['metadata'] = json.loads(result['metadata'])
                        except json.JSONDecodeError:
                            result['metadata'] = {}
                    return result
                return None
        except Exception as e:
            logger.error(f"Failed to get challenge: {e}")
            return None
    
    def delete_challenge(self, challenge: str) -> bool:
        """Delete a WebAuthn challenge from the database"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM webauthn_challenges WHERE challenge = ?', (challenge,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete challenge: {e}")
            return False
    
    def cleanup_expired_challenges(self) -> int:
        """Remove expired challenges"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM webauthn_challenges WHERE expires_at < CURRENT_TIMESTAMP')
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired challenges")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired challenges: {e}")
            return 0
