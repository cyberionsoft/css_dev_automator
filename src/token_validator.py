"""
Token Validator for CSS Dev Automator
Validates tokens received from dev_manager
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TokenValidator:
    """
    Validates tokens from dev_manager for CSS Dev Automator.
    """

    def __init__(self):
        """Initialize the token validator."""
        # Token file should be in dev_manager's config directory
        # Match dev_manager's CONFIG_DIR / TOKEN_FILE pattern
        config_dir = Path.home() / "AppData" / "Local" / "DevManager"
        self.token_file_path = config_dir / "auth_token.json"

    def validate_token(self, token: str) -> bool:
        """
        Validate a token received from dev_manager.

        Args:
            token: Token to validate

        Returns:
            True if token is valid, False otherwise
        """
        try:
            token_data = self._load_token_data()
            if not token_data:
                logging.warning("No token data found")
                return False

            # Check if token hash matches
            token_hash = self._hash_token(token)
            if token_data.get("token_hash") != token_hash:
                logging.warning("Token hash mismatch")
                return False

            # Check if token has expired
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(UTC) > expires_at:
                logging.warning("Token has expired")
                return False

            # Check if token has already been used (for one-time use tokens)
            if token_data.get("used", False):
                logging.warning("Token has already been used")
                return False

            logging.info("Token validation successful")
            return True

        except Exception as e:
            logging.error(f"Token validation error: {e}")
            return False

    def mark_token_used(self, token: str) -> bool:
        """
        Mark a token as used.

        Args:
            token: Token to mark as used

        Returns:
            True if successful, False otherwise
        """
        try:
            token_data = self._load_token_data()
            if not token_data:
                return False

            token_hash = self._hash_token(token)
            if token_data.get("token_hash") == token_hash:
                token_data["used"] = True
                token_data["used_at"] = datetime.now(UTC).isoformat()
                self._save_token_data(token_data)
                logging.info("Token marked as used")
                return True

            return False

        except Exception as e:
            logging.error(f"Error marking token as used: {e}")
            return False

    def _hash_token(self, token: str) -> str:
        """
        Hash a token for secure comparison.

        Args:
            token: Token to hash

        Returns:
            Hashed token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _load_token_data(self) -> dict[str, Any] | None:
        """
        Load token data from dev_manager's token file.

        Returns:
            Token data dictionary or None if file doesn't exist
        """
        try:
            if not self.token_file_path.exists():
                return None

            with open(self.token_file_path, encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            logging.error(f"Error loading token data: {e}")
            return None

    def _save_token_data(self, token_data: dict[str, Any]) -> bool:
        """
        Save token data to file.

        Args:
            token_data: Token data to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.token_file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.token_file_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)
            return True

        except Exception as e:
            logging.error(f"Error saving token data: {e}")
            return False
