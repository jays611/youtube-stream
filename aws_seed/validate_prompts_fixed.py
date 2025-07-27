#!/usr/bin/env python3
"""
Prompt Validation Script for Indian Lofi Stream
Generates 5-minute samples for all 10 prompts to validate audio quality
Run this on GPU instance before bootstrap to test prompts and estimate timing
"""

import sys
import os
import time
import subprocess
import torch

# Import config from parent directory
import importlib.util
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
PROMPTS = config.PROMPTS

# Validation configuration
CHUNK_DURATION = 60  # 5 minutes for validation
OUTPUT_DIR = "./prompt_validation"

def create_validation_script(audiocraft_dir, model_size):
    """Create GPU-optimized AudioCraft validation script"""
    script_content = f'''
import sys
sys.path.append("{audiocraft_dir}")
import torch
import os
import time
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
        
        print(f"Loading model on {{device}} ({{torch.cuda.get_device_name(0)}})...")
        model = MusicGen.get_pretrained(f"facebook/musicgen-{model_size}")
        
        print(f"Model loaded and optimized for GPU")
        
        model.set_generation_params(
            use_sampling=True,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
            duration={CHUNK_DURATION},
            cfg_coef=3.0
        )
        print(f"Model loaded and ready on {{device}}")
    return model

def generate_sample(prompt, output_path):
    model = load_model()
    
    print(f"Generating {CHUNK_DURATION}s audio: {{prompt[:50]}}...")
    start_time = time.time()
    
    # Use AudioCraft's built-in progress display
    with torch.no_grad():
        wav = model.generate([prompt], progress=True)
    
    generation_time = time.time() - start_time
    print(f"\\nGeneration completed in {{generation_time:.1f}}s ({{60/generation_time:.2f}}x realtime)")
    
    # Save as WAV directly without ffmpeg dependency
    import torchaudio
    torchaudio.save(output_path, wav[0].cpu(), model.sample_rate)
    
    return output_path, generation_time

if __name__ == "__main__":
    prompt = sys.argv[1]
    output_path = sys.argv[2]
    result_path, gen_time = generate_sample(prompt, output_path)
    print(f"RESULT:{{result_path}}:{{gen_time}}")
'''
    
    script_path = "/tmp/prompt_validator.py"
    with open(script_path, 'w') as f:
        f.write(script_content)
    return script_path

def validate_single_prompt(prompt_index, prompt, validation_script, audiocraft_venv, audiocraft_dir):
    """Generate validation sample for a single prompt"""
    filename = f"prompt_{prompt_index:02d}_{CHUNK_DURATION}s.wav"
    output_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))
    
    print(f"\n[{prompt_index+1:02d}/10] {filename}")
    print(f"Prompt: {prompt}")
    
    start_time = time.time()
    
    try:
        cmd = [audiocraft_venv, validation_script, prompt, output_path]
        result = subprocess.run(cmd, text=True, cwd=audiocraft_dir)
        
        if result.returncode == 0 and os.path.exists(output_path):
            generation_time = time.time() - start_time
            file_size = os.path.getsize(output_path) / (1024*1024)
            print(f"✓ Completed in {generation_time:.1f}s ({file_size:.1f}MB)")
            return True, generation_time
        else:
            print(f"✗ Failed (return code: {result.returncode})")
            return False, 0
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False, 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_prompts.py <audiocraft_directory> [model_size]")
        print("Example: python validate_prompts.py /path/to/audiocraft small")
        print("Model sizes: small, medium, large (default: small)")
        print("")
        print("This script validates all 10 prompts by generating 5-minute samples.")
        print("Run this before bootstrap to test audio quality and estimate timing.")
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
        print("This script requires CUDA GPU for validation.")
        print("Make sure you're running on a GPU instance (g4dn.xl, etc.)")
        sys.exit(1)
    
    print("=== Indian Lofi Prompt Validation ===")
    print(f"AudioCraft directory: {audiocraft_dir}")
    print(f"AudioCraft venv: {audiocraft_venv}")
    print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    print(f"Sample duration: {CHUNK_DURATION} seconds ({CHUNK_DURATION/60:.1f} minutes)")
    print(f"Total prompts: {len(PROMPTS)}")
    print()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create validation script
    validation_script = create_validation_script(audiocraft_dir, model_size)
    
    # Track validation
    successful_prompts = []
    failed_prompts = []
    total_start_time = time.time()
    
    # Validate all prompts
    for prompt_index, prompt in enumerate(PROMPTS):
        success, gen_time = validate_single_prompt(prompt_index, prompt, validation_script, audiocraft_venv, audiocraft_dir)
        
        if success:
            successful_prompts.append({
                "index": prompt_index,
                "prompt": prompt,
                "generation_time": gen_time,
                "filename": f"prompt_{prompt_index:02d}_{CHUNK_DURATION}s.wav"
            })
        else:
            failed_prompts.append({
                "index": prompt_index,
                "prompt": prompt
            })
    
    # Final summary
    total_time = time.time() - total_start_time
    
    print(f"\n=== VALIDATION COMPLETE ===")
    print(f"Successful: {len(successful_prompts)}/10 prompts")
    print(f"Failed: {len(failed_prompts)}/10 prompts")
    print(f"Total time: {total_time/60:.1f} minutes")
    
    if successful_prompts:
        avg_time = sum(p["generation_time"] for p in successful_prompts) / len(successful_prompts)
        print(f"Average generation time: {avg_time/60:.1f} minutes per 5-minute sample")
        print(f"Estimated 1-minute chunk time: {avg_time/5/60:.1f} minutes")
        print(f"Speed: {CHUNK_DURATION/avg_time:.2f}x realtime")
        
        print(f"\n=== SUCCESSFUL PROMPTS ===")
        for p in successful_prompts:
            print(f"✓ Prompt {p['index']:02d}: {p['filename']} ({p['generation_time']/60:.1f} min)")
    
    if failed_prompts:
        print(f"\n=== FAILED PROMPTS ===")
        for p in failed_prompts:
            print(f"✗ Prompt {p['index']:02d}: {p['prompt'][:50]}...")
    
    print(f"\n=== OUTPUT FILES ===")
    print(f"Location: {os.path.abspath(OUTPUT_DIR)}")
    print("Listen to the generated samples to validate audio quality.")
    print("If quality is good, proceed with bootstrap generation.")
    
    # Cleanup
    if os.path.exists(validation_script):
        os.remove(validation_script)

if __name__ == "__main__":
    main()