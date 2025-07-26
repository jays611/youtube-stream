#!/usr/bin/env python3
"""
Main orchestrator for Indian Lofi YouTube Stream
Phase 1: Core buffer system testing
"""

import os
import sys
import time
import subprocess
import signal
from buffer_manager import BufferManager
from config import *

class StreamOrchestrator:
    def __init__(self):
        self.buffer_manager = BufferManager()
        self.generator_process = None
        self.feeder_process = None
        self.running = False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\\nReceived signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def start_generator(self):
        """Start audio generator process"""
        print("Starting audio generator...")
        self.generator_process = subprocess.Popen([
            sys.executable, "audio_generator.py"
        ], cwd="/root/home_projects/youtube-stream")
        return self.generator_process
    
    def start_feeder(self):
        """Start stream feeder process"""
        print("Starting stream feeder...")
        self.feeder_process = subprocess.Popen([
            sys.executable, "stream_feeder.py"
        ], cwd="/root/home_projects/youtube-stream")
        return self.feeder_process
    
    def monitor_system(self):
        """Monitor system health and processes"""
        while self.running:
            try:
                # Check buffer status
                status = self.buffer_manager.get_buffer_status()
                
                print(f"\\n=== System Status ===")
                print(f"Buffer Health: {status['health']}")
                print(f"Chunks Available: {status['available_chunks']}")
                print(f"Hours Remaining: {status['hours_remaining']:.1f}")
                
                # Check if we should emergency shutdown
                if status['health'] == 'DEPLETED':
                    print("EMERGENCY: Buffer depleted, shutting down...")
                    self.shutdown()
                    break
                
                # Check process health
                if self.generator_process and self.generator_process.poll() is not None:
                    print("WARNING: Generator process died, restarting...")
                    self.start_generator()
                
                if self.feeder_process and self.feeder_process.poll() is not None:
                    print("WARNING: Feeder process died, restarting...")
                    self.start_feeder()
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(30)
    
    def shutdown(self):
        """Shutdown all processes"""
        print("Shutting down stream system...")
        self.running = False
        
        if self.generator_process:
            self.generator_process.terminate()
            self.generator_process.wait()
            print("Generator process stopped")
        
        if self.feeder_process:
            self.feeder_process.terminate()
            self.feeder_process.wait()
            print("Feeder process stopped")
    
    def run(self, mode="full"):
        """Run the stream system"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print("=== Indian Lofi Stream System ===")
        print(f"Mode: {mode}")
        
        if mode == "generator-only":
            print("Running generator only...")
            self.start_generator()
            self.generator_process.wait()
            
        elif mode == "feeder-only":
            print("Running feeder only...")
            self.start_feeder()
            self.feeder_process.wait()
            
        elif mode == "full":
            print("Running full system...")
            self.running = True
            
            # Start both processes
            self.start_generator()
            time.sleep(5)  # Let generator start first
            self.start_feeder()
            
            # Monitor system
            self.monitor_system()
        
        else:
            print(f"Unknown mode: {mode}")
            sys.exit(1)

def show_usage():
    print("Usage: python main.py [mode]")
    print("Modes:")
    print("  full          - Run both generator and feeder (default)")
    print("  generator-only - Run only audio generator")
    print("  feeder-only   - Run only stream feeder")
    print("  status        - Show buffer status")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "status":
            bm = BufferManager()
            status = bm.get_buffer_status()
            print("=== Buffer Status ===")
            for key, value in status.items():
                print(f"{key}: {value}")
            sys.exit(0)
        elif mode in ["full", "generator-only", "feeder-only"]:
            orchestrator = StreamOrchestrator()
            orchestrator.run(mode)
        else:
            show_usage()
            sys.exit(1)
    else:
        orchestrator = StreamOrchestrator()
        orchestrator.run("full")