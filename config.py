#!/usr/bin/env python3
"""
Configuration for Indian Lofi YouTube Stream
"""

import os

# Paths
CONTENT_LIBRARY_DIR = "/root/home_projects/youtube-stream/content_library"
AUDIOCRAFT_VENV = "/usr/bin/python3"

# Audio Generation Settings
CHUNK_DURATION = 30   # 30 seconds for new architecture
MODEL_SIZE = "small"
SAMPLE_RATE = 32000

# Content Library Management (1 month base + weekly additions)
BASE_CONTENT_FILES = 86400  # 1 month × 24h × 60min × 2 = 86,400 files
WEEKLY_GENERATION_FILES = 240  # 2 hours × 60min × 2 = 240 files per week
CHUNKS_PER_SESSION = 24  # Generate 24 chunks per session (12 minutes audio)
SESSIONS_PER_WEEK = 10   # 10 sessions to complete weekly target

# Stream Stitching
STREAM_SEGMENT_HOURS = [6, 8, 6, 4]  # Different duration segments
YOUTUBE_CONTENT_HOURS = 4  # 4 hours for weekly YouTube uploads

# Prompt Management (unchanged)
PROMPT_DURATION_HOURS = 1  # Each prompt plays for 1 hour
CHUNKS_PER_PROMPT = 120    # 120 × 30s = 1 hour per prompt

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

# Performance Metrics (updated for 30s chunks)
GENERATION_TIME_PER_CHUNK = 6 * 60  # 6 minutes per 30-second chunk (estimated)
FILE_SIZE_MB = 1.9  # MB per 30-second chunk
WEEKLY_GENERATION_TARGET = 240  # 240 chunks per week (2 hours audio)
WEEKLY_GENERATION_HOURS = WEEKLY_GENERATION_TARGET * 30 / 3600  # 2 hours per week

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "/root/home_projects/youtube-stream/stream.log"