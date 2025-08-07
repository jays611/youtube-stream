#!/usr/bin/env python3
"""
Seamless YouTube Streamer with Audio Crossfading
Creates ultra-smooth transitions between 30-second chunks
"""

import subprocess
import random
import tempfile
import os
from content_library import ContentLibrary

class SeamlessStreamer:
    def __init__(self, stream_key: str, video_loop: str):
        self.stream_key = stream_key
        self.video_loop = video_loop
        self.library = ContentLibrary()
        self.rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    def create_seamless_audio_stream(self, duration_hours: int = 24) -> str:
        """Create seamless audio with crossfades between chunks"""
        chunks_needed = duration_hours * 60 * 2  # 2 chunks per minute
        all_chunks = self.library.get_all_chunks()
        
        if len(all_chunks) < chunks_needed:
            chunks_needed = len(all_chunks)
        
        selected_chunks = random.sample(all_chunks, chunks_needed)
        
        # Create simple concatenation (crossfade is complex, let's start simple)
        inputs = []
        
        for chunk in selected_chunks:
            inputs.extend(['-i', chunk['path']])
        
        # Create ultra-smooth lofi transitions with ambient elements
        if len(selected_chunks) == 1:
            filter_complex = "[0:a]lowpass=f=8000,aecho=0.6:0.3:1000:0.2,aformat=sample_rates=44100[out]"
        else:
            # Build crossfade chain with lofi ambient elements
            filter_parts = []
            
            # Generate vinyl crackle noise for transitions
            noise_gen = "anoisesrc=duration=3:sample_rate=44100:amplitude=0.02:color=brown"
            
            # First chunk with lofi processing
            current_label = "0processed"
            filter_parts.append(f"[0:a]lowpass=f=8000,aecho=0.6:0.3:1000:0.2[{current_label}];")
            
            # Chain crossfades with ambient noise between chunks
            for i in range(1, len(selected_chunks)):
                processed_label = f"{i}processed"
                crossfade_label = f"cf{i}"
                noise_label = f"noise{i}"
                
                # Process current chunk with lofi effects
                filter_parts.append(f"[{i}:a]lowpass=f=8000,aecho=0.6:0.3:1000:0.2[{processed_label}];")
                
                # Generate transition noise
                filter_parts.append(f"{noise_gen}[{noise_label}];")
                
                # Crossfade with ambient noise mixed in
                filter_parts.append(f"[{current_label}][{processed_label}]acrossfade=d=3:c1=exp:c2=exp[temp{i}];")
                filter_parts.append(f"[temp{i}][{noise_label}]amix=inputs=2:duration=longest:weights=0.95 0.05[{crossfade_label}];")
                
                current_label = crossfade_label
            
            # Final output with gentle compression
            filter_complex = ''.join(filter_parts) + f"[{current_label}]acompressor=threshold=0.1:ratio=2:attack=200:release=1000,aformat=sample_rates=44100[out]"
        
        # Create temporary seamless audio file
        temp_audio = "/tmp/seamless_stream.wav"
        
        cmd = ['ffmpeg', '-y'] + inputs + [
            '-filter_complex', filter_complex,
            '-map', '[out]' if len(selected_chunks) > 1 else '0:a',
            '-c:a', 'pcm_s16le',
            temp_audio
        ]
        
        print("Creating seamless audio stream...")
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0:
            print(f"✅ Seamless audio created: {temp_audio}")
            return temp_audio
        else:
            print(f"✗ Audio creation failed: {result.stderr.decode()}")
            return None
    
    def start_youtube_stream(self, duration_hours: int = 24):
        """Start YouTube live stream with video loop and seamless audio"""
        
        # Create seamless audio
        audio_file = self.create_seamless_audio_stream(duration_hours)
        if not audio_file:
            return False
        
        print(f"🚀 Starting YouTube stream...")
        print(f"Video: {self.video_loop}")
        print(f"Audio: Seamless {duration_hours}h stream")
        print(f"RTMP: {self.rtmp_url}")
        
        # FFmpeg command for YouTube streaming (fixed buffering)
        cmd = [
            'ffmpeg',
            '-re',                  # Read at real-time rate
            '-stream_loop', '-1',   # Loop video infinitely
            '-i', self.video_loop,  # Video input (looped)
            '-thread_queue_size', '512',  # Increase buffer
            '-i', audio_file,       # Our generated music
            '-map', '0:v',          # Video from MP4
            '-map', '1:a',          # Audio from our music
            '-c:v', 'libx264',      # Video codec
            '-preset', 'veryfast',  # Encoding speed
            '-tune', 'zerolatency', # Low latency for live
            '-b:v', '6000k',        # Video bitrate (close to 6800k recommended)
            '-maxrate', '6800k',    # Max bitrate (YouTube recommended)
            '-bufsize', '13600k',   # Buffer size (2x maxrate)
            '-vf', 'scale=1920:1080,fps=24', # Scale + consistent fps
            '-g', '48',             # 2-second keyframes (24fps * 2)
            '-keyint_min', '48',    # Min keyframe interval
            '-c:a', 'aac',          # Audio codec
            '-b:a', '128k',         # Audio bitrate
            '-ar', '44100',         # Audio sample rate
            '-async', '1',          # Audio sync
            '-f', 'flv',            # Output format
            self.rtmp_url           # YouTube RTMP endpoint
        ]
        
        print("Stream command:", ' '.join(cmd))
        print("\n🔴 LIVE STREAMING - Press Ctrl+C to stop")
        
        try:
            # Start streaming (don't cleanup until done)
            process = subprocess.run(cmd)
            return True
        except KeyboardInterrupt:
            print("\n⏹️  Stream stopped by user")
            return True
        except Exception as e:
            print(f"✗ Stream failed: {e}")
            return False

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python seamless_streamer.py <youtube_stream_key> [duration_hours]")
        print("Example: python seamless_streamer.py abc123-def456-ghi789 24")
        sys.exit(1)
    
    stream_key = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    video_loop = "/root/home_projects/youtube-stream/indian-lofi-anime-loop-02.mp4"
    
    if not os.path.exists(video_loop):
        print(f"✗ Video file not found: {video_loop}")
        sys.exit(1)
    
    streamer = SeamlessStreamer(stream_key, video_loop)
    streamer.start_youtube_stream(duration)

if __name__ == "__main__":
    main()