import os
import subprocess
import glob
from pathlib import Path
import sys

def process_ply_files():
    # Get the absolute path to the generate_density_image.py script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    density_script = os.path.join(script_dir, "src", "generate_density_image.py")
    
    # Create output directory for density images
    output_dir = "density_images"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all PLY files
    ply_files = glob.glob("downloaded_ply_files/*.ply")
    total_files = len(ply_files)
    
    print(f"Found {total_files} PLY files to process")
    
    # Process each PLY file
    for idx, ply_file in enumerate(ply_files, 1):
        # Get the corresponding JSON file
        base_name = os.path.basename(ply_file).replace(".ply", "")
        json_file = os.path.join("sections", f"{base_name}.json")
        
        # Check if JSON file exists
        if not os.path.exists(json_file):
            print(f"Warning: No JSON file found for {ply_file}")
            continue
        
        print(f"\nProcessing {base_name} ({idx}/{total_files})...")
        
        # Construct the command
        cmd = [
            sys.executable,  # Use the current Python interpreter
            density_script,
            os.path.abspath(ply_file),
            "--annotations", os.path.abspath(json_file),
            "--output_dir", output_dir,
            "--high_res"  # Enable high resolution output
        ]
        
        try:
            # Run the command
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"Successfully processed {base_name}")
            
            # Check if output files were created
            density_output = os.path.join(output_dir, f"{base_name}_density.png")
            annotated_output = os.path.join(output_dir, f"{base_name}_annotated.png")
            
            if os.path.exists(density_output) and os.path.exists(annotated_output):
                print(f"Output files created successfully:")
                print(f"  - {density_output}")
                print(f"  - {annotated_output}")
            else:
                print(f"Warning: Some output files are missing for {base_name}")
                
        except subprocess.CalledProcessError as e:
            print(f"Error processing {base_name}:")
            print(f"Exit code: {e.returncode}")
            print(f"Error output: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error processing {base_name}: {e}")
        
        # Print progress
        print(f"Progress: {idx}/{total_files} files processed")

if __name__ == "__main__":
    try:
        process_ply_files()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1) 