"""Secure credential and session storage."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from src.auth.exceptions import SessionExpiredError
from src.logger import get_logger

logger = get_logger()


class CredentialStore:
    """Manages encrypted session state using Fernet symmetric encryption.

    Reads encryption key from environment variable SESSION_ENCRYPTION_KEY.
    Ensures no credentials or active cookies are written to disk in plain text.
    """

    def __init__(self, session_path: str | Path = "data/session.enc"):
        self.session_path = Path(session_path)
        self._key = os.getenv("SESSION_ENCRYPTION_KEY")
        if not self._key:
            raise ValueError("SESSION_ENCRYPTION_KEY environment variable is not set")

        try:
            self._fernet = Fernet(self._key.encode())
        except ValueError as e:
            raise ValueError(f"Invalid SESSION_ENCRYPTION_KEY format: {e}")

    def _ensure_data_dir(self) -> None:
        """Ensure the parent directory of the session file exists."""
        self.session_path.parent.mkdir(parents=True, exist_ok=True)

    def save_session(self, cookies: list[dict[str, Any]], username: str) -> None:
        """Encrypt and save cookies and session metadata to disk."""
        session_data = {
            "username": username,
            "cookies": cookies,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        json_data = json.dumps(session_data).encode("utf-8")
        encrypted_data = self._fernet.encrypt(json_data)

        self._ensure_data_dir()
        self.session_path.write_bytes(encrypted_data)
        logger.info("session_saved", username=username, path=str(self.session_path))

    def load_session(self, max_age_days: int = 7) -> list[dict[str, Any]] | None:
        """Load and decrypt session cookies from disk.

        Args:
            max_age_days: Maximum age of the session in days before it's considered expired.

        Returns:
            List of cookie dicts, or None if no valid session exists.
        """
        if not self.session_path.exists():
            return None

        try:
            encrypted_data = self.session_path.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            session_data = json.loads(decrypted_data.decode("utf-8"))

            saved_at = datetime.fromisoformat(session_data["saved_at"])
            age = datetime.now(timezone.utc) - saved_at

            if age > timedelta(days=max_age_days):
                logger.warning("session_expired", age_days=age.days, max_age_days=max_age_days)
                raise SessionExpiredError("Session file is too old")

            logger.info(
                "session_loaded",
                username=session_data["username"],
                age_hours=round(age.total_seconds() / 3600, 1),
            )

            cookies: list[dict[str, Any]] = session_data["cookies"]
            return cookies

        except InvalidToken:
            logger.error("session_load_failed", error="Invalid encryption token or corrupted file")
            return None
        except Exception as e:
            logger.error("session_load_failed", error=str(e))
            return None

    def clear_session(self) -> None:
        """Delete the session file securely."""
        if self.session_path.exists():
            self.session_path.unlink()
            logger.info("session_cleared", path=str(self.session_path))
