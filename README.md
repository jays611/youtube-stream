# Indian Lofi YouTube Live Stream System

## Overview
A 24/7 YouTube live stream system that generates continuous Indian lofi music using Meta's AudioCraft. The system pre-generates audio chunks to maintain a buffer, ensuring uninterrupted streaming despite slow generation times.

## System Architecture

```
[Audio Generator] → [Buffer Queue] → [Stream Feeder] → [YouTube Live]
                                  ↓
                              [Recording Capture]
```

### Key Components
- **Audio Generator**: Creates 10-minute lofi chunks using AudioCraft
- **Buffer Manager**: Manages chunk queue and health monitoring  
- **Stream Feeder**: Feeds chunks to YouTube with 3-second breaks between prompts
- **Main Orchestrator**: Coordinates all processes and handles failures

## Detailed Workflow Diagram

```mermaid
flowchart TD
    A[main.py] --> B[StreamOrchestrator.run]
    B --> C[Start Generator Process]
    B --> D[Start Feeder Process]
    B --> E[Monitor System]
    
    C --> F[audio_generator.py]
    F --> G[AudioGenerator.init]
    G --> H[Load BufferManager]
    G --> I[Create AudioCraft Script]
    
    F --> J[run_generation_loop]
    J --> K[buffer_manager.get_buffer_status]
    K --> L{Buffer Health?}
    L -->|DEPLETED and Empty| M[Continue Generation]
    L -->|DEPLETED and Has Chunks| N[Stop Generation]
    L -->|HEALTHY/WARNING/CRITICAL| M
    
    M --> O[buffer_manager.get_next_prompt_index]
    O --> P[generate_chunk]
    P --> Q[Subprocess AudioCraft Generation]
    Q --> R[audio_write Save WAV]
    R --> S[buffer_manager.add_chunk]
    S --> T[Take Break Based on Health]
    T --> J
    
    D --> U[stream_feeder.py]
    U --> V[StreamFeeder.init]
    V --> W[Load BufferManager]
    
    U --> X[stream_to_stdout]
    X --> Y[buffer_manager.get_next_chunk]
    Y --> Z{Chunk Available?}
    Z -->|No| AA[Wait 5 seconds]
    AA --> Y
    Z -->|Yes| BB[should_add_break]
    BB -->|Yes| CC[Add 3-second Silence]
    BB -->|No| DD[Stream Chunk]
    CC --> DD
    DD --> EE[read_audio_chunk]
    EE --> FF[Simulate Streaming]
    FF --> GG[buffer_manager.mark_chunk_consumed]
    GG --> X
    
    H --> HH[buffer_manager.py]
    HH --> II[BufferManager.init]
    II --> JJ[load_metadata]
    JJ --> KK[buffer_metadata.json]
    
    HH --> LL[Key Functions]
    LL --> MM[add_chunk]
    LL --> NN[get_next_chunk]
    LL --> OO[get_buffer_status]
    LL --> PP[mark_chunk_consumed]
    LL --> QQ[cleanup_consumed_chunks]
    
    E --> RR[monitor_system]
    RR --> SS[Check Buffer Status]
    RR --> TT[Check Process Health]
    TT --> UU{Process Dead?}
    UU -->|Yes| VV[Restart Process]
    UU -->|No| WW[Continue Monitoring]
    VV --> WW
    WW --> RR
    
    SS --> XX{Buffer Depleted?}
    XX -->|Yes| YY[Emergency Shutdown]
    XX -->|No| WW
```

### File-Function Mapping

| File | Key Functions | Purpose |
|------|---------------|----------|
| **main.py** | `StreamOrchestrator.run()`, `monitor_system()` | Process coordination, health monitoring |
| **audio_generator.py** | `generate_chunk()`, `run_generation_loop()` | AudioCraft chunk generation |
| **stream_feeder.py** | `stream_to_stdout()`, `should_add_break()` | Chunk streaming with breaks |
| **buffer_manager.py** | `add_chunk()`, `get_next_chunk()`, `get_buffer_status()` | Queue management, health tracking |
| **config.py** | `PROMPTS[]`, buffer settings | Configuration and prompts |
| **test_phase1.py** | `test_audio_generation()`, `test_buffer_manager()` | Testing utilities |

## Current Status: Phase 1 Complete ✅

### What's Been Built
1. **Core Buffer System** - Chunk generation, storage, and queue management
2. **10 Indian Lofi Prompts** - Rotating through different styles
3. **Health Monitoring** - Buffer levels (HEALTHY → WARNING → CRITICAL → EMERGENCY)
4. **Process Coordination** - Generator and feeder working together
5. **Testing Framework** - Comprehensive testing tools

### Files Created
```
youtube-stream/
├── config.py              # Settings, prompts, paths
├── buffer_manager.py       # Buffer queue management
├── audio_generator.py      # AudioCraft chunk generation  
├── stream_feeder.py        # Chunk streaming with breaks
├── main.py                # Main orchestrator
├── test_phase1.py         # Testing utilities
├── README.md              # This file
└── audio_buffer/          # Generated chunks storage
```

## Performance Metrics
- **Generation Speed**: ~24 minutes to create 10-minute chunk (0.42x realtime)
- **Target Buffer**: 24 hours (144 chunks)
- **CPU Usage**: ~90% during generation
- **Memory**: ~4GB for AudioCraft small model

## Testing Phase 1

### Prerequisites
- AudioCraft installed at `/root/home_projects/audiocraft/`
- Python virtual environment at `/root/home_projects/audiocraft/my_venv/`
- 60GB RAM, 12 CPU cores (your current setup)
- Working directory: `/root/home_projects/youtube-stream/`

### Test Commands
```bash
cd /root/home_projects/youtube-stream

# Test individual components
python test_phase1.py buffer     # Test buffer manager
python test_phase1.py generate   # Generate 1 chunk (~24 mins) - FIXED
python test_phase1.py stream     # Test streaming
python test_phase1.py status     # Show buffer contents

# Run full system
python main.py full              # Both generator + feeder
python main.py generator-only    # Just generate chunks
python main.py feeder-only       # Just stream chunks
```

### Recent Fixes
- **Generator Logic**: Fixed to allow initial generation when buffer is empty
- **Test Generation**: Now creates focused single-chunk test instead of full loop

### Expected Test Results
1. **Buffer Manager**: Prompt rotation, health monitoring working
2. **Audio Generation**: One 10-minute WAV file created in `audio_buffer/`
3. **Stream Feeder**: Simulated streaming with 3-second breaks
4. **Full System**: Both processes running, buffer health updating

## What You Need to Do

### Immediate (Phase 1 Testing)
1. **Run tests** to verify Phase 1 works on your system:
   ```bash
   cd /root/home_projects/youtube-stream
   python test_phase1.py buffer    # Should show prompt rotation
   python test_phase1.py generate  # Will take ~24 minutes
   python test_phase1.py status    # Should show 1 generated chunk
   ```
2. **Monitor CPU usage** during generation (should be ~90%)
3. **Check audio quality** of generated chunks in `audio_buffer/`
4. **Report any errors** or performance issues

### For Phase 2 (Next Steps)
1. **YouTube Live Setup**:
   - Create YouTube Live stream
   - Get RTMP URL and stream key
   - Install FFmpeg for video encoding

2. **Animation Preparation**:
   - Provide your 8-second animation file
   - Specify format (MP4, GIF, etc.)

3. **External Server Bootstrap** (Optional):
   - Set up external server for initial 24-hour generation
   - Configure file transfer method (rsync, scp)

## Upcoming Phases

### Phase 2: Production Streaming
- **FFmpeg Integration**: Real YouTube Live streaming
- **Animation Loop**: Your 8-second video on repeat
- **CPU Management**: Adaptive generation based on load
- **Process Recovery**: Auto-restart on failures

### Phase 3: Recording System  
- **Stream Capture**: Record variable-length segments (1hr, 30min, 4hr)
- **Auto-Upload**: Separate YouTube video uploads
- **File Management**: Cleanup and storage optimization

### Phase 4: Monitoring & Optimization
- **Web Dashboard**: Real-time system monitoring
- **Performance Tuning**: CPU optimization, faster generation
- **Alerting**: Email/SMS notifications for issues
- **Analytics**: Stream metrics and performance data

## Configuration Options

### Buffer Settings (config.py)
```python
TARGET_BUFFER_HOURS = 24    # Target buffer size
CHUNK_DURATION = 600        # 10-minute chunks
MODEL_SIZE = "small"        # AudioCraft model size
```

### Buffer Health Levels
- **HEALTHY**: >24 hours → 5-minute breaks between generation
- **WARNING**: 12-24 hours → 2-minute breaks
- **CRITICAL**: 6-12 hours → No breaks
- **EMERGENCY**: 2-6 hours → No breaks
- **DEPLETED**: <2 hours → Stop stream

## Troubleshooting

### Common Issues
1. **Generation Fails**: Check AudioCraft installation, Python path
2. **High CPU Usage**: Expected during generation, will add throttling in Phase 2
3. **Buffer Not Growing**: Check disk space, file permissions
4. **Process Crashes**: Check logs, memory usage

### Debug Commands
```bash
# Check buffer status
python main.py status

# View generated files
ls -la audio_buffer/

# Test single generation
python test_phase1.py generate

# Clean up test data
python test_phase1.py cleanup
```

## Next Steps
1. **Complete Phase 1 testing** and report results
2. **Prepare YouTube Live credentials** for Phase 2
3. **Provide animation file** for video stream
4. **Decide on external server** for bootstrap generation

The system is designed to be robust and handle the slow generation speed through intelligent buffering. Once Phase 2 is complete, you'll have a fully functional 24/7 Indian lofi stream!