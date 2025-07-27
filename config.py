#!/usr/bin/env python3
"""
Configuration for Indian Lofi YouTube Stream
"""

import os

# Paths
BUFFER_DIR = "/home/ec2-user/projects/youtube-stream/audio_buffer"
AUDIOCRAFT_VENV = "/usr/bin/python3"

# Audio Generation Settings
CHUNK_DURATION = 60   # 1 minute in seconds for testing
MODEL_SIZE = "small"
SAMPLE_RATE = 32000

# Fixed Buffer Management (1 week of audio)
MAX_BUFFER_FILES = 10080  # 1 week × 24h × 60min = 10,080 files
TARGET_BUFFER_HOURS = 24
WARNING_BUFFER_HOURS = 12
CRITICAL_BUFFER_HOURS = 6
EMERGENCY_BUFFER_HOURS = 2

# Cooldown after each chunk (seconds)
COOLDOWN_TIMINGS = {
    "HEALTHY": 120,    # 2 minutes
    "WARNING": 60,     # 1 minute
    "CRITICAL": 0,     # No break
    "EMERGENCY": 0     # No break
}

# Prompt Management
PROMPT_DURATION_HOURS = 1  # Each prompt plays for 1 hour
CHUNKS_PER_PROMPT = 60     # 60 chunks = 1 hour per prompt

# Indian Lofi Prompts (10 prompts rotating)
PROMPTS = [
    "gentle indian lofi hip hop with smooth sarod, subdued drums, and warm room tone",
    "low-key indian lofi hip hop with muted sitar, soft percussion, and subtle breeze textures",
    "quiet indian lofi hip hop with distant sarangi, hushed drums, and misty ambience",
    "downtempo indian lofi hip hop with delicate santoor, minimal beats, and calm water sounds",
    "tranquil indian lofi hip hop with soft esraj melody, gentle rhythm, and evening atmosphere",
    "understated indian lofi hip hop with ambient veena, whispered percussion, and twilight textures",
    "chill indian classical fusion lofi hip hop with harmonium, soft tabla, and vinyl crackle",
    "dreamy indian lofi hip hop with flute melody, tabla beats, and monsoon rain ambience",
    "smooth indian lofi hip hop with electric sitar, mellow drums, and ambient texture",
    "nostalgic indian lofi hip hop with santoor, gentle drums, and street sounds",
]

# Performance Metrics (measured)
GENERATION_TIME_PER_CHUNK = 12 * 60  # 12 minutes per 1-minute chunk (in seconds)
FILE_SIZE_MB = 3.8  # MB per 1-minute chunk
CHUNKS_PER_DAY = int(24 * 60 / (GENERATION_TIME_PER_CHUNK / 60))  # 120 chunks/day
AUDIO_HOURS_PER_DAY = CHUNKS_PER_DAY / 60  # 2 hours of audio/day

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "/root/home_projects/youtube-stream/stream.log"