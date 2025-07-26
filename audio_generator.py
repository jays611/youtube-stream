#!/usr/bin/env python3
"""
Audio Generator for Indian Lofi Stream
Generates 10-minute audio chunks using AudioCraft
"""

import sys
import os
import time
import subprocess
import tempfile
from buffer_manager import BufferManager
from config import *

class AudioGenerator:
    def __init__(self):
        self.buffer_manager = BufferManager()
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

def generate_chunk(prompt, duration, output_path):
    # Load model
    model = MusicGen.get_pretrained("facebook/musicgen-{MODEL_SIZE}")
    model.set_generation_params(
        use_sampling=True,
        top_k=250,
        top_p=0.0,
        temperature=1.0,
        duration=duration,
        cfg_coef=3.0
    )
    
    # Generate audio
    print(f"Generating {{duration}}s audio...")
    start_time = time.time()
    
    with torch.no_grad():
        wav = model.generate([prompt], progress=True)
    
    generation_time = time.time() - start_time
    print(f"Generation completed in {{generation_time:.1f}} seconds")
    
    # Save audio
    audio_write(output_path.replace('.wav', ''), wav[0].cpu(), model.sample_rate, strategy="loudness")
    print(f"Saved: {{output_path}}")
    
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
    
    def generate_chunk(self, prompt: str, output_path: str) -> bool:
        """Generate single audio chunk"""
        try:
            print(f"\\nGenerating chunk: {os.path.basename(output_path)}")
            print(f"Prompt: {prompt}")
            print(f"Duration: {CHUNK_DURATION} seconds")
            
            start_time = time.time()
            
            # Run AudioCraft generation in subprocess
            cmd = [
                AUDIOCRAFT_VENV,
                self.generation_script,
                prompt,
                str(CHUNK_DURATION),
                output_path
            ]
            
            result = subprocess.run(cmd, text=True, cwd="/root/home_projects/audiocraft")
            
            if result.returncode == 0:
                generation_time = time.time() - start_time
                print(f"✓ Generation successful in {generation_time:.1f} seconds")
                return True
            else:
                print(f"✗ Generation failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"✗ Generation error: {e}")
            return False
    
    def run_generation_loop(self):
        """Main generation loop"""
        print("Starting Audio Generation Loop...")
        
        while True:
            try:
                # Check buffer status
                status = self.buffer_manager.get_buffer_status()
                print(f"\\n=== Buffer Status ===")
                print(f"Health: {status['health']}")
                print(f"Available chunks: {status['available_chunks']}")
                print(f"Hours remaining: {status['hours_remaining']:.1f}")
                
                # Only quit if we have chunks but they're depleted
                # Allow initial generation when starting from empty
                if status['health'] == 'DEPLETED' and status['available_chunks'] > 0:
                    print("BUFFER DEPLETED - STOPPING GENERATION")
                    break
                
                # Get next prompt
                prompt_index = self.buffer_manager.get_next_prompt_index()
                prompt = PROMPTS[prompt_index]
                
                # Generate chunk
                temp_path = f"/tmp/chunk_temp_{int(time.time())}.wav"
                
                if self.generate_chunk(prompt, temp_path):
                    # Add to buffer
                    chunk_info = self.buffer_manager.add_chunk(temp_path, prompt_index)
                    print(f"✓ Added chunk {chunk_info['id']} to buffer")
                    
                    # Cleanup old chunks
                    self.buffer_manager.cleanup_consumed_chunks()
                else:
                    print("✗ Failed to generate chunk, retrying...")
                    continue
                
                # Take break based on buffer health
                break_time = status['recommended_break']
                if break_time > 0:
                    print(f"Taking {break_time}s break...")
                    time.sleep(break_time)
                
            except KeyboardInterrupt:
                print("\\nGeneration stopped by user")
                break
            except Exception as e:
                print(f"Generation loop error: {e}")
                time.sleep(30)  # Wait before retrying

if __name__ == "__main__":
    generator = AudioGenerator()
    generator.run_generation_loop()