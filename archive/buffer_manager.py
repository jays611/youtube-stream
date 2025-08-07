#!/usr/bin/env python3
"""
Rolling Buffer Manager for Indian Lofi Stream
Maintains exactly 1,440 files (1 week of audio) with rolling deletion
"""

import os
import glob
import json
import time
import fcntl
from typing import List, Dict, Optional
from config import *

class BufferManager:
    def __init__(self):
        self.buffer_dir = BUFFER_DIR
        os.makedirs(self.buffer_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.buffer_dir, "buffer_metadata.json")
        self.load_or_create_metadata()
        self.enforce_buffer_limit()
    
    def load_or_create_metadata(self):
        """Load existing metadata or create from files on disk with locking"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    self.metadata = json.load(f)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                print(f"Loaded metadata with {len(self.metadata['chunks'])} chunks")
            except Exception as e:
                print(f"Error loading metadata: {e}, rebuilding from files...")
                self.rebuild_metadata_from_files()
        else:
            print("No metadata found, scanning files...")
            self.rebuild_metadata_from_files()
    
    def rebuild_metadata_from_files(self):
        """Rebuild metadata by scanning audio_buffer directory with prompt validation"""
        print("Rebuilding metadata from files...")
        
        # Find all WAV files
        wav_files = glob.glob(os.path.join(self.buffer_dir, "chunk_*.wav"))
        wav_files.sort()  # Sort by filename
        
        self.metadata = {
            "chunks": [],
            "next_chunk_id": 1,
            "current_prompt_index": 0
        }
        
        prompt_mismatches = []
        
        for i, file_path in enumerate(wav_files):
            filename = os.path.basename(file_path)
            
            # Parse filename: chunk_001_prompt_0_60s.wav
            try:
                parts = filename.replace('.wav', '').split('_')
                chunk_id = int(parts[1])
                file_prompt_index = int(parts[3])
                
                # Calculate expected prompt based on position
                expected_prompt_index = ((i) // CHUNKS_PER_PROMPT) % len(PROMPTS)
                
                # Validate prompt alignment
                if file_prompt_index != expected_prompt_index:
                    prompt_mismatches.append({
                        "file": filename,
                        "position": i,
                        "file_prompt": file_prompt_index,
                        "expected_prompt": expected_prompt_index
                    })
                    print(f"WARNING: Prompt mismatch in {filename}: has {file_prompt_index}, expected {expected_prompt_index}")
                
                chunk_info = {
                    "id": chunk_id,
                    "filename": filename,
                    "path": file_path,
                    "prompt_index": file_prompt_index,  # Use file's prompt, not calculated
                    "prompt": PROMPTS[file_prompt_index] if file_prompt_index < len(PROMPTS) else "unknown",
                    "duration": CHUNK_DURATION,
                    "created_at": os.path.getctime(file_path),
                    "consumed": False
                }
                
                self.metadata["chunks"].append(chunk_info)
                
                # Update next_chunk_id to be higher than any existing
                if chunk_id >= self.metadata["next_chunk_id"]:
                    self.metadata["next_chunk_id"] = chunk_id + 1
                    
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse filename {filename}: {e}")
                continue
        
        # Sort chunks by ID
        self.metadata["chunks"].sort(key=lambda x: x["id"])
        
        if prompt_mismatches:
            print(f"\n⚠️  PROMPT ALIGNMENT ISSUES DETECTED ({len(prompt_mismatches)} files)")
            print("This may cause missing 3-second breaks between prompts.")
            print("Consider manual repair or regeneration of affected segments.")
        
        print(f"Rebuilt metadata with {len(self.metadata['chunks'])} chunks")
        self.save_metadata()
    
    def enforce_buffer_limit(self):
        """Ensure buffer has exactly MAX_BUFFER_FILES or fewer"""
        current_count = len(self.metadata["chunks"])
        
        if current_count > MAX_BUFFER_FILES:
            print(f"Buffer has {current_count} files, trimming to {MAX_BUFFER_FILES}")
            
            # Sort by creation time, delete oldest
            self.metadata["chunks"].sort(key=lambda x: x["created_at"])
            
            files_to_delete = current_count - MAX_BUFFER_FILES
            for i in range(files_to_delete):
                chunk_to_delete = self.metadata["chunks"][i]
                self.delete_chunk_file(chunk_to_delete)
            
            # Keep only the newest MAX_BUFFER_FILES
            self.metadata["chunks"] = self.metadata["chunks"][files_to_delete:]
            self.save_metadata()
            
            print(f"Trimmed buffer to {len(self.metadata['chunks'])} files")
    
    def delete_chunk_file(self, chunk_info: Dict):
        """Delete a chunk file from disk"""
        try:
            if os.path.exists(chunk_info["path"]):
                os.remove(chunk_info["path"])
                print(f"Deleted old file: {chunk_info['filename']}")
        except Exception as e:
            print(f"Error deleting file {chunk_info['filename']}: {e}")
    
    def add_chunk(self, chunk_path: str, prompt_index: int) -> Dict:
        """Add new chunk to buffer with atomic write, defer deletion"""
        with self._metadata_lock():
            chunk_id = self.metadata["next_chunk_id"]
            filename = f"chunk_{chunk_id:03d}_prompt_{prompt_index}_{CHUNK_DURATION}s.wav"
            final_path = os.path.join(self.buffer_dir, filename)
            temp_path = os.path.join(self.buffer_dir, f".tmp_{filename}")
            
            # Atomic write: temp -> fsync -> rename
            if chunk_path != temp_path:
                os.rename(chunk_path, temp_path)
            
            # Fsync to ensure data is written
            with open(temp_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename to final location
            os.rename(temp_path, final_path)
            
            # Add new chunk to metadata
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
            
            # Purge old consumed files if over limit (deferred deletion)
            self.purge_consumed_files()
            
            self.save_metadata()
            
            print(f"Added chunk {chunk_id}, buffer size: {len(self.metadata['chunks'])}")
            return chunk_info
    
    def get_next_chunk(self) -> Optional[Dict]:
        """Get next unconsumed chunk for streaming with locking"""
        with self._metadata_lock():
            # Sort by ID to ensure proper order
            available_chunks = [c for c in self.metadata["chunks"] if not c["consumed"] and os.path.exists(c["path"])]
            available_chunks.sort(key=lambda x: x["id"])
            
            return available_chunks[0] if available_chunks else None
    
    def mark_chunk_consumed(self, chunk_id: int):
        """Mark chunk as consumed and trigger purge"""
        with self._metadata_lock():
            for chunk in self.metadata["chunks"]:
                if chunk["id"] == chunk_id:
                    chunk["consumed"] = True
                    break
            
            # Trigger purge after marking consumed
            self.purge_consumed_files()
            self.save_metadata()
    
    def get_buffer_status(self) -> Dict:
        """Get current buffer status based on UNCONSUMED count"""
        with self._metadata_lock():
            available_chunks = [c for c in self.metadata["chunks"] if not c["consumed"] and os.path.exists(c["path"])]
            unconsumed_count = len(available_chunks)
            
            # Calculate hours remaining (60 chunks = 1 hour)
            hours_remaining = unconsumed_count / 60
            
            # Determine buffer health based on UNCONSUMED hours
            if hours_remaining >= TARGET_BUFFER_HOURS:
                health = "HEALTHY"
            elif hours_remaining >= WARNING_BUFFER_HOURS:
                health = "WARNING"
            elif hours_remaining >= CRITICAL_BUFFER_HOURS:
                health = "CRITICAL"
            elif hours_remaining >= EMERGENCY_BUFFER_HOURS:
                health = "EMERGENCY"
            else:
                health = "DEPLETED"
            
            return {
                "total_files": len(self.metadata["chunks"]),
                "available_chunks": unconsumed_count,
                "hours_remaining": hours_remaining,
                "health": health,
                "cooldown_seconds": COOLDOWN_TIMINGS.get(health, 0),
                "next_prompt_index": self.metadata["current_prompt_index"],
                "buffer_full": len(self.metadata["chunks"]) >= MAX_BUFFER_FILES
            }
    
    def get_next_prompt_index(self) -> int:
        """Get next prompt index for generation with locking"""
        with self._metadata_lock():
            # Count chunks for current prompt
            current_prompt = self.metadata["current_prompt_index"]
            current_prompt_chunks = [c for c in self.metadata["chunks"] 
                                   if c["prompt_index"] == current_prompt]
            
            # If we have enough chunks for this prompt, move to next
            if len(current_prompt_chunks) >= CHUNKS_PER_PROMPT:
                self.metadata["current_prompt_index"] = (current_prompt + 1) % len(PROMPTS)
                self.save_metadata()
            
            return self.metadata["current_prompt_index"]
    
    def save_metadata(self):
        """Save buffer metadata to file with locking"""
        try:
            with open(self.metadata_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(self.metadata, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def get_file_count(self) -> int:
        """Get current number of files in buffer"""
        return len(self.metadata["chunks"])
    
    def _metadata_lock(self):
        """Context manager for metadata file locking"""
        class MetadataLock:
            def __init__(self, metadata_file):
                self.metadata_file = metadata_file
                self.lock_file = metadata_file + ".lock"
                self.lock_fd = None
            
            def __enter__(self):
                self.lock_fd = open(self.lock_file, 'w')
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.lock_fd:
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                    self.lock_fd.close()
                    try:
                        os.remove(self.lock_file)
                    except:
                        pass
        
        return MetadataLock(self.metadata_file)
    
    def purge_consumed_files(self):
        """Remove consumed files when buffer exceeds limit (deferred deletion)"""
        if len(self.metadata["chunks"]) <= MAX_BUFFER_FILES:
            return
        
        # Find consumed files, sorted by creation time (oldest first)
        consumed_chunks = [c for c in self.metadata["chunks"] if c["consumed"]]
        consumed_chunks.sort(key=lambda x: x["created_at"])
        
        # Calculate how many to remove
        excess_count = len(self.metadata["chunks"]) - MAX_BUFFER_FILES
        to_remove = consumed_chunks[:excess_count]
        
        for chunk in to_remove:
            self.delete_chunk_file(chunk)
            self.metadata["chunks"].remove(chunk)
            print(f"Purged consumed file: {chunk['filename']}")
        
        if to_remove:
            print(f"Purged {len(to_remove)} consumed files, buffer size: {len(self.metadata['chunks'])}")

if __name__ == "__main__":
    # Test buffer manager
    bm = BufferManager()
    status = bm.get_buffer_status()
    print(f"Buffer Status: {status}")