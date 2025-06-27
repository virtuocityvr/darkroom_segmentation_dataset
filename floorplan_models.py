from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class DeviceType(Enum):
    BLK2GO = "BLK2GO"
    BLK360 = "BLK360"
    IMAGE_ONLY = "IMAGE_ONLY"
    UNKNOWN = "UNKNOWN"

@dataclass
class PlyFile:
    """Represents a PLY file with its metadata"""
    s3_path: str
    file_type: str  # "SUBSAMPLED", "UPLOADED", "CLASLAM"
    bucket: str
    scan_id: str

@dataclass
class Author:
    """Represents author information"""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None

@dataclass
class Scene:
    """Represents a scene/room in the floorplan"""
    id: int
    raw_id: str
    type: str  # "BEDROOM", "KITCHEN_RECEPTION", "BALCONY", etc.
    name: str
    outline: Optional[List[Dict[str, float]]] = None
    nia: Optional[float] = None
    description: Optional[Dict[str, Any]] = None

@dataclass
class Shape:
    """Represents a shape in the floorplan"""
    id: int
    type: str
    outline: Optional[List[Dict[str, float]]] = None
    sub_type: Optional[str] = None

@dataclass
class Door:
    """Represents a door in the floorplan"""
    id: int
    type: str  # "ARCHWAY", "LEFT_SLIDING_DOOR", "DOUBLE_DOORS", etc.
    point1: Dict[str, float]
    point2: Dict[str, float]
    thickness: float
    is_front_door: bool = False
    raw_scene_ids: Optional[List[str]] = None

@dataclass
class MeasurementArea:
    """Represents measurement area information"""
    external_structural_area: float
    residential: Dict[str, float]  # IPMS_3B, IPMS_3C, GIA, NIA
    commercial: Dict[str, float]   # IPMS_2_OFFICE, IPMS_3_OFFICE, etc.
    restricted_height_area: float
    void_area: float
    obstruction_area: float
    version: str

class Floorplan:
    """Main Floorplan class that captures all necessary data"""
    
    def __init__(self, capture_id: int, floorplan_id: int):
        self.processed_capture_id: int = capture_id
        self.floorplan_id: int = floorplan_id
        self.section_id: Optional[str] = None
        self.floor_num: Optional[int] = None
        self.is_final: bool = False
        self.device_type: DeviceType = DeviceType.UNKNOWN
        self.ply_file: Optional[PlyFile] = None
        self.list_of_scenes: List[Scene] = []
        self.list_of_shapes: List[Shape] = []
        self.author: Optional[Author] = None
        self.doors: List[Door] = []
        self.measurement_area: Optional[MeasurementArea] = None
        
    def set_from_capture_data(self, capture_floorplan: Dict[str, Any]):
        """Set data from capture.json floorplan"""
        self.floor_num = capture_floorplan.get('floor')
        self.section_id = capture_floorplan.get('section')
        
        # Determine device type from potreeConvertedScansResponse
        potree_scans = capture_floorplan.get('potreeConvertedScansResponse', [])
        if len(potree_scans) == 0:
            self.device_type = DeviceType.IMAGE_ONLY
        else:
            has_uploaded = any(scan.get('type') == 'UPLOADED' for scan in potree_scans)
            has_subsampled = any(scan.get('type') in ['SUBSAMPLED', 'CLASLAM'] for scan in potree_scans)
            
            if has_uploaded:
                self.device_type = DeviceType.BLK360
            elif has_subsampled:
                self.device_type = DeviceType.BLK2GO
            else:
                self.device_type = DeviceType.UNKNOWN
        
        # Set PLY file information (take first available scan)
        if potree_scans:
            first_scan = potree_scans[0]
            media_ref = first_scan.get('mediaReference', {})
            self.ply_file = PlyFile(
                s3_path=media_ref.get('path', ''),
                file_type=first_scan.get('type', ''),
                bucket=media_ref.get('bucket', ''),
                scan_id=str(first_scan.get('id', ''))
            )
        
        # Set author from createdBy
        created_by = capture_floorplan.get('createdBy')
        if created_by:
            self.author = Author(user_id=created_by)
    
    def set_from_sections_data(self, section_data: Dict[str, Any]):
        """Set data from sections.json section"""
        self.is_final = section_data.get('final', False)
        
        # Set author from sections (more complete author info)
        author_data = section_data.get('author')
        if author_data:
            self.author = Author(
                user_id=author_data.get('user_id', ''),
                email=author_data.get('email'),
                name=author_data.get('name'),
                picture=author_data.get('picture')
            )
        
        # Set scenes
        annotation = section_data.get('annotation', {})
        scenes_data = annotation.get('scenes', [])
        for scene_data in scenes_data:
            scene = Scene(
                id=scene_data.get('id'),
                raw_id=scene_data.get('rawId', ''),
                type=scene_data.get('type', ''),
                name=scene_data.get('name', ''),
                outline=scene_data.get('outline'),
                nia=scene_data.get('NIA'),
                description=scene_data.get('description')
            )
            self.list_of_scenes.append(scene)
        
        # Set shapes
        shapes_data = annotation.get('shapes', [])
        for shape_data in shapes_data:
            shape = Shape(
                id=shape_data.get('id'),
                type=shape_data.get('type', ''),
                outline=shape_data.get('outline'),
                sub_type=shape_data.get('subType')
            )
            self.list_of_shapes.append(shape)
        
        # Set doors
        doors_data = annotation.get('doorways', [])
        for door_data in doors_data:
            door = Door(
                id=door_data.get('id'),
                type=door_data.get('type', ''),
                point1=door_data.get('point1', {}),
                point2=door_data.get('point2', {}),
                thickness=door_data.get('thickness', 0.0),
                is_front_door=door_data.get('isFrontDoor', False),
                raw_scene_ids=door_data.get('rawSceneIds')
            )
            self.doors.append(door)
        
        # Set measurement area
        measurements = section_data.get('measurements', {})
        if measurements:
            self.measurement_area = MeasurementArea(
                external_structural_area=measurements.get('externalStructuralArea', 0.0),
                residential=measurements.get('residential', {}),
                commercial=measurements.get('commercial', {}),
                restricted_height_area=measurements.get('restrictedHeightArea', 0.0),
                void_area=measurements.get('voidArea', 0.0),
                obstruction_area=measurements.get('obstructionArea', 0.0),
                version=measurements.get('version', '')
            )
    
    def is_image_only(self) -> bool:
        """Check if this is an image-only section"""
        return self.device_type == DeviceType.IMAGE_ONLY
    
    def get_scene_count(self) -> int:
        """Get the number of scenes"""
        return len(self.list_of_scenes)
    
    def get_shape_count(self) -> int:
        """Get the number of shapes"""
        return len(self.list_of_shapes)
    
    def get_door_count(self) -> int:
        """Get the number of doors"""
        return len(self.doors)
    
    def get_total_nia(self) -> float:
        """Get total NIA from measurement area"""
        if self.measurement_area and self.measurement_area.residential:
            return self.measurement_area.residential.get('NIA', 0.0)
        return 0.0
    
    def __str__(self) -> str:
        return f"Floorplan(id={self.floorplan_id}, floor={self.floor_num}, section={self.section_id}, final={self.is_final}, device={self.device_type.value})"

class FloorplanProcessor:
    """Processor class to create Floorplan objects from JSON data"""
    
    def __init__(self, cache_dir: str = 'api_cache'):
        self.cache_dir = cache_dir
    
    def get_cached_response(self, capture_id: int, response_type: str) -> Optional[Dict[str, Any]]:
        """Get cached response if it exists"""
        import json
        import os
        
        cache_file = os.path.join(self.cache_dir, f"{capture_id}_{response_type}.json")
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {cache_file}: {e}")
            return None
    
    def process_capture(self, capture_id: int) -> List[Floorplan]:
        """Process a capture and return list of Floorplan objects"""
        floorplans = []
        
        # Get capture data
        capture_data = self.get_cached_response(capture_id, 'capture')
        if not capture_data:
            return floorplans
        
        # Check if published
        if capture_data.get('publishedState') != 'PUBLISHED':
            return floorplans
        
        # Get sections data
        sections_data = self.get_cached_response(capture_id, 'sections')
        if not sections_data:
            return floorplans
        
        # Process floors and sections
        floors = sections_data.get('floors', {})
        for floor_key in floors.keys():
            floor = floors[floor_key]
            
            for section_key in floor.keys():
                sections = floor[section_key]
                
                for section in sections:
                    # Only process final sections
                    if section.get('final') == True:
                        floorplan_id = section.get('floorplanId')
                        
                        # Find corresponding floorplan in capture data
                        capture_floorplans = [fp for fp in capture_data.get('floorplans', []) 
                                            if fp.get('id') == floorplan_id]
                        
                        if capture_floorplans:
                            capture_floorplan = capture_floorplans[0]
                            
                            # Create Floorplan object
                            floorplan = Floorplan(capture_id, floorplan_id)
                            
                            # Set data from both sources
                            floorplan.set_from_capture_data(capture_floorplan)
                            floorplan.set_from_sections_data(section)
                            
                            # Skip image-only sections
                            if not floorplan.is_image_only():
                                floorplans.append(floorplan)
        
        return floorplans

def main():
    """Example usage"""
    processor = FloorplanProcessor()
    
    # Process capture 74230
    floorplans = processor.process_capture(74230)
    
    print(f"Found {len(floorplans)} non-image-only floorplans:")
    for fp in floorplans:
        print(f"  {fp}")
        print(f"    Scenes: {fp.get_scene_count()}")
        print(f"    Shapes: {fp.get_shape_count()}")
        print(f"    Doors: {fp.get_door_count()}")
        print(f"    NIA: {fp.get_total_nia()}")
        print()

if __name__ == "__main__":
    main() 