# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **mouse** library - a Python package that provides full control over mouse input on Windows, Linux, and macOS. It enables global mouse event hooking, mouse simulation, and high-level mouse operations like recording and replaying mouse actions.

## Architecture

### Core Components

- **mouse/__init__.py**: Main API module that exposes all public functions and handles platform detection
- **mouse/_mouse_event.py**: Defines mouse event data structures (ButtonEvent, MoveEvent, WheelEvent) and constants
- **mouse/_generic.py**: Contains GenericListener class that provides cross-platform event handling with threading
- **Platform-specific modules**:
  - **mouse/_winmouse.py**: Windows implementation using ctypes and Windows API
  - **mouse/_nixmouse.py**: Linux implementation using X11 and raw input devices
  - **mouse/_darwinmouse.py**: macOS implementation using Quartz/Core Graphics

### Key Design Patterns

1. **Platform Abstraction**: The main module automatically imports the appropriate platform-specific implementation
2. **Event-Driven Architecture**: Uses GenericListener with a queue-based system for handling mouse events in separate threads
3. **Hook System**: Global mouse hooks that capture events regardless of application focus
4. **High-Level API**: Provides both low-level event handling and high-level functions like record/replay

## Development Commands

### Testing
```bash
# Run all tests with coverage
make test

# Individual test commands (from Makefile)
python2 -m coverage run -m mouse._mouse_tests
python2 -m coverage run -am mouse._mouse_tests
python -m coverage run -am mouse._mouse_tests
python -m coverage run -am mouse._mouse_tests
python -m coverage report && coverage3 html
```

### Building
```bash
# Build package and check distribution
make build

# Build command details:
python setup.py sdist --format=zip bdist_wheel --universal bdist_wininst && twine check dist/*
```

### Release
```bash
make release  # Uses make_release.py script
```

### Installation
```bash
# For development
python setup.py install

# For users
pip install mouse
```

## Platform-Specific Requirements

- **Linux**: Requires `sudo` privileges to access `/dev/input/input*` raw device files
- **macOS**: Requires granting accessibility permissions to terminal/Python in System Preferences
- **Windows**: No special requirements, uses Windows API directly

## Key Limitations

1. Windows events don't report device ID (event.device == None)
2. Linux requires root access for raw device file access
3. Some applications may register hooks that intercept all mouse events
4. Thread-based event processing means handlers should be thread-safe

## Testing Strategy

- Uses unittest framework with mock OS mouse implementation (FakeOsMouse)
- Tests cover all public API functions and platform-specific behavior
- Coverage reporting enabled for quality assurance
- Mock-based testing isolates platform dependencies

## Code Organization Notes

- Constants are defined in `_mouse_event.py` (LEFT, RIGHT, MIDDLE, etc.)
- Cross-platform compatibility handled through dynamic imports
- Event processing uses separate threads to avoid blocking main program
- All platform modules implement the same interface for consistency