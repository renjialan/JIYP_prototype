from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import json
import streamlit as st
import time

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet_config(email: str):
    """Get the appropriate spreadsheet configuration based on user email."""
    if "mike" in email.lower():
        return {
            "spreadsheet_id": st.secrets["google_sheets"]["mike_spreadsheet_id"],
            "sheet_name": st.secrets["google_sheets"]["mike_sheet_name"]
        }
    elif "shelby" in email.lower():
        return {
            "spreadsheet_id": st.secrets["google_sheets"]["shelby_spreadsheet_id"],
            "sheet_name": st.secrets["google_sheets"]["shelby_sheet_name"]
        }
    else:
        raise ValueError(f"No sheet configuration found for email: {email}")

def append_values(spreadsheet_id, range_name, value_input_option, _values):
    try:
        print("Starting Google Sheets append operation...")
        print(f"Spreadsheet ID: {spreadsheet_id}")
        print(f"Range: {range_name}")
        print(f"Values to append: {_values}")
        
        # Parse the service account credentials from secrets
        credentials_dict = json.loads(st.secrets["api_keys"]["GOOGLE_CREDENTIALS"])
        print(f"Service account email: {credentials_dict.get('client_email')}")
        print(f"Project ID: {credentials_dict.get('project_id')}")
        print(f"Private key ID: {credentials_dict.get('private_key_id')}")
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        print(f"Credentials valid: {credentials.valid}")
        print(f"Credentials scopes: {credentials.scopes}")

        service = build("sheets", "v4", credentials=credentials)
        print("Successfully built Google Sheets service")

        # Test if we can read the spreadsheet first
        try:
            print("Testing spreadsheet access...")
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            print(f"Successfully accessed spreadsheet: {spreadsheet.get('properties', {}).get('title')}")
        except HttpError as e:
            print(f"Failed to access spreadsheet: {e}")
            raise

        body = {"values": _values}
        print("Sending request to Google Sheets API...")
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
        print(f"Successfully appended {result.get('updates', {}).get('updatedCells', 0)} cells")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        print(f"Error details: {error.error_details}")
        print(f"Error status: {error.status_code}")
        print(f"Error content: {error.content}")
        raise error
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise e

def log_interaction(prompt: str, response: str, interaction_type: str = "Chat Interaction", feedback_status: str = "Pending Feedback"):
    """Log an interaction to the appropriate Google Sheet based on the user's email."""
    try:
        if not st.session_state.get("user_info"):
            print("No user info found in session state")
            return

        email = st.session_state["user_info"].get("email")
        if not email:
            print("No email found in user info")
            return

        sheet_config = get_sheet_config(email)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        append_values(
            sheet_config["spreadsheet_id"],
            f"{sheet_config['sheet_name']}!A:A",
            "USER_ENTERED",
            [[
                timestamp,
                interaction_type,
                prompt,
                response,
                feedback_status
            ]]
        )
    except Exception as e:
        print(f"Failed to log interaction: {e}")

def log_feedback(sentiment: str, messages: list):
    """Log feedback to the appropriate Google Sheet based on the user's email."""
    try:
        if not st.session_state.get("user_info"):
            print("No user info found in session state")
            return

        email = st.session_state["user_info"].get("email")
        if not email:
            print("No email found in user info")
            return

        sheet_config = get_sheet_config(email)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Log feedback separately
        append_values(
            sheet_config["spreadsheet_id"],
            f"{sheet_config['sheet_name']}!A:A",
            "USER_ENTERED",
            [[
                timestamp,
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
                f"{sheet_config['sheet_name']}!A:A",
                "USER_ENTERED",
                [[
                    timestamp,
                    "Chat Interaction",
                    last_user_msg,
                    last_assistant_msg,
                    f"Feedback: {sentiment}"
                ]]
            )
    except Exception as e:
        print(f"Failed to log feedback: {e}")

