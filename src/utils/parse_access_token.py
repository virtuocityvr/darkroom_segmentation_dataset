import json
import os

def get_access_token():
    config_path = os.path.expanduser("~/darkroom-config/auth_prod.json")
    with open(config_path, 'r') as fp:
        access_json = json.load(fp)
        return access_json["token_type"] + " " + access_json["access_token"]

def get_access_token_staging(): 
    config_path = os.path.expanduser("~/darkroom-config/auth_staging.json")
    with open(config_path, 'r') as fp:
        access_json = json.load(fp)
        return access_json["token_type"] + " " + access_json["access_token"]
