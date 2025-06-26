#!/bin/bash

# Set paths
SCRIPT_DIR="/Users/apurv/Documents/office/code/ply_density_renderer"
PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"
DENSITY_SCRIPT="$SCRIPT_DIR/generate_density_image.py"
OUTPUT_DIR="density_images"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get all PLY files
PLY_FILES=(downloaded_ply_files/*.ply)
TOTAL_FILES=${#PLY_FILES[@]}

echo "Found $TOTAL_FILES PLY files to process"

# Process each PLY file
for i in "${!PLY_FILES[@]}"; do
    PLY_FILE="${PLY_FILES[$i]}"
    BASE_NAME=$(basename "$PLY_FILE" .ply)
    JSON_FILE="sections/${BASE_NAME}.json"
    
    # Check if JSON file exists
    if [ ! -f "$JSON_FILE" ]; then
        echo "Warning: No JSON file found for $PLY_FILE"
        continue
    fi
    
    echo -e "\nProcessing $BASE_NAME ($((i+1))/$TOTAL_FILES)..."
    
    # Run the command
    "$PYTHON_PATH" "$DENSITY_SCRIPT" \
        "$(pwd)/$PLY_FILE" \
        --annotations "$(pwd)/$JSON_FILE" \
        --output_dir "$OUTPUT_DIR" \
        --high_res
    
    # Check if the command was successful
    if [ $? -eq 0 ]; then
        echo "Successfully processed $BASE_NAME"
        
        # Check if output files were created
        DENSITY_OUTPUT="$OUTPUT_DIR/${BASE_NAME}_density.png"
        ANNOTATED_OUTPUT="$OUTPUT_DIR/${BASE_NAME}_annotated.png"
        
        if [ -f "$DENSITY_OUTPUT" ] && [ -f "$ANNOTATED_OUTPUT" ]; then
            echo "Output files created successfully:"
            echo "  - $DENSITY_OUTPUT"
            echo "  - $ANNOTATED_OUTPUT"
        else
            echo "Warning: Some output files are missing for $BASE_NAME"
        fi
    else
        echo "Error processing $BASE_NAME"
    fi
    
    echo "Progress: $((i+1))/$TOTAL_FILES files processed"
done 