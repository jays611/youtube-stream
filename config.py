#!/usr/bin/env python3
"""
Configuration for Indian Lofi YouTube Stream
"""

import os

# Paths
BUFFER_DIR = "/root/home_projects/youtube-stream/audio_buffer"
AUDIOCRAFT_VENV = "/root/home_projects/audiocraft/my_venv/bin/python"

# Audio Generation Settings
CHUNK_DURATION = 600  # 10 minutes in seconds
MODEL_SIZE = "small"
SAMPLE_RATE = 32000

# Buffer Management
TARGET_BUFFER_HOURS = 24
WARNING_BUFFER_HOURS = 12
CRITICAL_BUFFER_HOURS = 6
EMERGENCY_BUFFER_HOURS = 2

# Generation Breaks (seconds)
HEALTHY_BREAK = 300    # 5 minutes
WARNING_BREAK = 120    # 2 minutes  
CRITICAL_BREAK = 0     # No breaks
EMERGENCY_BREAK = 0    # No breaks

# Indian Lofi Prompts (10 prompts rotating)
PROMPTS = [
    "smooth indian lofi hip hop with electric sitar, mellow drums, and ambient textures",
    "meditative indian lofi beats with tanpura drone, soft tabla, and nature sounds",
    "peaceful indian lofi hip hop with sitar, tabla beats, and ambient rain sounds",
    "serene south indian tamil lofi with veena melody, mridangam rhythms, and temple bells ambience",
    "relaxing indian lofi music with sitar melody, gentle percussion, and atmospheric pads",
    "chill indian classical fusion lofi with harmonium, soft tabla, and vinyl crackle",
    "dreamy indian lofi with flute melody, tabla beats, and monsoon rain ambience",
    "nostalgic indian lofi hip hop with santoor, gentle drums, and street sounds",
    "tranquil indian lofi with bansuri flute, tanpura drone, and forest sounds",
    "mellow indian lofi beats with sarod melody, soft percussion, and evening ambience"
]

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "/root/home_projects/youtube-stream/stream.log"