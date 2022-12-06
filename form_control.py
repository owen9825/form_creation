from __future__ import print_function

import argparse
import random
from typing import Dict

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

naming_questions: Dict[str, str] = {
    "How easily would this name be understood by the mainstream electorate? 🤔": "scaleQuestion",
    "How well does this name engender the aspirations of the electorate? 🌠": "scaleQuestion",
    "How well does this name reflect the party's agreed values? Individual Freedom; Advancement; Deep Ecology; Safety; "
        "Ethical Conduct; Equity 🌟": "scaleQuestion",
    "How effectively could this name be used for advertisement; identity; and graphic-design aspects of "
    "public relations? 📺": "scaleQuestion",
    "How well does this name allow for long-term investment and recognition, for relevance and support over a "
    "long timeframe? ⏳": "scaleQuestion",
}

raw_names = {
    "Equalib", "Australian Democrats", "Science Party", "Fusion Party Australia", "Innovation Party", "Fusion",
    "Fusion Party", "Reason Party", "Progressives", "One but Many, we are Australian", "Fusion Australia Party",
    "Intergenerational Equity Party", "Fusion", "ISIS Party", "The AEGIS Party", "Australian Democracy Party",
    "Rational", "Environment & Science Party (ESP)", "Future", "Evocratic Party", "Evidence-Based Policy",
    "Progressive Alliance", "The Australia Party", "The Australian Vision Party", "Progress Party", "Progressive Party",
    "Eco Liberals", "Lime", "Third Way", "fusionparty.org.au", "The Real Alternative", "The Agile Party",
    "Fusion Party Australia", "The Rational Collective", "Fusion (aka the Fusion Party of Australia)", "FUSION",
    "Australian Fusion League", "Connect Party / Connection Party", "Australian Freedom League",
    "The Rational Alliance", "Good Future Australia", "The Secular Science Party", "Democracy and Labour Party",
    "The Teals", "The New Progressive Movement", "The Realignment Party",
    "The Modern Progressives − UBI, Climate Justice, etc", "Science and Engineering Technology Party",
    "Innovation Paradise", "Humanity Party", "Fusion"
}

sortable_names = {}
for name in raw_names:
    sorting_key = name if not name.lower().startswith('the ') else name[4:]
    sortable_names[sorting_key] = name

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


def create_questions_in_form(forms_service, form_id: str):
    location_counter = 0
    for question_text, body_type in naming_questions.items():
        questions = []
        for name in sorted_names:
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
        body = {"requests": questions}
        result = forms_service.forms().batchUpdate(formId=form_id, body=body).execute()
        print(f"Added questions for {name}: {result}")


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
