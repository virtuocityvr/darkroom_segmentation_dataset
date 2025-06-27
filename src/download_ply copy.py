from utils.httpHelper import getProcessedCapture, getFloorplanResponse, getSections
from utils.parse_access_token import get_access_token
import boto3
import json
import os

def get_cached_response(cache_dir, capture_id, response_type):
    """Get cached response if it exists"""
    cache_file = os.path.join(cache_dir, f"{capture_id}_{response_type}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None

def save_to_cache(cache_dir, capture_id, response_type, data):
    """Save response to cache"""
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{capture_id}_{response_type}.json")
    with open(cache_file, 'w') as f:
        json.dump(data, f)

def transform_media_reference(original_media_ref, section_number):
    """Transform the media reference into the required format"""
    # Split the path into parts
    parts = original_media_ref['path'].split('/')
    
    # Get the parts we need (from first to third forward slash)
    base_path = '/'.join(parts[1:3])
    
    # Get the base name without the __xxxxx suffix
    base_name = parts[-1].split('__')[0]
    
    # Construct the new path
    new_path = f"{base_path}/axis-alignment/{section_number}/{base_name}.ply"
    
    # Create new media reference
    new_media_ref = {
        'path': new_path,
        'bucket': 'pupil-darkroom-intermediate-media-prod'
    }
    
    return new_media_ref

def check_s3_file_exists(media_ref):
    """Check if a file exists in S3 bucket"""
    try:
        s3_client = boto3.client('s3')
        s3_client.head_object(
            Bucket=media_ref['bucket'],
            Key=media_ref['path']
        )
        return True
    except Exception as e:
        return False

def get_file_size(media_ref):
    """Get file size from S3 in bytes"""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.head_object(
            Bucket=media_ref['bucket'],
            Key=media_ref['path']
        )
        return response['ContentLength']
    except Exception as e:
        return 0

def format_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

if __name__ == '__main__':
    # Create cache directory
    CACHE_DIR = 'api_cache'
    
    # Read capture IDs from file
    with open('processed_capture_ids.txt', 'r') as f:
        capture_ids = [line.strip() for line in f if line.strip()]

    missionControlAuthToken = get_access_token()
    found_count = 0  # Counter for found files
    total_size_bytes = 0  # Counter for total size

    # Create a list to store download commands
    download_commands = []
    download_commands.append("#!/bin/bash")
    download_commands.append("# Script to download PLY files from S3")
    download_commands.append("mkdir -p downloaded_ply_files")
    download_commands.append("")

    # Statistics counters
    total_final_sections = 0
    uploaded_scans_distribution = {}  # Dictionary to count sections by num_uploaded_scans
    num_image_only_sections = 0
    for processed_capture_id in capture_ids:
        try:
            # Try to get from cache first
            processed_capture_json = get_cached_response(CACHE_DIR, processed_capture_id, 'capture')
            if not processed_capture_json:
                processed_capture_json = getProcessedCapture(processed_capture_id, missionControlAuthToken).json()
                save_to_cache(CACHE_DIR, processed_capture_id, 'capture', processed_capture_json)

            processedCapture_publishedState = processed_capture_json['publishedState']
            if processedCapture_publishedState=="PUBLISHED":
                # Try to get sections from cache
                section_response = get_cached_response(CACHE_DIR, processed_capture_id, 'sections')
                if not section_response:
                    section_response = getSections(processed_capture_id, missionControlAuthToken).json()
                    save_to_cache(CACHE_DIR, processed_capture_id, 'sections', section_response)

                floors = section_response['floors']
                for floor_key in floors.keys():
                    floor = floors[floor_key]  # Accessing each floor's data

                    for section_key in floor.keys():
                        sections = floor[section_key]
                        for section in sections:
                            if section['final'] == True:
                                total_final_sections += 1
                                final_floorplan_id = section['floorplanId']
                                floorplan = [floorplan for floorplan in processed_capture_json['floorplans'] if floorplan['id'] == final_floorplan_id][0]
                                
                                # Count uploaded scans
                                num_uploaded_scans = 0
                                uploaded_scan = None
                                
                                if 'potreeConvertedScansResponse' in floorplan.keys():
                                    if len(floorplan['potreeConvertedScansResponse']) == 0:
                                        print("This is an image only section with no scans")
                                        num_image_only_sections += 1
                                        continue # Skip the rest of the code for this section
                                        
                                    for scan in floorplan['potreeConvertedScansResponse']:
                                        if scan['type'] == 'UPLOADED':
                                            num_uploaded_scans += 1
                                            uploaded_scan = scan  # Store the scan details
                                
                                # Count in distribution
                                if num_uploaded_scans not in uploaded_scans_distribution:
                                    uploaded_scans_distribution[num_uploaded_scans] = 0
                                uploaded_scans_distribution[num_uploaded_scans] += 1
                                
                                # Print details for sections with more than 1 uploaded scan
                                if num_uploaded_scans > 1:
                                    print(f"\nCapture ID: {processed_capture_id}")
                                    print(f"Section: {floorplan['section']}")
                                    print(f"Floorplan ID: {final_floorplan_id}")
                                    print(f"Number of uploaded scans: {num_uploaded_scans}")
                                    print(f"Scan details:")
                                    for i, scan in enumerate(floorplan['potreeConvertedScansResponse']):
                                        if scan['type'] == 'UPLOADED':
                                            print(f"  Scan {i+1}: {scan}")

                                # Print details for sections with 0 uploaded scans
                                if num_uploaded_scans == 0:
                                    print(f"\nCapture ID: {processed_capture_id}")
                                    print(f"Section: {floorplan['section']}")
                                    print(f"Floorplan ID: {final_floorplan_id}")
                                    print(f"Number of uploaded scans: {num_uploaded_scans}")
                                    print(f"All potree converted scans:")
                                    if 'potreeConvertedScansResponse' in floorplan.keys():
                                        for i, scan in enumerate(floorplan['potreeConvertedScansResponse']):
                                            print(f"  Scan {i+1} (Type: {scan['type']}): {scan}")
                                    else:
                                        print("  No potree converted scans found")

                                # Only process if there is exactly one uploaded scan
                                # if num_uploaded_scans == 1:
                                #     # Transform the media reference
                                #     new_media_ref = transform_media_reference(uploaded_scan['mediaReference'], floorplan['section'])
                                    
                                #     # Check if the transformed file exists in S3
                                #     exists = check_s3_file_exists(new_media_ref)
                                #     if exists:
                                #         found_count += 1
                                #         dimensions_url = f"https://dimensions.hellopupil.com/processedCaptures/{processed_capture_id}/sections/{floorplan['section']}/floorplans/{final_floorplan_id}/annotation"
                                        
                                #         # Get file size
                                #         # file_size = get_file_size(new_media_ref)
                                #         # total_size_bytes += file_size
                                        
                                #         print(f"\nFound matching file for capture ID: {processed_capture_id}")
                                #         print(f"Section: {floorplan['section']}")
                                #         print(f"Floorplan ID: {final_floorplan_id}")
                                #         print(f"Dimensions URL: {dimensions_url}")
                                #         print(f"Transformed Media Reference: {new_media_ref}")
                                #         # print(f"File size: {format_size(file_size)}")

                                #         # Add download command to the list
                                #         local_path = f"downloaded_ply_files/capture_{processed_capture_id}_section_{floorplan['section']}.ply"
                                #         s3_path = f"s3://{new_media_ref['bucket']}/{new_media_ref['path']}"
                                #         download_commands.append(f"echo 'Downloading {s3_path}...'")
                                #         download_commands.append(f"aws s3 cp '{s3_path}' '{local_path}'")
                                #         download_commands.append("")

                                #         # Save section data to JSON file
                                #         section_data = {
                                #             'capture_id': processed_capture_id,
                                #             'section_id': floorplan['section'],
                                #             'floorplan_id': final_floorplan_id,
                                #             'dimensions_url': dimensions_url,
                                #             'transformed_media_reference': new_media_ref,
                                #             'section_details': section,
                                #             'file_size_bytes': file_size,
                                #             'file_size_human': format_size(file_size),
                                #             'local_path': local_path
                                #         }
                                        
                                #         # Create sections directory if it doesn't exist
                                #         os.makedirs('sections', exist_ok=True)
                                        
                                #         # Save to JSON file
                                #         output_file = f"sections/capture_{processed_capture_id}_section_{floorplan['section']}.json"
                                #         with open(output_file, 'w') as f:
                                #             json.dump(section_data, f, indent=2)
                                #         print(f"Section data saved to: {output_file}")

        except Exception as e:
            print(f"Error processing capture ID {processed_capture_id}: {e}")
            continue  # Continue with next capture ID even if one fails

    # Print statistics
    print(f"\n{'='*50}")
    print(f"UPLOADED SCANS DISTRIBUTION ANALYSIS")
    print(f"{'='*50}")
    print(f"Total final sections processed: {total_final_sections}")
    print(f"\nDistribution of uploaded scans:")
    print(f"{'Num Uploaded Scans':<20} {'Count':<10} {'Percentage':<10}")
    print(f"{'-'*40}")
    
    for num_scans in sorted(uploaded_scans_distribution.keys()):
        count = uploaded_scans_distribution[num_scans]
        percentage = (count / total_final_sections) * 100
        print(f"{num_scans:<20} {count:<10} {percentage:.1f}%")
    
    print(f"{'='*50}")

    # Write the download script
    with open('download_ply_files.sh', 'w') as f:
        f.write('\n'.join(download_commands))
    
    # Make the script executable
    os.chmod('download_ply_files.sh', 0o755)

    print(f"\nProcessing complete! Found {found_count} matching files in S3.")
    print(f"Total size of all files: {format_size(total_size_bytes)}")
    print(f"\nDownload script has been created: download_ply_files.sh")
    print("To download the files, run: ./download_ply_files.sh")

