"""
Role-Based Access Control (RBAC) Simulator - Authentication Module
Demonstrates the critical distinction between:
- Authentication (AuthN): "Who are you?" (Identity verification via salted password hashing)
- Authorization (AuthZ): "What are you allowed to do?" (RBAC engine permissions)
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from rbac.models import User, Role


class AuthenticationService:
    """
    Manages user authentication, secure salted hashing, lockout policies, and sessions.
    """

    def __init__(self, lockout_threshold: int = 3, lockout_minutes: int = 5):
        self.lockout_threshold = lockout_threshold
        self.lockout_duration = timedelta(minutes=lockout_minutes)
        # Active in-memory session tokens: token -> username
        self.active_sessions: Dict[str, str] = {}

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hashes a password using PBKDF2-HMAC-SHA256 with a cryptographically secure salt.
        Returns: (hash_hex, salt_hex)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 100,000 iterations of PBKDF2-HMAC-SHA256
        dk = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            iterations=100_000
        )
        return dk.hex(), salt

    @staticmethod
    def verify_password(provided_password: str, stored_hash: str, salt: str) -> bool:
        """
        Verifies a password against the stored hash and salt using constant-time comparison.
        """
        computed_hash, _ = AuthenticationService.hash_password(provided_password, salt)
        return hmac.compare_digest(computed_hash, stored_hash)

    def authenticate(
        self,
        username: str,
        password: str,
        users_store: Dict[str, User]
    ) -> Tuple[bool, str, Optional[str], Optional[User]]:
        """
        Authenticates a user against the user repository.
        Returns: (success: bool, message: str, session_token: Optional[str], user: Optional[User])
        """
        user = users_store.get(username.lower().strip())
        if not user:
            return False, "Authentication Failed: Invalid username or password.", None, None

        # Check if account is locked
        if user.is_locked():
            remaining_time = int((user.locked_until - datetime.now()).total_seconds())
            return (
                False,
                f"Authentication Blocked: Account locked due to multiple failed attempts. Try again in {remaining_time}s.",
                None,
                user
            )

        if not user.is_active:
            return False, "Authentication Failed: Account is disabled. Contact system administrator.", None, user

        # Verify password
        if self.verify_password(password, user.password_hash, user.salt):
            # Reset failed attempts upon successful login
            user.failed_attempts = 0
            user.locked_until = None
            
            # Issue session token
            session_token = secrets.token_urlsafe(32)
            self.active_sessions[session_token] = user.username
            return True, f"Authentication Successful. Welcome, {user.full_name} ({user.role.value}).", session_token, user
        else:
            # Increment failed attempt count
            user.failed_attempts += 1
            if user.failed_attempts >= self.lockout_threshold:
                user.locked_until = datetime.now() + self.lockout_duration
                return (
                    False,
                    f"Authentication Failed: Account has been temporarily locked for {int(self.lockout_duration.total_seconds() / 60)} minutes due to {user.failed_attempts} failed attempts.",
                    None,
                    user
                )
            remaining_attempts = self.lockout_threshold - user.failed_attempts
            return (
                False,
                f"Authentication Failed: Invalid credentials. {remaining_attempts} attempt(s) remaining before lockout.",
                None,
                user
            )

    def logout(self, session_token: str) -> bool:
        """Terminates an active session."""
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
            return True
        return False

    def get_user_from_session(self, session_token: str, users_store: Dict[str, User]) -> Optional[User]:
        """Resolves active user from session token."""
        username = self.active_sessions.get(session_token)
        if username and username in users_store:
            return users_store[username]
        return None

    @staticmethod
    def get_auth_comparison() -> Dict[str, Any]:
        """Returns comparison between Authentication and Authorization for educational display."""
        return {
            "authentication": {
                "question": "Who are you?",
                "mechanism": "Identity verification via credentials (username + salted SHA-256 hash)",
                "failure_code": "401 Unauthorized",
                "failure_meaning": "Identity is unverified or credentials were invalid."
            },
            "authorization": {
                "question": "What are you permitted to do?",
                "mechanism": "Access control matrix mapping roles (Admin, Teacher, Student) to permissions",
                "failure_code": "403 Forbidden",
                "failure_meaning": "Identity is verified, but role lacks required privilege."
            }
        }
