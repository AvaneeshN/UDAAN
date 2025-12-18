import json
def load_policy(policy_path: str) -> dict:
    with open(policy_path, "r") as file:
        data = json.load(file)
    return data  # return full policy
