import json
from argparse import ArgumentParser
from subprocess import Popen

from flask import Flask, request
from requests import post

app = Flask(__name__)


@app.route("/", methods=["POST"])
def github_payload():
    headers = request.headers
    event = headers.get("X-GitHub-Event")
    data = request.json
    event_full_name = event
    if action := data.get("action", ""):
        event_full_name = f"{event}.{action}"
    print("-" * 42 + ">  JSON saved  <" + "-" * 42)
    print(f"Event: {event_full_name}", end="")
    if repo := data.get("repository"):
        print(f" - Repo: {repo['full_name']}", end="")
    print()
    file_name = f"payloads/{event_full_name}.json"
    with open(file_name, "w") as file:
        json.dump(
            {
                "headers": dict[str, str](headers),
                "data": data,
            },
            file,
        )
    print("-" * 100)

    return "Ok"


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--record", default=False, action="store_true")
    parser.add_argument("--play", nargs=1)
    parser.add_argument("--installation_target_id", nargs=1)
    parser.add_argument("--installation_id", nargs=1)
    args = parser.parse_args()
    if args.record:
        print(1)
        with Popen("smee -u https://smee.io/polidoro-testing -p 3333 -P /".split()) as p:
            print(2)
            app.debug = True
            app.run(port=3333)
            print(3)
    elif payload := args.play:
        with open(payload[0]) as file:
            payload = json.load(file)
        headers = payload["headers"]
        data = payload["data"]

        if args.installation_target_id:
            headers["X-GitHub-Hook-Installation-Target-ID"] = args.installation_target_id[0]
        if args.installation_id:
            data["installation"]["id"] = args.installation_id[0]
        print(post(headers=headers, json=data, url="http://127.0.0.1:5000"))
