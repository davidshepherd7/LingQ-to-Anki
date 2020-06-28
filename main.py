#!/usr/bin/env python3

import json
import sys
import argparse
from typing import List, Optional, Dict, Any
import requests


def anki_request(action: str, params: Optional[Dict[str, Any]] = None) -> Any:
    r = requests.get(
        "http://localhost:8765",
        json={"action": action, "params": params or {}, "version": 6},
    )
    r.raise_for_status()

    j = r.json()

    error = j.get("error")
    if error is not None:
        raise Exception(f"Anki connect returned error: {error}")

    return j["result"]


def anki_connect_version() -> int:
    return int(anki_request("version"))


def anki_connect_list_decks() -> Any:
    return anki_request("deckNames")


def anki_connect_list_models() -> Any:
    return anki_request("modelNames")


def anki_connect_model_fields(model_name: str) -> List[str]:
    return anki_request("modelFieldNames", {"modelName": model_name})


def anki_connect_add_notes(note_data: List[Dict[str, str]]) -> Any:
    return anki_request(
        "addNotes",
        {
            "notes": note_data
        },
    )


def lingq_login(username: str, password: str) -> str:
    auth = requests.post(
        "https://www.lingq.com/api/api-token-auth/",
        data={"username": username, "password": password},
    )
    auth.raise_for_status()
    return auth.json()["token"]


def lingq_list_languages(token: str) -> List[str]:
    r = requests.get(
        "https://www.lingq.com/api/languages",
        headers={"Authorization": "Token {}".format(token)},
    )
    r.raise_for_status()
    return [l["code"] for l in r.json()]


def list_unlearned_cards(token: str, language_code: str) -> List[Any]:
    r = requests.get(
        f"https://www.lingq.com/api/v2/{language_code}/cards",
        params={"sort": "date", "status": "0"},
        headers={"Authorization": "Token {}".format(token)},
    )
    r.raise_for_status()
    x = r.json()

    results = x["results"]
    # TODO: pagination?
    assert len(results) == x["count"]
    return results



def parse_arguments(argv: List[str]) -> Any:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    decks = subparsers.add_parser("decks")

    models = subparsers.add_parser("models")

    model = subparsers.add_parser("model")
    model.add_argument("model_name")

    langs = subparsers.add_parser("langs")
    langs.add_argument("--username", help="", required=True)
    langs.add_argument("--password", help="", required=True)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--username", help="", required=True)
    import_parser.add_argument("--password", help="", required=True)
    import_parser.add_argument("--language", help="", required=True)
    import_parser.add_argument("--deck", help="")
    import_parser.add_argument("--model", help="")
    import_parser.add_argument("--dry-run", action="store_true", default=False)

    args = parser.parse_args(argv)
    return args


def main(argv: List[str]) -> int:
    args = parse_arguments(argv)

    if args.command == "decks":
        print(
            "Connected to Ankiconnect version", anki_connect_version(), file=sys.stderr
        )
        print(*anki_connect_list_decks(), sep="\n")
    elif args.command == "models":
        print(
            "Connected to Ankiconnect version", anki_connect_version(), file=sys.stderr
        )
        print(*anki_connect_list_models(), sep="\n")
    elif args.command == "model":
        print(
            "Connected to Ankiconnect version", anki_connect_version(), file=sys.stderr
        )
        print(*anki_connect_model_fields(args.model_name), sep="\n")
    elif args.command == "langs":
        token = lingq_login(args.username, args.password)
        langs = lingq_list_languages(token)
        print(*langs, sep="\n")
    elif args.command == "import":
        print(
            "Connected to Ankiconnect version", anki_connect_version(), file=sys.stderr
        )

        token = lingq_login(args.username, args.password)
        # NOTE: This only imports new(ish) cards (status 1)
        cards = list_unlearned_cards(token, args.language)

        notes_to_create = [
            {"deckName": args.deck,
            "modelName": args.model,
            "fields": {
                "Front": card["term"],
                "Back": card["hints"][0]["text"],
            },
             "tags": "lingq",
            }
            for card in cards
            # TODO: warn about cards with no translations
            if len(card["hints"]) > 0
        ]


        if args.dry_run:
            for card in notes_to_create:
                print("Would try to add card", card["fields"]["Front"], "->", card["fields"]["Back"])
        else:
            note_ids = anki_connect_add_notes(notes_to_create)
            for i, note_id in enumerate(note_ids):
                card = notes_to_create[i]
                if note_id is None:
                    print("Card was a duplicate:", card["fields"]["Front"])
                else:
                    print("Added card:", card["fields"]["Front"], "->", card["fields"]["Back"])

            valid_ids = [n for n in note_ids if n is not None]
            print(f"{len(valid_ids)} new cards added")
    else:
        print(f"No such command: {args.command}")
        return 1

    return 0


# If this script is run from a shell then run main() and return the result.
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
