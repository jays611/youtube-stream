#!/usr/bin/env python3
"""
Stream Stitcher for Pre-built Content
Creates continuous streams from 30-second chunks with prompt-based breaks
"""

import os
import subprocess
import json
import random
from typing import List, Dict
from content_library import ContentLibrary
from config import PROMPTS

class StreamStitcher:
    def __init__(self):
        self.library = ContentLibrary()
        self.stitched_dir = self.library.stitched_dir
    
    def create_stream_segment(self, duration_hours: int, output_name: str) -> str:
        """Create a continuous stream segment of specified duration"""
        chunks_needed = duration_hours * 60 * 2  # 2 chunks per minute (30s each)
        all_chunks = self.library.get_all_chunks()
        
        if len(all_chunks) < chunks_needed:
            raise ValueError(f"Not enough chunks: need {chunks_needed}, have {len(all_chunks)}")
        
        # Shuffle for variety
        selected_chunks = random.sample(all_chunks, chunks_needed)
        selected_chunks.sort(key=lambda x: x['id'])  # Maintain some order
        
        # Create file list for ffmpeg
        filelist_path = f"/tmp/stream_filelist_{output_name}.txt"
        output_path = os.path.join(self.stitched_dir, f"{output_name}_{duration_hours}h.wav")
        
        with open(filelist_path, 'w') as f:
            for chunk in selected_chunks:
                f.write(f"file '{chunk['path']}'\n")
        
        # Stitch with ffmpeg
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', filelist_path,
            '-c', 'copy',
            '-y', output_path
        ]
        
        print(f"Stitching {chunks_needed} chunks into {duration_hours}h stream...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            os.remove(filelist_path)
            print(f"✓ Created: {output_path}")
            
            # Update metadata
            stream_info = {
                "name": output_name,
                "path": output_path,
                "duration_hours": duration_hours,
                "chunk_count": chunks_needed,
                "created_at": time.time(),
                "chunks_used": [c['id'] for c in selected_chunks]
            }
            
            self.library.metadata["stitched_streams"]["playlists"].append(stream_info)
            self.library.save_metadata()
            
            return output_path
        else:
            print(f"✗ Stitching failed: {result.stderr}")
            return None
    
    def create_weekly_batch(self) -> List[str]:
        """Create standard weekly stream segments"""
        segments = []
        
        # Create different duration segments for variety
        configs = [
            {"hours": 6, "name": "morning_stream"},
            {"hours": 8, "name": "day_stream"},
            {"hours": 6, "name": "evening_stream"},
            {"hours": 4, "name": "night_stream"}
        ]
        
        for config in configs:
            segment_path = self.create_stream_segment(
                config["hours"], 
                f"{config['name']}_week_{int(time.time())}"
            )
            if segment_path:
                segments.append(segment_path)
        
        return segments
    
    def create_youtube_content(self, duration_hours: int = 4) -> str:
        """Create content specifically for YouTube upload"""
        return self.create_stream_segment(duration_hours, f"youtube_content_{int(time.time())}")

if __name__ == "__main__":
    import time
    stitcher = StreamStitcher()
    
    # Test with available content
    library_stats = stitcher.library.get_library_stats()
    print(f"Library has {library_stats['total_hours']:.1f} hours of content")
    
    if library_stats['total_hours'] >= 4:
        test_stream = stitcher.create_stream_segment(1, "test_stream")
        print(f"Test stream created: {test_stream}")
    else:
        print("Not enough content for testing")