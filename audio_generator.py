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

# Global model instance (load once, reuse for all chunks)
model = None

def load_model():
    global model
    if model is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        torch.set_default_device(device)
        
        print(f"Loading model on {{device}}...")
        model = MusicGen.get_pretrained("facebook/musicgen-{MODEL_SIZE}")
        
        # GPU optimization: use FP16 if available
        if device == 'cuda':
            model = model.to(dtype=torch.float16, device=device)
            print(f"Model optimized for GPU with FP16")
        
        model.set_generation_params(
            use_sampling=True,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
            duration=60,  # Will be overridden per call
            cfg_coef=3.0
        )
        print(f"Model loaded and ready on {{device}}")
    return model

def generate_chunk(prompt, duration, output_path):
    model = load_model()
    
    # Update duration for this generation
    model.set_generation_params(duration=duration)
    
    print(f"Generating {{duration}}s audio: {{prompt[:50]}}...")
    start_time = time.time()
    
    # Use AudioCraft's built-in progress display
    with torch.no_grad():
        wav = model.generate([prompt], progress=True)
    
    generation_time = time.time() - start_time
    print(f"\\nGeneration completed in {{generation_time:.1f}}s ({{duration/generation_time:.2f}}x realtime)")
    
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
        """Main generation loop - continuous with cooldowns"""
        print("Starting Continuous Audio Generation Loop...")
        print("Rolling buffer: always generates, deletes oldest when full")
        
        generation_count = 0
        loop_start_time = time.time()
        
        while True:
            try:
                # Check buffer status
                status = self.buffer_manager.get_buffer_status()
                generation_count += 1
                
                print(f"\n=== Generation #{generation_count} ===")
                print(f"Buffer: {status['total_files']}/{MAX_BUFFER_FILES} files | Health: {status['health']}")
                print(f"Available: {status['available_chunks']} chunks ({status['hours_remaining']:.1f}h remaining)")
                
                # Emergency stop only if truly depleted
                if status['health'] == 'DEPLETED':
                    print("BUFFER DEPLETED - STOPPING GENERATION")
                    break
                
                # Get next prompt (handles rotation automatically)
                prompt_index = self.buffer_manager.get_next_prompt_index()
                prompt = PROMPTS[prompt_index]
                
                print(f"Prompt {prompt_index}: {prompt[:60]}...")
                
                # Generate chunk
                temp_path = f"/tmp/chunk_temp_{int(time.time())}.wav"
                
                if self.generate_chunk(prompt, temp_path):
                    # Add to buffer (handles rolling deletion automatically)
                    chunk_info = self.buffer_manager.add_chunk(temp_path, prompt_index)
                    
                    # Calculate running stats
                    elapsed = time.time() - loop_start_time
                    avg_time = elapsed / generation_count
                    
                    print(f"✓ Added chunk {chunk_info['id']} to rolling buffer")
                    print(f"Stats: {generation_count} chunks in {elapsed/3600:.1f}h (avg: {avg_time/60:.1f} min/chunk)")
                else:
                    print("✗ Failed to generate chunk, retrying...")
                    continue
                
                # Cooldown based on buffer health
                cooldown = status['cooldown_seconds']
                if cooldown > 0:
                    print(f"Cooldown: {cooldown}s ({status['health']} state)")
                    time.sleep(cooldown)
                
            except KeyboardInterrupt:
                print("\nGeneration stopped by user")
                break
            except Exception as e:
                print(f"Generation loop error: {e}")
                time.sleep(30)  # Wait before retrying

if __name__ == "__main__":
    generator = AudioGenerator()
    generator.run_generation_loop()