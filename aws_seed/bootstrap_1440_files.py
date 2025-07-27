#!/usr/bin/env python3
"""
Bootstrap script to generate initial 1,440 files (1 week of audio)
Run this on a powerful server, then transfer files + metadata to main system
"""

import sys
import os
import time
import json
import subprocess
import torch

# Import config from parent directory
import importlib.util
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
PROMPTS = config.PROMPTS

# Bootstrap configuration
CHUNK_DURATION = 60  # 1 minute chunks
TOTAL_FILES = 10080   # 1 week of audio
CHUNKS_PER_PROMPT = 60  # 1 hour per prompt
OUTPUT_DIR = "./bootstrap_output"

def create_generation_script(audiocraft_dir, model_size):
    """Create AudioCraft generation script"""
    script_content = f'''
import sys
sys.path.append("{audiocraft_dir}")
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
        # GPU REQUIRED - fail if not available
        if not torch.cuda.is_available():
            raise RuntimeError("GPU not available! This script requires CUDA GPU for AWS efficiency.")
        
        device = 'cuda'
        
        print(f"🚀 Loading model on {{device}} ({{torch.cuda.get_device_name(0)}})...")
        model = MusicGen.get_pretrained("facebook/musicgen-{model_size}")
        
        print(f"✅ Model loaded and optimized for GPU (VRAM: {{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}}GB)")
        
        model.set_generation_params(
            use_sampling=True,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
            duration=60,  # Will be overridden per call
            cfg_coef=3.0
        )
        print(f"✅ Model loaded and ready on {{device}}")
    return model

def generate_chunk(prompt, duration, output_path):
    model = load_model()
    
    # Update duration for this generation
    model.set_generation_params(duration=duration)
    
    print(f"🎵 Generating {{duration}}s audio...")
    print(f"📝 Prompt: {{prompt[:60]}}...")
    start_time = time.time()
    
    with torch.no_grad():
        wav = model.generate([prompt], progress=True)
    
    generation_time = time.time() - start_time
    print(f"✅ Generation completed in {{generation_time:.1f}} seconds")
    print(f"⚡ Generation speed: {{duration/generation_time:.2f}}x realtime")
    print(f"💾 Saving to: {{output_path}}")
    
    # Save as WAV directly without ffmpeg dependency
    import torchaudio
    torchaudio.save(output_path, wav[0].cpu(), model.sample_rate)
    
    file_size = os.path.getsize(output_path) / (1024*1024)
    print(f"✅ Saved {{file_size:.1f}}MB file")
    
    return output_path, generation_time

if __name__ == "__main__":
    prompt = sys.argv[1]
    duration = int(sys.argv[2])
    output_path = sys.argv[3]
    result_path, gen_time = generate_chunk(prompt, duration, output_path)
    print(f"RESULT:{{result_path}}:{{gen_time}}")
'''
    
    script_path = "/tmp/bootstrap_generator.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    return script_path

def generate_single_chunk(chunk_id, prompt_index, generation_script, audiocraft_venv, audiocraft_dir):
    """Generate a single 1-minute chunk with detailed logging"""
    prompt = PROMPTS[prompt_index]
    filename = f"chunk_{chunk_id:03d}_prompt_{prompt_index}_{CHUNK_DURATION}s.wav"
    output_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"🎯 CHUNK {chunk_id:03d}/10080 ({chunk_id/TOTAL_FILES*100:.1f}% complete)")
    print(f"📁 File: {filename}")
    print(f"🎨 Prompt {prompt_index}: {prompt[:50]}...")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        cmd = [audiocraft_venv, generation_script, prompt, str(CHUNK_DURATION), output_path]
        result = subprocess.run(cmd, text=True, cwd=audiocraft_dir)
        
        if result.returncode == 0:
            generation_time = time.time() - start_time
            
            # Verify file exists and get size
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024*1024)
                print(f"\n✅ SUCCESS: Chunk {chunk_id} completed")
                print(f"⏱️  Generation time: {generation_time:.1f}s ({generation_time/60:.1f} min)")
                print(f"📊 File size: {file_size:.1f} MB")
                print(f"⚡ Speed: {CHUNK_DURATION/generation_time:.2f}x realtime")
                return True, generation_time
            else:
                print(f"\n❌ FAILED: File not created for chunk {chunk_id}")
                return False, 0
        else:
            print(f"\n❌ FAILED: Generation failed with return code {result.returncode}")
            return False, 0
            
    except Exception as e:
        print(f"\n❌ FAILED: Generation error for chunk {chunk_id}: {e}")
        return False, 0

def create_metadata(generated_chunks):
    """Create metadata.json for all generated chunks"""
    metadata = {
        "chunks": [],
        "next_chunk_id": TOTAL_FILES + 1,
        "current_prompt_index": 0,  # Will start from prompt 0 for new generation
        "bootstrap_info": {
            "total_files": TOTAL_FILES,
            "chunks_per_prompt": CHUNKS_PER_PROMPT,
            "generated_at": time.time(),
            "generation_stats": {
                "total_time": sum(chunk["generation_time"] for chunk in generated_chunks),
                "avg_time_per_chunk": sum(chunk["generation_time"] for chunk in generated_chunks) / len(generated_chunks)
            }
        }
    }
    
    for chunk in generated_chunks:
        chunk_info = {
            "id": chunk["id"],
            "filename": chunk["filename"],
            "path": os.path.join("audio_buffer", chunk["filename"]),  # Path for main system
            "prompt_index": chunk["prompt_index"],
            "prompt": PROMPTS[chunk["prompt_index"]],
            "duration": CHUNK_DURATION,
            "created_at": chunk["created_at"],
            "consumed": False,
            "generation_time": chunk["generation_time"]
        }
        metadata["chunks"].append(chunk_info)
    
    return metadata

def main():
    if len(sys.argv) < 2:
        print("Usage: python bootstrap_1440_files.py <audiocraft_directory> [model_size]")
        print("Example: python bootstrap_1440_files.py /path/to/audiocraft large")
        print("Model sizes: small, medium, large (default: small)")
        print("")
        print("Setup instructions:")
        print("1. Clone AudioCraft: git clone https://github.com/facebookresearch/audiocraft")
        print("2. Setup venv: cd audiocraft && python -m venv my_venv")
        print("3. Install: source my_venv/bin/activate && pip install -e .")
        print("4. Run bootstrap: python bootstrap_1440_files.py /path/to/audiocraft")
        sys.exit(1)
    
    audiocraft_dir = os.path.abspath(sys.argv[1])
    model_size = sys.argv[2] if len(sys.argv) > 2 else "small"
    audiocraft_venv = os.path.join(audiocraft_dir, "my_venv", "bin", "python")
    
    # Validate paths
    if not os.path.exists(audiocraft_dir):
        print(f"Error: AudioCraft directory not found: {audiocraft_dir}")
        sys.exit(1)
    
    if not os.path.exists(audiocraft_venv):
        print(f"Error: AudioCraft venv not found: {audiocraft_venv}")
        print("Please setup AudioCraft venv first:")
        print(f"cd {audiocraft_dir} && python -m venv my_venv")
        print("source my_venv/bin/activate && pip install -e .")
        sys.exit(1)
    
    print("=== Bootstrap 1,440 File Generation ===")
    print(f"AudioCraft directory: {audiocraft_dir}")
    print(f"AudioCraft venv: {audiocraft_venv}")
    
    # GPU REQUIRED - fail fast if not available
    if not torch.cuda.is_available():
        print("ERROR: GPU not available!")
        print("This script requires CUDA GPU for AWS efficiency.")
        print("Make sure you're running on a GPU instance (g4dn.xl, etc.)")
        sys.exit(1)
    
    print(f"🚀 GPU device: {torch.cuda.get_device_name(0)}")
    print(f"💾 GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    print(f"⏱️  Expected runtime: ~72-96 hours (3-4 min per chunk = 3-4 days)")
    print(f"💰 Estimated AWS cost: ~$50-70 for g4dn.xl")
    print(f"Target: {TOTAL_FILES} files ({TOTAL_FILES/60:.1f} hours = {TOTAL_FILES/60/24:.1f} days)")
    print(f"Chunk duration: {CHUNK_DURATION} seconds")
    print(f"Chunks per prompt: {CHUNKS_PER_PROMPT}")
    print(f"Total prompts: {len(PROMPTS)}")
    print()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create generation script
    generation_script = create_generation_script(audiocraft_dir, model_size)
    
    # Track generation
    generated_chunks = []
    total_start_time = time.time()
    
    # Generate all 1,440 files
    for chunk_id in range(1, TOTAL_FILES + 1):
        # Calculate which prompt to use (60 chunks per prompt)
        prompt_index = ((chunk_id - 1) // CHUNKS_PER_PROMPT) % len(PROMPTS)
        
        success, gen_time = generate_single_chunk(chunk_id, prompt_index, generation_script, audiocraft_venv, audiocraft_dir)
        
        if success:
            generated_chunks.append({
                "id": chunk_id,
                "filename": f"chunk_{chunk_id:03d}_prompt_{prompt_index}_{CHUNK_DURATION}s.wav",
                "prompt_index": prompt_index,
                "created_at": time.time(),
                "generation_time": gen_time
            })
            
            # Progress update every hour (60 chunks)
            if chunk_id % 60 == 0:
                elapsed = time.time() - total_start_time
                avg_time_per_chunk = elapsed / chunk_id
                remaining = (TOTAL_FILES - chunk_id) * avg_time_per_chunk
                completed_hours = chunk_id / 60
                remaining_hours = (TOTAL_FILES - chunk_id) / 60
                
                print(f"\n{'='*80}")
                print(f"📈 PROGRESS REPORT - Hour {completed_hours:.0f}/24 Complete")
                print(f"{'='*80}")
                print(f"✅ Completed: {chunk_id:,}/1,440 chunks ({chunk_id/TOTAL_FILES*100:.1f}%)")
                print(f"⏳ Remaining: {TOTAL_FILES-chunk_id:,} chunks ({remaining_hours:.1f} hours of audio)")
                print(f"⏱️  Time elapsed: {elapsed/3600:.1f} hours")
                print(f"⏱️  Time remaining: {remaining/3600:.1f} hours")
                print(f"📊 Average generation: {avg_time_per_chunk/60:.1f} min per chunk")
                print(f"🚀 Speed vs CPU: {12*60/avg_time_per_chunk:.1f}x faster")
                print(f"💰 AWS cost so far: ~${elapsed/3600 * 0.526:.2f} (g4dn.xl rate)")
                print(f"📅 ETA: {time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time() + remaining))}")
                print(f"{'='*80}")
        else:
            print(f"\n{'='*80}")
            print(f"❌ CRITICAL ERROR: Failed to generate chunk {chunk_id}")
            print(f"🛑 Stopping bootstrap process...")
            print(f"📊 Progress: {len(generated_chunks)}/{TOTAL_FILES} chunks completed")
            print(f"{'='*80}")
            break
    
    # Create metadata
    if generated_chunks:
        metadata = create_metadata(generated_chunks)
        metadata_path = os.path.join(OUTPUT_DIR, "buffer_metadata.json")
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        total_time_hours = (time.time() - total_start_time)/3600
        avg_time_per_chunk = (time.time() - total_start_time) / len(generated_chunks)
        total_size_gb = len(generated_chunks) * 3.8 / 1024
        
        print(f"\n{'='*80}")
        print(f"🎉 BOOTSTRAP GENERATION COMPLETE!")
        print(f"{'='*80}")
        print(f"✅ Generated: {len(generated_chunks):,}/1,440 files ({len(generated_chunks)/TOTAL_FILES*100:.1f}%)")
        print(f"⏱️  Total time: {total_time_hours:.1f} hours ({total_time_hours/24:.1f} days)")
        print(f"📊 Average time per chunk: {avg_time_per_chunk/60:.1f} minutes")
        print(f"🚀 Speed vs CPU: {12*60/avg_time_per_chunk:.1f}x faster")
        print(f"💾 Total size: {total_size_gb:.2f} GB")
        print(f"💰 Total AWS cost: ~${total_time_hours * 0.526:.2f} (g4dn.xl)")
        print(f"🎵 Audio generated: {len(generated_chunks)/60:.1f} hours")
        print(f"✓ Output directory: {os.path.abspath(OUTPUT_DIR)}")
        print(f"✓ Metadata: {metadata_path}")
        
        # File transfer instructions
        print(f"\n{'='*80}")
        print(f"📦 TRANSFER INSTRUCTIONS")
        print(f"{'='*80}")
        print(f"1. Copy all .wav files to main system:")
        print(f"   rsync -av {OUTPUT_DIR}/*.wav user@mainserver:/root/home_projects/youtube-stream/audio_buffer/")
        print(f"2. Copy metadata:")
        print(f"   scp {metadata_path} user@mainserver:/root/home_projects/youtube-stream/audio_buffer/")
        
    else:
        print(f"\n{'='*80}")
        print(f"❌ BOOTSTRAP FAILED - No files generated successfully")
        print(f"{'='*80}")
    
    # Cleanup
    if os.path.exists(generation_script):
        os.remove(generation_script)

if __name__ == "__main__":
    main()