#!/usr/bin/env python3
"""
New Main Orchestrator for Pre-built Content Architecture
Manages content library, scheduled generation, and stream stitching
"""

import sys
import os
from content_library import ContentLibrary
from stream_stitcher import StreamStitcher
from scheduled_generator import ScheduledGenerator

class NewStreamOrchestrator:
    def __init__(self):
        self.library = ContentLibrary()
        self.stitcher = StreamStitcher()
        self.generator = ScheduledGenerator()
    
    def setup_library(self):
        """Initial setup: scan existing content"""
        print("=== Setting up Content Library ===")
        
        # Scan base content
        chunks = self.library.scan_base_content()
        stats = self.library.get_library_stats()
        
        print(f"Library Status:")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Total hours: {stats['total_hours']:.1f}")
        print(f"  Total days: {stats['total_days']:.1f}")
        print(f"  Storage: {stats['storage_gb']:.1f} GB")
        
        return stats
    
    def create_streams(self):
        """Create stitched streams for broadcasting"""
        print("=== Creating Stitched Streams ===")
        
        stats = self.library.get_library_stats()
        if stats['total_hours'] < 24:
            print(f"⚠️  Only {stats['total_hours']:.1f} hours available, need at least 24h for streaming")
            return False
        
        # Create weekly batch of streams
        segments = self.stitcher.create_weekly_batch()
        print(f"✅ Created {len(segments)} stream segments")
        
        return segments
    
    def create_youtube_content(self):
        """Create 4-hour content for YouTube upload"""
        print("=== Creating YouTube Content ===")
        
        stats = self.library.get_library_stats()
        if stats['total_hours'] < 4:
            print(f"⚠️  Only {stats['total_hours']:.1f} hours available, need at least 4h")
            return None
        
        youtube_file = self.stitcher.create_youtube_content(4)
        if youtube_file:
            print(f"✅ YouTube content created: {youtube_file}")
        
        return youtube_file
    
    def generate_weekly_content(self):
        """Generate weekly content (2 hours)"""
        print("=== Generating Weekly Content ===")
        
        # Check current progress
        progress = self.generator.get_weekly_progress()
        print(f"Current week progress: {progress['progress_percent']:.1f}%")
        
        if progress['remaining_chunks'] > 0:
            success = self.generator.generate_weekly_batch()
            if success:
                print("✅ Weekly generation complete")
                return True
            else:
                print("✗ Weekly generation failed")
                return False
        else:
            print("✅ Weekly target already met")
            return True
    
    def show_status(self):
        """Show comprehensive system status"""
        print("=== System Status ===")
        
        # Library stats
        stats = self.library.get_library_stats()
        print(f"\nContent Library:")
        print(f"  Total content: {stats['total_hours']:.1f} hours ({stats['total_days']:.1f} days)")
        print(f"  Base content: {stats['base_chunks']} chunks")
        print(f"  Weekly additions: {stats['weekly_chunks']} chunks ({stats['weeks_added']} weeks)")
        print(f"  Storage used: {stats['storage_gb']:.1f} GB")
        
        # Weekly progress
        progress = self.generator.get_weekly_progress()
        print(f"\nWeekly Generation:")
        print(f"  Week: {progress['week_id']}")
        print(f"  Progress: {progress['completed_chunks']}/{progress['target_chunks']} chunks ({progress['progress_percent']:.1f}%)")
        print(f"  Sessions remaining: {progress['sessions_remaining']}")
        
        # Streaming readiness
        streaming_ready = stats['total_hours'] >= 24
        youtube_ready = stats['total_hours'] >= 4
        
        print(f"\nReadiness:")
        print(f"  24/7 Streaming: {'✅ Ready' if streaming_ready else '❌ Need more content'}")
        print(f"  YouTube Content: {'✅ Ready' if youtube_ready else '❌ Need more content'}")

def show_usage():
    print("Usage: python main_new.py [command]")
    print("Commands:")
    print("  setup          - Initial library setup")
    print("  status         - Show system status")
    print("  generate       - Generate weekly content")
    print("  streams        - Create stitched streams")
    print("  youtube        - Create YouTube content")
    print("  full-setup     - Complete setup process")

def main():
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    orchestrator = NewStreamOrchestrator()
    
    if command == "setup":
        orchestrator.setup_library()
    elif command == "status":
        orchestrator.show_status()
    elif command == "generate":
        orchestrator.generate_weekly_content()
    elif command == "streams":
        orchestrator.create_streams()
    elif command == "youtube":
        orchestrator.create_youtube_content()
    elif command == "full-setup":
        print("=== Full System Setup ===")
        orchestrator.setup_library()
        orchestrator.create_streams()
        orchestrator.show_status()
    else:
        print(f"Unknown command: {command}")
        show_usage()

if __name__ == "__main__":
    main()