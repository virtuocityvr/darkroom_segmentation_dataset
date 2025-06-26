import os

from src.utils.httpHelper import *
from urllib.parse import urlparse


import json
from src.utils.parse_access_token import get_access_token

def init_auth_token():
    auth_token = get_access_token()
    return auth_token

def download_floorplan(dimensions_url):
    final_section_floorplans_file_paths=[]

    auth_token = init_auth_token()
    # The given URL
    url = "https://dimensions.hellopupil.com/processedCaptures/73238/sections/6/floorplans/1019834/annotation"

    # Parse the URL
    parsed_url = urlparse(url)

    # Split the path to extract components
    path_parts = parsed_url.path.split('/')

    # Initialize a dictionary to hold the IDs
    id_map = {}

    # Iterate through the path parts and identify IDs based on the keywords
    for i, part in enumerate(path_parts):
        if part == 'processedCaptures':
            id_map['processed_capture_id'] = path_parts[i + 1]
        elif part == 'sections':
            id_map['section_id'] = path_parts[i + 1]
        elif part == 'floorplans':
            id_map['floorplan_id'] = path_parts[i + 1]

    # Extracted IDs
    processed_capture_id = id_map.get('processed_capture_id')
    section_id = id_map.get('section_id')
    floorplan_id = id_map.get('floorplan_id')
    floorplan_response = getFloorplanResponse(processed_capture_id,section_id, floorplan_id,auth_token)
    floorplan_json =floorplan_response.json()
    floorplan_json_filename = f'{processed_capture_id}_{section_id}_{floorplan_id}.json'
    floorplan_json_download_root = "../data/floorplan_json/"
    if not os.path.exists(floorplan_json_download_root):
        os.makedirs(floorplan_json_download_root, exist_ok=True)

    json_download_dir = f"{floorplan_json_download_root}/{processed_capture_id}"
    if not os.path.exists(json_download_dir):
        os.mkdir(json_download_dir)

    with open(f"{json_download_dir}/{floorplan_json_filename}", 'w') as fp:
        json.dump(floorplan_json, fp, indent=4)
    abs_path = os.path.abspath(os.path.join(json_download_dir, floorplan_json_filename))
    final_section_floorplans_file_paths.append(abs_path)
    return  final_section_floorplans_file_paths


def download_all_final_floorplans(processed_capture_id: int):
    final_section_floorplans_file_paths=[]
    auth_token = init_auth_token()
    floorplan_json_download_root = "./data/floorplan_json/"
    if not os.path.exists(floorplan_json_download_root):
        os.makedirs(floorplan_json_download_root, exist_ok=True)

    processed_capture_id = processed_capture_id
    json_download_dir = f"{floorplan_json_download_root}/{processed_capture_id}"
    if not os.path.exists(json_download_dir):
        os.mkdir(json_download_dir)

    response = getProcessedCapture(processed_capture_id, auth_token)
    y = response.json()
    publishedState = y['publishedState']

    if(publishedState =="PUBLISHED"):
        section_response = getSections(processed_capture_id, auth_token).json()
        floors = section_response['floors']
        # Iterating through the floors
        for floor_key in floors.keys():
            floor = floors[floor_key]  # Accessing each floor's data

            for section_key in floor.keys():
                sections = floor[section_key]
                for section in sections:
                    if section['final']==True:
                        final_section_json = section
                        final_section_filename = f"{processed_capture_id}_floor{floor_key }_section{section_key}.json"
                        final_section_file_path = os.path.abspath(os.path.join(json_download_dir, final_section_filename))
                        with open(f"{json_download_dir}/{final_section_filename}", 'w') as fp:
                            json.dump(final_section_json, fp, indent=4)
                        final_section_floorplans_file_paths.append(final_section_file_path)

    return final_section_floorplans_file_paths


    


if __name__ == '__main__':
    final_sections_file_paths = download_all_final_floorplans(73238)
    # download_floorplan('https://dimensions.hellopupil.com/processedCaptures/73238/sections/6/floorplans/1019834/annotation')

