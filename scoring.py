# https://developers.google.com/sheets/api/quickstart/python
import argparse
from operator import itemgetter
from typing import List, Any, Optional, Dict, Tuple

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from httplib2 import Http
from oauth2client import client, file, tools

from form_control import naming_questions

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


def parse_party_and_question(column_name: str):
    if ":" not in column_name:
        raise ValueError(f"Our predicted delimiter was missing from this column: {column_name}")
    else:
        return column_name.rsplit(":", maxsplit=1)


Name = str
Question = str
TIMESTAMP_COL = 0
EMAIL_COL = 1
NAME_COL = 2


def get_name_and_question_columns(headers: List[str]) -> Tuple[Dict[int, Name], Dict[int, Question]]:
    names_by_column: Dict[int, Name] = {}
    questions_by_column: Dict[int, Question] = {}
    for c, column in enumerate(headers):
        if c == TIMESTAMP_COL and column != "Timestamp":
            raise ValueError(f"It was thought that the timestamps were in column {c}")
        elif c == EMAIL_COL and column != "Email address":
            raise ValueError(f"It was thought that the email addresses were in column {c}")
        elif c == NAME_COL and "your name" not in column.lower():
            raise ValueError(f"It was thought that the voters' names would be in column {c}")
        else:
            if not column:
                break  # No more meaningful columns
            else:
                party, question = parse_party_and_question(column_name=column)
                names_by_column[c] = party
                questions_by_column[c] = question
    return names_by_column, questions_by_column


def print_scores(scores: Dict[Question, Dict[Name, int]]):
    total_naming_scores: Dict[Name, int] = {}
    for question, naming_scores in scores.items():
        summarized = sorted([(name, score) for name, score in naming_scores.items()], key=itemgetter(1), reverse=True)
        for name, score in naming_scores.items():
            total_naming_scores[name] = total_naming_scores.get(name, 0) + score
        print(f"Scores for {question}")
        for entry in summarized[:10]:
            print(f"{entry[0]: {entry[1]}}")
    listed_results = [(key, val) for key, val in total_naming_scores.items()]
    listed_results.sort(key=itemgetter(1), reverse=True)
    print(f"Overall scores:")
    for entry in listed_results:
        print(f"{entry[0]}: {entry[1]:,}")


def print_approval(approval: Dict[Name, int]):
    approval_results = [(key, val) for key, val in approval.items()]
    approval_results.sort(key=itemgetter(1), reverse=True)  # High first
    print("The parties with the most approvals:")
    for entry in approval_results:
        print(f"{entry[0]}: 👍 {entry[1]:,}")


def run_name_calculation(sheets_service, sheet_id):
    data = get_sheet_data(sheets_service, sheet_id)
    scores: Dict[str, Dict[str, int]]
    names_by_column, questions_by_column = get_name_and_question_columns(data[0])
    scores: Dict[Question, Dict[Name, int]] = {q: {n: 0 for n in names_by_column} for q in questions_by_column}
    approval: Dict[Name, int] = {n: 0 for n in names_by_column}  # Some questions are meant to be yes/no
    seen_emails = Dict[str, str]  # email -> timestamp
    seen_names: Dict[str, str] = {}  # name -> email
    for r in range(1, len(data)):
        row = data[r]
        for c, col in enumerate(row):
            if c == TIMESTAMP_COL:
                continue
            elif c == EMAIL_COL:
                if col in seen_emails:
                    print(f"{col} already voted at {seen_emails[col]}. "
                          f"We will ignore this later vote at {row[TIMESTAMP_COL]}")
                    break
                else:
                    seen_emails[col] = row[TIMESTAMP_COL]
            elif c == NAME_COL:
                normalized = name.lower()
                if normalized in seen_names:
                    print(f"{name} already cast a vote as {seen_names[normalized]} "
                          f"at {seen_emails[seen_names[normalized]]} − is {row[EMAIL_COL]} really a different person?")
                # Tricky to enforce − a moderator needs to get involved
                seen_names[normalized] = row[EMAIL_COL]
            else:
                name = names_by_column.get(c)
                question = questions_by_column[c]
                weighting = naming_questions[question][0]
                if weighting == 0:
                    approval[name] += int(bool(int(col) >= 5))
                else:
                    scores[question][name] += int(col) * weighting
    print_scores(scores)
    print_approval(approval)
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
