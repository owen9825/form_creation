# https://developers.google.com/sheets/api/quickstart/python
import os.path

import argparse
from typing import List, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from httplib2 import Http
from oauth2client import client, file, tools

from form_control import get_authenticated_forms_service

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
DISCOVERY_DOC = "https://sheets.googleapis.com/$discovery/rest?version=v4"
READING_RANGE = 'Form responses 1!A1:AJC300'


def get_authenticated_sheets_service():
    store = file.Storage('token.json')
    creds = None
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return discovery.build('sheets', 'v4', http=creds.authorize(
        Http()), discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)


def get_sheet_data(sheets_service, sheet_id: str) -> Optional[List[List[Any]]]:
    try:
        sheet = sheets_service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id,
                                    range=READING_RANGE).execute()
        values = result.get('values', [])
        if not values:
            print(f'No data found in sheet {sheet_id}')
            return None
        return values
    except HttpError as err:
        print(err)


def run_name_calculation(sheets_service, sheet_id):
    data = get_sheet_data(sheets_service, sheet_id)
    print(f"{len(data)} rows were retrieved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This program pulls form responses from a Google Sheet, then scores the names being discussed"
    )
    parser.add_argument(
        "--sheet-id",
        type=str,
        default="1iAHnxY-moMASKvZSqtxk-Pj6ZifdQZQguaESyddOwH4",
        help="The identifier for the sheet where responses have been saved",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="naming_results.csv",
        help="The output path for the results"
    )
    args = parser.parse_args()
    sheets_service = get_authenticated_sheets_service()
    run_name_calculation(sheets_service, sheet_id=args.sheet_id)
