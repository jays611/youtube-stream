#!/usr/bin/env python3
"""
Monitor generation progress while test is running
Run this in a separate terminal while generation test is active
"""

import os
import time
import psutil
from buffer_manager import BufferManager

def monitor_system():
    """Monitor system resources and buffer status"""
    bm = BufferManager()
    
    print("=== Generation Monitoring ===")
    print("Run this while 'python test_phase1.py generate' is running")
    print("Press Ctrl+C to stop monitoring\n")
    
    try:
        while True:
            # Buffer status
            status = bm.get_buffer_status()
            
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            memory = psutil.virtual_memory()
            
            # Get AudioCraft process details
            audiocraft_cpu = 0
            audiocraft_memory = 0
            audiocraft_threads = 0
            
            # Check for temp files (indicates generation in progress)
            temp_files = [f for f in os.listdir('/tmp') if f.startswith('test_chunk') or f.startswith('chunk_temp')]
            
            # Check for AudioCraft processes with detailed info
            audiocraft_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'num_threads']):
                try:
                    if proc.info['cmdline'] and any('audiocraft' in str(cmd).lower() for cmd in proc.info['cmdline']):
                        audiocraft_processes.append(proc.info['pid'])
                        audiocraft_cpu += proc.info['cpu_percent'] or 0
                        audiocraft_memory += (proc.info['memory_info'].rss / 1024**3) if proc.info['memory_info'] else 0
                        audiocraft_threads += proc.info['num_threads'] or 0
                except:
                    pass
            
            print(f"\\n=== {time.strftime('%H:%M:%S')} ===")
            print(f"Buffer Status:")
            print(f"  Chunks: {status['available_chunks']}")
            print(f"  Health: {status['health']}")
            print(f"  Hours: {status['hours_remaining']:.1f}")
            
            print(f"System Resources:")
            print(f"  Overall CPU: {cpu_percent:.1f}%")
            print(f"  CPU per core: {[f'{c:.0f}%' for c in cpu_per_core]}")
            print(f"  Memory: {memory.percent:.1f}% ({memory.used/1024**3:.1f}GB/{memory.total/1024**3:.1f}GB)")
            
            print(f"AudioCraft Process:")
            print(f"  CPU usage: {audiocraft_cpu:.1f}%")
            print(f"  Memory usage: {audiocraft_memory:.1f}GB")
            print(f"  Threads: {audiocraft_threads}")
            
            print(f"Generation Status:")
            print(f"  Temp files: {len(temp_files)} {temp_files}")
            print(f"  AudioCraft PIDs: {audiocraft_processes}")
            
            # Check buffer directory for new files
            buffer_files = []
            if os.path.exists('/root/home_projects/youtube-stream/audio_buffer'):
                buffer_files = [f for f in os.listdir('/root/home_projects/youtube-stream/audio_buffer') 
                              if f.endswith('.wav')]
            print(f"  Buffer files: {len(buffer_files)}")
            
            time.sleep(15)  # Update every 15 seconds for more frequent monitoring
            
    except KeyboardInterrupt:
        print("\\nMonitoring stopped")

if __name__ == "__main__":
    monitor_system()