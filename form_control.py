from __future__ import print_function

import argparse
from typing import Dict, List, Tuple, Union

# https://developers.google.com/forms/api/quickstart/python

from apiclient import discovery
from httplib2 import Http
from oauth2client import client, file, tools

SCOPES = "https://www.googleapis.com/auth/drive"
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"


def get_authenticated_forms_service():
    store = file.Storage('token.json')
    creds = None
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return discovery.build('forms', 'v1', http=creds.authorize(
        Http()), discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)


question_body = {
    "textQuestion": {
        "paragraph": False
    },
    "choiceQuestion": {
        "type": "DROP_DOWN",
        "options": [
            {"value": "Yes"},
            {"value": "No"}
        ],
        "shuffle": False
    },
    "scaleQuestion": {
        "low": 0,
        "high": 10
    }

}

naming_questions: Dict[str, Tuple[int, str]] = {
    "How easily would this name be understood by the mainstream electorate? 🤔 (weighting: 2)": (2, "scaleQuestion"),
    "How well does this name engender the aspirations of the electorate? 🌠 (weighting: 2)": (2, "scaleQuestion"),
    "How well does this name reflect the party's agreed values? Individual Freedom; Advancement; Deep Ecology; Safety; "
        "Ethical Conduct; Equity 🌟 (weighting: 0)": (0, "scaleQuestion"),
    "How effectively could this name be used for advertisement; identity; and graphic-design aspects of "
    "public relations? 📺 (weighting: 2)": (2, "scaleQuestion"),
    "How well does this name allow for long-term investment and recognition, for relevance and support over a "
    "long timeframe? ⏳ (weighting: 3)": (3, "scaleQuestion"),
}

raw_names = {
    "Equilib", "Science Party", "Fusion Party Australia", "Innovation Party", "Fusion", "Fusion Party",
    "One but Many, we are Australian", "Fusion Australia Party", "Intergenerational equity party",
    "Fusion", "The AEGIS Party", "Australian Democracy Party", "Rational",
    "Environment & Science Party (ESP)", "Future", "Evocratic Party", "Evidence-Based Policy", "Progressive Alliance",
    "The Australia Party", "The Australia Vision Party ", "Progress Party", "Lime",
    "Third Way", "The Real Alternative", "The Agile Party", "Fusion Party Australia",
    "The Rational Collective", "Fusion (aka the Fusion Party of Australia).", "FUSION", "Australian Fusion League",
    "Connect or Connection Party", "Australian Freedom League", "The Rational Alliance", "Good Future Australia",
    "The Secular Science Party", "Democracy and Labour Party ", "The Teals", "The New Progressive Movement",
    "The Realignment Party", "N/A",
    "Science and Engineering Technology Party", "Innovation Paradise", "Humanity Party"
}

sortable_names = {}
for name in raw_names:
    sorting_key = name if not name.lower().startswith('the ') else name[4:]
    sortable_names[sorting_key.strip()] = name.strip()

sorted_names = [sortable_names[key] for key in sorted(sortable_names.keys())]

batch_size = 10


def clear_questions(forms_service, form_id: str):
    # More reliable than updating the questions
    existing = forms_service.forms().get(formId=form_id).execute()
    print(f"There are {len(existing.get('items', []))} existing items")
    indices = list(range(len(existing.get("items", []))))
    for b in range(1, (len(indices) // batch_size) + 1):
        batch = indices[:batch_size]
        indices = indices[batch_size:]
        if not batch:
            continue
        print(f"Deleting questions {batch}")
        body = {
            "requests": [
                {
                    "deleteItem": {
                        "location":
                            {"index": i}
                    }
                }
                for i in range(len(batch))]
        }
        deletion = forms_service.forms().batchUpdate(formId=form_id, body=body).execute()
        print(f"Deletion: {deletion}")


def submit_batch(questions: List[dict], forms_service, form_id: str):
    body = {"requests": questions}
    result = forms_service.forms().batchUpdate(formId=form_id, body=body).execute()
    questions.clear()


initial_questions = [{
        "createItem": {
            "item": {
                "title": "What is your name? (for deduplication)",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False
                        }
                    }
                }
            },
            "location": {
                "index": 0
            }
        }
    }]

closing_questions: Dict[str, Tuple[int, str]] = {
    "What is the switching cost, from the brand recognition "
        "already achieved under \"Fusion\"? 🔀 (weighting: 1)": (1, "scaleQuestion"),
}


def create_questions_in_form(forms_service, form_id: str):
    questions = initial_questions.copy()
    location_counter = len(initial_questions)
    for question_text, details in naming_questions.items():
        print(f"Adding questions for {question_text[:7]}…")
        body_type = details[1]
        for n, name in enumerate(sorted_names):
            if n == 1:
                # Shorten the question to just the Unicode
                question_text = question_text.rsplit("(")[0].strip()[-1:]
            questions.append(
                {
                    "createItem": {
                        "item": {
                            "title": name + ": " + question_text,
                            "questionItem": {
                                "question": {
                                    "required": True,
                                    body_type: question_body[body_type]
                                }
                            }
                        },
                        "location": {
                            "index": location_counter
                        }
                    }
                })
            location_counter += 1
            if len(questions) > batch_size:
                submit_batch(questions, forms_service, form_id=form_id)
    if len(questions) > batch_size:
        submit_batch(questions, forms_service, form_id=form_id)
    print("Adding closing questions")
    for question_text, details in closing_questions.items():
        print(f"Adding questions for {question_text[:7]}…")
        body_type = details[1]
        questions.append(
            {
                "createItem": {
                        "item": {
                            "title": question_text,
                            "questionItem": {
                                "question": {
                                    "required": True,
                                    body_type: question_body[body_type]
                                }
                            }
                        },
                        "location": {
                            "index": location_counter
                        }
                    }
                })
        location_counter += 1
    print(f"Submitting final batch of {len(questions)} questions")
    submit_batch(questions, forms_service, form_id=form_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="This program adds questions to a form"
    )
    parser.add_argument(
        "--form-id",
        type=str,
        default="1H1xtqtTjUfiP_HrESN6QsLkOxoMltvBmuUScbHnvRs4",
        help="The identifier for the form being updated",
    )
    args = parser.parse_args()
    forms_service = get_authenticated_forms_service()
    clear_questions(forms_service=forms_service, form_id=args.form_id)
    create_questions_in_form(forms_service=forms_service, form_id=args.form_id)
