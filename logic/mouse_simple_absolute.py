"""
简化版绝对移动鼠标控制器
直接使用Windows API，绕过复杂的驱动系统
专门解决Raw Input游戏鼠标响应问题
"""

import math
import time
import ctypes
from ctypes import wintypes, windll
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class SimpleAbsoluteMouse:
    """简化版绝对移动鼠标控制器 - 直接使用Windows API"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        logger.info("🎯 Simple Absolute Mouse: 直接Windows API绝对移动")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        logger.info("💡 使用SetCursorPos直接移动，Raw Input兼容")
    
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
        """移动到目标 - 简化版绝对移动"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用简化绝对移动
        success = self.simple_absolute_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ 简化绝对移动成功")
        else:
            logger.error(f"❌ 简化绝对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def simple_absolute_move(self, target_x, target_y):
        """简化绝对移动实现"""
        try:
            start_time = time.perf_counter()
            
            # 方法1: 直接使用SetCursorPos
            result = windll.user32.SetCursorPos(target_x, target_y)
            
            move_time = (time.perf_counter() - start_time) * 1000
            
            if result:
                logger.info(f"🚀 SetCursorPos移动: 目标({target_x}, {target_y}) [耗时{move_time:.2f}ms]")
                return True
            else:
                logger.error(f"❌ SetCursorPos失败")
                
                # 方法2: 尝试使用mouse_event
                return self.mouse_event_absolute_move(target_x, target_y)
                
        except Exception as e:
            logger.error(f"❌ 简化绝对移动异常: {e}")
            return False
    
    def mouse_event_absolute_move(self, target_x, target_y):
        """使用mouse_event的绝对移动"""
        try:
            start_time = time.perf_counter()
            
            # 转换坐标到0-65535范围 (mouse_event绝对坐标系统)
            abs_x = int((target_x * 65535) / self.screen_width_pixels)
            abs_y = int((target_y * 65535) / self.screen_height_pixels)
            
            # 使用mouse_event绝对移动
            windll.user32.mouse_event(
                MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE,
                abs_x, abs_y, 0, 0
            )
            
            move_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"🚀 mouse_event绝对移动: 目标({target_x}, {target_y}) 归一化({abs_x}, {abs_y}) [耗时{move_time:.2f}ms]")
            return True
            
        except Exception as e:
            logger.error(f"❌ mouse_event绝对移动失败: {e}")
            return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            point = ctypes.wintypes.POINT()
            result = windll.user32.GetCursorPos(ctypes.byref(point))
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
        
        logger.info("🔄 Simple Absolute Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        logger.info("🔄 Simple Absolute Mouse清理完成")

# 创建全局实例
mouse = SimpleAbsoluteMouse()