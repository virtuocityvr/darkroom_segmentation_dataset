import logging
from urllib.parse import urlparse
import json
import os
def parse_url_for_ids(url):
    """
    Parse the URL to extract processed_capture_id, section_id, and floorplan_id.
    """
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        id_map = {}
        for i, part in enumerate(path_parts):
            if part == 'processedCaptures':
                id_map['processed_capture_id'] = path_parts[i + 1]
            elif part == 'sections':
                id_map['section_id'] = path_parts[i + 1]
            elif part == 'floorplans':
                id_map['floorplan_id'] = path_parts[i + 1]
        return id_map['processed_capture_id'], id_map['section_id'], id_map['floorplan_id']
    except Exception as e:
        logging.error(f"Error parsing URL: {url}. Error: {str(e)}")
        return None, None, None

def save_json_to_file(json_data, json_path):
    """
    Save the floorplan JSON data to a file.
    """
    try:
        with open(json_path, 'w') as fp:
            json.dump(json_data, fp, indent=4)
        logging.info(f"JSON saved to: {json_path}")
    except Exception as e:
        logging.error(f"Error saving JSON to file: {json_path}. Error: {str(e)}")

def ensure_directory_exists(directory):
    """
    Ensure the specified directory exists; create if it doesn't.
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logging.info(f"Directory created: {directory}")
    except Exception as e:
        logging.error(f"Error creating directory: {directory}. Error: {str(e)}")
