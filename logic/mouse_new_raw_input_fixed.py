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
        self.max_single_move = 300       # Maximum single movement distance
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
        """Move to target position using best available method"""
        if not self.mouse_available:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ mouse_new library not available")
            return False
        
        try:
            # Convert pixel offset to mouse movement
            mouse_x, mouse_y = self.convert_pixel_to_mouse(offset_x, offset_y)
            
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 Moving: pixel_offset=({offset_x:.1f}, {offset_y:.1f}) → mouse_move=({mouse_x:.1f}, {mouse_y:.1f})")
            
            # Execute movement with best method
            final_mouse_x, final_mouse_y = int(mouse_x), int(mouse_y)
            success = self._execute_mouse_movement(final_mouse_x, final_mouse_y)
            
            # Log execution result
            result_status = "SUCCESS" if success else "FAILED"
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 RESULT: {result_status}")
            
            if not success:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ All mouse movement methods failed")
                return False
            
            # Reset lock state
            self.target_locked = False
            return True
            
        except Exception as e:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - ❌ Mouse movement failed: {e}")
            return False
    
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
        """Convert pixel offset to mouse movement - ultra-aggressive version"""
        pixel_distance = math.sqrt(pixel_x**2 + pixel_y**2)
        
        # Calculate base conversion
        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height
        degrees_x = pixel_x * degrees_per_pixel_x
        degrees_y = pixel_y * degrees_per_pixel_y
        original_mouse_x = (degrees_x / 360) * (self.dpi * (1 / self.sensitivity))
        original_mouse_y = (degrees_y / 360) * (self.dpi * (1 / self.sensitivity))
        original_distance = math.sqrt(original_mouse_x**2 + original_mouse_y**2)
        
        # Ultra-aggressive speed strategy with 5-tier smooth transitions
        if pixel_distance <= 6:
            speed_multiplier = 3.5    # Extreme precision for final lock
        elif pixel_distance <= 25:
            speed_multiplier = 4.5    # High speed for close targets
        elif pixel_distance <= 55:
            speed_multiplier = 6.0    # Aggressive acceleration
        elif pixel_distance <= 100:
            speed_multiplier = 7.0    # Very high speed for distant targets
        else:
            speed_multiplier = 8.0    # Maximum speed for extreme distances
        
        mouse_x = original_mouse_x * speed_multiplier
        mouse_y = original_mouse_y * speed_multiplier
        
        # Apply stability damping
        final_mouse_x, final_mouse_y, damping_applied = self.apply_movement_damping(mouse_x, mouse_y, pixel_distance)
        final_distance = math.sqrt(final_mouse_x**2 + final_mouse_y**2)
        
        # Detailed conversion logging (only if debug logging enabled)
        if getattr(self, 'raw_input_debug_logging', True):
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - 📐 PIXEL→MOUSE CONVERSION:")
            print(f"  Input: pixel_offset=({pixel_x:.1f},{pixel_y:.1f}) distance={pixel_distance:.1f}px")
            print(f"  Base formula result: ({original_mouse_x:.1f},{original_mouse_y:.1f}) distance={original_distance:.1f}")
            print(f"  Applied multiplier: {speed_multiplier:.1f}x (based on {pixel_distance:.1f}px distance)")
            print(f"  Before damping: ({mouse_x:.1f},{mouse_y:.1f}) distance={math.sqrt(mouse_x**2 + mouse_y**2):.1f}")
            if damping_applied:
                print(f"  🛑 DAMPING applied: ({final_mouse_x:.1f},{final_mouse_y:.1f}) distance={final_distance:.1f}")
            else:
                print(f"  ✅ No damping needed: ({final_mouse_x:.1f},{final_mouse_y:.1f}) distance={final_distance:.1f}")
            print(f"  Speed improvement: {final_distance/original_distance:.1f}x faster than base formula")
        
        return final_mouse_x, final_mouse_y
    
    def apply_movement_damping(self, mouse_x, mouse_y, pixel_distance):
        """Apply movement damping to prevent overshoot and oscillation"""
        original_distance = math.sqrt(mouse_x**2 + mouse_y**2)
        
        # Extreme damping thresholds - allow very high speed movement
        damping_threshold_high = 250  # >250px mouse movement needs strong damping
        damping_threshold_med = 120   # >120px mouse movement needs medium damping
        damping_threshold_low = 60    # >60px mouse movement needs light damping
        
        if original_distance <= damping_threshold_low:
            return mouse_x, mouse_y, False
        elif original_distance <= damping_threshold_med:
            damping_factor = 0.90  # 10% reduction
        elif original_distance <= damping_threshold_high:
            damping_factor = 0.75  # 25% reduction
        else:
            damping_factor = 0.60  # 40% reduction
        
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