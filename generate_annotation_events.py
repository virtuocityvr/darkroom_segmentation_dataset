import json
import random
from datetime import datetime, timedelta
import copy

class AnnotationEventGenerator:
    def __init__(self, input_json_path):
        with open(input_json_path, 'r') as f:
            self.input_data = json.load(f)
        
        self.start_time = datetime(2024, 3, 21, 10, 0, 0)
        self.current_time = self.start_time
        self.events = []
        
    def get_random_click_interval(self):
        base_time = random.uniform(0.8, 2.5)
        if random.random() < 0.2:  # 20% chance of longer pause
            base_time += random.uniform(1.0, 3.0)
        return base_time
    
    def get_random_break(self):
        break_types = [
            (random.uniform(8, 15), 0.4),    # Short break
            (random.uniform(15, 30), 0.4),   # Medium break
            (random.uniform(30, 60), 0.2)    # Long break
        ]
        
        r = random.random()
        cumulative = 0
        for duration, weight in break_types:
            cumulative += weight
            if r < cumulative:
                return duration
        return break_types[0][0]
    
    def get_random_type_assignment_time(self):
        return random.uniform(2.0, 8.0)
    
    def add_tool_switch_event(self, tool):
        self.events.append({
            "timestamp": self.current_time.isoformat(),
            "event_type": "tool_switch",
            "tool": tool,
            "time_since_last_event": 0
        })
    
    def generate_polygon_events(self, points, annotation_type, polygon_id, type_name):
        # Add tool switch if it's the first polygon
        if not self.events or self.events[-1]["event_type"] != "tool_switch":
            self.add_tool_switch_event(f"{annotation_type}_outline")
        
        # Generate click events for each point
        start_time = self.current_time
        for i, point in enumerate(points):
            if i > 0:
                interval = self.get_random_click_interval()
                self.current_time += timedelta(seconds=interval)
            
            self.events.append({
                "timestamp": self.current_time.isoformat(),
                "event_type": "polygon_click",
                "annotation_type": annotation_type,
                "point": point,
                "click_number": i + 1,
                "time_since_last_click": interval if i > 0 else 0,
                "time_since_start": (self.current_time - start_time).total_seconds(),
                "is_closing_click": i == len(points) - 1
            })
        
        # Add type assignment event
        assignment_time = self.get_random_type_assignment_time()
        self.current_time += timedelta(seconds=assignment_time)
        
        self.events.append({
            "timestamp": self.current_time.isoformat(),
            "event_type": "type_assignment",
            "polygon_id": polygon_id,
            "annotation_type": annotation_type,
            "room_type" if annotation_type == "scene" else "shape_type": type_name,
            "time_since_polygon_completion": assignment_time,
            "total_points": len(points),
            "total_drawing_time": (self.current_time - start_time).total_seconds()
        })
        
        # Add break between polygons
        break_duration = self.get_random_break()
        self.current_time += timedelta(seconds=break_duration)
        self.events.append({
            "timestamp": self.current_time.isoformat(),
            "event_type": "break",
            "break_type": "between_polygons",
            "duration": break_duration
        })
    
    def generate_all_events(self):
        # Generate events for scenes
        for scene in self.input_data["annotation"]["scenes"]:
            self.generate_polygon_events(
                scene["outline"],
                "scene",
                scene["id"],
                scene["type"]
            )
        
        # Generate events for shapes
        for shape in self.input_data["annotation"]["shapes"]:
            self.generate_polygon_events(
                shape["outline"],
                "shape",
                shape["id"],
                shape["type"]
            )
        
        # Create final output
        output = {
            "annotation_events": {
                "metadata": {
                    "floorplan_id": self.input_data["floorplanId"],
                    "section_id": "floor2_section2",
                    "start_time": self.start_time.isoformat(),
                    "end_time": self.current_time.isoformat(),
                    "total_events": len(self.events),
                    "total_scenes": len(self.input_data["annotation"]["scenes"]),
                    "total_shapes": len(self.input_data["annotation"]["shapes"])
                },
                "events": self.events
            }
        }
        
        return output

def main():
    # Initialize generator with input JSON
    generator = AnnotationEventGenerator("data/floorplan_json/73883/73883_floor2_section2.json")
    
    # Generate all events
    output = generator.generate_all_events()
    
    # Save to file
    with open("annotation_events.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main() 