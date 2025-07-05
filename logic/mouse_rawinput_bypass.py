"""
Raw Input绕过鼠标控制器
使用低级鼠标钩子和相对移动来绕过Raw Input限制
专门解决游戏拦截鼠标绝对移动的问题
"""

import math
import time
import ctypes
from ctypes import wintypes, windll, byref
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
MOUSEEVENTF_MOVE = 0x0001
HC_ACTION = 0
WM_MOUSEMOVE = 0x0200
WH_MOUSE_LL = 14

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class RawInputBypassMouse:
    """Raw Input绕过鼠标控制器 - 使用相对移动模拟绝对移动"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        # 鼠标灵敏度配置
        self.dpi = getattr(cfg, 'mouse_dpi', 1600)
        self.sensitivity = getattr(cfg, 'mouse_sensitivity', 2.0)
        
        # 计算移动比例 (像素到鼠标计数的转换)
        # 一般来说: 鼠标计数 = 像素 * (DPI / 屏幕DPI) / 灵敏度
        # Windows标准DPI = 96
        base_ratio = (self.dpi / 96.0) / self.sensitivity
        ratio_adjustment = getattr(cfg, 'mouse_rawinput_move_ratio', 1.0)
        self.move_ratio = base_ratio * ratio_adjustment
        
        logger.info("🎯 Raw Input Bypass Mouse: 相对移动绕过Raw Input")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        logger.info(f"🔧 鼠标参数: DPI={self.dpi}, 灵敏度={self.sensitivity}, 移动比例={self.move_ratio:.3f}")
        logger.info("💡 使用相对移动模拟绝对移动，绕过Raw Input拦截")
    
    def update_detection_window_offset(self):
        """计算检测窗口偏移"""
        if cfg.Bettercam_capture:
            offset = capture.calculate_screen_offset()
            self.detection_window_left = offset[0]
            self.detection_window_top = offset[1]
        elif cfg.mss_capture:
            offset = capture.calculate_mss_offset()
            self.detection_window_left = offset[0]
            self.detection_window_top = offset[1]
        else:
            primary_width, primary_height = capture.get_primary_display_resolution()
            self.detection_window_left = int(primary_width / 2 - self.screen_width / 2)
            self.detection_window_top = int(primary_height / 2 - self.screen_height / 2)
    
    def detection_to_screen_coordinates(self, detection_x, detection_y):
        """检测坐标转屏幕坐标"""
        screen_x = self.detection_window_left + detection_x
        screen_y = self.detection_window_top + detection_y
        return int(screen_x), int(screen_y)
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """移动到目标 - Raw Input绕过版本"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用Raw Input绕过移动
        success = self.raw_input_bypass_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ Raw Input绕过移动成功")
        else:
            logger.error(f"❌ Raw Input绕过移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def raw_input_bypass_move(self, target_x, target_y):
        """Raw Input绕过移动实现"""
        try:
            # 获取当前鼠标位置
            current_x, current_y = self.get_current_mouse_position()
            
            # 计算需要移动的像素距离
            pixel_delta_x = target_x - current_x
            pixel_delta_y = target_y - current_y
            
            # 计算距离
            distance = math.sqrt(pixel_delta_x**2 + pixel_delta_y**2)
            
            # 如果距离很小，不需要移动
            if distance < 2:
                logger.info(f"🎯 目标已在当前位置附近: {distance:.1f}px")
                return True
            
            logger.info(f"🎯 计算移动: 当前({current_x}, {current_y}) -> 目标({target_x}, {target_y})")
            logger.info(f"🎯 像素偏移: ({pixel_delta_x}, {pixel_delta_y}) 距离{distance:.1f}px")
            
            # 转换为鼠标相对移动量
            # 这里使用经验公式，可能需要根据实际情况调整
            mouse_delta_x = int(pixel_delta_x * self.move_ratio)
            mouse_delta_y = int(pixel_delta_y * self.move_ratio)
            
            logger.info(f"🎯 鼠标移动量: ({mouse_delta_x}, {mouse_delta_y})")
            
            start_time = time.perf_counter()
            
            # 方法1: 使用mouse_event相对移动
            success = self.mouse_event_relative_move(mouse_delta_x, mouse_delta_y)
            
            if not success:
                # 方法2: 多步小幅度移动
                success = self.step_by_step_move(mouse_delta_x, mouse_delta_y)
            
            move_time = (time.perf_counter() - start_time) * 1000
            
            if success:
                logger.info(f"🚀 Raw Input绕过移动: 鼠标偏移({mouse_delta_x}, {mouse_delta_y}) [耗时{move_time:.2f}ms]")
                return True
            else:
                logger.error(f"❌ Raw Input绕过移动失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ Raw Input绕过移动异常: {e}")
            return False
    
    def mouse_event_relative_move(self, delta_x, delta_y):
        """使用mouse_event的相对移动"""
        try:
            # 限制单次移动的最大值，避免游戏忽略大幅度移动
            max_move = 100
            
            if abs(delta_x) > max_move or abs(delta_y) > max_move:
                # 分步移动
                steps = max(abs(delta_x) // max_move, abs(delta_y) // max_move) + 1
                step_x = delta_x // steps
                step_y = delta_y // steps
                
                logger.info(f"🔄 分步移动: {steps}步, 每步({step_x}, {step_y})")
                
                for i in range(steps):
                    # 最后一步移动剩余的距离
                    if i == steps - 1:
                        remaining_x = delta_x - step_x * i
                        remaining_y = delta_y - step_y * i
                        windll.user32.mouse_event(MOUSEEVENTF_MOVE, remaining_x, remaining_y, 0, 0)
                    else:
                        windll.user32.mouse_event(MOUSEEVENTF_MOVE, step_x, step_y, 0, 0)
                    
                    # 短暂延迟，让游戏处理每步移动
                    time.sleep(0.001)
            else:
                # 单步移动
                windll.user32.mouse_event(MOUSEEVENTF_MOVE, delta_x, delta_y, 0, 0)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ mouse_event相对移动失败: {e}")
            return False
    
    def step_by_step_move(self, delta_x, delta_y):
        """逐步小幅度移动"""
        try:
            # 将移动分解为更小的步骤
            max_step = 5
            total_steps = max(abs(delta_x), abs(delta_y))
            
            if total_steps <= max_step:
                # 单步移动
                windll.user32.mouse_event(MOUSEEVENTF_MOVE, delta_x, delta_y, 0, 0)
                return True
            
            # 多步移动
            steps = total_steps // max_step + 1
            step_x = delta_x / steps
            step_y = delta_y / steps
            
            logger.info(f"🔄 逐步移动: {steps}步, 每步({step_x:.1f}, {step_y:.1f})")
            
            accumulated_x = 0
            accumulated_y = 0
            
            for i in range(steps):
                # 计算当前步骤应该移动的距离
                target_x = (i + 1) * step_x
                target_y = (i + 1) * step_y
                
                # 计算实际需要移动的距离
                actual_x = int(target_x - accumulated_x)
                actual_y = int(target_y - accumulated_y)
                
                if actual_x != 0 or actual_y != 0:
                    windll.user32.mouse_event(MOUSEEVENTF_MOVE, actual_x, actual_y, 0, 0)
                    accumulated_x += actual_x
                    accumulated_y += actual_y
                
                # 短暂延迟
                time.sleep(0.002)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 逐步移动失败: {e}")
            return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            point = POINT()
            result = windll.user32.GetCursorPos(byref(point))
            if result:
                return (point.x, point.y)
            else:
                return (0, 0)
        except Exception as e:
            logger.error(f"❌ 获取鼠标位置失败: {e}")
            return (0, 0)
    
    def get_shooting_key_state(self):
        """检查射击键状态"""
        if not WIN32_AVAILABLE:
            return False
            
        if not hasattr(cfg, 'hotkey_targeting_list'):
            return False
            
        for key_name in cfg.hotkey_targeting_list:
            key_code = Buttons.KEY_CODES.get(key_name.strip())
            if key_code:
                key_state = win32api.GetAsyncKeyState(key_code) if not cfg.mouse_lock_target else win32api.GetKeyState(key_code)
                if key_state < 0:
                    return True
        return False
    
    def update_settings(self):
        """更新设置"""
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 重新获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        # 更新移动参数
        self.dpi = getattr(cfg, 'mouse_dpi', 1600)
        self.sensitivity = getattr(cfg, 'mouse_sensitivity', 2.0)
        self.move_ratio = (self.dpi / 96.0) / self.sensitivity
        
        logger.info("🔄 Raw Input Bypass Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        logger.info("🔄 Raw Input Bypass Mouse清理完成")

# 创建全局实例
mouse = RawInputBypassMouse()