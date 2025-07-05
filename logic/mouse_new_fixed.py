"""
修复版的鼠标控制器 - 解决Raw Input游戏问题

这个版本使用原有的硬件驱动系统（GHub/MouseControl等），
可以绕过Raw Input限制，在FPS游戏中正常工作。

修复原理：
- 问题：mouse_new库使用标准Windows API，被Raw Input游戏忽略  
- 解决：使用硬件驱动（DLL），直接在驱动级别控制鼠标移动
- 结果：保持新系统的简化逻辑，底层使用游戏兼容的驱动
"""

import sys
import os
import time
import math

def load_hardware_driver():
    """加载硬件驱动系统 - 可以绕过Raw Input限制"""
    try:
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 添加mouse系统到路径
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        print(f"Loading hardware mouse drivers from: {project_root}")
        
        # 导入原有的鼠标控制系统
        from mouse.mouse_controller.mouse_controller import MouseController
        
        # 初始化鼠标控制器
        controller = MouseController()
        
        # 自动初始化最佳驱动
        if controller.initialize_driver():
            driver_info = controller.get_driver_info()
            print(f"✅ Hardware driver loaded: {driver_info['type']}")
            print(f"✅ Driver available: {driver_info['available']}")
            return controller
        else:
            print(f"❌ Failed to initialize hardware drivers")
            available = controller.get_available_drivers()
            print(f"Available drivers: {available}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to load hardware driver: {e}")
        import traceback
        traceback.print_exc()
        return None

# 加载硬件驱动系统
mouse_lib = load_hardware_driver()

class FixedMouseController:
    """修复版的鼠标控制器"""
    
    def __init__(self):
        # 尝试导入基础配置
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
            # 默认配置
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
        self.aim_threshold = 3           # 超激进瞄准阈值，极精准锁定
        self.min_move_threshold = 1      # 极小移动阈值，允许精细微调
        self.max_single_move = 300       # 降低最大单次移动距离
        self.target_locked = False
        self.lock_start_time = 0
        self.lock_timeout = 1.5          # 缩短锁定超时时间
        
        # 检查硬件驱动状态
        self.mouse_available = mouse_lib is not None and mouse_lib.is_ready()
        
        print(f"🎯 FixedMouseController initialized")
        print(f"   Screen: {self.screen_width}x{self.screen_height}")
        print(f"   Hardware driver available: {'✅' if self.mouse_available else '❌'}")
        if mouse_lib and self.mouse_available:
            driver_info = mouse_lib.get_driver_info()
            print(f"   Using driver: {driver_info['type']}")
    
    def process_target(self, target_x, target_y, target_w=0, target_h=0, target_cls=0):
        """处理检测到的目标"""
        if not self.mouse_available:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Mouse library not available")
            return False
        
        # 精确瞄准胸口中心位置
        original_target_x, original_target_y = target_x, target_y
        if target_cls != 7:  # 不是头部目标时应用偏移
            # Y轴偏移：向上移动到胸口区域
            target_y += target_h * self.body_y_offset
            # X轴偏移：向右微调到正中心（修正左肩膀问题）
            target_x += target_w * 0.05  # 向右偏移5%
            
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📐 TRANSFORM OFFSET: "
                  f"original=({original_target_x:.1f},{original_target_y:.1f}) → "
                  f"adjusted=({target_x:.1f},{target_y:.1f}) | "
                  f"body_offset={self.body_y_offset} x_adjust=5%")
        else:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📐 TRANSFORM OFFSET: "
                  f"HEAD target - no offset applied ({target_x:.1f},{target_y:.1f})")
        
        # 计算距离中心的偏移
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        target_type = "HEAD" if target_cls == 7 else "BODY"
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - 📐 PIXEL OFFSET: "
              f"target=({target_x:.1f},{target_y:.1f}) center=({self.center_x:.1f},{self.center_y:.1f}) → "
              f"offset=({offset_x:.1f},{offset_y:.1f}) distance={distance:.1f}px")
        print(f"{current_time} - 🎯 Processing {target_type} target: ({target_x:.1f}, {target_y:.1f}), distance={distance:.1f}px")
        
        # 检查是否需要移动
        if distance <= self.aim_threshold:
            if not self.target_locked:
                self.target_locked = True
                self.lock_start_time = time.time()
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔒 Target locked! Distance: {distance:.1f}px")
            return True
        
        # 检查是否移动距离过小（避免微小抖动）
        if distance <= self.min_move_threshold:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔄 Movement too small ({distance:.1f}px), ignoring to prevent jitter")
            return True
        
        # 需要移动到目标
        return self.move_to_target(offset_x, offset_y, target_cls)
    
    def move_to_target(self, offset_x, offset_y, target_cls):
        """移动到目标位置"""
        if not self.mouse_available:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Hardware driver not available")
            return False
        
        try:
            # 检查是否需要渐进式移动
            distance = math.sqrt(offset_x**2 + offset_y**2)
            progressive_threshold = 100  # 超过100px使用渐进式移动
            
            if distance > progressive_threshold:
                return self.progressive_move_to_target(offset_x, offset_y, target_cls)
            else:
                return self.single_move_to_target(offset_x, offset_y, target_cls)
            
        except Exception as e:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - ❌ Mouse movement failed: {e}")
            print(f"{current_time} - ❌ Driver type: {type(mouse_lib)}")
            print(f"{current_time} - ❌ Driver ready: {mouse_lib.is_ready() if mouse_lib else 'None'}")
            return False
    
    def single_move_to_target(self, offset_x, offset_y, target_cls):
        """单次移动到目标位置"""
        # 限制单次移动距离
        distance = math.sqrt(offset_x**2 + offset_y**2)
        if distance > self.max_single_move:
            scale = self.max_single_move / distance
            offset_x *= scale
            offset_y *= scale
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔧 Movement scaled: {distance:.1f}px → {self.max_single_move}px")
        
        # 转换为鼠标移动
        mouse_x, mouse_y = self.convert_pixel_to_mouse(offset_x, offset_y)
        
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 Moving: pixel_offset=({offset_x:.1f}, {offset_y:.1f}) → mouse_move=({mouse_x:.1f}, {mouse_y:.1f})")
        
        # 鼠标执行前日志
        final_mouse_x, final_mouse_y = int(mouse_x), int(mouse_y)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 EXECUTE: move_relative({final_mouse_x}, {final_mouse_y})")
        
        # 执行移动（使用硬件驱动相对移动）
        success = mouse_lib.move_relative(final_mouse_x, final_mouse_y)
        
        # 执行结果日志
        result_status = "SUCCESS" if success else "FAILED"
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 RESULT: {result_status}")
        
        if not success:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Hardware driver move_relative failed")
            return False
        
        # 重置锁定状态
        self.target_locked = False
        
        return True
    
    def progressive_move_to_target(self, offset_x, offset_y, target_cls):
        """渐进式移动到目标位置 - 将大移动分解为多个步骤"""
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 计算移动步数 (每步最多80px)
        max_step_size = 80
        steps = max(2, int(distance / max_step_size))
        
        step_x = offset_x / steps
        step_y = offset_y / steps
        
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🚶 PROGRESSIVE MOVE: {distance:.1f}px in {steps} steps of ({step_x:.1f}, {step_y:.1f})")
        
        # 执行每一步
        for step in range(steps):
            # 最后一步使用剩余的精确距离
            if step == steps - 1:
                remaining_x = offset_x - (step_x * step)
                remaining_y = offset_y - (step_y * step)
                current_step_x, current_step_y = remaining_x, remaining_y
            else:
                current_step_x, current_step_y = step_x, step_y
            
            # 转换为鼠标移动
            mouse_x, mouse_y = self.convert_pixel_to_mouse(current_step_x, current_step_y)
            
            # 执行移动
            final_mouse_x, final_mouse_y = int(mouse_x), int(mouse_y)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🚶 Step {step+1}/{steps}: move_relative({final_mouse_x}, {final_mouse_y})")
            
            success = mouse_lib.move_relative(final_mouse_x, final_mouse_y)
            
            if not success:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Progressive move step {step+1} failed")
                return False
            
            # 步骤间短暂延迟以确保平滑移动
            if step < steps - 1:
                time.sleep(0.002)  # 2ms延迟
        
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ✅ PROGRESSIVE MOVE completed in {steps} steps")
        
        # 重置锁定状态
        self.target_locked = False
        
        return True
    
    def convert_pixel_to_mouse(self, pixel_x, pixel_y):
        """像素到鼠标移动转换 - 重新校准版本"""
        import time
        
        # 计算像素距离
        pixel_distance = math.sqrt(pixel_x**2 + pixel_y**2)
        
        # 首先计算原版转换结果作为基准
        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height
        degrees_x = pixel_x * degrees_per_pixel_x
        degrees_y = pixel_y * degrees_per_pixel_y
        original_mouse_x = (degrees_x / 360) * (self.dpi * (1 / self.sensitivity))
        original_mouse_y = (degrees_y / 360) * (self.dpi * (1 / self.sensitivity))
        original_distance = math.sqrt(original_mouse_x**2 + original_mouse_y**2)
        
        # 超激进速度策略 - 5档位平滑过渡，解决突然减速问题
        if pixel_distance <= 6:
            # 极近距离：精确锁定前最后冲刺
            speed_multiplier = 3.5
            mouse_x = original_mouse_x * speed_multiplier
            mouse_y = original_mouse_y * speed_multiplier
        elif pixel_distance <= 25:
            # 近距离：大幅加速，平滑过渡
            speed_multiplier = 4.5
            mouse_x = original_mouse_x * speed_multiplier
            mouse_y = original_mouse_y * speed_multiplier
        elif pixel_distance <= 55:
            # 中距离：激进加速，强力推进
            speed_multiplier = 6.0
            mouse_x = original_mouse_x * speed_multiplier
            mouse_y = original_mouse_y * speed_multiplier
        elif pixel_distance <= 100:
            # 远距离：超高速移动，快速接近
            speed_multiplier = 7.0
            mouse_x = original_mouse_x * speed_multiplier
            mouse_y = original_mouse_y * speed_multiplier
        else:
            # 极远距离：终极速度，瞬间到达
            speed_multiplier = 8.0
            mouse_x = original_mouse_x * speed_multiplier
            mouse_y = original_mouse_y * speed_multiplier
        
        # 应用稳定性阻尼
        final_mouse_x, final_mouse_y, damping_applied = self.apply_movement_damping(mouse_x, mouse_y, pixel_distance)
        
        final_distance = math.sqrt(final_mouse_x**2 + final_mouse_y**2)
        
        # 详细坐标转换日志
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
        """
        应用移动阻尼系统以防止过冲和震荡
        
        Returns:
            tuple: (damped_mouse_x, damped_mouse_y, damping_applied)
        """
        original_distance = math.sqrt(mouse_x**2 + mouse_y**2)
        
        # 极端阻尼阈值 - 允许超高速移动
        damping_threshold_high = 250  # 超过250px的鼠标移动需要强阻尼
        damping_threshold_med = 120   # 超过120px的鼠标移动需要中等阻尼
        damping_threshold_low = 60    # 超过60px的鼠标移动需要轻微阻尼
        
        if original_distance <= damping_threshold_low:
            # 小移动，无需阻尼
            return mouse_x, mouse_y, False
        elif original_distance <= damping_threshold_med:
            # 中等移动，轻微阻尼 (10%减少)
            damping_factor = 0.90
        elif original_distance <= damping_threshold_high:
            # 大移动，中等阻尼 (25%减少)
            damping_factor = 0.75
        else:
            # 极大移动，强阻尼 (40%减少)
            damping_factor = 0.60
        
        # 应用阻尼
        damped_x = mouse_x * damping_factor
        damped_y = mouse_y * damping_factor
        
        return damped_x, damped_y, True
    
    def handle_no_target(self):
        """处理无目标情况"""
        if self.target_locked:
            if time.time() - self.lock_start_time > self.lock_timeout:
                self.target_locked = False
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔄 Target lock timeout - resetting")
    
    def update_settings(self):
        """更新配置"""
        try:
            from logic.config_watcher import cfg
            self.screen_width = cfg.detection_window_width
            self.screen_height = cfg.detection_window_height
            self.center_x = self.screen_width / 2
            self.center_y = self.screen_height / 2
            self.dpi = cfg.mouse_dpi
            self.sensitivity = cfg.mouse_sensitivity
            self.fov_x = cfg.mouse_fov_width
            self.fov_y = cfg.mouse_fov_height
            self.body_y_offset = getattr(cfg, 'body_y_offset', -0.3)
            self.auto_aim = cfg.mouse_auto_aim
            self.auto_shoot = cfg.auto_shoot
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ✅ Settings updated")
        except Exception as e:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ⚠️ Settings update failed: {e}")

# 创建全局实例
fixed_mouse_controller = FixedMouseController()

if __name__ == "__main__":
    # 测试模式
    print("🧪 Testing FixedMouseController")
    controller = FixedMouseController()
    
    # 测试处理目标
    test_targets = [
        (200, 170, 50, 80, 0, "Body target right"),
        (190, 190, 30, 40, 7, "Head target center"),
    ]
    
    for target_x, target_y, target_w, target_h, target_cls, description in test_targets:
        print(f"\n🎯 Testing: {description}")
        controller.process_target(target_x, target_y, target_w, target_h, target_cls)
    
    print("\n✅ Test completed")