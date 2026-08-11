import json


def load_json_data(path: str) -> dict:
    with open(path, "r") as file:
        data = json.load(file)

    return data