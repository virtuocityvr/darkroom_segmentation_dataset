import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime

class AnnotationDashboard:
    def __init__(self, events_json_path):
        with open(events_json_path, 'r') as f:
            self.data = json.load(f)
        self.events = self.data['annotation_events']['events']
        self.metadata = self.data['annotation_events']['metadata']
        
    def prepare_data(self):
        # Extract scene and shape data
        scenes = []
        shapes = []
        
        for event in self.events:
            if event['event_type'] == 'type_assignment':
                if event['annotation_type'] == 'scene':
                    scenes.append({
                        'polygon_id': event.get('polygon_id'),
                        'type': event.get('room_type'),
                        'duration': event.get('total_drawing_time'),
                        'points': event.get('total_points'),
                        'category': 'Scene'
                    })
                elif event['annotation_type'] == 'shape':
                    shapes.append({
                        'polygon_id': event.get('polygon_id'),
                        'type': event.get('shape_type'),
                        'duration': event.get('total_drawing_time'),
                        'points': event.get('total_points'),
                        'category': 'Shape'
                    })
        
        # Create DataFrames
        self.scenes_df = pd.DataFrame(scenes)
        self.shapes_df = pd.DataFrame(shapes)
        
        # Combine for total view
        self.all_df = pd.concat([self.scenes_df, self.shapes_df])
        
    def create_dashboard(self):
        # Create a figure with subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Points vs Duration', 'Drawing Time by Type',
                'Duration Distribution', 'Type Distribution',
                'Points Distribution', 'Category Distribution'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "box"}],
                [{"type": "histogram"}, {"type": "pie"}],
                [{"type": "histogram"}, {"type": "pie"}]
            ]
        )

        # 1. Points vs Duration scatter plot
        for category in ['Scene', 'Shape']:
            df = self.all_df[self.all_df['category'] == category]
            fig.add_trace(
                go.Scatter(
                    x=df['points'],
                    y=df['duration'],
                    mode='markers',
                    name=category,
                    text=df['type']
                ),
                row=1, col=1
            )

        # 2. Drawing Time by Type box plot
        fig.add_trace(
            go.Box(
                x=self.all_df['type'],
                y=self.all_df['duration'],
                name='Duration'
            ),
            row=1, col=2
        )

        # 3. Duration histogram
        fig.add_trace(
            go.Histogram(
                x=self.all_df['duration'],
                name='Duration'
            ),
            row=2, col=1
        )

        # 4. Type distribution pie chart
        type_counts = self.all_df['type'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=type_counts.index,
                values=type_counts.values,
                name='Types'
            ),
            row=2, col=2
        )

        # 5. Points histogram
        fig.add_trace(
            go.Histogram(
                x=self.all_df['points'],
                name='Points'
            ),
            row=3, col=1
        )

        # 6. Category distribution pie chart
        category_counts = self.all_df['category'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=category_counts.index,
                values=category_counts.values,
                name='Categories'
            ),
            row=3, col=2
        )

        # Update layout
        fig.update_layout(
            height=1200,
            width=1600,
            title_text="Annotation Event Analysis Dashboard",
            showlegend=True
        )

        # Add summary statistics
        stats = self.all_df.groupby('type').agg({
            'duration': ['mean', 'std', 'min', 'max'],
            'points': ['mean', 'std']
        }).round(2)

        # Create a table figure
        table_fig = go.Figure(data=[go.Table(
            header=dict(
                values=['Type', 'Mean Duration', 'Std Duration', 'Min Duration', 'Max Duration', 'Mean Points', 'Std Points'],
                fill_color='paleturquoise',
                align='left'
            ),
            cells=dict(
                values=[
                    stats.index,
                    stats[('duration', 'mean')],
                    stats[('duration', 'std')],
                    stats[('duration', 'min')],
                    stats[('duration', 'max')],
                    stats[('points', 'mean')],
                    stats[('points', 'std')]
                ],
                fill_color='lavender',
                align='left'
            )
        )])

        # Save both figures to HTML
        fig.write_html('annotation_dashboard.html')
        table_fig.write_html('annotation_stats.html')

def main():
    dashboard = AnnotationDashboard('annotation_events.json')
    dashboard.prepare_data()
    dashboard.create_dashboard()
    print("Dashboard has been generated as 'annotation_dashboard.html'")
    print("Statistics table has been generated as 'annotation_stats.html'")

if __name__ == "__main__":
    main() 