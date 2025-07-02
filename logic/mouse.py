import win32con, win32api
import time
import math
import os
import supervision as sv
from enum import Enum

from logic.config_watcher import cfg
from logic.visual import visuals
from logic.shooting import shooting
from logic.buttons import Buttons
from logic.logger import logger

# Import new PID-based mouse controller
from mouse.mouse_controller import MouseController

class MovementState(Enum):
    """Movement state enumeration for better coordination"""
    IDLE = "IDLE"           # No active movement
    MOVING = "MOVING"       # General movement in progress
    COARSE = "COARSE"       # Coarse aiming stage
    FINE = "FINE"           # Fine aiming stage
    COMPLETING = "COMPLETING"  # Movement completion phase

if cfg.mouse_rzr:
    from logic.rzctl import RZCONTROL

if cfg.arduino_move or cfg.arduino_shoot:
    from logic.arduino import arduino

class MouseThread:
    def __init__(self):
        self.initialize_parameters()
        self.setup_hardware()
        self.setup_pid_controller()

    def initialize_parameters(self):
        self.dpi = cfg.mouse_dpi
        self.mouse_sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.disable_prediction = cfg.disable_prediction
        self.prediction_interval = cfg.prediction_interval
        self.bScope_multiplier = cfg.bScope_multiplier
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        self.prev_x = 0
        self.prev_y = 0
        self.prev_time = None
        self.max_distance = math.sqrt(self.screen_width**2 + self.screen_height**2) / 2
        self.min_speed_multiplier = cfg.mouse_min_speed_multiplier
        self.max_speed_multiplier = cfg.mouse_max_speed_multiplier
        self.prev_distance = None
        self.speed_correction_factor = 0.1
        self.bScope = False
        self.arch = self.get_arch()
        self.section_size_x = self.screen_width / 100
        self.section_size_y = self.screen_height / 100
        
        # 头部瞄准优化相关参数
        self.current_target_class = None  # 当前目标类型 (7=头部)
        self.current_move_distance = 0    # 当前移动距离
        
        # 快速瞄准系统参数 - 优化缓冲机制
        self.movement_buffer_x = 0.0      # X轴移动缓冲
        self.movement_buffer_y = 0.0      # Y轴移动缓冲
        self.last_move_time = 0.0         # 上次移动时间
        self.fast_aim_mode = False        # 快速瞄准模式标志
        self.aim_start_time = 0.0         # 瞄准开始时间
        self.buffer_window_ms = 30        # 缓冲窗口30ms (减少延迟)
        self.movement_threshold = 8       # 最小移动阈值8像素 (减少缓冲，增加直接移动)
        self.max_aim_time_ms = 300        # 最大瞄准时间300ms (更快结束)
        
        # 两段式瞄准状态管理
        self.aim_stage = "NONE"           # 瞄准阶段: NONE/COARSE/FINE/COMPLETE
        self.coarse_target_x = 0.0        # 粗瞄目标X坐标
        self.coarse_target_y = 0.0        # 粗瞄目标Y坐标
        self.fine_target_x = 0.0          # 精瞄目标X坐标
        self.fine_target_y = 0.0          # 精瞄目标Y坐标
        self.stage_start_time = 0.0       # 当前阶段开始时间
        self.coarse_aim_time_ms = 200     # 粗瞄阶段时限200ms
        self.fine_aim_time_ms = 300       # 精瞄阶段时限300ms
        
        # Enhanced movement state management with configurable parameters
        self.movement_state = MovementState.IDLE  # Current movement state
        self.movement_start_time = 0.0            # Movement start timestamp
        self.movement_timeout_ms = getattr(cfg, 'movement_timeout_ms', 500)  # Max movement duration
        self.last_movement_command_time = 0.0     # Last command timestamp
        self.movement_completion_threshold = getattr(cfg, 'movement_completion_threshold', 10)  # Pixels threshold
        self.state_transition_cooldown = getattr(cfg, 'state_transition_cooldown_ms', 20) / 1000.0  # State change cooldown
        
        # Configurable timing parameters for optimized performance
        self.head_precision_threshold = getattr(cfg, 'head_precision_threshold', 25)  # Pixels for precision mode
        self.head_direct_threshold = getattr(cfg, 'head_direct_threshold', 100)       # Pixels for direct mode
        self.min_coarse_time_ms = getattr(cfg, 'min_coarse_time_ms', 100)             # Minimum coarse aiming time
        self.min_fine_time_ms = getattr(cfg, 'min_fine_time_ms', 50)                  # Minimum fine aiming time
        
        # Logging frequency control
        self.log_interval_ms = getattr(cfg, 'mouse_log_interval_ms', 200)  # Log every 200ms max
        self.last_log_time = 0.0

    def get_arch(self):
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        if 'cpu' in cfg.AI_device:
            return 'cpu'
        return f'cuda:{cfg.AI_device}'

    def setup_hardware(self):
        if cfg.mouse_ghub:
            from logic.ghub import gHub
            self.ghub = gHub

        if cfg.mouse_rzr:
            dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rzctl.dll")
            self.rzr = RZCONTROL(dll_path)
            if not self.rzr.init():
                logger.error("Failed to initialize rzctl")
    
    def setup_pid_controller(self):
        """Initialize the PID-based mouse controller"""
        try:
            self.mouse_controller = MouseController()
            if self.mouse_controller.initialize_driver():
                logger.info("PID mouse controller initialized successfully")
                self.pid_enabled = True
            else:
                logger.warning("Failed to initialize PID mouse controller, falling back to legacy methods")
                self.pid_enabled = False
        except Exception as e:
            logger.error(f"Error initializing PID mouse controller: {e}")
            self.pid_enabled = False
            self.mouse_controller = None

    def process_data(self, data):
        if isinstance(data, sv.Detections):
            target_x, target_y = data.xyxy.mean(axis=1)
            target_w, target_h = data.xyxy[:, 2] - data.xyxy[:, 0], data.xyxy[:, 3] - data.xyxy[:, 1]
            target_cls = data.class_id[0] if data.class_id.size > 0 else None
        else:
            target_x, target_y, target_w, target_h, target_cls = data

        # 强制检查快速瞄准模式超时
        if self.fast_aim_mode and self.is_aim_timeout():
            logger.info("⚡ Force stopping fast aim mode due to timeout")
            self.stop_fast_aim_mode()

        self.visualize_target(target_x, target_y, target_cls)
        self.bScope = self.check_target_in_scope(target_x, target_y, target_w, target_h, self.bScope_multiplier) if cfg.auto_shoot or cfg.triggerbot else False
        self.bScope = cfg.force_click or self.bScope

        if not self.disable_prediction:
            current_time = time.time()
            if not isinstance(data, sv.Detections):
                target_x, target_y = self.predict_target_position(target_x, target_y, current_time)
            self.visualize_prediction(target_x, target_y, target_cls)

        move_x, move_y = self.calc_movement(target_x, target_y, target_cls)
        
        self.visualize_history(target_x, target_y)
        shooting.queue.put((self.bScope, self.get_shooting_key_state()))
        self.move_mouse(move_x, move_y)
        
        # 检查快速瞄准完成条件 - 优化结束条件
        if self.fast_aim_mode:
            if self.bScope and target_cls == 7:
                # 目标在瞄准范围内且是头部目标
                if self.aim_stage == "FINE":
                    # 精瞄阶段完成，瞄准成功
                    logger.info("✅ Fast aim completed: fine stage + in scope")
                    self.stop_fast_aim_mode()
                elif self.aim_stage == "COARSE":
                    # 粗瞄阶段完成，切换到精瞄
                    self.switch_to_fine_aiming()
                else:
                    # 普通快速瞄准完成
                    logger.info("✅ Fast aim completed: normal mode + in scope")
                    self.stop_fast_aim_mode()
            # 检查是否应该强制结束快速瞄准模式
            elif self.should_force_end_fast_aim():
                logger.info("⚡ Force ending fast aim mode")
                self.stop_fast_aim_mode()

    def handle_no_target(self):
        """处理无目标情况"""
        logger.info("🔄 No target detected - cleaning up states")
        
        # 刷新任何剩余的移动缓冲
        if self.should_flush_buffer():
            logger.info("🔄 Flushing remaining movement buffer")
            self.flush_movement_buffer()
        
        # 停止快速瞄准模式和重置两段式瞄准状态
        if self.fast_aim_mode:
            logger.info("🔄 Stopping fast aim mode due to no target")
            self.stop_fast_aim_mode()
        
        # 重置两段式瞄准状态
        if self.aim_stage != "NONE":
            logger.info(f"🔄 Resetting aim stage from {self.aim_stage} to NONE")
            self.reset_aiming_state()
        
        # Transition to IDLE state when no target
        logger.info("🔄 Setting movement state to IDLE (no target)")
        self.set_movement_state(MovementState.IDLE)
        
        # Force clear movement flags
        self.force_clear_movement_state()
    
    def is_movement_active(self):
        """
        Check if any movement is currently active.
        Used by frame parser to coordinate detection timing.
        """
        current_time = time.time()
        
        # Check if movement state indicates activity
        if self.movement_state != MovementState.IDLE:
            # Check for movement timeout
            time_elapsed = (current_time - self.movement_start_time) * 1000
            if time_elapsed > self.movement_timeout_ms:
                # Movement timed out, reset to idle
                logger.info(f"🔄 Movement timeout detected: {time_elapsed:.0f}ms > {self.movement_timeout_ms}ms, resetting to IDLE")
                self.set_movement_state(MovementState.IDLE)
                return False
            
            # Log active movement state (with controlled frequency)
            if self.should_log_movement():
                logger.info(f"🔄 Movement active: state={self.movement_state.value}, elapsed={time_elapsed:.0f}ms")
            return True
        
        # Check if we're still in fast aim mode
        if self.fast_aim_mode:
            aim_elapsed = (current_time - self.aim_start_time) * 1000
            if self.should_log_movement():
                logger.info(f"🚀 Fast aim mode active: elapsed={aim_elapsed:.0f}ms")
            return True
            
        # Check if we have pending buffer movements
        buffer_distance = math.sqrt(self.movement_buffer_x**2 + self.movement_buffer_y**2)
        if buffer_distance > 0:
            if self.should_log_movement():
                logger.info(f"⚡ Buffer pending: distance={buffer_distance:.1f}px ({self.movement_buffer_x:.1f}, {self.movement_buffer_y:.1f})")
            return True
            
        # Check recent movement commands (within cooldown period) - but make it less restrictive
        time_since_last_command = current_time - self.last_movement_command_time
        if time_since_last_command < self.state_transition_cooldown:
            # Only block if it's very recent (reduce the blocking time)
            if time_since_last_command < (self.state_transition_cooldown * 0.5):  # Only block for half the cooldown
                if self.should_log_movement():
                    logger.info(f"⏰ Command cooldown: {time_since_last_command*1000:.0f}ms < {self.state_transition_cooldown*500:.0f}ms")
                return True
            
        # If we get here, no movement is active
        if self.should_log_movement():
            logger.info("✅ No movement active - detection allowed")
        return False
    
    def force_clear_movement_state(self):
        """
        Force clear all movement state flags.
        Used when no target is detected to ensure clean state.
        """
        logger.info("🔄 Force clearing movement state")
        self.movement_buffer_x = 0.0
        self.movement_buffer_y = 0.0
        self.fast_aim_mode = False
        self.aim_stage = "NONE"
        self.movement_state = MovementState.IDLE
        self.last_movement_command_time = 0.0
    
    def should_force_end_fast_aim(self):
        """
        检查是否应该强制结束快速瞄准模式
        """
        if not self.fast_aim_mode:
            return False
        
        current_time = time.time()
        elapsed_ms = (current_time - self.aim_start_time) * 1000
        
        # 超时强制结束
        if elapsed_ms >= (self.max_aim_time_ms * 0.8):  # 80%时间强制结束
            return True
        
        # 如果缓冲区空且没有新的移动命令一段时间，认为瞄准完成
        buffer_empty = (self.movement_buffer_x == 0 and self.movement_buffer_y == 0)
        time_since_last_command = (current_time - self.last_movement_command_time) * 1000
        
        if buffer_empty and time_since_last_command > 100:  # 100ms没有新命令
            return True
        
        # 如果两段式瞄准都完成
        if self.aim_stage == "COMPLETE":
            return True
            
        return False
    
    def set_movement_state(self, new_state):
        """
        Safely transition between movement states with proper timing.
        """
        current_time = time.time()
        
        # Prevent rapid state changes
        if hasattr(self, '_last_state_change_time'):
            time_since_last_change = current_time - self._last_state_change_time
            if time_since_last_change < self.state_transition_cooldown:
                return False
        
        # Update state
        old_state = self.movement_state
        self.movement_state = new_state
        self._last_state_change_time = current_time
        
        # Track movement start time for active states
        if new_state != MovementState.IDLE and old_state == MovementState.IDLE:
            self.movement_start_time = current_time
        
        # Log significant state changes (reduce noise)
        if new_state != old_state and new_state in [MovementState.COARSE, MovementState.FINE]:
            logger.info(f"🔄 Movement state: {old_state.value} → {new_state.value}")
        
        return True
    
    def should_log_movement(self):
        """
        Control logging frequency to reduce spam while maintaining useful information.
        Returns True if enough time has passed since last log.
        """
        current_time = time.time()
        time_since_last_log = (current_time - self.last_log_time) * 1000
        
        if time_since_last_log >= self.log_interval_ms:
            self.last_log_time = current_time
            return True
        return False
    
    def log_movement_info(self, message, force=False):
        """
        Log movement information with frequency control.
        Set force=True for important events that should always be logged.
        """
        if force or self.should_log_movement():
            logger.info(message)

    def predict_target_position(self, target_x, target_y, current_time):
        # First target
        if self.prev_time is None:
            self.prev_time = current_time
            self.prev_x = target_x
            self.prev_y = target_y
            self.prev_velocity_x = 0
            self.prev_velocity_y = 0
            return target_x, target_y
        
        # Next target?
        max_jump = max(self.screen_width, self.screen_height) * 0.3 # 30%
        if abs(target_x - self.prev_x) > max_jump or abs(target_y - self.prev_y) > max_jump:
            self.prev_x, self.prev_y = target_x, target_y
            self.prev_velocity_x = 0
            self.prev_velocity_y = 0
            self.prev_time = current_time
            return target_x, target_y

        delta_time = current_time - self.prev_time
        
        if delta_time == 0:
            delta_time = 1e-6
    
        velocity_x = (target_x - self.prev_x) / delta_time
        velocity_y = (target_y - self.prev_y) / delta_time
        acceleration_x = (velocity_x - self.prev_velocity_x) / delta_time
        acceleration_y = (velocity_y - self.prev_velocity_y) / delta_time

        prediction_interval = delta_time * self.prediction_interval
        current_distance = math.sqrt((target_x - self.prev_x)**2 + (target_y - self.prev_y)**2)
        proximity_factor = max(0.1, min(1, 1 / (current_distance + 1)))

        speed_correction = 1 + (abs(current_distance - (self.prev_distance or 0)) / self.max_distance) * self.speed_correction_factor if self.prev_distance is not None else .0001

        predicted_x = target_x + velocity_x * prediction_interval * proximity_factor * speed_correction + 0.5 * acceleration_x * (prediction_interval ** 2) * proximity_factor * speed_correction
        predicted_y = target_y + velocity_y * prediction_interval * proximity_factor * speed_correction + 0.5 * acceleration_y * (prediction_interval ** 2) * proximity_factor * speed_correction

        self.prev_x, self.prev_y = target_x, target_y
        self.prev_velocity_x, self.prev_velocity_y = velocity_x, velocity_y
        self.prev_time = current_time
        self.prev_distance = current_distance

        return predicted_x, predicted_y

    def calculate_speed_multiplier(self, target_x, target_y, distance):
        if any(map(math.isnan, (target_x, target_y))) or self.section_size_x == 0:
            return self.min_speed_multiplier
    
        normalized_distance = min(distance / self.max_distance, 1)
        base_speed = self.min_speed_multiplier + (self.max_speed_multiplier - self.min_speed_multiplier) * (1 - normalized_distance)
        
        if self.section_size_x == 0:
            return self.min_speed_multiplier

        target_x_section = int((target_x - self.center_x + self.screen_width / 2) / self.section_size_x)
        target_y_section = int((target_y - self.center_y + self.screen_height / 2) / self.section_size_y)
        
        distance_from_center = max(abs(50 - target_x_section), abs(50 - target_y_section))
        
        if distance_from_center == 0:
            return 1
        elif 5 <= distance_from_center <= 10:
            return self.max_speed_multiplier
        else:
            speed_reduction = min(distance_from_center - 10, 45) / 100.0
            speed_multiplier = base_speed * (1 - speed_reduction)

        if self.prev_distance is not None:
            speed_adjustment = 1 + (abs(distance - self.prev_distance) / self.max_distance) * self.speed_correction_factor
            return speed_multiplier * speed_adjustment
        
        return speed_multiplier

    def calc_movement(self, target_x, target_y, target_cls):
        # Enhanced head targeting with precise movement calculation
        if target_cls == 7:  # Head target
            return self.calculate_precise_head_movement(target_x, target_y, target_cls)
        else:
            # Use existing logic for body targets
            return self.calculate_standard_movement(target_x, target_y, target_cls)
    
    def calculate_precise_head_movement(self, target_x, target_y, target_cls):
        """
        Calculate precise movement for head targets with minimal corrections.
        This method aims to reach the head position in a single, smooth movement.
        """
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        total_distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # For very small distances, use direct movement
        if total_distance <= self.head_precision_threshold:
            stage = "PRECISION"
            speed_multiplier = self.calculate_speed_multiplier(target_x, target_y, total_distance) * 0.8  # Slightly slower for precision
        
        # For medium distances, use optimized single-stage movement
        elif total_distance <= self.head_direct_threshold:
            stage = "DIRECT"
            speed_multiplier = self.calculate_speed_multiplier(target_x, target_y, total_distance) * 1.5  # Faster direct movement
        
        # For large distances, use two-stage but with better coordination
        else:
            offset_x, offset_y, stage, total_distance = self.calculate_two_stage_movement(target_x, target_y, target_cls)
            base_speed_multiplier = self.calculate_speed_multiplier(target_x, target_y, total_distance)
            speed_multiplier = self.get_stage_speed_multiplier(base_speed_multiplier, stage, total_distance)
        
        # Record current state
        self.current_target_class = target_cls
        self.current_move_distance = total_distance
        
        # Log stage information (controlled frequency)
        if not hasattr(self, '_last_stage') or self._last_stage != stage:
            stage_message = ""
            if stage == "PRECISION":
                stage_message = f"🎯 HEAD precision: distance={total_distance:.1f}px, speed={speed_multiplier:.1f}x"
            elif stage == "DIRECT":
                stage_message = f"🎯 HEAD direct: distance={total_distance:.1f}px, speed={speed_multiplier:.1f}x"
            elif stage == "COARSE":
                stage_message = f"🚀 HEAD coarse: distance={total_distance:.1f}px, speed={speed_multiplier:.1f}x"
            elif stage == "FINE":
                stage_message = f"🔍 HEAD fine: distance={total_distance:.1f}px, speed={speed_multiplier:.1f}x"
            
            if stage_message:
                self.log_movement_info(stage_message, force=(stage in ["COARSE", "FINE"]))  # Force log for stage changes
            self._last_stage = stage

        return self.convert_to_mouse_movement(offset_x, offset_y, speed_multiplier, stage)
    
    def calculate_standard_movement(self, target_x, target_y, target_cls):
        """
        Standard movement calculation for body targets (existing logic).
        """
        # Use existing two-stage movement algorithm
        offset_x, offset_y, stage, distance = self.calculate_two_stage_movement(target_x, target_y, target_cls)
        
        # Calculate speed multiplier
        base_speed_multiplier = self.calculate_speed_multiplier(target_x, target_y, distance)
        speed_multiplier = self.get_stage_speed_multiplier(base_speed_multiplier, stage, distance)
        
        # Record current state
        self.current_target_class = target_cls
        self.current_move_distance = distance
        
        return self.convert_to_mouse_movement(offset_x, offset_y, speed_multiplier, stage)
    
    def convert_to_mouse_movement(self, offset_x, offset_y, speed_multiplier, stage):
        """
        Convert pixel offsets to mouse movement with appropriate smoothing.
        """
        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height

        mouse_move_x = offset_x * degrees_per_pixel_x
        mouse_move_y = offset_y * degrees_per_pixel_y

        # Adaptive smoothing based on movement type
        if stage in ["PRECISION"]:
            alpha = 0.9  # High smoothing for precision
        elif stage in ["DIRECT"]:
            alpha = 0.6  # Low smoothing for direct movement
        elif stage in ["COARSE", "FINE"]:
            alpha = 0.7  # Medium smoothing for two-stage
        else:
            alpha = 0.85  # Default smoothing
            
        if not hasattr(self, 'last_move_x'):
            self.last_move_x, self.last_move_y = 0, 0
        
        move_x = alpha * mouse_move_x + (1 - alpha) * self.last_move_x
        move_y = alpha * mouse_move_y + (1 - alpha) * self.last_move_y
        
        self.last_move_x, self.last_move_y = move_x, move_y

        move_x = (move_x / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * speed_multiplier
        move_y = (move_y / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * speed_multiplier

        return move_x, move_y

    def calculate_two_stage_movement(self, target_x, target_y, target_cls):
        """计算两段式移动：粗瞄+精瞄"""
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        total_distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 只对头部目标且距离>50px的情况使用两段式移动
        if target_cls == 7 and total_distance > 50:
            if self.aim_stage == "NONE" or self.aim_stage == "COARSE":
                # 粗瞄阶段：移动到目标80%位置
                self.coarse_target_x = self.center_x + offset_x * 0.8
                self.coarse_target_y = self.center_y + offset_y * 0.8
                self.fine_target_x = target_x  # 保存最终目标
                self.fine_target_y = target_y
                
                if self.aim_stage == "NONE":
                    self.start_coarse_aiming()
                
                # 返回粗瞄移动量
                coarse_offset_x = self.coarse_target_x - self.center_x
                coarse_offset_y = self.coarse_target_y - self.center_y
                return coarse_offset_x, coarse_offset_y, "COARSE", math.sqrt(coarse_offset_x**2 + coarse_offset_y**2)
            
            elif self.aim_stage == "FINE":
                # 精瞄阶段：调整到最终目标位置
                fine_offset_x = self.fine_target_x - self.center_x
                fine_offset_y = self.fine_target_y - self.center_y
                return fine_offset_x, fine_offset_y, "FINE", math.sqrt(fine_offset_x**2 + fine_offset_y**2)
        
        # 普通移动（非头部目标或小距离）
        return offset_x, offset_y, "NORMAL", total_distance

    def get_stage_speed_multiplier(self, base_multiplier, stage, distance):
        """获取阶段化的速度倍数"""
        # 基础速度提升50%
        enhanced_base = base_multiplier * 1.5
        
        if stage == "COARSE":
            # 粗瞄阶段：极速移动，提升150%
            return enhanced_base * 2.5
        elif stage == "FINE":
            # 精瞄阶段：快速精确，提升80%
            return enhanced_base * 1.8
        elif stage == "NORMAL" and self.current_target_class == 7:
            # 头部目标普通移动：保持原有的头部优化
            if distance <= 80:
                return enhanced_base * 1.30
            elif distance <= 180:
                return enhanced_base * 1.50
            else:
                return enhanced_base * 1.80
        else:
            # 非头部目标：50%基础提升
            return enhanced_base

    def start_coarse_aiming(self):
        """启动粗瞄阶段"""
        self.aim_stage = "COARSE"
        self.stage_start_time = time.time()
        self.set_movement_state(MovementState.COARSE)
        logger.info("🎯 Coarse aiming started - targeting 80% position")

    def switch_to_fine_aiming(self):
        """切换到精瞄阶段"""
        if self.aim_stage == "COARSE":
            coarse_time = (time.time() - self.stage_start_time) * 1000
            self.aim_stage = "FINE"
            self.stage_start_time = time.time()
            self.set_movement_state(MovementState.FINE)
            logger.info(f"🔍 Fine aiming started - coarse completed in {coarse_time:.0f}ms")
            return True
        return False

    def is_coarse_aiming_complete(self):
        """检查粗瞄是否完成"""
        if self.aim_stage != "COARSE":
            return False
        
        # 检查粗瞄阶段移动是否足够完成
        time_elapsed = (time.time() - self.stage_start_time) * 1000
        
        # 粗瞄完成条件：
        # 1. 时间达到最小阈值（确保移动有时间执行）
        # 2. 时间超过最大限制（防止卡死）
        # 3. 移动缓冲区为空（当前移动已完成）
        
        # 必须达到最小时间
        if time_elapsed < self.min_coarse_time_ms:
            return False
        
        # 超时或移动缓冲区为空
        buffer_empty = (self.movement_buffer_x == 0 and self.movement_buffer_y == 0)
        return time_elapsed >= self.coarse_aim_time_ms or buffer_empty

    def is_fine_aiming_complete(self):
        """检查精瞄是否完成"""
        if self.aim_stage != "FINE":
            return False
        
        time_elapsed = (time.time() - self.stage_start_time) * 1000
        
        # 必须达到最小时间
        if time_elapsed < self.min_fine_time_ms:
            return False
        
        # 精瞄完成条件：移动缓冲区为空或超时
        buffer_empty = (self.movement_buffer_x == 0 and self.movement_buffer_y == 0)
        return time_elapsed >= self.fine_aim_time_ms or buffer_empty

    def is_stage_timeout(self):
        """检查当前阶段是否超时"""
        if self.aim_stage == "NONE":
            return False
        
        time_elapsed = (time.time() - self.stage_start_time) * 1000
        
        if self.aim_stage == "COARSE":
            return time_elapsed >= self.coarse_aim_time_ms
        elif self.aim_stage == "FINE":
            return time_elapsed >= self.fine_aim_time_ms
        
        return False

    def complete_two_stage_aiming(self):
        """完成两段式瞄准"""
        if self.aim_stage in ["COARSE", "FINE"]:
            total_time = (time.time() - self.aim_start_time) * 1000
            logger.info(f"✅ Two-stage aiming completed in {total_time:.0f}ms (stage: {self.aim_stage})")
            self.aim_stage = "COMPLETE"

    def select_optimal_pid_preset(self):
        """根据当前目标类型和距离选择最优PID预设"""
        if self.current_target_class == 7:  # 头部目标
            if self.current_move_distance <= 80:
                return OptimizedPIDPresets.HEAD_PRECISION, "HEAD_PRECISION"
            elif self.current_move_distance <= 180:
                return OptimizedPIDPresets.HEAD_BALANCED, "HEAD_BALANCED"
            else:
                return OptimizedPIDPresets.HEAD_SPEED, "HEAD_SPEED"
        else:
            # 身体目标使用原有逻辑
            move_distance = self.current_move_distance
            if move_distance < 10:
                return OptimizedPIDPresets.FPS_AIMING, "FPS_AIMING"
            elif move_distance > 100:
                return OptimizedPIDPresets.FPS_QUICK_TURN, "FPS_QUICK_TURN"
            elif move_distance > 50:
                return OptimizedPIDPresets.FPS_TRACKING, "FPS_TRACKING"
            else:
                return OptimizedPIDPresets.FPS_COMBAT, "FPS_COMBAT"

    def start_fast_aim_mode(self):
        """启动快速瞄准模式"""
        if not self.fast_aim_mode:
            self.fast_aim_mode = True
            self.aim_start_time = time.time()
            self.movement_buffer_x = 0.0
            self.movement_buffer_y = 0.0
            # 重置两段式瞄准状态
            logger.info(f"🚀 Fast aim mode activated: target_cls={getattr(self, 'current_target_class', 'unknown')}, aim_stage={self.aim_stage}")
        else:
            logger.info("🚀 Fast aim mode already active - continuing")

    def is_aim_timeout(self):
        """检查瞄准是否超时"""
        if self.fast_aim_mode:
            elapsed_ms = (time.time() - self.aim_start_time) * 1000
            is_timeout = elapsed_ms >= self.max_aim_time_ms
            if is_timeout:
                logger.info(f"⏰ Fast aim timeout: {elapsed_ms:.0f}ms >= {self.max_aim_time_ms}ms")
            return is_timeout
        return False

    def should_flush_buffer(self):
        """检查是否应该刷新移动缓冲 - 更积极的刷新策略"""
        if self.movement_buffer_x == 0 and self.movement_buffer_y == 0:
            return False
        
        # 缓冲区移动距离超过阈值 - 降低阈值让缓冲更快执行
        buffer_distance = math.sqrt(self.movement_buffer_x**2 + self.movement_buffer_y**2)
        if buffer_distance >= (self.movement_threshold * 0.6):  # 降低到60%，让缓冲更快执行
            return True
        
        # 缓冲窗口超时 - 时间窗口已经减少到30ms
        current_time = time.time()
        if (current_time - self.last_move_time) * 1000 >= self.buffer_window_ms:
            return True
        
        # 快速瞄准模式超时
        if self.is_aim_timeout():
            return True
        
        # 头部目标时更积极刷新缓冲
        if hasattr(self, 'current_target_class') and self.current_target_class == 7:
            if buffer_distance >= 3:  # 头部目标3像素就刷新
                return True
            
        return False

    def flush_movement_buffer(self):
        """执行缓冲区中的移动"""
        if self.movement_buffer_x == 0 and self.movement_buffer_y == 0:
            return False
        
        buffer_x = int(round(self.movement_buffer_x))
        buffer_y = int(round(self.movement_buffer_y))
        buffer_distance = math.sqrt(buffer_x*buffer_x + buffer_y*buffer_y)
        
        # 执行累积的移动
        success = False
        if self.pid_enabled and self.mouse_controller:
            try:
                # 检测是否为头部目标以使用专用模式
                is_head_target = hasattr(self, 'current_target_class') and self.current_target_class == 7
                # 缓冲移动使用高精度模式
                tolerance = 1 if is_head_target else 2
                success = self.mouse_controller.move_relative_to_target(
                    buffer_x, buffer_y, tolerance=tolerance, is_head_target=is_head_target
                )
                if success:
                    elapsed_ms = (time.time() - self.aim_start_time) * 1000 if self.fast_aim_mode else 0
                    self.log_movement_info(f"⚡ Buffered move executed: ({buffer_x}, {buffer_y}) | Time: {elapsed_ms:.0f}ms")
                else:
                    logger.warning("🎯 Buffered PID movement failed, falling back to legacy method")
            except Exception as e:
                logger.error(f"🎯 Buffered PID movement error: {e}, falling back to legacy method")
        
        # 如果PID失败，使用原有方法
        if not success:
            if not cfg.mouse_ghub and not cfg.arduino_move and not cfg.mouse_rzr:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, buffer_x, buffer_y, 0, 0)
                success = True
            elif cfg.mouse_ghub:
                self.ghub.mouse_xy(buffer_x, buffer_y)
                success = True
            elif cfg.arduino_move:
                arduino.move(buffer_x, buffer_y)
                success = True
            elif cfg.mouse_rzr:
                self.rzr.mouse_move(buffer_x, buffer_y, True)
                success = True
        
        # 清空缓冲区
        self.movement_buffer_x = 0.0
        self.movement_buffer_y = 0.0
        self.last_move_time = time.time()
        
        # Update movement state after buffer execution
        if success and buffer_distance < self.movement_completion_threshold:
            # Small movement completed, transition to completing state briefly
            self.set_movement_state(MovementState.COMPLETING)
            # Set a timer to return to idle after brief completion phase
        
        return success

    def stop_fast_aim_mode(self):
        """停止快速瞄准模式"""
        if self.fast_aim_mode:
            elapsed_ms = (time.time() - self.aim_start_time) * 1000
            self.fast_aim_mode = False
            # 刷新剩余缓冲
            self.flush_movement_buffer()
            # 完成两段式瞄准
            if self.aim_stage in ["COARSE", "FINE"]:
                self.complete_two_stage_aiming()
            else:
                logger.info(f"🎯 Fast aim completed in {elapsed_ms:.0f}ms")
            # 重置状态
            self.reset_aiming_state()
            # Return to idle state
            self.set_movement_state(MovementState.IDLE)

    def reset_aiming_state(self):
        """重置瞄准状态"""
        self.aim_stage = "NONE"
        self.coarse_target_x = 0.0
        self.coarse_target_y = 0.0
        self.fine_target_x = 0.0
        self.fine_target_y = 0.0
        self.stage_start_time = 0.0

    def move_mouse(self, x, y):
        current_time = time.time()
        self.last_movement_command_time = current_time
        
        if x == 0 and y == 0:
            # 即使是0移动，也要检查是否需要刷新缓冲区或处理阶段超时
            if self.should_flush_buffer():
                self.flush_movement_buffer()
            if self.is_stage_timeout():
                self.handle_stage_timeout()
            return

        shooting_state = self.get_shooting_key_state()

        if shooting_state or cfg.mouse_auto_aim:
            # Update movement state based on current activity
            if self.movement_state == MovementState.IDLE:
                # Check if we need to start two-stage aiming
                if hasattr(self, 'current_target_class') and self.current_target_class == 7:
                    if self.aim_stage == "COARSE":
                        self.set_movement_state(MovementState.COARSE)
                    elif self.aim_stage == "FINE":
                        self.set_movement_state(MovementState.FINE)
                    else:
                        self.set_movement_state(MovementState.MOVING)
                else:
                    self.set_movement_state(MovementState.MOVING)
            
            # 检查是否需要启动快速瞄准模式
            if hasattr(self, 'current_target_class') and self.current_target_class == 7 and not self.fast_aim_mode:
                self.start_fast_aim_mode()
            
            # 计算移动距离
            move_distance = math.sqrt(x*x + y*y)
            
            # Check stage transitions and timeouts
            if self.check_stage_transitions():
                # Stage transition occurred, recalculate movement if needed
                pass
            elif self.is_stage_timeout():
                self.handle_stage_timeout()
            
            # 两段式移动策略决策
            use_buffer = self.should_use_buffer(move_distance)
            
            if use_buffer:
                # 使用缓冲机制
                self.movement_buffer_x += x
                self.movement_buffer_y += y
                
                # 检查是否需要刷新缓冲区
                if self.should_flush_buffer():
                    self.flush_movement_buffer()
                
                # 如果快速瞄准模式超时，强制停止
                if self.is_aim_timeout():
                    self.stop_fast_aim_mode()
                    
                return
            else:
                # 直接执行大移动
                self.execute_direct_move(x, y, move_distance)

    def should_use_buffer(self, move_distance):
        """判断是否应该使用缓冲机制 - 优化为更多直接移动"""
        use_buffer = False
        reason = ""
        
        # Only use buffer for very small movements and specific scenarios
        
        # For head targets, prefer direct movement for better precision
        if hasattr(self, 'current_target_class') and self.current_target_class == 7:
            # For head targets, only buffer very tiny movements
            use_buffer = move_distance < (self.movement_threshold * 0.5)  # 4px threshold for heads
            reason = f"head_target, distance={move_distance:.1f} < threshold={self.movement_threshold * 0.5:.1f}"
        
        # 两段式移动中的小调整使用缓冲，但阈值更低
        elif self.aim_stage in ["COARSE", "FINE"]:
            use_buffer = move_distance < (self.movement_threshold * 0.7)  # 5.6px threshold
            reason = f"aim_stage={self.aim_stage}, distance={move_distance:.1f} < threshold={self.movement_threshold * 0.7:.1f}"
        
        # 快速瞄准模式下也优先直接移动
        elif self.fast_aim_mode:
            use_buffer = move_distance < (self.movement_threshold * 0.6)  # 4.8px threshold  
            reason = f"fast_aim_mode, distance={move_distance:.1f} < threshold={self.movement_threshold * 0.6:.1f}"
        
        # 普通情况下只有非常小的移动才缓冲
        else:
            use_buffer = move_distance < (self.movement_threshold * 0.5)  # 4px threshold
            reason = f"normal_mode, distance={move_distance:.1f} < threshold={self.movement_threshold * 0.5:.1f}"
        
        # Log buffer decision (with controlled frequency)
        if self.should_log_movement():
            buffer_status = "BUFFER" if use_buffer else "DIRECT"
            logger.info(f"🎯 Movement decision: {buffer_status} - {reason}")
        
        return use_buffer

    def execute_direct_move(self, x, y, move_distance):
        """执行直接移动"""
        success = False
        
        if self.pid_enabled and self.mouse_controller:
            try:
                # 检测是否为头部目标以使用专用模式
                is_head_target = hasattr(self, 'current_target_class') and self.current_target_class == 7
                # 根据距离动态设置精度：近距离高精度，远距离快速响应
                if move_distance <= 50:
                    tolerance = 1  # 高精度
                elif move_distance <= 150:
                    tolerance = 2  # 平衡精度
                else:
                    tolerance = 3  # 快速响应
                
                success = self.mouse_controller.move_relative_to_target(
                    int(x), int(y), tolerance=tolerance, is_head_target=is_head_target
                )
                
                if success:
                    if not hasattr(self, '_pid_success_logged'):
                        logger.info("🎯 PID relative movement initialized successfully")
                        self._pid_success_logged = True
                    
                    # 根据阶段记录不同的日志（控制频率）
                    if self.aim_stage == "COARSE":
                        self.log_movement_info(f"🚀 COARSE direct move: ({int(x)}, {int(y)}) distance={move_distance:.1f}px", force=True)
                    elif self.aim_stage == "FINE":
                        self.log_movement_info(f"🔍 FINE direct move: ({int(x)}, {int(y)}) distance={move_distance:.1f}px", force=True)
                    else:
                        self.log_movement_info(f"⚡ Direct move: ({int(x)}, {int(y)}) distance={move_distance:.1f}px")
                    
                    self.last_move_time = time.time()
                    return
                else:
                    logger.warning("🎯 PID movement failed, falling back to legacy method")
            except Exception as e:
                logger.error(f"🎯 PID movement error: {e}, falling back to legacy method")
        
        # 回退方法
        if not success:
            if not cfg.mouse_ghub and not cfg.arduino_move and not cfg.mouse_rzr:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(x), int(y), 0, 0)
            elif cfg.mouse_ghub:
                self.ghub.mouse_xy(int(x), int(y))
            elif cfg.arduino_move:
                arduino.move(int(x), int(y))
            elif cfg.mouse_rzr:
                self.rzr.mouse_move(int(x), int(y), True)
            
            self.last_move_time = time.time()

    def handle_stage_timeout(self):
        """处理阶段超时"""
        if self.aim_stage == "COARSE":
            logger.info("⏰ Coarse aiming timeout - switching to fine aiming")
            if self.switch_to_fine_aiming():
                # Flush any pending coarse movements before starting fine aiming
                self.flush_movement_buffer()
        elif self.aim_stage == "FINE":
            logger.info("⏰ Fine aiming timeout - completing aiming")
            self.complete_two_stage_aiming()
            if self.fast_aim_mode:
                self.stop_fast_aim_mode()

    def check_stage_transitions(self):
        """
        Check and handle stage transitions based on completion status.
        This method ensures smooth transitions between aiming stages.
        """
        if self.aim_stage == "COARSE" and self.is_coarse_aiming_complete():
            if self.switch_to_fine_aiming():
                # Ensure coarse movement is completed before fine aiming
                self.flush_movement_buffer()
                return True
        elif self.aim_stage == "FINE" and self.is_fine_aiming_complete():
            self.complete_two_stage_aiming()
            return True
        return False

    def get_shooting_key_state(self):
        for key_name in cfg.hotkey_targeting_list:
            key_code = Buttons.KEY_CODES.get(key_name.strip())
            if key_code and (win32api.GetKeyState(key_code) if cfg.mouse_lock_target else win32api.GetAsyncKeyState(key_code)) < 0:
                return True
        return False

    def check_target_in_scope(self, target_x, target_y, target_w, target_h, reduction_factor):
        reduced_w, reduced_h = target_w * reduction_factor / 2, target_h * reduction_factor / 2
        x1, x2, y1, y2 = target_x - reduced_w, target_x + reduced_w, target_y - reduced_h, target_y + reduced_h
        bScope = self.center_x > x1 and self.center_x < x2 and self.center_y > y1 and self.center_y < y2
        
        if cfg.show_window and cfg.show_bScope_box:
            visuals.draw_bScope(x1, x2, y1, y2, bScope)
        
        return bScope

    def update_settings(self):
        self.dpi = cfg.mouse_dpi
        self.mouse_sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.disable_prediction = cfg.disable_prediction
        self.prediction_interval = cfg.prediction_interval
        self.bScope_multiplier = cfg.bScope_multiplier
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # Reinitialize PID controller with updated settings
        self.setup_pid_controller()
    
    def cleanup(self):
        """Clean up resources when mouse controller is no longer needed"""
        if hasattr(self, 'mouse_controller') and self.mouse_controller:
            try:
                self.mouse_controller.cleanup()
                logger.info("PID mouse controller cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up PID mouse controller: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()

    def visualize_target(self, target_x, target_y, target_cls):
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, target_cls)

    def visualize_prediction(self, target_x, target_y, target_cls):
        if (cfg.show_window and cfg.show_target_prediction_line) or (cfg.show_overlay and cfg.show_target_prediction_line):
            visuals.draw_predicted_position(target_x, target_y, target_cls)

    def visualize_history(self, target_x, target_y):
        if (cfg.show_window and cfg.show_history_points) or (cfg.show_overlay and cfg.show_history_points):
            visuals.draw_history_point_add_point(target_x, target_y)

# Optimized PID presets for different scenarios
class OptimizedPIDPresets:
    # FPS游戏精确瞄准场景
    FPS_AIMING = {
        'tolerance': 2,        # 平衡精度与速度
        'max_iterations': 50   # 快速收敛
    }
    
    # FPS游戏快速转身场景
    FPS_QUICK_TURN = {
        'tolerance': 15,       # 优先速度
        'max_iterations': 30   # 极速响应
    }
    
    # FPS游戏目标追踪场景
    FPS_TRACKING = {
        'tolerance': 12,       # 快速跟踪
        'max_iterations': 25   # 实时响应
    }
    
    # FPS游戏压枪控制场景
    FPS_RECOIL_CONTROL = {
        'tolerance': 8,        # 快速补偿
        'max_iterations': 15   # 射击节奏匹配
    }
    
    # FPS游戏综合战斗场景
    FPS_COMBAT = {
        'tolerance': 10,       # 平衡性能
        'max_iterations': 40   # 稳定输出
    }
    
    # === 头部瞄准专用预设 - 三级渐进式优化 ===
    
    # 头部精确瞄准模式 (≤ 80px)
    HEAD_PRECISION = {
        'tolerance': 1,        # 超高精度要求
        'max_iterations': 25   # 适中迭代，保证精度
    }
    
    # 头部平衡模式 (80-180px)
    HEAD_BALANCED = {
        'tolerance': 2,        # 高精度要求
        'max_iterations': 20   # 快速收敛
    }
    
    # 头部高速模式 (> 180px)
    HEAD_SPEED = {
        'tolerance': 4,        # 合理精度要求
        'max_iterations': 15   # 极速响应
    }

mouse = MouseThread()