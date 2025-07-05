# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Main aimbot application
python3 run.py

# Simplified version with enhanced logging
python3 run_simple.py

# Helper/configuration GUI (Streamlit)
python3 run_helper.bat
# or manually:
streamlit run helper.py --server.fileWatcherType none
```

### Testing
```bash
# Use python3 instead of python (see rule.md for details)
python3 -m mouse._fps_relative_movement_tests

# Test logging format
python3 -c "from logic.logger import logger; logger.info('Testing updated timestamp format')"
```

#### Testing Guidelines (Based on rule.md)
**Test File Design Principles:**
1. **No User Interaction**: Tests must be fully automated with no manual input required
2. **Comprehensive Coverage**: Tests should cover as many scenarios and edge cases as possible
3. **Direct Result Output**: Tests should directly output results without additional processing
4. **Self-Contained**: Each test file should include all necessary dependencies and configuration

**Test File Writing Best Practices:**
- Use standard testing frameworks (e.g., unittest)
- Include detailed test case descriptions
- Provide clear test result output
- Ensure test repeatability and stability
- All tests must run completely automated without user interaction

**Dependency Handling in WSL Environment:**
- **Context**: Currently running in WSL environment which may lack some dependencies that exist in the user's Windows environment
- **Strategy**:
  1. If missing dependencies occur during testing, ignore the issue (focus on code logic validation)
  2. Optionally attempt to install missing dependencies: `pip install [dependency]`
  3. If dependency installation fails or is unavailable, ignore and proceed
  4. Testing priority is code logic verification, not environment dependency resolution

### Dependencies

#### WSL Environment Python Module Installation
```bash
# WSL环境Python模块安装关键流程

# 1. 安装pip (WSL环境需要特殊处理)
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py --user --break-system-packages

# 2. 永久添加pip到PATH
export PATH=$PATH:/home/pepsi/.local/bin
echo 'export PATH=$PATH:/home/pepsi/.local/bin' >> ~/.bashrc

# 3. 使用--break-system-packages标志安装模块
pip3 install --break-system-packages --user <package_name>

# 4. 常用模块批量安装
pip3 install --break-system-packages --user \
  numpy pandas matplotlib requests beautifulsoup4 \
  pillow pyyaml configparser wheel setuptools

# 5. 验证安装
python3 -c "import numpy, pandas, requests; print('✅ 核心模块安装成功')"
```

#### Project Dependencies
```bash
# Install requirements
pip install -r requirements.txt

# Main dependencies include:
# - ultralytics (YOLOv8/v10)
# - torch (CUDA support required)
# - opencv-python
# - supervision (ByteTrack)
# - streamlit (for helper GUI)

# WSL环境自动安装脚本
./install_python_modules.sh
```

#### Dependency Handling Strategy
- **WSL限制**: 使用`--break-system-packages --user`标志
- **缺失依赖**: 测试时如遇到缺失依赖，尝试自动安装：`pip3 install --break-system-packages --user <module>`
- **安装失败**: 如果安装失败，忽略并继续（优先验证代码逻辑）
- **模块指南**: 参考`PYTHON_MODULES_GUIDE.md`获取完整模块清单

## Architecture Overview

### High-Level System Design
This is an AI-powered aimbot that combines computer vision (YOLO), mouse control, and shooting logic:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Game Screen   │ -> │   AI Detection  │ -> │ Mouse Movement  │
│   (Capture)     │    │   (YOLO + Aim)  │    │   (PID/Linear)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

#### 1. Detection & AI System (`logic/`)
- **Model**: YOLOv8/v10 for enemy detection (`models/sunxds_0.5.6.pt`)
- **Frame Processing**: `frame_parser.py` and `frame_parser_simple.py`
- **Capture Methods**: MSS, Bettercam, OBS support in `capture.py`
- **Configuration**: `config_watcher.py` monitors `config.ini` for real-time updates

#### 2. Mouse Control System (`mouse/`)
**Advanced Multi-Driver Architecture** with three movement algorithms:

- **PID Controller** (Recommended): 2.38px accuracy, 0.009s speed, 100% success rate
- **LADRC Controller**: Linear Active Disturbance Rejection Control
- **Linear Movement**: Legacy Bezier-curve based movement

**Driver Support**:
- `MouseControlDriver`: Basic relative/absolute movement
- `GHubDriver`: Logitech G HUB integration
- `LogitechDriver`: Logitech Gaming Software support

#### 3. Shooting System (`logic/shooting.py`)
- Auto-shoot capabilities
- Trigger bot functionality
- Three-shot burst optimizations (95ms intervals for game adaptation)
- Recoil control patterns

#### 4. Configuration & Utils
- **Real-time Config**: `config.ini` with live reload (F4 hotkey)
- **Logging**: Dual system with improved timestamp formatting (YYYY-MM-DD HH:MM:SS)
- **Visual Debug**: OpenCV windows with overlay options
- **Hotkeys**: F2 (exit), F3 (pause), F4 (reload config)

### Critical Design Patterns

#### Mouse Controller Integration
```python
# High-performance PID movement (optimized for FPS games)
from mouse.mouse_controller import MouseController, MovementAlgorithm

with MouseController() as controller:
    # FPS-optimized parameters for different scenarios
    controller.smooth_move_to(x, y, 
        algorithm=MovementAlgorithm.PID,
        tolerance=2,        # Balance precision vs speed
        max_iterations=50   # Optimized for <20ms response
    )
```

#### AI Detection Pipeline
```python
# Main detection loop with performance optimization
def perform_detection(model, image, tracker):
    # Frame rate limiting (120 FPS detection_fps_limit)
    # Skip detection if time_since_last < detection_interval
    
    result = model.predict(source=image, conf=cfg.AI_conf, device=cfg.AI_device)
    
    if tracker:
        # ByteTrack for object tracking
        return tracker.update_with_detections(det)
    return result
```

#### Configuration Management
The system uses real-time configuration with hot-reload:
- Monitor `config.ini` for changes
- Apply updates without restart
- Maintain backwards compatibility
- Validate settings on load

### Performance Optimizations

#### Detection System
- **Frame Rate Limiting**: Configurable detection_fps_limit (default 120 FPS)
- **Smart Skipping**: Skip detection when FPS limit exceeded
- **Circle Capture**: Optional circular detection area
- **Device Selection**: GPU/CPU detection with device=0 or device=cpu

#### Mouse Movement
- **PID Optimization**: 1000-5000x performance improvement over legacy methods
- **Algorithm Parameters**:
  - `kp=0.5, ki=0.02, kd=0.01` (optimized for speed)
  - Single-step movement capped at 50px
  - 1ms loop delay to prevent CPU overload
- **FPS Game Presets**: Specialized parameters for different gaming scenarios

#### Shooting System
- **Three-Shot Burst**: 95ms target intervals with game-optimized timing
- **Performance Logging**: Detailed timing analysis for optimization
- **Cooldown Management**: 700ms cooldown after burst completion

## Project-Specific Guidelines

### Key Files to Understand
1. **`run.py`**: Main application entry point with detection loop
2. **`run_simple.py`**: Simplified version with streamlined logging
3. **`config.ini`**: All configuration parameters with Chinese comments
4. **`logic/frame_parser_simple.py`**: Core aiming and target selection logic
5. **`mouse/mouse_controller/`**: Complete mouse control system
6. **`PID_INTEGRATION_GUIDE.md`**: Comprehensive mouse system documentation

### Development Practices
- **Python Version**: Use `python3` command (python may not be available)
- **Testing**: All test files must be fully automated with no user interaction
- **Logging**: Two-tier system - simple logger for logic, advanced logger for mouse controller
- **Error Handling**: Graceful degradation with detailed logging
- **Configuration**: Real-time updates with validation

### Core Logging System Requirements

For continuous algorithm optimization and problem resolution, the system MUST implement **comprehensive core flow logging** covering the complete pipeline from YOLO detection to mouse movement execution.

#### Critical Logging Components

1. **YOLO Detection Stage Logging**
   - Target count and confidence scores for each detection
   - Raw bounding box coordinates (x1, y1, x2, y2) before processing
   - Target classification (HEAD=7, BODY=0) with confidence
   - Calculated center points and dimensions from bounding boxes
   ```
   Example: "🔍 YOLO: 2 targets | BODY(0.85): bbox=(150,200,220,350) center=(185,275) size=70x150"
   ```

2. **Coordinate Transformation Logging**
   - Before/after coordinates when applying body/head offsets
   - Screen center to target pixel offset calculations
   - Pixel-to-mouse conversion process with intermediate values
   - Speed multiplier selection and application reasoning
   ```
   Example: "📐 TRANSFORM: target=(185,275) → offset_applied=(188,238) → pixel_offset=(-2,48) → mouse_move=(-24,576)"
   ```

3. **Mouse Execution Logging**
   - Final mouse movement command parameters sent to hardware
   - Driver execution results and any scaling applied
   - Movement distance limitations and adjustment reasons
   ```
   Example: "🎯 EXECUTE: move_relative(-24,576) → driver_result=SUCCESS | scaled=NO"
   ```

#### Logging Implementation Guidelines
- **Timestamps**: All core logs include precise timestamps (YYYY-MM-DD HH:MM:SS)
- **Flow Tracking**: Use session/frame IDs to correlate related log entries
- **Precision**: Numerical values to 1 decimal place for readability
- **Performance**: Logging must not impact system performance
- **Consistency**: Standardized format across all components

#### Usage for Algorithm Optimization
These logs enable:
- **Parameter Tuning**: Analyze conversion multipliers and offset values
- **Problem Isolation**: Identify exact stage where issues occur (detection vs conversion vs execution)
- **Performance Analysis**: Measure processing time and accuracy at each stage
- **Regression Testing**: Verify algorithm changes don't break existing functionality
- **Data-Driven Optimization**: Use real-world log data to improve algorithms

### AI-Driven Development and Logging Strategy

#### Core Logging Philosophy for AI Analysis
**Purpose**: All logging must support continuous AI-driven analysis and iterative optimization

#### Critical Logging Requirements for AI Development
1. **Problem Discovery Orientation**: Logs must enable effective problem identification
   - Record edge cases, anomalies, and performance bottlenecks
   - Include sufficient context for issue reproduction
   - Flag unexpected behaviors or deviations from expected patterns
   - Capture failure modes and recovery attempts

2. **Complete Flow Coverage**: Every critical node in the core pipeline requires logging
   - Input data characteristics and validation status
   - Intermediate processing steps with transformation details
   - Output results and execution outcomes
   - Performance metrics (timing, accuracy, success rates)
   - Decision points and branching logic

3. **AI Analysis-Friendly Format**: Structure logs for optimal AI interpretation
   - Use consistent, structured data formats (JSON-like when possible)
   - Include numerical metrics for trend analysis
   - Provide correlation identifiers for cross-stage analysis
   - Document decision rationale and parameter selection logic

#### Developer Logging Mindset
**Proactive Thinking**: When developing, always consider "What information will I need for future optimization?"
- Algorithm parameter selection rationale and effectiveness
- Data transformation formulas and intermediate calculations
- Decision branch conditions and outcomes
- Exception handling triggers and resolution strategies
- Performance optimization key metrics and changes

#### AI-Driven Development Workflow
1. **Development Phase**: Anticipate optimization needs, proactively add critical logging
2. **Testing Phase**: Collect comprehensive runtime log data
3. **Analysis Phase**: Provide logs to AI for deep pattern analysis
4. **Optimization Phase**: Implement AI-recommended algorithm and parameter adjustments
5. **Validation Phase**: Use log comparison to verify optimization effectiveness

#### Log Analysis Guidelines for AI
When analyzing provided logs, focus on:
- **Performance Patterns**: Identify consistent issues or optimization opportunities
- **Parameter Sensitivity**: Determine which parameters most impact performance
- **Failure Analysis**: Root cause analysis of missed targets or poor performance
- **Optimization Opportunities**: Suggest specific parameter adjustments or algorithm improvements
- **Regression Detection**: Compare before/after performance to validate changes

### Common Workflows
- **Adding New Algorithms**: Extend `MovementAlgorithm` enum and implement in `algorithms/`
- **New Drivers**: Inherit from `BaseDriver` and add to auto-detection
- **Configuration Changes**: Update `config.ini` and `config_watcher.py`
- **Performance Tuning**: Adjust PID parameters in mouse controller config

### Integration Points
- **AI Model Updates**: Place new `.pt` files in `models/` directory
- **Driver Extensions**: Add new DLLs to `mouse/drivers/` and register in controller
- **Visual Overlays**: Extend `visual.py` for new debugging displays
- **Hotkey System**: Modify `hotkeys_watcher.py` for new keyboard shortcuts

## Important Notes

### Security & Detection Avoidance
This is a defensive security analysis tool. The mouse control system includes:
- Humanization options with random delays
- Multiple driver options to avoid detection
- Configurable movement patterns

### Performance Requirements
- **GPU**: RTX 20 series or better recommended
- **CUDA**: Version 12.4+ required for optimal performance
- **TensorRT**: Optional for model acceleration
- **Memory**: Sufficient for YOLOv8/v10 model loading

### File Structure Significance
- `logic/`: Core application logic (detection, aiming, shooting)
- `mouse/`: Isolated, reusable mouse control system
- `models/`: AI model files (.pt format)
- `drivers/`: Hardware driver DLLs
- `screenshots/`: Debug output directory
- `media/tests/`: Test videos for validation