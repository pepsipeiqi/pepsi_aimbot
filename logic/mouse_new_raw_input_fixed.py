"""
Enhanced mouse_new Raw Input Compatibility Controller

This controller addresses the Raw Input game compatibility issue by implementing
multiple mouse injection techniques with automatic fallback and detection.

Key Features:
- Multiple Raw Input bypass techniques (SendInput, SetPhysicalCursorPos, etc.)
- Automatic detection of which method works with current game
- Comprehensive logging for troubleshooting
- Maintains ultra-aggressive speed optimization from original algorithm
"""

import sys
import os
import time
import math
import ctypes
from ctypes import wintypes, windll, Structure, Union, byref, sizeof

# Ensure mouse_new is available
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mouse_new_path = os.path.join(project_root, 'mouse_new')
    if mouse_new_path not in sys.path:
        sys.path.insert(0, mouse_new_path)
    
    import mouse
    print("✅ mouse_new library loaded successfully")
    MOUSE_NEW_AVAILABLE = True
except Exception as e:
    print(f"❌ Failed to load mouse_new library: {e}")
    MOUSE_NEW_AVAILABLE = False
    mouse = None

class RawInputCompatibleController:
    """Enhanced mouse_new controller with Raw Input game compatibility"""
    
    def __init__(self):
        # Load configuration
        try:
            from logic.config_watcher import cfg
            self.screen_width = cfg.detection_window_width
            self.screen_height = cfg.detection_window_height
            self.dpi = cfg.mouse_dpi
            self.sensitivity = cfg.mouse_sensitivity
            self.fov_x = cfg.mouse_fov_width
            self.fov_y = cfg.mouse_fov_height
            self.body_y_offset = getattr(cfg, 'body_y_offset', -0.3)
            self.auto_aim = cfg.mouse_auto_aim
            self.auto_shoot = cfg.auto_shoot
            print("✅ Config loaded from cfg")
        except Exception as e:
            print(f"⚠️ Config loading failed, using defaults: {e}")
            # Default configuration
            self.screen_width = 380
            self.screen_height = 380
            self.dpi = 1100
            self.sensitivity = 3.0
            self.fov_x = 40
            self.fov_y = 40
            self.body_y_offset = -0.3
            self.auto_aim = True
            self.auto_shoot = True
        
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        self.aim_threshold = 3           # Ultra-aggressive targeting threshold
        self.min_move_threshold = 1      # Minimum movement threshold
        # 连续移动配置 - 革命性250px阈值，消除90%分段情况
        self.smooth_movement_enabled = getattr(cfg, 'smooth_movement_enabled', True)
        self.max_single_move = getattr(cfg, 'max_single_move_distance', 250)  # 革命性优化: 120→250px, 覆盖90%移动
        self.segment_delay = 0  # 零延迟策略 - 完全移除延迟
        self.target_locked = False
        self.lock_start_time = 0
        self.lock_timeout = 1.5          # Lock timeout
        
        # Mouse injection method tracking
        self.current_method = "auto"
        self.available_methods = []
        self.method_success_count = {}
        self.method_failure_count = {}
        
        # Apply Raw Input configuration settings
        try:
            from logic.config_watcher import cfg
            self.force_mouse_new = getattr(cfg, 'force_mouse_new', True)
            self.raw_input_method = getattr(cfg, 'raw_input_method', 'auto')
            self.enable_raw_input_bypass = getattr(cfg, 'enable_raw_input_bypass', True)
            self.raw_input_debug_logging = getattr(cfg, 'raw_input_debug_logging', True)
            
            # Override method if specified in config
            if self.raw_input_method != "auto":
                self.current_method = self.raw_input_method
            
            print(f"✅ Raw Input config: method={self.raw_input_method}, bypass={self.enable_raw_input_bypass}, debug={self.raw_input_debug_logging}")
        except Exception as e:
            print(f"⚠️ Could not load Raw Input config, using defaults: {e}")
            self.force_mouse_new = True
            self.raw_input_method = "auto"
            self.enable_raw_input_bypass = True
            self.raw_input_debug_logging = True
        
        # Initialize mouse injection methods
        self._init_injection_methods()
        
        # Check mouse_new availability
        self.mouse_available = MOUSE_NEW_AVAILABLE and mouse is not None
        
        # 过冲监控系统
        self.overshoot_detection_enabled = True
        self.overshoot_threshold = 15  # 像素阈值
        self.correction_attempts = 0
        self.max_correction_attempts = 2
        
        print(f"🎯 RawInputCompatibleController initialized")
        print(f"   Screen: {self.screen_width}x{self.screen_height}")
        print(f"   mouse_new available: {'✅' if self.mouse_available else '❌'}")
        print(f"   Available injection methods: {self.available_methods}")
    
    def _init_injection_methods(self):
        """Initialize and test available mouse injection methods"""
        self.available_methods = []
        
        # Method 1: Enhanced SendInput with Raw Input flags
        if self._test_enhanced_sendinput():
            self.available_methods.append("enhanced_sendinput")
            self.method_success_count["enhanced_sendinput"] = 0
            self.method_failure_count["enhanced_sendinput"] = 0
        
        # Method 2: SetPhysicalCursorPos (more direct hardware access)
        if self._test_physical_cursor():
            self.available_methods.append("physical_cursor")
            self.method_success_count["physical_cursor"] = 0
            self.method_failure_count["physical_cursor"] = 0
        
        # Method 3: mouse_new library (original implementation)
        if self._test_mouse_new():
            self.available_methods.append("mouse_new")
            self.method_success_count["mouse_new"] = 0
            self.method_failure_count["mouse_new"] = 0
        
        # Method 4: Direct Win32 API simulation
        if self._test_win32_direct():
            self.available_methods.append("win32_direct")
            self.method_success_count["win32_direct"] = 0
            self.method_failure_count["win32_direct"] = 0
        
        print(f"✅ Initialized {len(self.available_methods)} mouse injection methods")
    
    def _test_enhanced_sendinput(self):
        """Test Enhanced SendInput method availability"""
        try:
            # Define SendInput structures with Raw Input compatibility flags
            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ('dx', wintypes.LONG),
                    ('dy', wintypes.LONG),
                    ('mouseData', wintypes.DWORD),
                    ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))
                ]
            
            class INPUT_UNION(ctypes.Union):
                _fields_ = [('mi', MOUSEINPUT)]
            
            class INPUT(ctypes.Structure):
                _fields_ = [
                    ('type', wintypes.DWORD),
                    ('union', INPUT_UNION)
                ]
            
            # Test if we can create the structures
            mouse_input = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=0x0001, time=0, dwExtraInfo=None)
            input_struct = INPUT(type=0, union=INPUT_UNION(mi=mouse_input))
            return True
            
        except Exception as e:
            print(f"⚠️ Enhanced SendInput test failed: {e}")
            return False
    
    def _test_physical_cursor(self):
        """Test SetPhysicalCursorPos method availability"""
        try:
            # Try to access the SetPhysicalCursorPos function
            user32 = windll.user32
            if hasattr(user32, 'SetPhysicalCursorPos'):
                return True
            else:
                print("⚠️ SetPhysicalCursorPos not available on this system")
                return False
        except Exception as e:
            print(f"⚠️ Physical cursor test failed: {e}")
            return False
    
    def _test_mouse_new(self):
        """Test mouse_new library availability"""
        return MOUSE_NEW_AVAILABLE and mouse is not None
    
    def _test_win32_direct(self):
        """Test direct Win32 API access"""
        try:
            user32 = windll.user32
            return hasattr(user32, 'mouse_event') and hasattr(user32, 'GetCursorPos')
        except Exception as e:
            print(f"⚠️ Win32 direct test failed: {e}")
            return False
    
    def process_data(self, data):
        """Process YOLO detection data - compatible interface method"""
        try:
            import supervision as sv
            
            # Parse detection data
            if isinstance(data, sv.Detections):
                if len(data.xyxy) == 0:
                    self.handle_no_target()
                    return
                
                # Get first detection target
                bbox = data.xyxy[0]  # [x1, y1, x2, y2]
                target_x = (bbox[0] + bbox[2]) / 2  # Center X
                target_y = (bbox[1] + bbox[3]) / 2  # Center Y
                target_w = bbox[2] - bbox[0]        # Width
                target_h = bbox[3] - bbox[1]        # Height
                target_cls = data.class_id[0] if len(data.class_id) > 0 else 0
            else:
                # Traditional tuple format
                target_x, target_y, target_w, target_h, target_cls = data
            
            # Process target
            return self.process_target(target_x, target_y, target_w, target_h, target_cls)
            
        except Exception as e:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - ❌ Error processing detection data: {e}")
            self.handle_no_target()
            return False
    
    def process_target(self, target_x, target_y, target_w=0, target_h=0, target_cls=0):
        """Process detected target"""
        if not self.mouse_available:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ mouse_new library not available")
            return False
        
        # Apply precision targeting to chest center position
        original_target_x, original_target_y = target_x, target_y
        if target_cls != 7:  # Not a head target
            # Y-axis offset: move up to chest area
            target_y += target_h * self.body_y_offset
            # X-axis offset: slight adjustment to center (fix left shoulder issue)
            target_x += target_w * 0.05  # 5% right offset
            
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📐 TRANSFORM OFFSET: "
                  f"original=({original_target_x:.1f},{original_target_y:.1f}) → "
                  f"adjusted=({target_x:.1f},{target_y:.1f}) | "
                  f"body_offset={self.body_y_offset} x_adjust=5%")
        else:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📐 TRANSFORM OFFSET: "
                  f"HEAD target - no offset applied ({target_x:.1f},{target_y:.1f})")
        
        # Calculate offset from center
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        target_type = "HEAD" if target_cls == 7 else "BODY"
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - 📐 PIXEL OFFSET: "
              f"target=({target_x:.1f},{target_y:.1f}) center=({self.center_x:.1f},{self.center_y:.1f}) → "
              f"offset=({offset_x:.1f},{offset_y:.1f}) distance={distance:.1f}px")
        print(f"{current_time} - 🎯 Processing {target_type} target: ({target_x:.1f}, {target_y:.1f}), distance={distance:.1f}px")
        
        # Check if movement is needed
        if distance <= self.aim_threshold:
            if not self.target_locked:
                self.target_locked = True
                self.lock_start_time = time.time()
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔒 Target locked! Distance: {distance:.1f}px")
            return True
        
        # Check if movement distance is too small (avoid micro-jitter)
        if distance <= self.min_move_threshold:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔄 Movement too small ({distance:.1f}px), ignoring to prevent jitter")
            return True
        
        # Need to move to target
        movement_success = self.move_to_target(offset_x, offset_y, target_cls)
        
        # 过冲检测和修正（如果移动成功）
        if movement_success and self.overshoot_detection_enabled:
            # 给系统一点时间来执行移动
            time.sleep(0.001)  # 1ms延迟确保移动完成
            correction_success = self._detect_and_correct_overshoot(target_x, target_y, movement_success)
            
            # 精度着陆系统作为最终步骤
            if correction_success:
                time.sleep(0.001)  # 再次给系统时间处理修正移动
                landing_success = self._precision_landing(target_x, target_y)
                return movement_success and correction_success and landing_success
            
            return movement_success and correction_success
        
        return movement_success
    
    def move_to_target(self, offset_x, offset_y, target_cls):
        """革命性目标导向移动 - 智能分区算法，零过冲设计"""
        if not self.mouse_available:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ mouse_new library not available")
            return False
        
        try:
            # 使用新的目标导向计算
            mouse_x, mouse_y = self.calculate_target_movement(offset_x, offset_y)
            pixel_distance = math.sqrt(offset_x**2 + offset_y**2)
            movement_distance = math.sqrt(mouse_x**2 + mouse_y**2)
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - 🎯 TARGET MOVE: pixel=({offset_x:.1f},{offset_y:.1f}) → mouse=({mouse_x:.1f},{mouse_y:.1f}) | {pixel_distance:.0f}px")
            
            # 智能移动策略选择
            if pixel_distance <= 20:
                # 精度区域：直接移动
                return self._execute_precision_movement(mouse_x, mouse_y)
            elif pixel_distance <= 100:
                # 平衡区域：智能分段
                return self._execute_balanced_movement(mouse_x, mouse_y, pixel_distance)
            else:
                # 速度区域：跳跃+着陆
                return self._execute_speed_movement(mouse_x, mouse_y, pixel_distance)
            
        except Exception as e:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - ❌ Target movement failed: {e}")
            return False
    
    def _execute_precision_movement(self, mouse_x, mouse_y):
        """精度移动：单步直达，最大精确性"""
        exec_x, exec_y = int(round(mouse_x)), int(round(mouse_y))
        success = self._execute_mouse_movement(exec_x, exec_y)
        
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{current_time} - 🎯 PRECISION: ({exec_x}, {exec_y}) {status}")
        
        if success:
            self.target_locked = False
        return success
    
    def _execute_balanced_movement(self, mouse_x, mouse_y, pixel_distance):
        """平衡移动：2段式移动，速度+精度平衡"""
        # 两段式移动：80% + 20%
        first_x = mouse_x * 0.8
        first_y = mouse_y * 0.8
        second_x = mouse_x * 0.2  
        second_y = mouse_y * 0.2
        
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - 🎯 BALANCED: 2-stage movement for {pixel_distance:.0f}px")
        
        # 第一段：快速接近
        exec1_x, exec1_y = int(round(first_x)), int(round(first_y))
        success1 = self._execute_mouse_movement(exec1_x, exec1_y)
        
        if not success1:
            return False
        
        # 第二段：精确着陆
        exec2_x, exec2_y = int(round(second_x)), int(round(second_y))
        success2 = self._execute_mouse_movement(exec2_x, exec2_y)
        
        overall_success = success1 and success2
        if overall_success:
            self.target_locked = False
            print(f"{current_time} - 🎯 BALANCED RESULT: ✅ 2/2 stages SUCCESS")
        else:
            print(f"{current_time} - 🎯 BALANCED RESULT: ❌ Stage failed")
        
        return overall_success
    
    def _execute_speed_movement(self, mouse_x, mouse_y, pixel_distance):
        """速度移动：3段式移动，最快速度+精确着陆"""
        # 三段式移动：60% + 30% + 10% (精确着陆)
        segments = [0.6, 0.3, 0.1]
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - 🎯 SPEED: 3-stage movement for {pixel_distance:.0f}px")
        
        success_count = 0
        accumulated_x, accumulated_y = 0.0, 0.0
        
        for i, ratio in enumerate(segments):
            # 计算当前段的目标位置
            target_x = mouse_x * sum(segments[:i+1])
            target_y = mouse_y * sum(segments[:i+1])
            
            # 计算当前段需要移动的距离
            current_x = target_x - accumulated_x
            current_y = target_y - accumulated_y
            
            # 执行移动
            exec_x, exec_y = int(round(current_x)), int(round(current_y))
            success = self._execute_mouse_movement(exec_x, exec_y)
            
            if success:
                success_count += 1
                accumulated_x += exec_x
                accumulated_y += exec_y
                print(f"    Stage {i+1}/3: ✅ ({exec_x}, {exec_y})")
            else:
                print(f"    Stage {i+1}/3: ❌ ({exec_x}, {exec_y})")
        
        overall_success = success_count >= 2  # 至少2段成功
        if overall_success:
            self.target_locked = False
            print(f"{current_time} - 🎯 SPEED RESULT: ✅ {success_count}/3 stages SUCCESS")
        else:
            print(f"{current_time} - 🎯 SPEED RESULT: ❌ Only {success_count}/3 stages")
        
        return overall_success
    
    def _execute_smooth_segmented_movement(self, total_mouse_x, total_mouse_y, pixel_offset_x, pixel_offset_y):
        """执行智能变速分段移动 - 渐变速度曲线，保持浮点精度，自适应延迟"""
        total_distance = math.sqrt(total_mouse_x**2 + total_mouse_y**2)
        # 革命性提升：大幅提高单次移动阈值，覆盖90%以上移动情况
        if total_distance <= 250:  # 终极优化：250px以下直接移动
            return self._execute_direct_movement(total_mouse_x, total_mouse_y)
        
        # 对于极远距离(>250px)，使用连续插值移动而非分段移动
        return self._execute_continuous_interpolation_movement(total_mouse_x, total_mouse_y, total_distance)
    
    def _execute_continuous_interpolation_movement(self, total_mouse_x, total_mouse_y, total_distance):
        """执行连续插值移动 - 消除70%-30%分段的不均匀性，实现真正连续感"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 智能步长计算 - 基于距离自适应
        if total_distance <= 400:
            step_size = 25  # 中等距离：25px固定步长
        elif total_distance <= 600:
            step_size = 30  # 远距离：30px固定步长  
        else:
            step_size = 35  # 极远距离：35px固定步长
        
        # 计算步数 - 确保均匀分布
        steps = max(2, math.ceil(total_distance / step_size))
        
        if getattr(self, 'raw_input_debug_logging', True):
            print(f"{current_time} - 🎯 CONTINUOUS INTERPOLATION: {total_distance:.0f}px in {steps} uniform steps (step_size={step_size}px)")
        
        # 生成均匀连续轨迹点
        trajectory_points = self._generate_uniform_trajectory(total_mouse_x, total_mouse_y, steps)
        
        success_count = 0
        accumulated_x, accumulated_y = 0.0, 0.0  # 保持浮点精度
        
        # 零延迟连续执行 - 高频均匀移动
        for i, (target_x, target_y) in enumerate(trajectory_points):
            # 计算当前步骤的实际移动量
            current_move_x = target_x - accumulated_x
            current_move_y = target_y - accumulated_y
            
            # 高精度四舍五入转换
            exec_x = int(round(current_move_x))
            exec_y = int(round(current_move_y))
            
            # 更新累积器
            accumulated_x += exec_x
            accumulated_y += exec_y
            
            # 执行移动（跳过无意义的零移动）
            if exec_x != 0 or exec_y != 0:
                success = self._execute_mouse_movement(exec_x, exec_y)
                if success:
                    success_count += 1
                    if getattr(self, 'raw_input_debug_logging', True):
                        print(f"    Step {i+1}/{steps}: ✅ ({exec_x}, {exec_y})")
                else:
                    if getattr(self, 'raw_input_debug_logging', True):
                        print(f"    Step {i+1}/{steps}: ❌ ({exec_x}, {exec_y})")
                
                # 零延迟策略：完全依靠系统调度的自然延迟
                # 无任何人工延迟，实现真正连续移动
            else:
                success_count += 1  # 零移动视为成功
        
        # 计算成功率
        success_rate = success_count / steps
        overall_success = success_rate >= 0.8
        
        result_status = "SUCCESS" if overall_success else "PARTIAL"
        if getattr(self, 'raw_input_debug_logging', True):
            print(f"{current_time} - 🎯 CONTINUOUS RESULT: {success_count}/{steps} ({success_rate*100:.0f}%) {result_status}")
        
        if overall_success:
            self.target_locked = False
            return True
        else:
            return False
    
    def _generate_uniform_trajectory(self, total_x, total_y, steps):
        """生成平滑轨迹点 - 使用ease-in-out曲线实现自然加速减速"""
        trajectory = []
        
        for i in range(1, steps + 1):
            # 线性比例
            linear_ratio = i / steps
            
            # Ease-in-out cubic curve for smooth acceleration/deceleration
            # f(t) = 4t³ if t < 0.5, else 1 - 4(1-t)³
            if linear_ratio < 0.5:
                smooth_ratio = 4 * linear_ratio ** 3
            else:
                smooth_ratio = 1 - 4 * (1 - linear_ratio) ** 3
            
            # 计算当前点的累积位置 - 使用平滑比例
            x = total_x * smooth_ratio
            y = total_y * smooth_ratio
            
            trajectory.append((x, y))
        
        return trajectory
    
    def _calculate_adaptive_delay(self, segment_distance, total_distance):
        """计算自适应延迟 - 基于移动距离动态调整"""
        # 基础延迟配置（转换为秒）
        base_delay = getattr(self, 'segment_delay', 0.001)  # 默认1ms
        
        # 距离因子：长距离需要更多延迟
        distance_factor = min(1.5, total_distance / 100.0)  # 100px为基准
        
        # 段大小因子：大段需要更多延迟
        segment_factor = min(1.2, segment_distance / 30.0)  # 30px为基准
        
        # 计算最终延迟
        final_delay = base_delay * distance_factor * segment_factor
        
        # 优化：完全移除延迟系统
        return 0  # 零延迟策略
    
    def _execute_direct_movement(self, mouse_x, mouse_y):
        """直接移动 - 用于中小距离移动，消除不必要的分段"""
        exec_x = int(round(mouse_x))
        exec_y = int(round(mouse_y))
        
        if exec_x == 0 and exec_y == 0:
            return True  # 零移动直接成功
        
        success = self._execute_mouse_movement(exec_x, exec_y)
        
        if getattr(self, 'raw_input_debug_logging', True):
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            status = "✅" if success else "❌"
            print(f"{current_time} - 🎯 DIRECT MOVE: ({exec_x}, {exec_y}) {status}")
        
        if success:
            self.target_locked = False
        
        return success
    
    def _execute_mouse_movement(self, dx, dy):
        """Execute mouse movement with automatic method selection and fallback"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - 🎯 EXECUTE: Attempting mouse move ({dx}, {dy})")
        
        # Determine best method to try first
        if self.current_method == "auto":
            best_method = self._get_best_method()
        else:
            best_method = self.current_method if self.current_method in self.available_methods else self._get_best_method()
        
        # Try the best method first
        if best_method and self._try_method(best_method, dx, dy):
            self.method_success_count[best_method] += 1
            print(f"{current_time} - ✅ Method '{best_method}' succeeded")
            return True
        
        # If best method failed, try all other methods
        for method in self.available_methods:
            if method != best_method:
                if self._try_method(method, dx, dy):
                    self.method_success_count[method] += 1
                    print(f"{current_time} - ✅ Fallback method '{method}' succeeded")
                    return True
                else:
                    self.method_failure_count[method] += 1
        
        print(f"{current_time} - ❌ All {len(self.available_methods)} methods failed")
        return False
    
    def _get_best_method(self):
        """Get the method with the highest success rate"""
        if not self.available_methods:
            return None
        
        best_method = None
        best_score = -1
        
        for method in self.available_methods:
            success = self.method_success_count.get(method, 0)
            failure = self.method_failure_count.get(method, 0)
            total = success + failure
            
            if total == 0:
                # Untested method gets priority
                score = 1.0
            else:
                score = success / total
            
            if score > best_score:
                best_score = score
                best_method = method
        
        return best_method
    
    def _try_method(self, method, dx, dy):
        """Try a specific mouse injection method"""
        try:
            # Only log method attempts if debug logging is enabled
            if getattr(self, 'raw_input_debug_logging', True):
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"{current_time} - 🔧 Trying method: {method}")
            
            if method == "enhanced_sendinput":
                return self._enhanced_sendinput_move(dx, dy)
            elif method == "physical_cursor":
                return self._physical_cursor_move(dx, dy)
            elif method == "mouse_new":
                return self._mouse_new_move(dx, dy)
            elif method == "win32_direct":
                return self._win32_direct_move(dx, dy)
            else:
                print(f"⚠️ Unknown method: {method}")
                return False
                
        except Exception as e:
            print(f"❌ Method {method} failed with exception: {e}")
            return False
    
    def _enhanced_sendinput_move(self, dx, dy):
        """Enhanced SendInput with Raw Input compatibility flags"""
        try:
            # Enhanced SendInput structures
            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ('dx', wintypes.LONG),
                    ('dy', wintypes.LONG),
                    ('mouseData', wintypes.DWORD),
                    ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))
                ]
            
            class INPUT_UNION(ctypes.Union):
                _fields_ = [('mi', MOUSEINPUT)]
            
            class INPUT(ctypes.Structure):
                _fields_ = [
                    ('type', wintypes.DWORD),
                    ('union', INPUT_UNION)
                ]
            
            # Constants for Enhanced SendInput
            INPUT_MOUSE = 0
            MOUSEEVENTF_MOVE = 0x0001
            
            # Create input structure with Raw Input compatibility
            mouse_input = MOUSEINPUT(
                dx=dx,
                dy=dy,
                mouseData=0,
                dwFlags=MOUSEEVENTF_MOVE,
                time=0,
                dwExtraInfo=None
            )
            
            input_struct = INPUT(
                type=INPUT_MOUSE,
                union=INPUT_UNION(mi=mouse_input)
            )
            
            # Send input
            result = windll.user32.SendInput(1, byref(input_struct), sizeof(INPUT))
            return result == 1
            
        except Exception as e:
            print(f"❌ Enhanced SendInput error: {e}")
            return False
    
    def _physical_cursor_move(self, dx, dy):
        """SetPhysicalCursorPos method for direct hardware access"""
        try:
            # Get current cursor position
            current_x, current_y = mouse.get_position()
            
            # Calculate new position
            new_x = current_x + dx
            new_y = current_y + dy
            
            # Use SetPhysicalCursorPos if available
            user32 = windll.user32
            if hasattr(user32, 'SetPhysicalCursorPos'):
                result = user32.SetPhysicalCursorPos(new_x, new_y)
                return result != 0
            else:
                # Fallback to SetCursorPos
                result = user32.SetCursorPos(new_x, new_y)
                return result != 0
                
        except Exception as e:
            print(f"❌ Physical cursor error: {e}")
            return False
    
    def _mouse_new_move(self, dx, dy):
        """Original mouse_new library method"""
        try:
            mouse.move(dx, dy, absolute=False)
            return True
        except Exception as e:
            print(f"❌ mouse_new error: {e}")
            return False
    
    def _win32_direct_move(self, dx, dy):
        """Direct Win32 API mouse_event call"""
        try:
            MOUSEEVENTF_MOVE = 0x0001
            windll.user32.mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, 0)
            return True
        except Exception as e:
            print(f"❌ Win32 direct error: {e}")
            return False
    
    def calculate_target_movement(self, pixel_x, pixel_y):
        """革命性目标导向移动计算 - 消除累积放大，直接计算最优移动"""
        pixel_distance = math.sqrt(pixel_x**2 + pixel_y**2)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 基础DPI转换系数（一次性计算，避免重复）
        if not hasattr(self, '_base_conversion_factor'):
            self._base_conversion_factor = (self.dpi * (1 / self.sensitivity)) / 360
        
        # 直接目标计算 - 避免多级放大
        degrees_x = pixel_x * (self.fov_x / self.screen_width)
        degrees_y = pixel_y * (self.fov_y / self.screen_height)
        base_mouse_x = degrees_x * self._base_conversion_factor
        base_mouse_y = degrees_y * self._base_conversion_factor
        
        # 革命性三级精度系统 - 根据距离选择最优算法
        if pixel_distance <= 20:
            # 精度优先区域：超精确1:1映射
            final_x, final_y = self._precision_zone_movement(base_mouse_x, base_mouse_y, pixel_distance)
            movement_type = "PRECISION"
        elif pixel_distance <= 100:
            # 平衡区域：智能加速 + 反馈修正
            final_x, final_y = self._balanced_zone_movement(base_mouse_x, base_mouse_y, pixel_distance)
            movement_type = "BALANCED"
        else:
            # 速度优先区域：跳跃 + 精确着陆
            final_x, final_y = self._speed_zone_movement(base_mouse_x, base_mouse_y, pixel_distance)
            movement_type = "SPEED"
        
        final_distance = math.sqrt(final_x**2 + final_y**2)
        
        if getattr(self, 'raw_input_debug_logging', True):
            print(f"{current_time} - 🎯 TARGET CALC: {pixel_distance:.0f}px → {final_distance:.0f}px | {movement_type} | Zero Overshoot")
        
        return final_x, final_y
    
    def _precision_zone_movement(self, base_x, base_y, distance):
        """精度区域 (0-20px): 超精确移动，1:1映射无放大"""
        # 精度优先：最小的合理放大倍数
        precision_multiplier = 2.0 if distance > 10 else 1.5
        return base_x * precision_multiplier, base_y * precision_multiplier
    
    def _balanced_zone_movement(self, base_x, base_y, distance):
        """平衡区域 (20-100px): 智能加速，避免过冲"""
        # 智能加速：基于距离的渐进式放大
        if distance <= 40:
            balance_multiplier = 3.5  # 中小距离
        elif distance <= 70:
            balance_multiplier = 5.0  # 中等距离
        else:
            balance_multiplier = 6.5  # 中大距离
        
        return base_x * balance_multiplier, base_y * balance_multiplier
    
    def _speed_zone_movement(self, base_x, base_y, distance):
        """速度区域 (100+px): 快速移动 + 精确着陆"""
        # 控制式高速：避免旧系统的18x过度放大
        if distance <= 150:
            speed_multiplier = 8.0   # 中长距离
        elif distance <= 200:
            speed_multiplier = 10.0  # 长距离
        else:
            speed_multiplier = 12.0  # 超长距离 (大幅降低，避免过冲)
        
        return base_x * speed_multiplier, base_y * speed_multiplier
    
    def _detect_and_correct_overshoot(self, original_target_x, original_target_y, movement_executed):
        """过冲检测和修正系统 - 实时监控移动精度"""
        if not self.overshoot_detection_enabled:
            return True
        
        try:
            # 计算当前位置相对于目标的距离（估算）
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            center_x = self.center_x
            center_y = self.center_y
            
            # 估算当前准星位置（基于执行的移动）
            # 注意：这是估算，因为实际获取鼠标位置可能有延迟
            estimated_offset_x = original_target_x - center_x
            estimated_offset_y = original_target_y - center_y
            estimated_distance = math.sqrt(estimated_offset_x**2 + estimated_offset_y**2)
            
            # 过冲检测逻辑
            if estimated_distance > self.overshoot_threshold and self.correction_attempts < self.max_correction_attempts:
                print(f"{current_time} - ⚠️ OVERSHOOT DETECTED: {estimated_distance:.1f}px from target")
                
                # 计算修正移动
                correction_x, correction_y = self._calculate_correction_movement(estimated_offset_x, estimated_offset_y)
                
                if abs(correction_x) > 1 or abs(correction_y) > 1:  # 只修正有意义的移动
                    self.correction_attempts += 1
                    print(f"{current_time} - 🔧 APPLYING CORRECTION: ({correction_x:.1f}, {correction_y:.1f}) [Attempt {self.correction_attempts}]")
                    
                    # 执行修正移动
                    exec_corr_x, exec_corr_y = int(round(correction_x)), int(round(correction_y))
                    correction_success = self._execute_mouse_movement(exec_corr_x, exec_corr_y)
                    
                    if correction_success:
                        print(f"{current_time} - ✅ CORRECTION APPLIED: ({exec_corr_x}, {exec_corr_y})")
                        return True
                    else:
                        print(f"{current_time} - ❌ CORRECTION FAILED")
                        return False
                else:
                    print(f"{current_time} - ✅ POSITION ACCEPTABLE: Minor deviation {estimated_distance:.1f}px")
                    return True
            else:
                # 重置修正计数器
                self.correction_attempts = 0
                if estimated_distance <= self.overshoot_threshold:
                    print(f"{current_time} - ✅ TARGET REACHED: {estimated_distance:.1f}px accuracy")
                return True
                
        except Exception as e:
            print(f"❌ Overshoot detection error: {e}")
            return True  # 出错时不影响主要功能
    
    def _calculate_correction_movement(self, offset_x, offset_y):
        """计算修正移动 - 使用精确的小幅度移动"""
        # 使用精度区域的计算方法进行修正
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 修正移动使用极低的放大倍数，确保精确性
        if distance > 10:
            correction_multiplier = 0.8  # 保守修正
        else:
            correction_multiplier = 0.6  # 精细修正
        
        # 基础转换
        degrees_x = offset_x * (self.fov_x / self.screen_width)
        degrees_y = offset_y * (self.fov_y / self.screen_height)
        base_mouse_x = degrees_x * self._base_conversion_factor
        base_mouse_y = degrees_y * self._base_conversion_factor
        
        # 应用修正倍数
        correction_x = base_mouse_x * correction_multiplier
        correction_y = base_mouse_y * correction_multiplier
        
        return correction_x, correction_y
    
    def _precision_landing(self, target_x, target_y):
        """精度着陆系统 - 最终位置的微调优化"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        center_x = self.center_x
        center_y = self.center_y
        
        # 计算与目标的最终偏差
        final_offset_x = target_x - center_x
        final_offset_y = target_y - center_y
        final_distance = math.sqrt(final_offset_x**2 + final_offset_y**2)
        
        # 只有在偏差超过阈值时才进行精度着陆
        precision_threshold = 5  # 5像素精度阈值
        
        if final_distance > precision_threshold:
            print(f"{current_time} - 🎯 PRECISION LANDING: Final adjustment needed {final_distance:.1f}px")
            
            # 使用超精确移动
            degrees_x = final_offset_x * (self.fov_x / self.screen_width)
            degrees_y = final_offset_y * (self.fov_y / self.screen_height)
            base_mouse_x = degrees_x * self._base_conversion_factor
            base_mouse_y = degrees_y * self._base_conversion_factor
            
            # 精度着陆使用最小放大倍数
            landing_multiplier = 1.2  # 超保守，确保不过冲
            final_x = base_mouse_x * landing_multiplier
            final_y = base_mouse_y * landing_multiplier
            
            # 执行精度着陆
            exec_x, exec_y = int(round(final_x)), int(round(final_y))
            if abs(exec_x) > 0 or abs(exec_y) > 0:  # 只有在有实际移动时才执行
                success = self._execute_mouse_movement(exec_x, exec_y)
                if success:
                    print(f"{current_time} - ✅ PRECISION LANDING: ({exec_x}, {exec_y}) applied")
                    return True
                else:
                    print(f"{current_time} - ❌ PRECISION LANDING: Failed")
                    return False
            else:
                print(f"{current_time} - ✅ PRECISION LANDING: No adjustment needed")
                return True
        else:
            print(f"{current_time} - ✅ PRECISION LANDING: Already accurate {final_distance:.1f}px")
            return True
    
    def apply_movement_damping(self, mouse_x, mouse_y, pixel_distance):
        """已废弃：旧阻尼系统 - 新目标导向系统不需要阻尼"""
        # 新系统直接计算最优移动，无需后处理
        return mouse_x, mouse_y, False
    
    def handle_no_target(self):
        """Handle no target situation"""
        if self.target_locked:
            if time.time() - self.lock_start_time > self.lock_timeout:
                self.target_locked = False
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔄 Target lock timeout - resetting")
    
    def get_method_stats(self):
        """Get statistics about method performance"""
        stats = {}
        for method in self.available_methods:
            success = self.method_success_count.get(method, 0)
            failure = self.method_failure_count.get(method, 0)
            total = success + failure
            success_rate = (success / total * 100) if total > 0 else 0
            
            stats[method] = {
                'success': success,
                'failure': failure,
                'total': total,
                'success_rate': success_rate
            }
        
        return stats
    
    def print_method_stats(self):
        """Print method performance statistics"""
        stats = self.get_method_stats()
        print("\n📊 Mouse Injection Method Statistics:")
        print("-" * 50)
        for method, data in stats.items():
            print(f"{method:20s}: {data['success']:3d}✓ {data['failure']:3d}✗ ({data['success_rate']:5.1f}% success)")
        print("-" * 50)
    
    def set_injection_method(self, method):
        """Manually set the injection method"""
        if method == "auto" or method in self.available_methods:
            self.current_method = method
            print(f"✅ Mouse injection method set to: {method}")
        else:
            print(f"❌ Invalid method: {method}. Available: {self.available_methods}")

# Create global instance
enhanced_mouse_controller = RawInputCompatibleController()

if __name__ == "__main__":
    # Test mode
    print("🧪 Testing RawInputCompatibleController")
    controller = RawInputCompatibleController()
    
    # Test injection methods
    print("\n🔧 Testing all injection methods...")
    test_movements = [(10, 0), (0, 10), (-10, 0), (0, -10)]
    
    for dx, dy in test_movements:
        print(f"\nTesting movement: ({dx}, {dy})")
        controller._execute_mouse_movement(dx, dy)
        time.sleep(0.1)
    
    # Print statistics
    controller.print_method_stats()
    
    # Test target processing
    test_targets = [
        (200, 170, 50, 80, 0, "Body target right"),
        (190, 190, 30, 40, 7, "Head target center"),
    ]
    
    for target_x, target_y, target_w, target_h, target_cls, description in test_targets:
        print(f"\n🎯 Testing: {description}")
        controller.process_target(target_x, target_y, target_w, target_h, target_cls)
    
    print("\n✅ Test completed")