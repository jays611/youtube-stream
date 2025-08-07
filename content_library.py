#!/usr/bin/env python3
"""
Content Library Manager for Pre-built YouTube Stream
Manages 30-second chunks for 1-month base content + weekly additions
"""

import os
import json
import glob
import time
from typing import List, Dict, Optional
from config import *

class ContentLibrary:
    def __init__(self):
        self.library_dir = "/root/home_projects/youtube-stream/content_library"
        self.base_dir = os.path.join(self.library_dir, "base_content")
        self.weekly_dir = os.path.join(self.library_dir, "weekly_additions")
        self.stitched_dir = os.path.join(self.library_dir, "stitched_streams")
        self.metadata_file = os.path.join(self.library_dir, "library_metadata.json")
        
        self._ensure_directories()
        self.load_metadata()
    
    def _ensure_directories(self):
        """Create directory structure"""
        for dir_path in [self.library_dir, self.base_dir, self.weekly_dir, self.stitched_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def load_metadata(self):
        """Load or create library metadata"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "base_content": {"chunks": [], "total_duration_hours": 0},
                "weekly_additions": {"chunks": [], "weeks": []},
                "stitched_streams": {"playlists": []},
                "last_updated": time.time()
            }
            self.save_metadata()
    
    def scan_base_content(self):
        """Scan and catalog base content (30-second chunks)"""
        wav_files = glob.glob(os.path.join(self.base_dir, "*.wav"))
        wav_files.sort()
        
        chunks = []
        for i, file_path in enumerate(wav_files):
            filename = os.path.basename(file_path)
            chunk_info = {
                "id": i + 1,
                "filename": filename,
                "path": file_path,
                "duration": 30,
                "created_at": os.path.getctime(file_path),
                "week_added": "base"
            }
            chunks.append(chunk_info)
        
        self.metadata["base_content"]["chunks"] = chunks
        self.metadata["base_content"]["total_duration_hours"] = len(chunks) * 30 / 3600
        self.save_metadata()
        
        print(f"Cataloged {len(chunks)} base content chunks ({len(chunks) * 30 / 3600:.1f} hours)")
        return chunks
    
    def add_weekly_content(self, week_id: str, chunk_files: List[str]):
        """Add weekly generated content to library"""
        week_chunks = []
        
        for file_path in chunk_files:
            filename = os.path.basename(file_path)
            # Move to weekly directory
            dest_path = os.path.join(self.weekly_dir, f"week_{week_id}_{filename}")
            os.rename(file_path, dest_path)
            
            chunk_info = {
                "id": len(self.get_all_chunks()) + 1,
                "filename": os.path.basename(dest_path),
                "path": dest_path,
                "duration": 30,
                "created_at": time.time(),
                "week_added": week_id
            }
            week_chunks.append(chunk_info)
        
        # Add to metadata
        week_entry = {
            "week_id": week_id,
            "chunks": week_chunks,
            "added_at": time.time(),
            "chunk_count": len(week_chunks)
        }
        
        self.metadata["weekly_additions"]["weeks"].append(week_entry)
        self.metadata["weekly_additions"]["chunks"].extend(week_chunks)
        self.save_metadata()
        
        print(f"Added {len(week_chunks)} chunks for week {week_id}")
        return week_chunks
    
    def get_all_chunks(self) -> List[Dict]:
        """Get all available chunks (base + weekly)"""
        all_chunks = []
        all_chunks.extend(self.metadata["base_content"]["chunks"])
        all_chunks.extend(self.metadata["weekly_additions"]["chunks"])
        return all_chunks
    
    def get_library_stats(self) -> Dict:
        """Get library statistics"""
        all_chunks = self.get_all_chunks()
        total_hours = len(all_chunks) * 30 / 3600
        
        return {
            "total_chunks": len(all_chunks),
            "base_chunks": len(self.metadata["base_content"]["chunks"]),
            "weekly_chunks": len(self.metadata["weekly_additions"]["chunks"]),
            "total_hours": total_hours,
            "total_days": total_hours / 24,
            "weeks_added": len(self.metadata["weekly_additions"]["weeks"]),
            "storage_gb": len(all_chunks) * 1.9 / 1024  # Estimate 1.9MB per 30s chunk
        }
    
    def save_metadata(self):
        """Save library metadata"""
        self.metadata["last_updated"] = time.time()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

if __name__ == "__main__":
    library = ContentLibrary()
    library.scan_base_content()
    stats = library.get_library_stats()
    print("Library Stats:", stats)