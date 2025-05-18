from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
<<<<<<< HEAD
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

token_data = {
    "token": st.secrets["oauth2"]["token"],
    "refresh_token": st.secrets["oauth2"]["refresh_token"],
    "token_uri": st.secrets["oauth2"]["token_uri"],
    "client_id": st.secrets["oauth2"]["client_id"],
    "client_secret": st.secrets["oauth2"]["client_secret"],
    "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
    "universe_domain": "googleapis.com",
    "account": "",
    "expiry": "2024-08-06T08:36:06.391636Z",
}

json_data = json.dumps(token_data)
json_data = json.loads(json_data)

def append_values(spreadsheet_id, range_name, value_input_option, _values):
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  #creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  print(json_data)
  creds = Credentials.from_authorized_user_info(json_data)
  """
  Creates the batch_update the user has access to.
  Load pre-authorized user credentials from the environment.
  TODO(developer) - See https://developers.google.com/identity
  for guides on implementing OAuth2 for the application.
  """
  # creds, _ = google.auth.default()
  # pylint: disable=maybe-no-member
  try:
    service = build("sheets", "v4", credentials=creds)

    values = [
        [
            # Cell values ...
        ],
        # Additional rows ...
    ]
    body = {"values": _values}
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            body=body,
        )
        .execute()
    )
    print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
    return result

  except HttpError as error:
    print(f"An error occurred: {error}")
    return error
=======
from google.oauth2 import service_account
import json
import streamlit as st
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class FeedbackManager:
    def __init__(self):
        self.feedback_history = []

    def add_feedback(self, sentiment: str, messages: list):
        """Add feedback to the history and log it to Google Sheets."""
        self.feedback_history.append({
            "sentiment": sentiment,
            "messages": messages,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        log_feedback(sentiment, messages)

    def get_feedback_history(self):
        """Get the feedback history."""
        return self.feedback_history

def get_sheet_config(email: str):
    """Get the appropriate spreadsheet configuration based on user email."""
    try:
        # Get all allowed users from secrets
        allowed_users = st.secrets["auth"]["allowed_users"].split(",")
        
        # Find the matching user configuration
        for user in allowed_users:
            if user.strip().lower() == email.lower():
                return {
                    "spreadsheet_id": st.secrets["google_sheets"]["mike_spreadsheet_id"],
                    "sheet_name": st.secrets["google_sheets"]["mike_sheet_name"]
                }
        
        # If no specific configuration found, use default
        return {
            "spreadsheet_id": st.secrets["google_sheets"]["mike_spreadsheet_id"],
            "sheet_name": st.secrets["google_sheets"]["mike_sheet_name"]
        }
    except Exception as e:
        logger.error(f"Error getting sheet config: {e}")
        return None

def append_values(spreadsheet_id, range_name, value_input_option, _values):
    try:
        logger.info("Starting Google Sheets append operation...")
        
        # Parse the service account credentials from secrets
        credentials_dict = json.loads(st.secrets["api_keys"]["GOOGLE_CREDENTIALS"])
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )

        service = build("sheets", "v4", credentials=credentials)
        logger.info("Successfully built Google Sheets service")

        body = {"values": _values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        logger.info(f"Successfully appended {result.get('updates', {}).get('updatedCells', 0)} cells")
        return result
    except HttpError as error:
        logger.error(f"Google Sheets API error: {error}")
        raise error
    except Exception as e:
        logger.error(f"Unexpected error in append_values: {e}")
        raise e

def log_interaction(prompt: str, response: str, interaction_type: str = "Chat Interaction", feedback_status: str = "Pending Feedback"):
    """Log an interaction to the appropriate Google Sheet based on the user's email."""
    try:
        if not st.session_state.get("user_info"):
            logger.warning("No user_info found in session state")
            return

        email = st.session_state["user_info"].get("email")
        if not email:
            logger.warning("No email found in user_info")
            return

        sheet_config = get_sheet_config(email)
        if not sheet_config:
            logger.error("Failed to get sheet configuration")
            return
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        values = [[
            timestamp,
            email,
            interaction_type,
            prompt,
            response,
            feedback_status
        ]]
        
        append_values(
            sheet_config["spreadsheet_id"],
            f"{sheet_config['sheet_name']}!A:F",
            "USER_ENTERED",
            values
        )
        logger.info("Successfully logged interaction")
    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")

def log_feedback(sentiment: str, messages: list):
    """Log feedback to the appropriate Google Sheet based on the user's email."""
    try:
        if not st.session_state.get("user_info"):
            logger.warning("No user_info found in session state")
            return

        email = st.session_state["user_info"].get("email")
        if not email:
            logger.warning("No email found in user_info")
            return

        sheet_config = get_sheet_config(email)
        if not sheet_config:
            logger.error("Failed to get sheet configuration")
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Log feedback separately
        append_values(
            sheet_config["spreadsheet_id"],
            f"{sheet_config['sheet_name']}!A:F",
            "USER_ENTERED",
            [[
                timestamp,
                email,
                "Feedback",
                f"Last {len(messages)} messages",
                sentiment,
                "Session End"
            ]]
        )
        
        # Update the last chat interaction with feedback
        if len(messages) >= 2:
            last_user_msg = messages[-2]["content"]
            last_assistant_msg = messages[-1]["content"]
            append_values(
                sheet_config["spreadsheet_id"],
                f"{sheet_config['sheet_name']}!A:F",
                "USER_ENTERED",
                [[
                    timestamp,
                    email,
                    "Chat Interaction",
                    last_user_msg,
                    last_assistant_msg,
                    f"Feedback: {sentiment}"
                ]]
            )
        logger.info("Successfully logged feedback")
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")
>>>>>>> new-main

