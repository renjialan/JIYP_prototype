import sys
from datetime import datetime, timedelta
import streamlit as st
import extra_streamlit_components as stx
import logging
import os
import json

logger = logging.getLogger(__name__)

class AuthTokenManager:
    def __init__(
        self,
        cookie_name: str,
        token_key: str,
        token_duration_days: int,
    ):
        logger.info("Initializing AuthTokenManager")
        self.cookie_manager = stx.CookieManager()
        self.cookie_name = cookie_name
        self.token_key = token_key
        self.token_duration_days = token_duration_days
        self.token = None
        logger.info(f"AuthTokenManager initialized with cookie_name: {cookie_name}")

    def get_decoded_token(self) -> str:
        logger.info("Attempting to get decoded token")
        self.token = self.cookie_manager.get(self.cookie_name)
        if self.token is None:
            logger.info("No token found in cookies")
            return None
        return self._decode_token()

    def set_token(self, email: str, oauth_id: str):
        logger.info(f"Setting token for user: {email}")
        exp_date = (
            datetime.now() + timedelta(days=self.token_duration_days)
        ).timestamp()
        token_data = {
            "email": email,
            "oauth_id": oauth_id,
            "exp": exp_date
        }
        token = json.dumps(token_data)
        
        # Determine if we're in local development
        is_local = os.environ.get("STREAMLIT_SERVER_PORT") == "8501"
        
        # Set cookie with appropriate settings
        cookie_settings = {
            "expires_at": datetime.fromtimestamp(exp_date),
            "samesite": "Lax",
            "secure": True,
            "path": "/"
        }
        
        # Only set domain in production
        if not is_local:
            cookie_settings["domain"] = ".streamlit.app"
        
        logger.info(f"Setting cookie with settings: {cookie_settings}")
        self.cookie_manager.set(
            self.cookie_name,
            token,
            **cookie_settings
        )
        logger.info("Token set successfully with cookie settings")

    def delete_token(self):
        logger.info("Deleting token")
        try:
            self.cookie_manager.delete(self.cookie_name)
            logger.info("Token deleted successfully")
        except KeyError:
            logger.warning("No token found to delete")

    def _decode_token(self) -> str:
        try:
            logger.info("Decoding token")
            decoded = json.loads(self.token)
            if datetime.fromtimestamp(decoded["exp"]) < datetime.now():
                logger.warning("Token has expired")
                st.toast(":red[token expired, please login]")
                self.delete_token()
                return None
            logger.info("Token decoded successfully")
            return decoded
        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}", exc_info=True)
            raise 