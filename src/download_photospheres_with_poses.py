from utils.httpHelper import  getProcessedCaptureFloorplan, getProcessedCapture
from utils.parse_access_token import get_access_token
import json
import os
import requests
from urllib.parse import urljoin


def download_photosphere(media_reference, local_filename):
    """Download a photosphere from S3 to local file"""
    try:
        bucket = media_reference['bucket']
        path = media_reference['path']
        
        # Construct S3 URL
        if bucket == 'pupil-public':
            url = f"https://pupil-public.s3.amazonaws.com/{path}"
        else:
            url = f"https://{bucket}.s3.amazonaws.com/{path}"
        
        print(f"Downloading: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✓ Downloaded: {local_filename}")
        return True
    except Exception as e:
        print(f"✗ Failed to download {local_filename}: {e}")
        return False


if __name__ == '__main__':
    access_token = get_access_token()
    floorplan_id = 1036787
    processed_capture_id = 73870
    
    if os.path.exists(f"processed_capture_response_{processed_capture_id}.json"):
        with open(f"processed_capture_response_{processed_capture_id}.json", 'r') as f:
            processed_capture_response = json.load(f)
    else:
        processed_capture_response = getProcessedCapture(processed_capture_id, access_token).json()
        with open(f'processed_capture_response_{processed_capture_id}.json', 'w') as f:
            json.dump(processed_capture_response, f)

    # Extract floorplan data for the specified floorplan_id
    floorplans = processed_capture_response.get('floorplans', [])
    target_floorplan = None
    
    for floorplan in floorplans:
        if floorplan.get('id') == floorplan_id:
            target_floorplan = floorplan
            break
    
    if target_floorplan:
        print(f"Found floorplan with ID {floorplan_id}")
        
        # Create output directory
        output_dir = f"photospheres_processed_capture_{processed_capture_id}_floorplan_{floorplan_id}"
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
        
        # Extract all scan origins from all roomplans
        roomplans = target_floorplan.get('roomplans', [])
        all_scan_origins = []
        pose_metadata = []
        
        # Create a mapping of rawScanId to photosphere data from all scenes
        scenes = processed_capture_response.get('scenes', [])
        photosphere_mapping = {}
        
        for scene in scenes:
            scene_id = scene.get('id')
            scene_name = scene.get('name', 'Unknown')
            scene_type = scene.get('type', 'Unknown')
            photospheres = scene.get('photospheres', [])
            
            for photosphere in photospheres:
                raw_scan_id = photosphere.get('rawScanId')
                if raw_scan_id:
                    photosphere_mapping[raw_scan_id] = {
                        'scene_id': scene_id,
                        'scene_name': scene_name,
                        'scene_type': scene_type,
                        'photosphere_id': photosphere.get('id'),
                        'media_reference': photosphere.get('mediaReference'),
                        'original_media_reference': photosphere.get('originalMediaReference'),
                        'is_theta': photosphere.get('isTheta', False)
                    }
        
        print(f"\nFound {len(photosphere_mapping)} photospheres across {len(scenes)} scenes")
        print(f"Found {len(roomplans)} roomplans in floorplan {floorplan_id}")
        print("=" * 80)
        
        for i, roomplan in enumerate(roomplans, 1):
            roomplan_id = roomplan.get('id')
            scene_name = roomplan.get('sceneName', 'Unknown')
            scene_type = roomplan.get('sceneType', 'Unknown')
            scan_origins = roomplan.get('scanOrigins', [])
            
            print(f"\nRoomplan {i}: {scene_name} ({scene_type})")
            print(f"Roomplan ID: {roomplan_id}")
            print(f"Number of scan origins: {len(scan_origins)}")
            print("-" * 60)
            
            for j, scan_origin in enumerate(scan_origins, 1):
                scan_id = scan_origin.get('id')
                raw_scan_id = scan_origin.get('rawScanId')
                point = scan_origin.get('point', {})
                coordinates_cm = point.get('coordinates', [])
                rotation = scan_origin.get('rotationInDegree', 0)
                is_locked = scan_origin.get('isLocked', False)
                
                # Convert coordinates from cm to meters
                coordinates_m = [coord / 100.0 for coord in coordinates_cm]
                
                # Find corresponding photosphere
                photosphere_data = photosphere_mapping.get(raw_scan_id)
                
                print(f"  Scan Origin {j}:")
                print(f"    ID: {scan_id}")
                print(f"    Raw Scan ID: {raw_scan_id}")
                print(f"    Coordinates (cm): {coordinates_cm}")
                print(f"    Coordinates (m): {coordinates_m}")
                print(f"    Rotation: {rotation}°")
                print(f"    Locked: {is_locked}")
                
                if photosphere_data:
                    print(f"    ✓ Found matching photosphere:")
                    print(f"      Scene: {photosphere_data['scene_name']} ({photosphere_data['scene_type']})")
                    print(f"      Photosphere ID: {photosphere_data['photosphere_id']}")
                    print(f"      Media Reference: {photosphere_data['media_reference']}")
                    print(f"      Is Theta: {photosphere_data['is_theta']}")
                    
                    # Create local filename for the photosphere
                    local_filename = f"photosphere_{scan_id}.jpg"
                    local_filepath = os.path.join(output_dir, local_filename)
                    
                    # Download the photosphere
                    download_success = download_photosphere(photosphere_data['media_reference'], local_filepath)
                    
                    # Add to all scan origins list with simplified schema (for original file)
                    all_scan_origins.append({
                        'roomplan_name': scene_name,
                        'scan_origin_id': scan_id,
                        'raw_scan_id': raw_scan_id,
                        'coordinates': coordinates_m,  # Now in meters
                        'rotation': rotation,
                        'media_reference': photosphere_data['media_reference']
                    })
                    
                    # Add to pose metadata (simplified version for pose_metadata.json)
                    pose_metadata.append({
                        'roomplan_name': scene_name,
                        'coordinates': coordinates_m,  # Now in meters
                        'rotation': rotation,
                        'local_filename': local_filename if download_success else None
                    })
                    
                else:
                    print(f"    ✗ No matching photosphere found for raw_scan_id: {raw_scan_id}")
                    
                    # Add to all scan origins list without photosphere data
                    all_scan_origins.append({
                        'roomplan_name': scene_name,
                        'scan_origin_id': scan_id,
                        'raw_scan_id': raw_scan_id,
                        'coordinates': coordinates_m,  # Now in meters
                        'rotation': rotation,
                        'media_reference': None
                    })
                    
                    # Add to pose metadata without photosphere data
                    pose_metadata.append({
                        'roomplan_name': scene_name,
                        'coordinates': coordinates_m,  # Now in meters
                        'rotation': rotation,
                        'local_filename': None
                    })
        
        print(f"\n" + "=" * 80)
        print(f"SUMMARY: Total scan origins found: {len(all_scan_origins)}")
        
        # Count how many have photosphere data
        with_photosphere = sum(1 for so in all_scan_origins if so['media_reference'] is not None)
        without_photosphere = len(all_scan_origins) - with_photosphere
        
        print(f"Scan origins with photosphere data: {with_photosphere}")
        print(f"Scan origins without photosphere data: {without_photosphere}")
        
        # Save scan origins to a separate file with simplified schema
        scan_origins_filename = f"scan_origins_{floorplan_id}.json"
        with open(scan_origins_filename, 'w') as f:
            json.dump(all_scan_origins, f, indent=2)
        print(f"Scan origins data saved to {scan_origins_filename}")
        
        # Save pose metadata to the output directory
        pose_metadata_filename = os.path.join(output_dir, "pose_metadata.json")
        with open(pose_metadata_filename, 'w') as f:
            json.dump(pose_metadata, f, indent=2)
        print(f"Pose metadata saved to {pose_metadata_filename}")
        
        # Save the floorplan data to a separate file
        floorplan_filename = f"floorplan_{floorplan_id}.json"
        with open(floorplan_filename, 'w') as f:
            json.dump(target_floorplan, f, indent=2)
        print(f"Floorplan data saved to {floorplan_filename}")
        
        print(f"\nAll files saved to directory: {output_dir}")
        
    else:
        print(f"Floorplan with ID {floorplan_id} not found in processed capture response")
        print(f"Available floorplan IDs: {[fp.get('id') for fp in floorplans]}")

