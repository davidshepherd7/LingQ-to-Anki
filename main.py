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


def anki_connect_list_decks():
    return anki_request("deckNames")


def anki_connect_list_models():
    return anki_request("modelNames")


def anki_connect_model_fields(model_name: str) -> List[str]:
    return anki_request("modelFieldNames", {"modelName": model_name})


def anki_connect_add_note(deck: str, model: str, fields: Dict[str, str]):
    return anki_request(
        "addNote",
        {
            "note": {
                "deckName": deck,
                "modelName": model,
                "fields": fields,
                "options": {"allowDuplicate": False},
                "tags": ["lingq"],
            }
        },
    )


def lingq_login(username, password):
    auth = requests.post(
        "https://www.lingq.com/api/api-token-auth/",
        data={"username": username, "password": password},
    )
    auth.raise_for_status()
    return auth.json()["token"]


def lingq_list_languages(token) -> List[str]:
    r = requests.get(
        "https://www.lingq.com/api/languages",
        headers={"Authorization": "Token {}".format(token)},
    )
    r.raise_for_status()
    return [l["code"] for l in r.json()]


def lingq_list_cards(token: str, language_code: str):
    r = requests.get(
        f"https://www.lingq.com/api/v2/{language_code}/cards",
        params={"sort": "date"},
        headers={"Authorization": "Token {}".format(token)},
    )
    r.raise_for_status()
    x = r.json()

    results = x["results"]
    # TODO: pagination?
    assert len(results) == x["count"]
    return results


def parse_arguments(argv):
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


def main(argv):
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
        cards = lingq_list_cards(token, args.language)

        for card in cards:
            term = card["term"]
            translation = card["hints"][0]["text"]
            print("Adding card", term, "->", translation)
            if not args.dry_run:
                note_id = anki_connect_add_note(
                    args.deck, args.model, {"Front": term, "Back": translation}
                )
                if note_id is None:
                    print("Card was a duplicate, skipped")
    else:
        print(f"No such command: {args.command}")
        return 1

    return 0


# If this script is run from a shell then run main() and return the result.
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
