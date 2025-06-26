import numpy as np
import open3d as o3d
import scipy.sparse

def find_triplets(kdtree, point_cloud, radius, max_nn):
    """
    Find triplets of points within radius.
    Replacement for pupil_vision.find_triplets.
    
    Args:
        kdtree: Open3D KDTree object
        point_cloud: Open3D PointCloud
        radius: Search radius
        max_nn: Maximum number of neighbors per point
        
    Returns:
        Numpy array of triplets [point_i, point_j, weight]
    """
    points = np.asarray(point_cloud.points)
    num_points = len(points)
    
    # Pre-allocate a list for storing triplets (estimated size)
    # In worst case, each point has max_nn neighbors, but in practice 
    # it's often less. We'll use an estimated 20% of this max capacity
    # and resize as needed.
    estimated_capacity = int(num_points * max_nn * 0.2)
    triplets_i = np.zeros(estimated_capacity, dtype=np.int32)
    triplets_j = np.zeros(estimated_capacity, dtype=np.int32)
    current_idx = 0
    
    # Report progress periodically
    print_interval = max(1, num_points // 10)
    
    print(f"Finding triplets for {num_points} points...")
    last_resize = 0
    
    for i in range(num_points):
        if i % print_interval == 0:
            print(f"  Processing point {i}/{num_points} ({i*100/num_points:.1f}%)")
        
        # Find neighbors within radius
        [k, idx, _] = kdtree.search_radius_vector_3d(point_cloud.points[i], radius)
        
        # Check if we need to resize arrays (only if we're close to filling up)
        if current_idx + k > triplets_i.shape[0] - 100:
            # This resizing happens rarely, only when needed
            if last_resize != i:  # Avoid multiple resizes for the same point
                last_resize = i
                new_size = triplets_i.shape[0] * 2
                print(f"  Resizing triplets array to {new_size} at point {i}")
                triplets_i.resize(new_size, refcheck=False)
                triplets_j.resize(new_size, refcheck=False)
        
        # Add triplets where j > i (avoid duplicates)
        neighbor_count = 0
        for j in idx:
            if j > i:  # Avoid duplicate connections
                triplets_i[current_idx] = i
                triplets_j[current_idx] = j
                current_idx += 1
                neighbor_count += 1
                if neighbor_count >= max_nn:
                    break
    
    # Trim arrays to actual size used
    triplets_i = triplets_i[:current_idx]
    triplets_j = triplets_j[:current_idx]
    
    # Create weights array (all ones)
    weights = np.ones(current_idx, dtype=np.int32)
    
    # Combine into triplets format
    triplets = np.column_stack((triplets_i, triplets_j, weights))
    
    print(f"Found {len(triplets)} triplets")
    return triplets

def filter_by_connected_components(point_cloud, scan_origins, radius=0.1, max_nn=10, max_num_nearby_points=300, always_include_radius=10.0):
    """
    Filter point cloud by connected components, keeping only components that contain
    points near scan origins.
    
    Args:
        point_cloud: Open3D PointCloud object
        scan_origins: List of scan origin positions (where scanner was located)
        radius: Connectivity radius for components
        max_nn: Maximum number of neighbors to consider per point
        max_num_nearby_points: Number of points close to origins to force-connect
        always_include_radius: Points within this distance to scan origins are always included
        
    Returns:
        Filtered point cloud with only the main components
    """
    points = np.asarray(point_cloud.points)
    num_points = len(points)
    
    print(f"Filtering point cloud of shape {points.shape} using connected components")
    print(f"Using parameters (radius={radius}, max_nn={max_nn}, max_num_nearby_points={max_num_nearby_points}, always_include_radius={always_include_radius})")
    
    # Try to use DBSCAN clustering if available
    try:
        return filter_using_dbscan(point_cloud, scan_origins, radius, always_include_radius)
    except Exception as e:
        print(f"DBSCAN clustering not available: {e}")
        print("Falling back to graph-based implementation")
        return filter_using_graph(point_cloud, scan_origins, radius, max_nn, max_num_nearby_points, always_include_radius)

def filter_using_dbscan(point_cloud, scan_origins, radius, always_include_radius):
    """
    Filter using Open3D's DBSCAN clustering.
    """
    points = np.asarray(point_cloud.points)
    num_points = len(points)
    
    # Calculate distance from each point to nearest scan origin
    min_distances = np.ones(num_points) * float('inf')
    for origin in scan_origins:
        origin_array = np.array(origin)
        distances = np.linalg.norm(points - origin_array, axis=1)
        min_distances = np.minimum(min_distances, distances)
    
    # Find points close to scan origins
    always_included_indices = np.where(min_distances < always_include_radius)[0]
    
    # Use Open3D's DBSCAN clustering
    print("Using Open3D's DBSCAN clustering")
    
    # Run DBSCAN clustering
    labels = np.array(point_cloud.cluster_dbscan(eps=radius, min_points=3))
    
    # Find components that contain points close to scan origins
    valid_clusters = np.unique(labels[always_included_indices])
    valid_clusters = valid_clusters[valid_clusters >= 0]  # Remove noise label (-1)
    print(f"Found {len(valid_clusters)} valid clusters near scan origins")
    
    # Create mask for points in these components
    if len(valid_clusters) > 0:
        main_component_mask = np.isin(labels, valid_clusters)
    else:
        # If no valid clusters found, keep points close to origins
        main_component_mask = min_distances < always_include_radius
    
    # Create filtered point cloud
    filtered_cloud = o3d.geometry.PointCloud()
    filtered_cloud.points = o3d.utility.Vector3dVector(points[main_component_mask])
    
    # Copy colors and normals if available
    if point_cloud.has_colors():
        filtered_cloud.colors = o3d.utility.Vector3dVector(
            np.asarray(point_cloud.colors)[main_component_mask])
    if point_cloud.has_normals():
        filtered_cloud.normals = o3d.utility.Vector3dVector(
            np.asarray(point_cloud.normals)[main_component_mask])
    
    print(f"Main component has {len(filtered_cloud.points)} points")
    return filtered_cloud

def filter_using_graph(point_cloud, scan_origins, radius, max_nn, max_num_nearby_points, always_include_radius):
    """
    Filter using the original graph-based approach with scipy.
    Fallback for older versions of Open3D without native connected components.
    """
    points = np.asarray(point_cloud.points)
    num_points = len(points)
    
    # Build KD-tree for efficient neighbor search
    kdtree = o3d.geometry.KDTreeFlann(point_cloud)
    
    # Calculate distances to scan origins
    min_distances = np.ones(num_points) * float('inf')
    for origin in scan_origins:
        origin_array = np.array(origin)
        distances = np.linalg.norm(points - origin_array, axis=1)
        min_distances = np.minimum(min_distances, distances)
    
    # Get points sorted by distance to origins
    sorted_point_indices = np.argsort(min_distances)
    
    # Find indices of points close to origins
    always_included_indices = np.where(min_distances < always_include_radius)[0]
    
    # Find neighbors of points using non-parallel implementation
    print("Finding triplets using serial implementation...")
    filtered_triplets = find_triplets(kdtree, point_cloud, radius, max_nn)
    
    # Find closest points to origin and connect them
    nearby_point_triplet_list = []
    num_nearby_points = min(max_num_nearby_points, sorted_point_indices.shape[0])
    
    print(f"Connecting {num_nearby_points} points closest to origins...")
    for index in range(num_nearby_points):
        for pair_index in range(index + 1, num_nearby_points):
            if sorted_point_indices[index] > sorted_point_indices[pair_index]:
                nearby_point_triplet_list.append([sorted_point_indices[index], sorted_point_indices[pair_index], 1])
            else:
                nearby_point_triplet_list.append([sorted_point_indices[pair_index], sorted_point_indices[index], 1])
    
    nearby_point_triplets = np.array(nearby_point_triplet_list, dtype=np.int32)
    
    # Concatenate triplets from NN search and closest points search
    all_triplets = np.concatenate((filtered_triplets, nearby_point_triplets), axis=0)
    del filtered_triplets
    del nearby_point_triplets
    del nearby_point_triplet_list
    
    print(f"Constructing sparse matrix with (shape = {(num_points, num_points)}, nnz = {all_triplets.shape[0]})")
    graph = scipy.sparse.coo_matrix((all_triplets[:, 2], (all_triplets[:, 0], all_triplets[:, 1])), shape=(num_points, num_points))
    
    print("Finding connected components from sparse matrix")
    num_components, components = scipy.sparse.csgraph.connected_components(graph, directed=False)
    
    print(f"Found {num_components} components")
    always_included_components = np.unique(components[always_included_indices])
    main_component_mask = np.isin(components, always_included_components)
    
    # Create filtered point cloud
    filtered_cloud = o3d.geometry.PointCloud()
    filtered_cloud.points = o3d.utility.Vector3dVector(points[main_component_mask])
    
    # Copy colors and normals if available
    if point_cloud.has_colors():
        filtered_cloud.colors = o3d.utility.Vector3dVector(
            np.asarray(point_cloud.colors)[main_component_mask])
    if point_cloud.has_normals():
        filtered_cloud.normals = o3d.utility.Vector3dVector(
            np.asarray(point_cloud.normals)[main_component_mask])
    
    print(f"Main component has {len(filtered_cloud.points)} points")
    return filtered_cloud