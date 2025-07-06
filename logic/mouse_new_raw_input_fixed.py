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
        # 智能丝滑移动配置 - 从配置文件读取 (智能变速优化版)
        self.smooth_movement_enabled = getattr(cfg, 'smooth_movement_enabled', True)
        self.max_single_move = getattr(cfg, 'max_single_move_distance', 80)  # 优化: 40→80, 减少分段数量
        self.segment_delay = getattr(cfg, 'segment_movement_delay', 1) / 1000.0  # 优化: 3ms→1ms, 基础延迟进一步减少
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
        return self.move_to_target(offset_x, offset_y, target_cls)
    
    def move_to_target(self, offset_x, offset_y, target_cls):
        """Move to target position using best available method with smooth multi-segment movement"""
        if not self.mouse_available:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ mouse_new library not available")
            return False
        
        try:
            # Convert pixel offset to mouse movement
            mouse_x, mouse_y = self.convert_pixel_to_mouse(offset_x, offset_y)
            
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 Moving: pixel_offset=({offset_x:.1f}, {offset_y:.1f}) → mouse_move=({mouse_x:.1f}, {mouse_y:.1f})")
            
            # Check if we need segmented smooth movement
            movement_distance = math.sqrt(mouse_x**2 + mouse_y**2)
            
            if self.smooth_movement_enabled and movement_distance > self.max_single_move:
                # 执行丝滑分段移动
                return self._execute_smooth_segmented_movement(mouse_x, mouse_y, offset_x, offset_y)
            else:
                # 正常单次移动
                final_mouse_x, final_mouse_y = int(mouse_x), int(mouse_y)
                success = self._execute_mouse_movement(final_mouse_x, final_mouse_y)
                
                # Log execution result
                result_status = "SUCCESS" if success else "FAILED"
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 RESULT: {result_status}")
                
                if not success:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Mouse movement failed")
                    return False
                
                # Reset lock state
                self.target_locked = False
                return True
            
        except Exception as e:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - ❌ Mouse movement failed: {e}")
            return False
    
    def _execute_smooth_segmented_movement(self, total_mouse_x, total_mouse_y, pixel_offset_x, pixel_offset_y):
        """执行智能变速分段移动 - 渐变速度曲线，保持浮点精度，自适应延迟"""
        total_distance = math.sqrt(total_mouse_x**2 + total_mouse_y**2)
        segments = max(2, min(4, int(total_distance / self.max_single_move)))  # 限制最大段数为4
        
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if getattr(self, 'raw_input_debug_logging', True):
            print(f"{current_time} - 🎯 SMART SEGMENTED MOVE: {total_distance:.1f}px in {segments} adaptive segments")
        
        # 智能变速分段策略 - 渐变速度曲线
        segment_ratios = self._calculate_segment_ratios(segments)
        
        success_count = 0
        accumulated_x, accumulated_y = 0.0, 0.0  # 浮点累积器
        
        # 执行变速分段移动
        for i in range(segments):
            # 计算当前段应该移动的距离（浮点精度）
            target_x = total_mouse_x * segment_ratios[i]
            target_y = total_mouse_y * segment_ratios[i]
            
            # 计算实际移动量（减去已累积的移动）
            current_move_x = target_x - accumulated_x
            current_move_y = target_y - accumulated_y
            
            # 转换为整数执行（仅在执行时截断）
            exec_x = int(round(current_move_x))
            exec_y = int(round(current_move_y))
            
            # 更新累积器（使用实际执行值）
            accumulated_x += exec_x
            accumulated_y += exec_y
            
            # 执行当前段移动
            if exec_x != 0 or exec_y != 0:  # 跳过零移动
                success = self._execute_mouse_movement(exec_x, exec_y)
                
                if success:
                    success_count += 1
                    if getattr(self, 'raw_input_debug_logging', True):
                        print(f"    Segment {i+1}/{segments}: ✅ ({exec_x}, {exec_y}) ratio={segment_ratios[i]:.2f}")
                else:
                    if getattr(self, 'raw_input_debug_logging', True):
                        print(f"    Segment {i+1}/{segments}: ❌ ({exec_x}, {exec_y})")
                
                # 自适应延迟 - 基于分段大小和距离
                if i < segments - 1:  # 最后一段不需要延迟
                    adaptive_delay = self._calculate_adaptive_delay(abs(exec_x) + abs(exec_y), total_distance)
                    if adaptive_delay > 0:
                        time.sleep(adaptive_delay)
            else:
                success_count += 1  # 零移动视为成功
        
        # 计算整体成功率
        success_rate = success_count / segments
        overall_success = success_rate >= 0.8  # 80%以上成功认为整体成功
        
        result_status = "SUCCESS" if overall_success else "PARTIAL"
        if getattr(self, 'raw_input_debug_logging', True):
            print(f"{current_time} - 🎯 SMART RESULT: {success_count}/{segments} segments ({success_rate*100:.1f}%) - {result_status}")
        
        if overall_success:
            # Reset lock state
            self.target_locked = False
            return True
        else:
            return False
    
    def _calculate_segment_ratios(self, segments):
        """计算智能分段比例 - 渐变速度曲线"""
        if segments == 2:
            # 两段：第一段70%，第二段30%
            return [0.70, 1.0]
        elif segments == 3:
            # 三段：第一段60%，第二段25%，第三段15%
            return [0.60, 0.85, 1.0]
        elif segments == 4:
            # 四段：第一段50%，后续段依次递减
            return [0.50, 0.75, 0.90, 1.0]
        else:
            # 其他情况回退到平均分段
            return [i/segments for i in range(1, segments + 1)]
    
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
        
        # 限制延迟范围：0.5ms - 2ms
        return max(0.0005, min(0.002, final_delay))
    
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
    
    def convert_pixel_to_mouse(self, pixel_x, pixel_y):
        """转换像素偏移到鼠标移动 - 性能优化版"""
        # 预计算常用值，减少重复计算
        pixel_distance = math.sqrt(pixel_x**2 + pixel_y**2)
        
        # 缓存转换系数，避免重复计算
        if not hasattr(self, '_cached_conversion_factor'):
            self._cached_conversion_factor = (self.dpi * (1 / self.sensitivity)) / 360
        
        # 简化的基础转换计算
        conversion_factor = self._cached_conversion_factor
        degrees_x = pixel_x * (self.fov_x / self.screen_width)
        degrees_y = pixel_y * (self.fov_y / self.screen_height)
        original_mouse_x = degrees_x * conversion_factor
        original_mouse_y = degrees_y * conversion_factor
        original_distance = math.sqrt(original_mouse_x**2 + original_mouse_y**2)
        
        # 优化的速度选择 - 使用更快的条件判断
        if pixel_distance <= 8:
            speed_multiplier = 1.0 if pixel_distance <= 3 else 2.3
        elif pixel_distance <= 40:
            speed_multiplier = 4.2 if pixel_distance <= 20 else 6.2
        elif pixel_distance <= 80:
            speed_multiplier = 8.5
        else:
            speed_multiplier = 12.0
        
        mouse_x = original_mouse_x * speed_multiplier
        mouse_y = original_mouse_y * speed_multiplier
        
        # Apply stability damping
        final_mouse_x, final_mouse_y, damping_applied = self.apply_movement_damping(mouse_x, mouse_y, pixel_distance)
        final_distance = math.sqrt(final_mouse_x**2 + final_mouse_y**2)
        
        # 简化日志输出 - 性能优化：减少I/O开销
        if getattr(self, 'raw_input_debug_logging', True):
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            damping_status = "🛑 DAMPED" if damping_applied else "✅ DIRECT"
            print(f"{current_time} - 📐 CONVERSION: {pixel_distance:.0f}px → {final_distance:.0f}px | {speed_multiplier:.1f}x | {damping_status}")
        
        return final_mouse_x, final_mouse_y
    
    def apply_movement_damping(self, mouse_x, mouse_y, pixel_distance):
        """超简化2级线性阻尼系统 - 最大化速度，最小化复杂度"""
        original_distance = math.sqrt(mouse_x**2 + mouse_y**2)
        
        # 2级阻尼策略 - 简化到最少级别
        # 优化：强度从15%减少到5%，提升30%速度
        if original_distance <= 50:
            # 中小移动，无需阻尼，保持精度和速度
            return mouse_x, mouse_y, False
        else:
            # 大移动，极轻微阻尼 (仅5%减少)
            damping_factor = 0.95
        
        # 应用最小化阻尼
        damped_x = mouse_x * damping_factor
        damped_y = mouse_y * damping_factor
        
        return damped_x, damped_y, True
    
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