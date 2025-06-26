import numpy as np
import open3d as o3d
from PIL import Image, ImageDraw, ImageEnhance
import os
import argparse
import json
import colorsys
from connected_components import filter_by_connected_components

def make_homogeneous(points):
    """Convert 3D points to homogeneous coordinates"""
    return np.hstack((points, np.ones((points.shape[0], 1))))

def enhance_image(image):
    """Enhance the contrast of the density image"""
    enhancer = ImageEnhance.Contrast(image)
    enhanced_image = enhancer.enhance(4.0)
    return enhanced_image

def create_density_image(point_cloud, resolution=100, flip_y=True, remove_outliers=False, outlier_std_ratio=2.0):
    """Create a top-down density visualization of a point cloud"""
    # Optional outlier removal
    processed_cloud = point_cloud
    if remove_outliers:
        print(f"Removing outliers with std_ratio={outlier_std_ratio}...")
        processed_cloud, _ = point_cloud.remove_statistical_outlier(
            nb_neighbors=20,
            std_ratio=outlier_std_ratio
        )
        print(f"After outlier removal: {len(processed_cloud.points)} points (removed {len(point_cloud.points) - len(processed_cloud.points)} points)")
    
    # Get bounds
    min_bound = processed_cloud.get_min_bound()
    max_bound = processed_cloud.get_max_bound()
    
    # Print bounds for debugging
    print(f"Point cloud bounds: min={min_bound}, max={max_bound}")
    print(f"X range: {min_bound[0]:.2f} to {max_bound[0]:.2f} (width: {max_bound[0] - min_bound[0]:.2f})")
    print(f"Y range: {min_bound[1]:.2f} to {max_bound[1]:.2f} (height: {max_bound[1] - min_bound[1]:.2f})")
    print(f"Z range: {min_bound[2]:.2f} to {max_bound[2]:.2f} (depth: {max_bound[2] - min_bound[2]:.2f})")

    min_xy = min_bound[:2]
    max_xy = max_bound[:2]
    
    # Calculate image dimensions
    size_xy = (max_xy - min_xy) * resolution
    width = int(np.ceil(size_xy[0]))
    height = int(np.ceil(size_xy[1]))
    
    print(f"Calculated image dimensions: {width}x{height} pixels")
    
    # Ensure reasonable image size (cap at 10000x10000)
    if width > 10000 or height > 10000:
        print(f"WARNING: Image dimensions too large ({width}x{height}), will be scaled down")
        scale_factor = min(10000 / width, 10000 / height)
        width = int(width * scale_factor)
        height = int(height * scale_factor)
        resolution = resolution * scale_factor
        print(f"Adjusted image dimensions: {width}x{height} pixels, resolution={resolution}")
    
    # Create projection matrix
    shape = np.array([float(width), float(height)])
    focal_length = resolution / shape
    principal_point = -min_xy * resolution / shape

    projection_matrix = np.array([
        [focal_length[0], 0.0, 0.0, principal_point[0]],
        [0.0, -focal_length[1], 0.0, principal_point[1]],
        [0.0, 0.0, 0.0, 0.0],  # Discard Z for top-down view
        [0.0, 0.0, 0.0, 1.0]
    ])

    # Get raw points
    points = np.asarray(processed_cloud.points)
    
    # Flip Y-coordinate for alignment with annotations (optional)
    if flip_y:
        flipped_points = points.copy()
        flipped_points[:, 1] = -flipped_points[:, 1]
    else:
        flipped_points = points
    
    # Rasterize density image (following C++ implementation approach)
    # Create empty image
    density_image = np.zeros((height, width), dtype=np.uint16)
    
    # Project to 2D and count points per pixel (vectorized implementation)
    homogeneous_points = make_homogeneous(flipped_points)
    projected = np.matmul(homogeneous_points, projection_matrix.transpose())
    uv = projected[:, :2]

    # Scale to integer pixel coordinates
    width_minus_one = width - 1
    height_minus_one = height - 1
    pixel_x = np.round(uv[:, 0] * width_minus_one).astype(np.int32)
    pixel_y = np.round(uv[:, 1] * height_minus_one).astype(np.int32)

    # Keep only points inside the image
    valid_mask = (
        (pixel_x >= 0) & (pixel_x < width) & 
        (pixel_y >= 0) & (pixel_y < height)
    )
    pixel_x = pixel_x[valid_mask]
    pixel_y = pixel_y[valid_mask]
    
    # Print projection statistics
    total_points = len(points)
    valid_points = np.sum(valid_mask)
    print(f"Projection statistics:")
    print(f"  Total points: {total_points}")
    print(f"  Points inside image: {valid_points} ({valid_points/total_points*100:.2f}%)")
    print(f"  Points outside image: {total_points - valid_points} ({(total_points - valid_points)/total_points*100:.2f}%)")
    
    if valid_points < 1000:
        print("WARNING: Very few points projected within image bounds!")
        print("Consider using --remove_outliers or manually specifying --crop_bounds")
    
    # Count points per pixel - following the C++ implementation's approach
    for x, y in zip(pixel_x, pixel_y):
        density_image[y, x] += 1
    
    # Normalize by maximum (following C++ implementation)
    max_val = np.max(density_image)
    print(f"Maximum density value: {max_val}")
    
    if max_val > 0:
        # Invert and scale to 0-255 range
        normalized = 255.0 - ((density_image.astype(np.float32) / max_val) * 255.0)
    else:
        normalized = np.ones((height, width), dtype=np.float32) * 255.0
        print("WARNING: No points were projected to the image!")
    
    # Convert to image
    image_8bit = normalized.astype(np.uint8)
    pil_image = Image.fromarray(image_8bit)
    
    # Enhance the image
    enhanced_image = enhance_image(pil_image)
    
    # Return image and projection parameters
    params = {
        'width': width,
        'height': height,
        'projection_matrix': projection_matrix.tolist(),
    }
    
    return enhanced_image, params

def draw_scene_outlines(image, annotations_file, projection_params):
    """Draw scene outlines from annotations JSON file on density image"""
    try:
        # Load annotations
        with open(annotations_file, 'r') as f:
            annotations = json.load(f)['section_details']
        
        # Convert to RGB for colored outlines
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract projection parameters
        width = projection_params['width']
        height = projection_params['height']
        projection_matrix = np.array(projection_params['projection_matrix'])
        
        # Create drawing context
        draw = ImageDraw.Draw(image, 'RGBA')  # Use RGBA mode to support transparency
        
        # Function to project annotation points
        def project_point(x, y):
            point = np.array([[x, y, 0]])
            projected = np.matmul(make_homogeneous(point), projection_matrix.transpose())
            uv = projected[:, :2]
            px = np.floor(uv[0, 0] * width).astype(np.int32)
            py = np.floor(uv[0, 1] * height).astype(np.int32)
            px = max(0, min(px, width - 1))
            py = max(0, min(py, height - 1))
            return px, py
        
        # Generate colors for scenes
        scene_count = len(annotations['annotation']['scenes'])
        scene_colors = []
        for i in range(scene_count):
            h = i / scene_count
            r, g, b = colorsys.hsv_to_rgb(h, 0.9, 0.9)
            scene_colors.append((int(r * 255), int(g * 255), int(b * 255)))
        
        # Draw each scene outline
        for i, scene in enumerate(annotations['annotation']['scenes']):
            outline_points = scene['outline']
            
            # Project points to image coordinates
            image_points = []
            for point in outline_points:
                image_points.append(project_point(point['x'], point['y']))
            
            # Get color for this scene
            color = scene_colors[i]
            
            # Fill scene with semi-transparent color
            fill_color = (color[0], color[1], color[2], 80)  # Add alpha channel (0-255, where 0 is transparent)
            draw.polygon(image_points, fill=fill_color, outline=None)
            
            # Draw outline with more opacity
            draw.line(image_points + [image_points[0]], fill=color, width=3)
            
            # Add label
            centroid_x = sum(p[0] for p in image_points) // len(image_points)
            centroid_y = sum(p[1] for p in image_points) // len(image_points)
            
            scene_name = scene.get('name', f"Scene {scene['id']}")
            scene_type = scene.get('type', '')
            label_text = f"{scene_name} ({scene_type})"
            
            # Add text with background
            text_width = len(label_text) * 6
            draw.rectangle(
                [(centroid_x - 5, centroid_y - 10), (centroid_x + text_width + 5, centroid_y + 10)],
                fill=(0, 0, 0, 160)
            )
            draw.text((centroid_x, centroid_y), label_text, fill=color)
            
        return image
        
    except Exception as e:
        print(f"Error drawing scene outlines: {e}")
        import traceback
        traceback.print_exc()
        return image

def generate_from_ply(input_file, output_dir='output', resolution=100, high_res=False, annotations_file=None, 
                     use_connected_components=False, cc_radius=0.1, cc_always_include_radius=10.0,
                     flip_y=True, remove_outliers=False, outlier_std_ratio=2.0, crop_bounds=None):
    """Generate density image from a PLY point cloud file"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Output file paths
    density_output = os.path.join(output_dir, f"{base_name}_density.png")
    annotated_output = os.path.join(output_dir, f"{base_name}_annotated.png") if annotations_file else None
    
    # Adjust resolution if high_res is specified
    effective_resolution = resolution * (4 if high_res else 1)
    
    # Check input file
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file {input_file} not found")
    
    # Load point cloud directly - no preprocessing
    print(f"Loading point cloud from {input_file}...")
    point_cloud = o3d.io.read_point_cloud(input_file)
    print(f"Point cloud has {len(point_cloud.points)} points")
    
    # Optional manual cropping
    if crop_bounds is not None:
        print(f"Applying manual crop with bounds: {crop_bounds}")
        min_bounds = np.array([crop_bounds[0], crop_bounds[2], float('-inf')])
        max_bounds = np.array([crop_bounds[1], crop_bounds[3], float('inf')])
        bbox = o3d.geometry.AxisAlignedBoundingBox(min_bound=min_bounds, max_bound=max_bounds)
        point_cloud = point_cloud.crop(bbox)
        print(f"After cropping: {len(point_cloud.points)} points")
    
    # Apply connected components filtering if requested
    if use_connected_components:
        print("Applying connected components filtering...")
        # Use mean of points as scan origin
        mean_point = np.mean(np.asarray(point_cloud.points), axis=0)
        scan_origins = [mean_point]
        print(f"Using mean point as scan origin: {mean_point}")
        
        # Filter the point cloud
        filtered_point_cloud = filter_by_connected_components(
            point_cloud,
            scan_origins,
            radius=cc_radius,
            always_include_radius=cc_always_include_radius
        )
        
        print(f"Filtered point cloud has {len(filtered_point_cloud.points)} points")
        point_cloud = filtered_point_cloud
    
    # Generate density image directly from raw points
    print(f"Generating density image...")
    density_image, proj_params = create_density_image(
        point_cloud, 
        resolution=effective_resolution,
        flip_y=flip_y,
        remove_outliers=remove_outliers,
        outlier_std_ratio=outlier_std_ratio
    )
    
    # Save density image
    density_image.save(density_output)
    print(f"Density image saved to {density_output}")
    
    # Draw scene outlines if annotations provided
    if annotations_file and os.path.exists(annotations_file):
        print(f"Adding scene outlines from {annotations_file}...")
        annotated_image = draw_scene_outlines(
            density_image.copy(), 
            annotations_file, 
            proj_params
        )
        annotated_image.save(annotated_output)
        print(f"Annotated image saved to {annotated_output}")
        return annotated_output
        
    return density_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate density visualization from PLY point cloud")
    parser.add_argument("input_file", help="Path to the input PLY file")
    parser.add_argument("--output_dir", "-o", default="output", help="Directory to save output images")
    parser.add_argument("--resolution", "-r", type=int, default=100, help="Base resolution multiplier (default: 100)")
    parser.add_argument("--high_res", "-hr", action="store_true", help="Generate high-resolution images (4x)")
    parser.add_argument("--annotations", "-a", help="Path to annotations JSON file to draw scene outlines")
    
    # Connected components options
    parser.add_argument("--use_connected_components", "-cc", action="store_true", 
                        help="Filter point cloud using connected components before visualization")
    parser.add_argument("--cc_radius", type=float, default=0.1, 
                        help="Radius for connected components filtering (default: 0.1)")
    parser.add_argument("--cc_always_include_radius", type=float, default=10.0, 
                        help="Radius around scan origin to always include points (default: 10.0)")
    
    # New options for handling different point clouds
    parser.add_argument("--flip_y", action="store_true", default=True,
                        help="Flip Y coordinates for alignment with annotations (default: True)")
    parser.add_argument("--no_flip_y", action="store_false", dest="flip_y", 
                        help="Don't flip Y coordinates (use if your point cloud has different orientation)")
    parser.add_argument("--remove_outliers", action="store_true",
                        help="Remove statistical outliers before projection (useful for noisy point clouds)")
    parser.add_argument("--outlier_std_ratio", type=float, default=2.0,
                        help="Standard deviation ratio for outlier removal (default: 2.0)")
    parser.add_argument("--crop_bounds", type=float, nargs=4, metavar=('X_MIN', 'X_MAX', 'Y_MIN', 'Y_MAX'),
                        help="Manually crop point cloud to these X,Y bounds before processing")
    
    args = parser.parse_args()
    
    # Generate the density image
    output_file = generate_from_ply(
        input_file=args.input_file,
        output_dir=args.output_dir,
        resolution=args.resolution,
        high_res=args.high_res,
        annotations_file=args.annotations,
        use_connected_components=args.use_connected_components,
        cc_radius=args.cc_radius,
        cc_always_include_radius=args.cc_always_include_radius,
        flip_y=args.flip_y,
        remove_outliers=args.remove_outliers,
        outlier_std_ratio=args.outlier_std_ratio,
        crop_bounds=args.crop_bounds
    )
    
    print("\nGeneration complete!")
    print(f"Output saved to: {output_file}")                               