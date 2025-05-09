from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import json
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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

