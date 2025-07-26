#!/usr/bin/env python3
"""
Stream Feeder for Indian Lofi Stream
Feeds audio chunks to output with 3-second breaks between prompts
"""

import os
import time
import wave
import numpy as np
from buffer_manager import BufferManager
from config import *

class StreamFeeder:
    def __init__(self):
        self.buffer_manager = BufferManager()
        self.current_chunk = None
        self.last_prompt_index = None
    
    def create_silence(self, duration_seconds: float) -> bytes:
        """Create silence audio data"""
        samples = int(SAMPLE_RATE * duration_seconds)
        silence = np.zeros(samples, dtype=np.int16)
        return silence.tobytes()
    
    def read_audio_chunk(self, file_path: str) -> bytes:
        """Read audio chunk from WAV file"""
        try:
            with wave.open(file_path, 'rb') as wav_file:
                return wav_file.readframes(wav_file.getnframes())
        except Exception as e:
            print(f"Error reading audio chunk {file_path}: {e}")
            return b''
    
    def should_add_break(self, chunk_info: dict) -> bool:
        """Check if we should add 3-second break between prompts"""
        if self.last_prompt_index is None:
            return False
        return chunk_info['prompt_index'] != self.last_prompt_index
    
    def stream_to_stdout(self):
        """Stream audio chunks to stdout (for testing)"""
        print("Starting stream feeder (outputting to stdout)...")
        
        while True:
            try:
                # Get next chunk
                chunk_info = self.buffer_manager.get_next_chunk()
                
                if chunk_info is None:
                    print("No chunks available, waiting...")
                    time.sleep(5)
                    continue
                
                print(f"\\nStreaming chunk {chunk_info['id']}: {chunk_info['filename']}")
                print(f"Prompt: {chunk_info['prompt'][:50]}...")
                
                # Add 3-second break if prompt changed
                if self.should_add_break(chunk_info):
                    print("Adding 3-second break (prompt change)")
                    silence = self.create_silence(3.0)
                    # In real implementation, this would go to FFmpeg
                    # For testing, we just simulate
                    time.sleep(0.1)  # Simulate break
                
                # Stream the chunk
                audio_data = self.read_audio_chunk(chunk_info['path'])
                if audio_data:
                    # In real implementation, this would pipe to FFmpeg
                    # For testing, we simulate streaming time
                    print(f"Streaming {len(audio_data)} bytes...")
                    
                    # Simulate real-time streaming (10 minutes = 600 seconds)
                    # For testing, we'll just wait 2 seconds
                    time.sleep(2)
                    
                    print(f"✓ Finished streaming chunk {chunk_info['id']}")
                    
                    # Mark chunk as consumed
                    self.buffer_manager.mark_chunk_consumed(chunk_info['id'])
                    self.last_prompt_index = chunk_info['prompt_index']
                else:
                    print(f"✗ Failed to read chunk {chunk_info['id']}")
                
            except KeyboardInterrupt:
                print("\\nStream feeder stopped by user")
                break
            except Exception as e:
                print(f"Stream feeder error: {e}")
                time.sleep(5)
    
    def get_stream_status(self) -> dict:
        """Get current streaming status"""
        buffer_status = self.buffer_manager.get_buffer_status()
        return {
            "buffer_health": buffer_status['health'],
            "chunks_available": buffer_status['available_chunks'],
            "hours_remaining": buffer_status['hours_remaining'],
            "current_chunk": self.current_chunk['id'] if self.current_chunk else None,
            "last_prompt": self.last_prompt_index
        }

if __name__ == "__main__":
    feeder = StreamFeeder()
    feeder.stream_to_stdout()