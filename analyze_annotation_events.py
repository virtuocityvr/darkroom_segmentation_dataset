import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class AnnotationEventAnalyzer:
    def __init__(self, events_json_path):
        with open(events_json_path, 'r') as f:
            self.data = json.load(f)
        self.events = self.data['annotation_events']['events']
        self.metadata = self.data['annotation_events']['metadata']
        
    def parse_timestamp(self, timestamp):
        return datetime.fromisoformat(timestamp)
    
    def get_polygon_events(self, polygon_id):
        """Get all events related to a specific polygon"""
        polygon_events = []
        for event in self.events:
            if event.get('polygon_id') == polygon_id:
                polygon_events.append(event)
        return polygon_events
    
    def analyze_drawing_times(self):
        """Analyze time taken to draw each polygon"""
        scenes = []
        shapes = []
        for event in self.events:
            if event['event_type'] == 'type_assignment':
                if event['annotation_type'] == 'scene':
                    scenes.append({
                        'polygon_id': event.get('polygon_id'),
                        'room_type': event.get('room_type'),
                        'duration': event.get('total_drawing_time'),
                        'points': event.get('total_points')
                    })
                elif event['annotation_type'] == 'shape':
                    shapes.append({
                        'polygon_id': event.get('polygon_id'),
                        'shape_type': event.get('shape_type'),
                        'duration': event.get('total_drawing_time'),
                        'points': event.get('total_points')
                    })
        return {'scenes': scenes, 'shapes': shapes}
    
    def analyze_break_patterns(self):
        """Analyze patterns in breaks between polygons"""
        breaks = []
        for event in self.events:
            if event['event_type'] == 'break':
                breaks.append(event['duration'])
        return breaks
    
    def analyze_click_intervals(self):
        """Analyze intervals between clicks"""
        intervals = []
        for event in self.events:
            if event['event_type'] == 'polygon_click' and 'time_since_last_click' in event:
                intervals.append(event['time_since_last_click'])
        return intervals
    
    def generate_reports(self):
        """Generate comprehensive analysis reports"""
        # Get drawing times
        drawing_times = self.analyze_drawing_times()
        
        # Convert to DataFrames for easier analysis
        scenes_df = pd.DataFrame(drawing_times['scenes'])
        shapes_df = pd.DataFrame(drawing_times['shapes'])
        
        # Basic statistics
        print("\n=== Drawing Time Analysis ===")
        print("\nScenes:")
        if not scenes_df.empty:
            print(scenes_df.groupby('room_type').agg({
                'duration': ['mean', 'std', 'min', 'max'],
                'points': ['mean', 'std']
            }).round(2))
        else:
            print("No scene data available.")
        
        print("\nShapes:")
        if not shapes_df.empty:
            print(shapes_df.groupby('shape_type').agg({
                'duration': ['mean', 'std', 'min', 'max'],
                'points': ['mean', 'std']
            }).round(2))
        else:
            print("No shape data available.")
        
        # Break analysis
        breaks = self.analyze_break_patterns()
        print("\n=== Break Analysis ===")
        print(f"Average break duration: {sum(breaks)/len(breaks):.2f} seconds")
        print(f"Total break time: {sum(breaks):.2f} seconds")
        
        # Click interval analysis
        intervals = self.analyze_click_intervals()
        print("\n=== Click Interval Analysis ===")
        print(f"Average interval between clicks: {sum(intervals)/len(intervals):.2f} seconds")
        print(f"Max interval: {max(intervals):.2f} seconds")
        print(f"Min interval: {min(intervals):.2f} seconds")
        
        # Generate visualizations
        self.generate_visualizations(scenes_df, shapes_df, breaks, intervals)
    
    def generate_visualizations(self, scenes_df, shapes_df, breaks, intervals):
        """Generate visualizations of the analysis"""
        # Set style
        plt.style.use('seaborn-v0_8')
        
        # Create figure with subplots
        fig = plt.figure(figsize=(15, 10))
        
        # 1. Drawing time by type
        plt.subplot(2, 2, 1)
        if not scenes_df.empty:
            sns.boxplot(data=scenes_df, x='room_type', y='duration')
            plt.title('Scene Drawing Times by Type')
            plt.xticks(rotation=45)
        
        # 2. Points vs Duration
        plt.subplot(2, 2, 2)
        if not scenes_df.empty:
            sns.scatterplot(data=scenes_df, x='points', y='duration', hue='room_type')
            plt.title('Points vs Duration for Scenes')
        
        # 3. Break duration distribution
        plt.subplot(2, 2, 3)
        if breaks:
            sns.histplot(breaks, bins=20)
            plt.title('Break Duration Distribution')
        
        # 4. Click interval distribution
        plt.subplot(2, 2, 4)
        if intervals:
            sns.histplot(intervals, bins=20)
            plt.title('Click Interval Distribution')
        
        plt.tight_layout()
        plt.savefig('annotation_analysis.png')
        plt.close()

def main():
    analyzer = AnnotationEventAnalyzer('annotation_events.json')
    analyzer.generate_reports()

if __name__ == "__main__":
    main() 