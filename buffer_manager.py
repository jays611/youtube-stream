#!/usr/bin/env python3
"""
Buffer Manager for Indian Lofi Stream
Manages audio chunk queue and buffer health monitoring
"""

import os
import glob
import json
import time
from typing import List, Dict, Optional
from config import *

class BufferManager:
    def __init__(self):
        self.buffer_dir = BUFFER_DIR
        os.makedirs(self.buffer_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.buffer_dir, "buffer_metadata.json")
        self.load_metadata()
    
    def load_metadata(self):
        """Load buffer metadata from file"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "chunks": [],
                "next_chunk_id": 1,
                "current_prompt_index": 0
            }
    
    def save_metadata(self):
        """Save buffer metadata to file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def get_chunk_filename(self, chunk_id: int, prompt_index: int) -> str:
        """Generate chunk filename"""
        return f"chunk_{chunk_id:03d}_prompt_{prompt_index}_{CHUNK_DURATION}s.wav"
    
    def add_chunk(self, chunk_path: str, prompt_index: int) -> Dict:
        """Add new chunk to buffer"""
        chunk_id = self.metadata["next_chunk_id"]
        filename = self.get_chunk_filename(chunk_id, prompt_index)
        final_path = os.path.join(self.buffer_dir, filename)
        
        # Move chunk to buffer directory with proper name
        if chunk_path != final_path:
            os.rename(chunk_path, final_path)
        
        chunk_info = {
            "id": chunk_id,
            "filename": filename,
            "path": final_path,
            "prompt_index": prompt_index,
            "prompt": PROMPTS[prompt_index],
            "duration": CHUNK_DURATION,
            "created_at": time.time(),
            "consumed": False
        }
        
        self.metadata["chunks"].append(chunk_info)
        self.metadata["next_chunk_id"] += 1
        self.save_metadata()
        
        return chunk_info
    
    def get_next_chunk(self) -> Optional[Dict]:
        """Get next unconsumed chunk for streaming"""
        for chunk in self.metadata["chunks"]:
            if not chunk["consumed"] and os.path.exists(chunk["path"]):
                return chunk
        return None
    
    def mark_chunk_consumed(self, chunk_id: int):
        """Mark chunk as consumed (streamed)"""
        for chunk in self.metadata["chunks"]:
            if chunk["id"] == chunk_id:
                chunk["consumed"] = True
                break
        self.save_metadata()
    
    def get_buffer_status(self) -> Dict:
        """Get current buffer status"""
        available_chunks = [c for c in self.metadata["chunks"] if not c["consumed"] and os.path.exists(c["path"])]
        total_duration = len(available_chunks) * CHUNK_DURATION
        hours_remaining = total_duration / 3600
        
        # Determine buffer health
        if hours_remaining >= TARGET_BUFFER_HOURS:
            health = "HEALTHY"
            break_time = HEALTHY_BREAK
        elif hours_remaining >= WARNING_BUFFER_HOURS:
            health = "WARNING"
            break_time = WARNING_BREAK
        elif hours_remaining >= CRITICAL_BUFFER_HOURS:
            health = "CRITICAL"
            break_time = CRITICAL_BREAK
        elif hours_remaining >= EMERGENCY_BUFFER_HOURS:
            health = "EMERGENCY"
            break_time = EMERGENCY_BREAK
        else:
            health = "DEPLETED"
            break_time = 0
        
        return {
            "available_chunks": len(available_chunks),
            "total_duration_seconds": total_duration,
            "hours_remaining": hours_remaining,
            "health": health,
            "recommended_break": break_time,
            "next_prompt_index": self.metadata["current_prompt_index"]
        }
    
    def get_next_prompt_index(self) -> int:
        """Get next prompt index and update rotation"""
        current_index = self.metadata["current_prompt_index"]
        self.metadata["current_prompt_index"] = (current_index + 1) % len(PROMPTS)
        self.save_metadata()
        return current_index
    
    def cleanup_consumed_chunks(self, keep_last_n: int = 10):
        """Remove old consumed chunk files, keep last N for safety"""
        consumed_chunks = [c for c in self.metadata["chunks"] if c["consumed"]]
        consumed_chunks.sort(key=lambda x: x["created_at"])
        
        # Remove old consumed chunks, keep last N
        to_remove = consumed_chunks[:-keep_last_n] if len(consumed_chunks) > keep_last_n else []
        
        for chunk in to_remove:
            if os.path.exists(chunk["path"]):
                os.remove(chunk["path"])
            self.metadata["chunks"].remove(chunk)
        
        if to_remove:
            self.save_metadata()
            print(f"Cleaned up {len(to_remove)} old chunks")

if __name__ == "__main__":
    # Test buffer manager
    bm = BufferManager()
    status = bm.get_buffer_status()
    print(f"Buffer Status: {status}")