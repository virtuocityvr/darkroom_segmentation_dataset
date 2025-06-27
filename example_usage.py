#!/usr/bin/env python3
"""
Example usage of the Floorplan object-oriented structure
Processes all capture IDs from processed_capture_ids.txt
"""

from floorplan_models import FloorplanProcessor, DeviceType
from typing import List, Dict, Any

def load_capture_ids(filename: str = 'processed_capture_ids.txt') -> List[int]:
    """Load capture IDs from the text file"""
    try:
        with open(filename, 'r') as f:
            return [int(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using sample capture ID.")
        return [74230]  # Fallback to sample capture ID

def process_all_captures() -> Dict[int, List]:
    """Process all captures and return results"""
    processor = FloorplanProcessor()
    capture_ids = load_capture_ids()
    
    all_results = {}
    
    print(f"Processing {len(capture_ids)} captures...")
    print("=" * 60)
    
    for i, capture_id in enumerate(capture_ids, 1):
        print(f"Processing capture {i}/{len(capture_ids)}: {capture_id}")
        
        try:
            floorplans = processor.process_capture(capture_id)
            all_results[capture_id] = floorplans
            
            if floorplans:
                print(f"  ✓ Found {len(floorplans)} non-image-only floorplans")
            else:
                print(f"  - No non-image-only floorplans found")
                
        except Exception as e:
            print(f"  ✗ Error processing capture {capture_id}: {e}")
            all_results[capture_id] = []
    
    return all_results

def print_detailed_results(all_results: Dict[int, List]):
    """Print detailed results for all captures"""
    print("\n" + "=" * 80)
    print("DETAILED RESULTS FOR ALL CAPTURES")
    print("=" * 80)
    
    total_floorplans = 0
    total_scenes = 0
    total_shapes = 0
    total_doors = 0
    total_nia = 0.0
    
    device_type_counts = {
        DeviceType.BLK2GO: 0,
        DeviceType.BLK360: 0,
        DeviceType.IMAGE_ONLY: 0,
        DeviceType.UNKNOWN: 0
    }
    
    for capture_id, floorplans in all_results.items():
        if not floorplans:
            continue
            
        print(f"\nCapture {capture_id}:")
        print(f"  Floorplans: {len(floorplans)}")
        
        for i, floorplan in enumerate(floorplans, 1):
            print(f"    Floorplan {i}: {floorplan}")
            print(f"      Scenes: {floorplan.get_scene_count()}")
            print(f"      Shapes: {floorplan.get_shape_count()}")
            print(f"      Doors: {floorplan.get_door_count()}")
            print(f"      NIA: {floorplan.get_total_nia()}")
            
            # Display PLY file information
            if floorplan.ply_file:
                print(f"      PLY File: {floorplan.ply_file.s3_path}")
                print(f"        Type: {floorplan.ply_file.file_type}")
                print(f"        Bucket: {floorplan.ply_file.bucket}")
                print(f"        Scan ID: {floorplan.ply_file.scan_id}")
            else:
                print(f"      PLY File: None")
            
            # Display author information
            if floorplan.author:
                author_info = floorplan.author.name or floorplan.author.user_id
                print(f"      Author: {author_info}")
                if floorplan.author.email:
                    print(f"        Email: {floorplan.author.email}")
            else:
                print(f"      Author: None")
            
            # Update totals
            total_floorplans += 1
            total_scenes += floorplan.get_scene_count()
            total_shapes += floorplan.get_shape_count()
            total_doors += floorplan.get_door_count()
            total_nia += floorplan.get_total_nia()
            device_type_counts[floorplan.device_type] += 1
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total captures processed: {len(all_results)}")
    print(f"Captures with floorplans: {len([c for c, fps in all_results.items() if fps])}")
    print(f"Total floorplans: {total_floorplans}")
    print(f"Total scenes: {total_scenes}")
    print(f"Total shapes: {total_shapes}")
    print(f"Total doors: {total_doors}")
    print(f"Total NIA: {total_nia:.2f}")
    
    print(f"\nDevice Type Distribution:")
    for device_type, count in device_type_counts.items():
        if count > 0:
            print(f"  {device_type.value}: {count}")

def filter_by_device_type(all_results: Dict[int, List]):
    """Filter and analyze floorplans by device type"""
    print("\n" + "=" * 60)
    print("FILTERING BY DEVICE TYPE")
    print("=" * 60)
    
    blk2go_floorplans = []
    blk360_floorplans = []
    
    for capture_id, floorplans in all_results.items():
        for floorplan in floorplans:
            if floorplan.device_type == DeviceType.BLK2GO:
                blk2go_floorplans.append((capture_id, floorplan))
            elif floorplan.device_type == DeviceType.BLK360:
                blk360_floorplans.append((capture_id, floorplan))
    
    print(f"BLK2GO floorplans: {len(blk2go_floorplans)}")
    for capture_id, floorplan in blk2go_floorplans:
        print(f"  Capture {capture_id}: {floorplan}")
    
    print(f"\nBLK360 floorplans: {len(blk360_floorplans)}")
    for capture_id, floorplan in blk360_floorplans:
        print(f"  Capture {capture_id}: {floorplan}")

def get_capture_statistics(all_results: Dict[int, List]):
    """Get statistics for each capture"""
    print("\n" + "=" * 60)
    print("CAPTURE STATISTICS")
    print("=" * 60)
    
    capture_stats = []
    
    for capture_id, floorplans in all_results.items():
        if not floorplans:
            continue
            
        stats = {
            'capture_id': capture_id,
            'floorplan_count': len(floorplans),
            'total_scenes': sum(fp.get_scene_count() for fp in floorplans),
            'total_shapes': sum(fp.get_shape_count() for fp in floorplans),
            'total_doors': sum(fp.get_door_count() for fp in floorplans),
            'total_nia': sum(fp.get_total_nia() for fp in floorplans),
            'device_types': list(set(fp.device_type.value for fp in floorplans))
        }
        capture_stats.append(stats)
    
    # Sort by total NIA (descending)
    capture_stats.sort(key=lambda x: x['total_nia'], reverse=True)
    
    print(f"{'Capture ID':<12} {'Floorplans':<12} {'Scenes':<8} {'Shapes':<8} {'Doors':<8} {'NIA':<10} {'Devices':<15}")
    print("-" * 80)
    
    for stats in capture_stats:
        devices_str = ", ".join(stats['device_types'])
        print(f"{stats['capture_id']:<12} {stats['floorplan_count']:<12} {stats['total_scenes']:<8} "
              f"{stats['total_shapes']:<8} {stats['total_doors']:<8} {stats['total_nia']:<10.2f} {devices_str:<15}")

def save_results_to_file(all_results: Dict[int, List], filename: str = 'floorplan_analysis_results.json'):
    """Save results to a JSON file"""
    import json
    
    # Convert results to serializable format
    serializable_results = {}
    
    for capture_id, floorplans in all_results.items():
        floorplan_data = []
        for floorplan in floorplans:
            fp_data = {
                'floorplan_id': floorplan.floorplan_id,
                'section_id': floorplan.section_id,
                'floor_num': floorplan.floor_num,
                'is_final': floorplan.is_final,
                'device_type': floorplan.device_type.value,
                'scene_count': floorplan.get_scene_count(),
                'shape_count': floorplan.get_shape_count(),
                'door_count': floorplan.get_door_count(),
                'total_nia': floorplan.get_total_nia(),
                'author': floorplan.author.user_id if floorplan.author else None,
                'ply_file': {
                    's3_path': floorplan.ply_file.s3_path if floorplan.ply_file else None,
                    'file_type': floorplan.ply_file.file_type if floorplan.ply_file else None,
                    'bucket': floorplan.ply_file.bucket if floorplan.ply_file else None,
                    'scan_id': floorplan.ply_file.scan_id if floorplan.ply_file else None
                } if floorplan.ply_file else None
            }
            floorplan_data.append(fp_data)
        
        serializable_results[capture_id] = floorplan_data
    
    with open(filename, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\nResults saved to: {filename}")

def main():
    """Main function to process all captures"""
    print("=== PROCESSING ALL CAPTURES ===")
    
    # Process all captures
    all_results = process_all_captures()
    
    # Print detailed results
    print_detailed_results(all_results)
    
    # Filter by device type
    filter_by_device_type(all_results)
    
    # Get capture statistics
    get_capture_statistics(all_results)
    
    # Save results to file
    save_results_to_file(all_results)

if __name__ == "__main__":
    main() 