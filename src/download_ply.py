from utils.httpHelper import getProcessedCapture, getFloorplanResponse, getSections, getProcessedCaptureFloorplan
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

def get_s3_cache_key(media_ref):
    """Generate a cache key for S3 file existence check"""
    return f"{media_ref['bucket']}_{media_ref['path'].replace('/', '_')}"

def get_cached_s3_exists(cache_dir, media_ref):
    """Get cached S3 file existence result"""
    cache_key = get_s3_cache_key(media_ref)
    cache_file = os.path.join(cache_dir, f"s3_exists_{cache_key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)['exists']
    return None

def save_s3_exists_to_cache(cache_dir, media_ref, exists):
    """Save S3 file existence result to cache"""
    cache_key = get_s3_cache_key(media_ref)
    cache_file = os.path.join(cache_dir, f"s3_exists_{cache_key}.json")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump({'exists': exists}, f)

def get_cached_file_size(cache_dir, media_ref):
    """Get cached file size result"""
    cache_key = get_s3_cache_key(media_ref)
    cache_file = os.path.join(cache_dir, f"s3_size_{cache_key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)['size']
    return None

def save_file_size_to_cache(cache_dir, media_ref, size):
    """Save file size result to cache"""
    cache_key = get_s3_cache_key(media_ref)
    cache_file = os.path.join(cache_dir, f"s3_size_{cache_key}.json")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump({'size': size}, f)

def transform_media_reference(original_media_ref, section_number, missionControlAuthToken):
    """Transform the media reference into the required format"""
    # Split the path into parts
    parts = original_media_ref['path'].split('/')

    # parts is a list of strings in which one of the item is "uploaded_ply". The next item in the list is the original floorplan_id
    #We need to get the original floorplan_id and use it to construct the new path
    for i, part in enumerate(parts):
        if part == 'uploaded_ply':
            original_floorplan_id = parts[i+1]
            break
    
    original_floorplan_response = getProcessedCaptureFloorplan(original_floorplan_id, missionControlAuthToken).json()
    # Construct the new path
    original_section_number = original_floorplan_response['section']
    
    base_path = '/'.join(parts[1:3])
    
    # Get the base name without the __xxxxx suffix
    # We have to ignore the __xxxxx suffix but just splitting  by __ and 
    # taking the first part might not work as there are multiple 
    # occurances of __ and we need the last one
    
    base_name = parts[-1].rsplit('__', 1)[0]
    # print(base_name)
    
    # Construct the new path
    new_path = f"{base_path}/axis-alignment/{original_section_number}/{base_name}.ply"
    
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

def analyze_device_type(floorplan, num_uploaded_scans):
    """
    Analyze the device type based on scan types and uploaded scan count.
    
    Args:
        floorplan: The floorplan object containing potreeConvertedScansResponse
        num_uploaded_scans: Number of uploaded scans in the floorplan
    
    Returns:
        tuple: (device_type, has_point_clouds)
    """
    if len(floorplan['potreeConvertedScansResponse']) == 0:
        return "IMAGE_ONLY", False
    
    # Check if it's BLK360 (has at least 1 uploaded scan)
    if num_uploaded_scans > 0:
        return "BLK360", True
    else:
        # Check if it's BLK2GO (has SUBSAMPLED or CLASLAM scans but no uploaded scans)
        has_subsampled_or_claslam = False
        for scan in floorplan['potreeConvertedScansResponse']:
            if scan['type'] in ['SUBSAMPLED', 'CLASLAM']:
                has_subsampled_or_claslam = True
                break
        
        if has_subsampled_or_claslam:
            return "BLK2GO", True
        else:
            return "UNKNOWN", True

def print_floorplan_measurements(capture_id, floorplan, device_type, output_file=None):
    """
    Print non-null floorplan measurements for sections with point clouds.
    
    Args:
        capture_id: The capture ID
        floorplan: The floorplan object
        device_type: The device type (BLK360, BLK2GO, etc.)
        output_file: File object to write to (if None, prints to console)
    """
    output = []
    output.append(f"\nCapture ID: {capture_id}")
    output.append(f"Section: {floorplan['section']}")
    output.append(f"Floorplan ID: {floorplan['id']}")
    output.append(f"Device Type: {device_type}")
    
    if 'floorplanMeasurement' in floorplan:
        output.append(f"Floorplan Measurements (non-null values):")
        measurements = floorplan['floorplanMeasurement']
        for key, value in measurements.items():
            if value is not None:
                if isinstance(value, dict) and 'amount' in value and 'unit' in value:
                    output.append(f"  {key}: {value['amount']} {value['unit']}")
                else:
                    output.append(f"  {key}: {value}")
    else:
        output.append(f"No floorplan measurements found")
    
    if output_file:
        output_file.write('\n'.join(output) + '\n')
    else:
        print('\n'.join(output))

def print_scan_details(capture_id, floorplan, num_uploaded_scans, output_file=None):
    """
    Print detailed scan information for sections with 0 or multiple uploaded scans.
    
    Args:
        capture_id: The capture ID
        floorplan: The floorplan object
        num_uploaded_scans: Number of uploaded scans
        output_file: File object to write to (if None, prints to console)
    """
    output = []
    output.append(f"\nCapture ID: {capture_id}")
    output.append(f"Section: {floorplan['section']}")
    output.append(f"Floorplan ID: {floorplan['id']}")
    output.append(f"Number of uploaded scans: {num_uploaded_scans}")
    
    if num_uploaded_scans > 1:
        output.append(f"Scan details:")
        for i, scan in enumerate(floorplan['potreeConvertedScansResponse']):
            if scan['type'] == 'UPLOADED':
                output.append(f"  Scan {i+1}: {scan}")
    elif num_uploaded_scans == 0:
        output.append(f"All potree converted scans:")
        if 'potreeConvertedScansResponse' in floorplan.keys():
            for i, scan in enumerate(floorplan['potreeConvertedScansResponse']):
                output.append(f"  Scan {i+1} (Type: {scan['type']}): {scan}")
        else:
            output.append("  No potree converted scans found")
    
    if output_file:
        output_file.write('\n'.join(output) + '\n')
    else:
        print('\n'.join(output))

def process_final_section(processed_capture_id, section, processed_capture_json, stats, output_file=None):
    """
    Process a final section and update statistics.
    
    Args:
        processed_capture_id: The capture ID
        section: The section object
        processed_capture_json: The processed capture JSON
        stats: Dictionary containing all statistics counters
        output_file: File object to write analysis output to
    
    Returns:
        tuple: (updated_stats, num_uploaded_scans, uploaded_scan, final_floorplan_id, floorplan)
    """
    stats['total_final_sections'] += 1
    final_floorplan_id = section['floorplanId']
    floorplan = [floorplan for floorplan in processed_capture_json['floorplans'] if floorplan['id'] == final_floorplan_id][0]
    
    # Count uploaded scans
    num_uploaded_scans = 0
    uploaded_scan = None
    
    if 'potreeConvertedScansResponse' in floorplan.keys():
        if len(floorplan['potreeConvertedScansResponse']) == 0:
            # Print basic details for image-only sections
            output = []
            output.append(f"\nCapture ID: {processed_capture_id}")
            output.append(f"Section: {floorplan['section']}")
            output.append(f"Floorplan ID: {floorplan['id']}")
            output.append("This is an image only section with no scans")
            output.append("-" * 50)
            
            if output_file:
                output_file.write('\n'.join(output) + '\n')
            else:
                print('\n'.join(output))
            
            stats['num_image_only_sections'] += 1
            return stats, 0, None, final_floorplan_id, floorplan
            
        for scan in floorplan['potreeConvertedScansResponse']:
            if scan['type'] == 'UPLOADED':
                num_uploaded_scans += 1
                uploaded_scan = scan
    
    # Count in distribution
    if num_uploaded_scans not in stats['uploaded_scans_distribution']:
        stats['uploaded_scans_distribution'][num_uploaded_scans] = 0
    stats['uploaded_scans_distribution'][num_uploaded_scans] += 1
    
    # Device type analysis
    device_type, has_point_clouds = analyze_device_type(floorplan, num_uploaded_scans)
    
    if has_point_clouds:
        stats['total_sections_with_point_clouds'] += 1
        
        if device_type == "BLK2GO":
            stats['total_blk2go_sections'] += 1
        elif device_type == "BLK360":
            stats['total_blk360_sections'] += 1
        
        # Print floorplan measurements for sections with point clouds
        print_floorplan_measurements(processed_capture_id, floorplan, device_type, output_file)
    
    # Print details for sections with 0 or multiple uploaded scans
    if num_uploaded_scans == 0 or num_uploaded_scans > 1:
        print_scan_details(processed_capture_id, floorplan, num_uploaded_scans, output_file)
    
    # Add separator between sections
    if output_file:
        output_file.write("-" * 50 + "\n")
    
    return stats, num_uploaded_scans, uploaded_scan, final_floorplan_id, floorplan

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
    
    # Device type counters
    total_sections_with_point_clouds = 0
    total_blk2go_sections = 0
    total_blk360_sections = 0
    
    # S3 cache statistics
    s3_cache_hits = 0
    s3_cache_misses = 0
    s3_size_cache_hits = 0
    s3_size_cache_misses = 0
    
    # Initialize stats dictionary
    stats = {
        'total_final_sections': 0,
        'uploaded_scans_distribution': {},
        'num_image_only_sections': 0,
        'total_sections_with_point_clouds': 0,
        'total_blk2go_sections': 0,
        'total_blk360_sections': 0
    }

    # Open analysis output file
    with open('analysis_output.txt', 'w') as analysis_file:
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
                                    # Process the final section using the helper function
                                    stats, num_uploaded_scans, uploaded_scan, final_floorplan_id, floorplan = process_final_section(processed_capture_id, section, processed_capture_json, stats)

                                    # Only process if there is exactly one uploaded scan
                                    if num_uploaded_scans == 1:
                                        # Transform the media reference
                                        new_media_ref = transform_media_reference(uploaded_scan['mediaReference'], floorplan['section'], missionControlAuthToken)
                                        # Check if the transformed file exists in S3
                                        exists = get_cached_s3_exists(CACHE_DIR, new_media_ref)
                                        if exists is None:
                                            # Not in cache, check S3 and cache the result
                                            exists = check_s3_file_exists(new_media_ref)
                                            save_s3_exists_to_cache(CACHE_DIR, new_media_ref, exists)
                                            s3_cache_misses += 1
                                        else:
                                            s3_cache_hits += 1
                                        
                                        if not exists:  
                                            print(f"New media reference does not exist: {new_media_ref}")
                                            print(uploaded_scan['mediaReference'],"\n",new_media_ref,)

                                        if exists:
                                            found_count += 1
                                            dimensions_url = f"https://dimensions.hellopupil.com/processedCaptures/{processed_capture_id}/sections/{floorplan['section']}/floorplans/{final_floorplan_id}/annotation"
                                            
                                            # Get file size (cached)
                                            file_size = get_cached_file_size(CACHE_DIR, new_media_ref)
                                            if file_size is None:
                                                # Not in cache, get from S3 and cache the result
                                                file_size = get_file_size(new_media_ref)
                                                save_file_size_to_cache(CACHE_DIR, new_media_ref, file_size)
                                                s3_size_cache_misses += 1
                                            else:
                                                s3_size_cache_hits += 1
                                            total_size_bytes += file_size
                                            
                                            # Add download command to the list
                                            local_path = f"downloaded_ply_files/capture_{processed_capture_id}_section_{floorplan['section']}.ply"
                                            s3_path = f"s3://{new_media_ref['bucket']}/{new_media_ref['path']}"
                                            download_commands.append(f"echo 'Downloading {s3_path}...'")
                                            download_commands.append(f"aws s3 cp '{s3_path}' '{local_path}'")
                                            download_commands.append("")

                                            # Save section data to JSON file
                                            section_data = {
                                                'capture_id': processed_capture_id,
                                                'section_id': floorplan['section'],
                                                'floorplan_id': final_floorplan_id,
                                                'dimensions_url': dimensions_url,
                                                'transformed_media_reference': new_media_ref,
                                                'section_details': section,
                                                'file_size_bytes': file_size,
                                                'file_size_human': format_size(file_size),
                                                'local_path': local_path
                                            }
                                            
                                            # Create sections directory if it doesn't exist
                                            os.makedirs('sections', exist_ok=True)
                                            
                                            # Save to JSON file
                                            output_file = f"sections/capture_{processed_capture_id}_section_{floorplan['section']}.json"
                                            with open(output_file, 'w') as f:
                                                json.dump(section_data, f, indent=2)

            except Exception as e:
                print(f"Error processing capture ID {processed_capture_id}: {e}")
                continue  # Continue with next capture ID even if one fails

    # Extract final statistics from the stats dictionary
    total_final_sections = stats['total_final_sections']
    uploaded_scans_distribution = stats['uploaded_scans_distribution']
    num_image_only_sections = stats['num_image_only_sections']
    total_sections_with_point_clouds = stats['total_sections_with_point_clouds']
    total_blk2go_sections = stats['total_blk2go_sections']
    total_blk360_sections = stats['total_blk360_sections']

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

    # Print device type statistics
    print(f"\n{'='*50}")
    print(f"DEVICE TYPE ANALYSIS")
    print(f"{'='*50}")
    print(f"Total final sections with point clouds: {total_sections_with_point_clouds}")
    print(f"Total BLK2GO sections: {total_blk2go_sections}")
    print(f"Total BLK360 sections: {total_blk360_sections}")
    print(f"Image-only sections (no point clouds): {num_image_only_sections}")
    print(f"{'='*50}")

    # Print S3 cache statistics
    print(f"\n{'='*50}")
    print(f"S3 CACHE STATISTICS")
    print(f"{'='*50}")
    print(f"S3 existence cache hits: {s3_cache_hits}")
    print(f"S3 existence cache misses: {s3_cache_misses}")
    print(f"Total S3 existence checks: {s3_cache_hits + s3_cache_misses}")
    if s3_cache_hits + s3_cache_misses > 0:
        cache_hit_rate = (s3_cache_hits / (s3_cache_hits + s3_cache_misses)) * 100
        print(f"Existence cache hit rate: {cache_hit_rate:.1f}%")
    
    print(f"\nS3 file size cache hits: {s3_size_cache_hits}")
    print(f"S3 file size cache misses: {s3_size_cache_misses}")
    print(f"Total S3 file size checks: {s3_size_cache_hits + s3_size_cache_misses}")
    if s3_size_cache_hits + s3_size_cache_misses > 0:
        size_cache_hit_rate = (s3_size_cache_hits / (s3_size_cache_hits + s3_size_cache_misses)) * 100
        print(f"File size cache hit rate: {size_cache_hit_rate:.1f}%")
    
    total_api_calls_saved = s3_cache_hits + s3_size_cache_hits
    print(f"\nTotal S3 API calls saved: {total_api_calls_saved}")
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

