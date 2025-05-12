import time
import streamlit as st
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from auth.token_manager import AuthTokenManager
import os
import secrets
import logging
import json
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Authenticator:
    def __init__(
        self,
        allowed_users: list,
        secret_path: str,
        redirect_uri: str,
        token_key: str,
        cookie_name: str = "auth_jwt",
        token_duration_days: int = 1,
    ):
        logger.info("Initializing Authenticator")
        st.session_state["connected"] = st.session_state.get("connected", False)
        self.allowed_users = allowed_users
        self.secret_path = secret_path
        self.redirect_uri = redirect_uri
        self.auth_token_manager = AuthTokenManager(
            cookie_name=cookie_name,
            token_key=token_key,
            token_duration_days=token_duration_days,
        )
        self.cookie_name = cookie_name
        logger.info(f"Authenticator initialized with redirect_uri: {redirect_uri}")
        logger.info(f"Allowed users: {allowed_users}")
        
        # Initialize state if not exists
        if "oauth_state" not in st.session_state:
            st.session_state.oauth_state = secrets.token_urlsafe(32)

    def _initialize_flow(self) -> google_auth_oauthlib.flow.Flow:
        try:
            # Force using production URL for testing
            redirect_uri = "https://jiyp-proto.streamlit.app/_stcore/streamlit_oauth2_callback"
            logger.info(f"Using redirect URI: {redirect_uri}")
            
            # Load client secrets
            with open(self.secret_path, 'r') as f:
                client_config = json.load(f)
            logger.info("Loaded client secrets successfully")
            
            flow = google_auth_oauthlib.flow.Flow.from_client_config(
                client_config,
                scopes=[
                    "openid",
                    "https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/userinfo.email",
                ],
                redirect_uri=redirect_uri,
            )
            logger.info("Flow initialized successfully")
            return flow
        except Exception as e:
            logger.error(f"Error initializing flow: {str(e)}", exc_info=True)
            st.error(f"Error initializing authentication: {str(e)}")
            raise

    def get_auth_url(self) -> str:
        try:
            flow = self._initialize_flow()
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent"
            )
            logger.info(f"Generated auth URL: {auth_url}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {str(e)}", exc_info=True)
            st.error(f"Error generating login URL: {str(e)}")
            raise

    def login(self):
        if not st.session_state["connected"]:
            try:
                auth_url = self.get_auth_url()
                logger.info("Displaying login button")
                st.link_button("login with google", auth_url)
            except Exception as e:
                logger.error(f"Error in login: {str(e)}", exc_info=True)
                st.error(f"Error setting up login: {str(e)}")

    def check_auth(self):
        logger.info("Checking authentication status")
        logger.info(f"Session state: {dict(st.session_state)}")
        
        if st.session_state["connected"]:
            logger.info("User is already connected")
            st.toast(":green[user is authenticated]")
            return

        if st.session_state.get("logout"):
            logger.info("User has logged out")
            st.toast(":green[user logged out]")
            st.session_state["connected"] = False
            return

        token = self.auth_token_manager.get_decoded_token()
        if token is not None:
            logger.info("Found valid token in cookies")
            st.query_params.clear()
            st.session_state["connected"] = True
            st.session_state["user_info"] = {
                "email": token["email"],
                "oauth_id": token["oauth_id"],
            }
            st.rerun()

        time.sleep(1)  # important for the token to be set correctly

        auth_code = st.query_params.get("code")
        logger.info(f"Auth code from query params: {auth_code}")
        st.query_params.clear()
        
        if auth_code:
            try:
                flow = self._initialize_flow()
                logger.info("Initialized flow for token exchange")
                
                flow.fetch_token(code=auth_code)
                logger.info("Successfully fetched token")
                
                creds = flow.credentials
                logger.info("Built credentials object")

                oauth_service = build(serviceName="oauth2", version="v2", credentials=creds)
                user_info = oauth_service.userinfo().get().execute()
                logger.info(f"Retrieved user info: {user_info}")
                
                oauth_id = user_info.get("id")
                email = user_info.get("email")
                logger.info(f"Processing user: {email}")

                if email in self.allowed_users:
                    logger.info(f"User {email} is authorized")
                    self.auth_token_manager.set_token(email, oauth_id)
                    st.session_state["connected"] = True
                    st.session_state["user_info"] = {
                        "oauth_id": oauth_id,
                        "email": email,
                    }
                else:
                    logger.warning(f"Unauthorized access attempt: {email}")
                    st.toast(":red[access denied: Unauthorized user]")
            except Exception as e:
                logger.error(f"Error during authentication: {str(e)}", exc_info=True)
                st.error(f"Authentication error: {str(e)}")

    def logout(self):
        logger.info("Logging out user")
        st.session_state["logout"] = True
        st.session_state["user_info"] = None
        st.session_state["connected"] = False
        self.auth_token_manager.delete_token()
        st.rerun() 