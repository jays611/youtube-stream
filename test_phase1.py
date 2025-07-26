#!/usr/bin/env python3
"""
Phase 1 Testing Script
Tests the core buffer system components
"""

import os
import sys
import time
import subprocess
from buffer_manager import BufferManager

def test_buffer_manager():
    """Test buffer manager functionality"""
    print("=== Testing Buffer Manager ===")
    
    bm = BufferManager()
    
    # Test initial status
    status = bm.get_buffer_status()
    print(f"Initial buffer status: {status}")
    
    # Test prompt rotation
    print("\\nTesting prompt rotation:")
    for i in range(12):  # Test more than 10 to see rotation
        prompt_idx = bm.get_next_prompt_index()
        print(f"Prompt {i+1}: Index {prompt_idx} - {bm.metadata['current_prompt_index']}")
    
    print("✓ Buffer Manager test completed")

def test_audio_generation():
    """Test audio generation (single chunk)"""
    print("\\n=== Testing Audio Generation ===")
    print("This will generate one 10-minute chunk...")
    print("This will take approximately 24 minutes...")
    
    # Create a test script that generates just one chunk then exits
    test_script = '''
import sys
sys.path.append("/root/home_projects/youtube-stream")
from audio_generator import AudioGenerator

generator = AudioGenerator()
status = generator.buffer_manager.get_buffer_status()
print(f"Starting generation with {status['available_chunks']} chunks")

# Generate exactly one chunk
prompt_index = generator.buffer_manager.get_next_prompt_index()
from config import PROMPTS
prompt = PROMPTS[prompt_index]
temp_path = "/tmp/test_chunk.wav"

if generator.generate_chunk(prompt, temp_path):
    chunk_info = generator.buffer_manager.add_chunk(temp_path, prompt_index)
    print(f"✓ Successfully generated test chunk {chunk_info['id']}")
else:
    print("✗ Failed to generate test chunk")
'''
    
    try:
        with open('/tmp/test_generation.py', 'w') as f:
            f.write(test_script)
        
        # Run the test script
        result = subprocess.run([
            sys.executable, "/tmp/test_generation.py"
        ], cwd="/root/home_projects/youtube-stream", timeout=1800)  # 30 min timeout
        
        if result.returncode == 0:
            print("✓ Audio generation test completed")
        else:
            print("✗ Audio generation test failed")
            
    except subprocess.TimeoutExpired:
        print("⚠ Audio generation test timed out (this is normal for testing)")
    except KeyboardInterrupt:
        print("⚠ Audio generation test interrupted by user")
    finally:
        # Clean up test script
        if os.path.exists('/tmp/test_generation.py'):
            os.remove('/tmp/test_generation.py')

def test_stream_feeder():
    """Test stream feeder"""
    print("\\n=== Testing Stream Feeder ===")
    
    # Check if we have any chunks to stream
    bm = BufferManager()
    status = bm.get_buffer_status()
    
    if status['available_chunks'] == 0:
        print("No chunks available for streaming test")
        print("Run audio generation test first")
        return
    
    print(f"Found {status['available_chunks']} chunks for streaming test")
    
    try:
        # Run feeder for a short time
        process = subprocess.Popen([
            sys.executable, "stream_feeder.py"
        ], cwd="/root/home_projects/youtube-stream")
        
        # Let it run for 10 seconds
        time.sleep(10)
        process.terminate()
        process.wait()
        
        print("✓ Stream feeder test completed")
        
    except Exception as e:
        print(f"✗ Stream feeder test failed: {e}")

def show_buffer_contents():
    """Show current buffer contents"""
    print("\\n=== Buffer Contents ===")
    
    bm = BufferManager()
    
    if not bm.metadata['chunks']:
        print("No chunks in buffer")
        return
    
    print(f"Total chunks: {len(bm.metadata['chunks'])}")
    print("\\nChunk details:")
    
    for chunk in bm.metadata['chunks']:
        status = "✓" if os.path.exists(chunk['path']) else "✗"
        consumed = "CONSUMED" if chunk['consumed'] else "AVAILABLE"
        print(f"{status} Chunk {chunk['id']}: {chunk['filename']} ({consumed})")
        print(f"   Prompt: {chunk['prompt'][:50]}...")
        print(f"   Created: {time.ctime(chunk['created_at'])}")
        print()

def cleanup_test_data():
    """Clean up test data"""
    print("\\n=== Cleanup Test Data ===")
    
    import shutil
    buffer_dir = "/root/home_projects/youtube-stream/audio_buffer"
    
    if os.path.exists(buffer_dir):
        shutil.rmtree(buffer_dir)
        os.makedirs(buffer_dir)
        print("✓ Cleaned up buffer directory")
    else:
        print("Buffer directory doesn't exist")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_phase1.py <test>")
        print("Tests:")
        print("  buffer     - Test buffer manager")
        print("  generate   - Test audio generation (one chunk)")
        print("  stream     - Test stream feeder")
        print("  status     - Show buffer status and contents")
        print("  cleanup    - Clean up test data")
        print("  all        - Run all tests")
        return
    
    test = sys.argv[1]
    
    if test == "buffer":
        test_buffer_manager()
    elif test == "generate":
        test_audio_generation()
    elif test == "stream":
        test_stream_feeder()
    elif test == "status":
        show_buffer_contents()
    elif test == "cleanup":
        cleanup_test_data()
    elif test == "all":
        test_buffer_manager()
        test_audio_generation()
        test_stream_feeder()
        show_buffer_contents()
    else:
        print(f"Unknown test: {test}")

if __name__ == "__main__":
    main()