#!/usr/bin/env python3
"""
Bootstrap script to generate continuous 1-week audio (168 hours)
Generates 1-hour continuous blocks, then splits into 1-minute chunks
Run this on a powerful GPU server, then transfer files + metadata to main system
"""

import sys
import os
import time
import json
import subprocess
import torch
import torchaudio

# Import config from parent directory
import importlib.util
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
PROMPTS = config.PROMPTS

# Bootstrap configuration
CHUNK_DURATION = 60  # 1 minute chunks
TOTAL_FILES = 10080  # 1 week of audio (168 hours)
CHUNKS_PER_PROMPT = 60  # 1 hour per prompt
HOUR_DURATION = 3600  # 1 hour in seconds
CONTEXT_DURATION = 2  # 2 seconds context for seamless continuation
OUTPUT_DIR = "./bootstrap_output"

def check_dependencies():
    """Check all required dependencies before starting"""
    print("=== Dependency Check ===")
    
    # Check critical packages
    try:
        import torch
        print(f"✓ torch {torch.__version__}")
        
        import torchaudio
        print(f"✓ torchaudio {torchaudio.__version__}")
        
        # Test CUDA availability
        if torch.cuda.is_available():
            print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("✗ CUDA not available - GPU required!")
            return False
            
    except ImportError as e:
        print(f"✗ Missing critical package: {e}")
        print("Make sure you're running this in the AudioCraft environment.")
        return False
    
    # Check built-in modules
    builtin_modules = ['json', 'subprocess', 'time', 'os', 'sys']
    for module in builtin_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} - CRITICAL ERROR")
            return False
    
    print("✓ All dependencies available")
    return True

def create_continuous_generation_script(audiocraft_dir, model_size):
    """Create GPU-optimized AudioCraft continuous generation script"""
    script_content = f'''
import sys
sys.path.append("{audiocraft_dir}")
import torch
import torchaudio
import os
import time
import json
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

# Global model instance (load once, reuse for all prompts)
model = None

def load_model():
    global model
    if model is None:
        # GPU REQUIRED - fail if not available
        if not torch.cuda.is_available():
            raise RuntimeError("GPU not available! This script requires CUDA GPU.")
        
        device = 'cuda'
        torch.set_default_device(device)
        
        print(f"🚀 Loading model on {{device}} ({{torch.cuda.get_device_name(0)}})...")
        model = MusicGen.get_pretrained("facebook/musicgen-{model_size}")
        
        print(f"✅ Model loaded and optimized for GPU (VRAM: {{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}}GB)")
        
        model.set_generation_params(
            use_sampling=True,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
            duration={HOUR_DURATION},  # 1 hour continuous generation
            cfg_coef=3.0
        )
        print(f"✅ Model loaded and ready on {{device}}")
    return model

def generate_seamless_hour(prompt, output_dir, hour_index):
    """Generate 1 hour of seamless chunks using continuation method"""
    model = load_model()
    sample_rate = model.sample_rate
    context_samples = int({CONTEXT_DURATION} * sample_rate)
    chunk_samples = int({CHUNK_DURATION} * sample_rate)
    
    print(f"Generating seamless hour: {{prompt[:50]}}...")
    chunk_files = []
    previous_audio = None
    total_generation_time = 0
    
    for chunk_idx in range({CHUNKS_PER_PROMPT}):
        global_chunk_id = (hour_index * {CHUNKS_PER_PROMPT}) + chunk_idx + 1
        prompt_index = hour_index % len({PROMPTS})
        filename = f"chunk_{{global_chunk_id:05d}}_prompt_{{prompt_index}}_{CHUNK_DURATION}s.wav"
        output_path = os.path.join(output_dir, filename)
        
        print(f"  Chunk {{chunk_idx+1}}/60: {{filename}}")
        start_time = time.time()
        
        if chunk_idx == 0:
            # First chunk: generate normally
            model.set_generation_params(duration={CHUNK_DURATION})
            with torch.no_grad():
                wav = model.generate([prompt], progress=False)
            chunk_audio = wav[0]
        else:
            # Subsequent chunks: use last 2 seconds as context
            context_audio = previous_audio[..., -context_samples:]
            
            # Generate continuation (includes 2s overlap + new content)
            with torch.no_grad():
                continuation = model.generate_continuation(
                    context_audio.unsqueeze(0), 
                    prompt_sample_rate=sample_rate,
                    progress=False
                )
            
            # Remove first 2 seconds (overlap) to get clean 60s chunk
            chunk_audio = continuation[0][..., context_samples:]
        
        # Ensure exactly 60 seconds
        if chunk_audio.shape[-1] > chunk_samples:
            chunk_audio = chunk_audio[..., :chunk_samples]
        elif chunk_audio.shape[-1] < chunk_samples:
            padding = chunk_samples - chunk_audio.shape[-1]
            chunk_audio = torch.nn.functional.pad(chunk_audio, (0, padding))
        
        # Save chunk
        torchaudio.save(output_path, chunk_audio.cpu(), sample_rate)
        
        # Store for next iteration's context
        previous_audio = chunk_audio
        
        generation_time = time.time() - start_time
        total_generation_time += generation_time
        
        chunk_files.append({{
            "filename": filename,
            "path": output_path,
            "chunk_id": global_chunk_id,
            "prompt_index": prompt_index,
            "chunk_in_hour": chunk_idx
        }})
    
    print(f"Seamless hour complete: {{len(chunk_files)}} chunks created")
    return chunk_files, total_generation_time

if __name__ == "__main__":
    prompt = sys.argv[1]
    output_dir = sys.argv[2]
    hour_index = int(sys.argv[3])
    chunk_files, gen_time = generate_seamless_hour(prompt, output_dir, hour_index)
    
    # Return results as JSON for parsing
    result = {{
        "chunk_files": chunk_files,
        "generation_time": gen_time,
        "hour_index": hour_index
    }}
    print(f"RESULT:{{json.dumps(result)}}")
'''
    
    script_path = "/tmp/continuous_generator.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    return script_path

def generate_continuous_hour(hour_index, generation_script, audiocraft_venv, audiocraft_dir):
    """Generate 1 continuous hour for a prompt, split into 60 chunks"""
    prompt_index = hour_index % len(PROMPTS)
    prompt = PROMPTS[prompt_index]
    
    print(f"\n=== HOUR {hour_index+1:03d}/168 - CONTINUOUS GENERATION ===")
    print(f"Prompt {prompt_index}: {prompt}")
    print(f"Generating 1 hour continuous, splitting into 60 chunks...")
    
    start_time = time.time()
    
    try:
        cmd = [audiocraft_venv, generation_script, prompt, OUTPUT_DIR, str(hour_index)]
        result = subprocess.run(cmd, text=True, capture_output=True, cwd=audiocraft_dir)
        
        if result.returncode == 0:
            # Parse the JSON result
            output_lines = result.stdout.strip().split('\n')
            result_line = [line for line in output_lines if line.startswith('RESULT:')][0]
            result_data = json.loads(result_line.replace('RESULT:', ''))
            
            generation_time = time.time() - start_time
            chunk_files = result_data['chunk_files']
            
            print(f"✓ Generated {len(chunk_files)} chunks in {generation_time/60:.1f} minutes")
            print(f"  Avg: {generation_time/len(chunk_files):.1f}s per chunk")
            
            return True, chunk_files, generation_time
        else:
            print(f"✗ Failed (return code: {result.returncode})")
            print(f"STDERR: {result.stderr}")
            return False, [], 0
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False, [], 0

def create_metadata(generated_chunks):
    """Create metadata.json for all generated chunks"""
    metadata = {
        "chunks": [],
        "next_chunk_id": TOTAL_FILES + 1,
        "current_prompt_index": 0,
        "bootstrap_info": {
            "total_files": TOTAL_FILES,
            "chunks_per_prompt": CHUNKS_PER_PROMPT,
            "generated_at": time.time(),
            "generation_method": "continuous_hours",
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
            "path": os.path.join("audio_buffer", chunk["filename"]),
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
        print("Usage: python bootstrap_continuous.py <audiocraft_directory> [model_size]")
        print("Example: python bootstrap_continuous.py /path/to/audiocraft large")
        print("Model sizes: small, medium, large (default: small)")
        print("")
        print("Setup instructions:")
        print("1. Clone AudioCraft: git clone https://github.com/facebookresearch/audiocraft")
        print("2. Setup venv: cd audiocraft && python -m venv my_venv")
        print("3. Install: source my_venv/bin/activate && pip install -e .")
        print("4. Run bootstrap: python bootstrap_continuous.py /path/to/audiocraft")
        print("")
        print("This script generates 168 continuous hours (1 week) of audio.")
        print("Each hour is generated continuously, then split into 60 one-minute chunks.")
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
    
    # GPU REQUIRED - fail fast if not available
    if not torch.cuda.is_available():
        print("ERROR: GPU not available!")
        print("This script requires CUDA GPU for continuous generation.")
        print("Make sure you're running on a GPU instance (g4dn.xl, etc.)")
        sys.exit(1)
    
    print("=== Seamless Bootstrap Generation (1 Week) ===")
    print(f"AudioCraft directory: {audiocraft_dir}")
    print(f"AudioCraft venv: {audiocraft_venv}")
    print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    total_hours = TOTAL_FILES // CHUNKS_PER_PROMPT  # 168 hours
    print(f"Target: {TOTAL_FILES} files ({total_hours} seamless hours = {total_hours/24:.0f} days)")
    print(f"Model size: {model_size}")
    print(f"Expected runtime: ~{total_hours * 30/60:.0f}-{total_hours * 40/60:.0f} hours (30-40 min per hour)")
    print(f"Generating {total_hours} continuous hours, split into {TOTAL_FILES} chunks")
    print()
    
    # Check dependencies first
    if not check_dependencies():
        print("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create generation script
    generation_script = create_continuous_generation_script(audiocraft_dir, model_size)
    
    # Track generation
    generated_chunks = []
    total_start_time = time.time()
    
    # Generate continuous hours (168 total hours)
    for hour_index in range(total_hours):
        success, chunk_files, gen_time = generate_continuous_hour(hour_index, generation_script, audiocraft_venv, audiocraft_dir)
        
        if success:
            # Add all chunks from this hour to our tracking
            for chunk_file in chunk_files:
                generated_chunks.append({
                    "id": chunk_file["chunk_id"],
                    "filename": chunk_file["filename"],
                    "prompt_index": chunk_file["prompt_index"],
                    "created_at": time.time(),
                    "generation_time": gen_time / len(chunk_files)  # Distribute time across chunks
                })
            
            # Progress summary after each hour
            elapsed = time.time() - total_start_time
            completed_hours = hour_index + 1
            remaining_hours = total_hours - completed_hours
            avg_time_per_hour = elapsed / completed_hours
            remaining_time = remaining_hours * avg_time_per_hour
            
            print(f"\n=== PROGRESS: {completed_hours}/{total_hours} hours ({completed_hours/total_hours*100:.1f}%) ===")
            print(f"Completed: {len(generated_chunks)} chunks")
            print(f"Elapsed: {elapsed/3600:.1f}h | Remaining: {remaining_time/3600:.1f}h")
            print(f"Avg: {avg_time_per_hour/60:.1f} min/hour | {gen_time/60:.1f} min for this hour")
            print(f"ETA: {time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time() + remaining_time))}")
        else:
            print(f"\n=== CRITICAL ERROR ===")
            print(f"Failed to generate hour {hour_index+1}, stopping...")
            print(f"Progress: {len(generated_chunks)}/{TOTAL_FILES} chunks completed")
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
        
        print(f"\n=== BOOTSTRAP COMPLETE ===")
        print(f"Generated: {len(generated_chunks)}/10,080 files ({len(generated_chunks)/TOTAL_FILES*100:.1f}%)")
        print(f"Total time: {total_time_hours:.1f} hours ({total_time_hours/24:.1f} days)")
        print(f"Average: {avg_time_per_chunk/60:.1f} min/chunk")
        print(f"Total size: {total_size_gb:.2f} GB ({len(generated_chunks)/60:.1f} hours of audio)")
        print(f"Method: Seamless 1-hour blocks with 2-second context overlap")
        
        print(f"\n=== TRANSFER INSTRUCTIONS ===")
        print(f"1. Copy all .wav files to main system:")
        print(f"   rsync -av {OUTPUT_DIR}/*.wav user@mainserver:/root/home_projects/youtube-stream/audio_buffer/")
        print(f"2. Copy metadata:")
        print(f"   scp {metadata_path} user@mainserver:/root/home_projects/youtube-stream/audio_buffer/")
        
    else:
        print(f"\n=== BOOTSTRAP FAILED ===")
        print(f"No files generated successfully")
    
    # Cleanup
    if os.path.exists(generation_script):
        os.remove(generation_script)

if __name__ == "__main__":
    main()