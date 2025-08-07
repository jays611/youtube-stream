#!/usr/bin/env python3
"""
Scheduled Audio Generator for Weekly Content
Generates 240 chunks (2 hours) per week via cron scheduling
"""

import os
import sys
import time
import tempfile
from datetime import datetime
from content_library import ContentLibrary
import sys
import os
import subprocess
import tempfile
from datetime import datetime
from typing import List, Dict
from content_library import ContentLibrary
from config import PROMPTS, AUDIOCRAFT_VENV, CHUNK_DURATION

class AudioGenerator:
    def __init__(self):
        self.generation_script = self._create_generation_script()
    
    def _create_generation_script(self) -> str:
        """Create temporary script for AudioCraft generation"""
        script_content = f'''
import sys
sys.path.append("/root/home_projects/audiocraft")
import torch
import os
import time
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

# Global model instance (load once, reuse for all chunks)
model = None

def load_model():
    global model
    if model is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        torch.set_default_device(device)
        
        print(f"Loading model on {{device}}...")
        model = MusicGen.get_pretrained("facebook/musicgen-small")
        
        if device == 'cuda':
            model = model.to(dtype=torch.float16, device=device)
        
        model.set_generation_params(
            use_sampling=True,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
            duration=30,
            cfg_coef=3.0
        )
    return model

def generate_chunk(prompt, duration, output_path):
    model = load_model()
    model.set_generation_params(duration=duration)
    
    with torch.no_grad():
        wav = model.generate([prompt], progress=True)
    
    audio_write(
        output_path.replace('.wav', ''), 
        wav[0].cpu(), 
        model.sample_rate, 
        strategy="loudness", 
        loudness_compressor=True
    )
    
    return output_path

if __name__ == "__main__":
    prompt = sys.argv[1]
    duration = int(sys.argv[2])
    output_path = sys.argv[3]
    generate_chunk(prompt, duration, output_path)
'''
        
        script_path = "/tmp/audiocraft_generator.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        return script_path
    
    def generate_chunk(self, prompt: str, output_path: str, duration: int = 30) -> bool:
        """Generate single audio chunk"""
        try:
            cmd = [
                AUDIOCRAFT_VENV,
                self.generation_script,
                prompt,
                str(duration),
                output_path
            ]
            
            result = subprocess.run(cmd, text=True, cwd="/root/home_projects/audiocraft")
            return result.returncode == 0
        except Exception as e:
            print(f"Generation error: {e}")
            return False
from config import PROMPTS

class ScheduledGenerator:
    def __init__(self):
        self.library = ContentLibrary()
        self.generator = AudioGenerator()
        self.chunks_per_week = 240  # 2 hours = 240 × 30s chunks
        self.chunks_per_session = 24  # Generate 24 chunks per session (12 minutes of audio)
    
    def generate_weekly_batch(self, week_id: str = None) -> bool:
        """Generate full week's content (240 chunks)"""
        if not week_id:
            week_id = datetime.now().strftime("%Y_W%U")
        
        print(f"=== Generating Weekly Batch: {week_id} ===")
        print(f"Target: {self.chunks_per_week} chunks (2 hours)")
        
        generated_files = []
        sessions_needed = self.chunks_per_week // self.chunks_per_session  # 10 sessions
        
        for session in range(sessions_needed):
            print(f"\n--- Session {session + 1}/{sessions_needed} ---")
            session_files = self.generate_session_batch()
            
            if session_files:
                generated_files.extend(session_files)
                print(f"✓ Session complete: {len(session_files)} chunks")
            else:
                print(f"✗ Session failed")
                return False
        
        # Add to library
        if generated_files:
            self.library.add_weekly_content(week_id, generated_files)
            print(f"\n✅ Weekly batch complete: {len(generated_files)} chunks added to library")
            return True
        
        return False
    
    def generate_session_batch(self) -> List[str]:
        """Generate one session batch (24 chunks = 12 minutes audio)"""
        session_files = []
        temp_dir = tempfile.mkdtemp(prefix="weekly_gen_")
        
        try:
            for i in range(self.chunks_per_session):
                # Rotate through prompts
                prompt_index = i % len(PROMPTS)
                prompt = PROMPTS[prompt_index]
                
                # Generate 30-second chunk
                temp_path = os.path.join(temp_dir, f"chunk_{i:03d}_30s.wav")
                
                print(f"  Generating chunk {i+1}/24: prompt {prompt_index}")
                
                if self.generator.generate_chunk(prompt, temp_path, duration=30):
                    session_files.append(temp_path)
                else:
                    print(f"  ✗ Failed to generate chunk {i+1}")
                    break
            
            return session_files
            
        except Exception as e:
            print(f"Session generation error: {e}")
            return []
    
    def generate_single_session(self) -> bool:
        """Generate single session for cron scheduling"""
        week_id = datetime.now().strftime("%Y_W%U")
        
        print(f"=== Single Session Generation ===")
        print(f"Week: {week_id}")
        print(f"Generating {self.chunks_per_session} chunks...")
        
        session_files = self.generate_session_batch()
        
        if session_files:
            # Add to library with session timestamp
            session_id = f"{week_id}_s{int(time.time())}"
            self.library.add_weekly_content(session_id, session_files)
            
            print(f"✅ Session complete: {len(session_files)} chunks added")
            return True
        else:
            print(f"✗ Session failed")
            return False
    
    def get_weekly_progress(self, week_id: str = None) -> Dict:
        """Check progress for current week"""
        if not week_id:
            week_id = datetime.now().strftime("%Y_W%U")
        
        # Count chunks for this week
        week_chunks = [
            chunk for chunk in self.library.metadata["weekly_additions"]["chunks"]
            if chunk["week_added"].startswith(week_id)
        ]
        
        progress = len(week_chunks)
        remaining = max(0, self.chunks_per_week - progress)
        
        return {
            "week_id": week_id,
            "completed_chunks": progress,
            "target_chunks": self.chunks_per_week,
            "remaining_chunks": remaining,
            "progress_percent": (progress / self.chunks_per_week) * 100,
            "sessions_completed": progress // self.chunks_per_session,
            "sessions_remaining": remaining // self.chunks_per_session
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: python scheduled_generator.py [command]")
        print("Commands:")
        print("  session    - Generate single session (24 chunks)")
        print("  week       - Generate full week (240 chunks)")
        print("  progress   - Show weekly progress")
        sys.exit(1)
    
    command = sys.argv[1]
    generator = ScheduledGenerator()
    
    if command == "session":
        generator.generate_single_session()
    elif command == "week":
        generator.generate_weekly_batch()
    elif command == "progress":
        progress = generator.get_weekly_progress()
        print(f"Week {progress['week_id']} Progress:")
        print(f"  Completed: {progress['completed_chunks']}/{progress['target_chunks']} chunks")
        print(f"  Progress: {progress['progress_percent']:.1f}%")
        print(f"  Sessions: {progress['sessions_completed']}/{progress['sessions_remaining']} remaining")
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()