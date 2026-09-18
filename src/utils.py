import json

def import_json(path):


    with open(path, "r") as f:
        data = json.load(f)

    return data