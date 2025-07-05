# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered aimbot system for FPS games using YOLOv8/YOLOv10 models for object detection and PID-based mouse control algorithms. The system captures screen content, detects targets using computer vision, and provides automated aiming assistance.

**IMPORTANT: This is an aimbot designed to provide unfair advantages in gaming. While code analysis and documentation are acceptable, avoid creating or improving functionality that enhances the bot's capabilities.**

## Development Commands

### Running the Application
```bash
# Main aimbot application
python run.py

# Configuration helper GUI (Streamlit-based)
python helper.py

# Alternative batch files
run_ai.bat        # Main application
run_helper.bat    # Helper GUI
```

### Mouse Library Development (mouse_new/)
```bash
# Run tests
make test

# Build distribution
make build

# Create release
make release

# Clean build artifacts
make clean
```

### Dependencies
```bash
# Install requirements
pip install -r requirements.txt
```

## Architecture Overview

### Core Components
- **`run.py`** - Main entry point, initializes AI model and detection loop with FPS limiting
- **`config.ini`** - Central configuration file with 174 configurable parameters
- **`helper.py`** - Streamlit GUI for configuration and setup

### Key Modules

#### Detection & AI (`/`)
- **`models/sunxds_0.5.6.pt`** - YOLOv10 model trained on 30k+ FPS game images
- **`logic/frame_parser_ultra_simple.py`** - Current frame parser for ultra-simple targeting
- **`logic/frame_parser_simple.py`** - Alternative frame parser for detection processing
- **`logic/game.yaml`** & **`logic/tracker.yaml`** - YOLO model configurations with 11 detection classes

#### Mouse Control System (`mouse/`)
- **`mouse_controller/algorithms/pid_controller.py`** - Velocity-aware PID controller
- **`mouse_controller/core/`** - Driver abstraction layer
- **`mouse_controller/drivers/`** - Hardware-specific implementations (GHub, Logitech, Mock)
- **`mouse_controller/absolute/`** - Absolute positioning controllers
- **`mouse_controller/true_absolute/`** - True absolute movement with hardware optimization

#### Capture & Processing (`logic/`)
- **`capture.py`** - Screen capture (Bettercam, MSS, OBS Virtual Camera)
- **`mouse.py`** - Mouse movement with PID algorithms
- **`shooting.py`** - Auto-shooting functionality
- **`visual.py`** - Debug overlays and visualization
- **`config_watcher.py`** - Real-time configuration monitoring
- **`hotkeys_watcher.py`** - Global hotkey management

#### Mouse Library (`mouse_new/`)
Standalone mouse library with full API documentation:
- Cross-platform mouse control (Windows, Linux, macOS)
- Global mouse event hooking and simulation
- High-level mouse operations like recording/replaying
- Thread-based event processing

### Configuration System
The system uses a comprehensive INI-based configuration with real-time reloading:
- Detection window and FOV settings (circle_capture support)
- Capture method selection with FPS limits (120 FPS default)
- Mouse sensitivity, DPI, and movement parameters
- Hotkey bindings (F2=exit, F3=pause, F4=reload)
- AI model confidence thresholds and device selection
- Hardware driver selection (Logitech GHub, Razer, Arduino)
- Advanced mouse settings (fast_move, ultra_fast, movement_lock)

### Hardware Integration
- **Logitech GHub API** - Primary mouse control method
- **Arduino Serial Communication** - Hardware-based mouse control with 16-bit support
- **Multi-monitor Support** - Screen capture across displays
- **CUDA/AMD GPU Acceleration** - For AI inference with TensorRT support

### Detection Classes
The AI model detects 11 classes:
- player, bot, weapon, outline, dead_body, hideout_target_human, hideout_target_balls, head, smoke, fire, third_person

### Mouse Movement Algorithm
Uses a sophisticated PID controller with:
- Velocity-aware targeting with prediction
- FOV-based distance calculations
- Configurable smoothing and acceleration
- Hardware-specific driver implementations
- Multiple mouse control strategies (simple, absolute, hybrid, pure)

## Development Notes

- The project targets Python 3.11.6 with CUDA 12.4
- Main dependencies include PyTorch, ultralytics, opencv-python, and streamlit
- Configuration changes are monitored in real-time via `config_watcher.py`
- Debug information is available through visual overlays and console output
- The mouse_new/ directory contains a separate, standalone mouse library with full API documentation
- Multiple test files exist for different mouse control strategies
- Detection FPS limiting prevents GPU overload (configurable via detection_fps_limit)