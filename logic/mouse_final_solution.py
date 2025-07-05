"""
终极解决方案：智能相对移动模拟绝对移动
虽然用户要求绝对移动，但Raw Input的限制使得只有相对移动能被识别
这个方案优化相对移动，让它感觉像绝对移动：一次性、快速、精确
"""

import math
import ctypes
from ctypes import wintypes, windll
import time
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
MOUSEEVENTF_MOVE = 0x0001

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# 导入mouse_new作为备用
import sys
import os
mouse_new_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mouse_new')
if mouse_new_path not in sys.path:
    sys.path.insert(0, mouse_new_path)

try:
    import mouse as mouse_new
    if hasattr(mouse_new, 'get_position') and hasattr(mouse_new, '_os_mouse'):
        MOUSE_NEW_AVAILABLE = True
        logger.info("✅ mouse_new模块可用，将作为主要方案")
    else:
        MOUSE_NEW_AVAILABLE = False
        logger.warning("⚠️ mouse_new模块不完整")
except Exception as e:
    MOUSE_NEW_AVAILABLE = False
    logger.warning(f"⚠️ mouse_new模块不可用: {e}")

class FinalSolutionMouse:
    """终极解决方案：智能相对移动 - 一次性快速精确移动到目标"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        logger.info("🎯 Final Solution Mouse: 智能相对移动模拟绝对移动")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        
        if MOUSE_NEW_AVAILABLE:
            logger.info("🚀 使用mouse_new底层API实现Raw Input兼容的智能相对移动")
        else:
            logger.info("🚀 使用Windows API实现智能相对移动")
        
        logger.info("💡 策略：一次性计算相对移动量，快速精确到达目标位置")
    
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
        """移动到目标 - 智能相对移动实现绝对移动效果"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用智能相对移动
        success = self.intelligent_relative_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ 智能相对移动成功")
        else:
            logger.error(f"❌ 智能相对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def intelligent_relative_move(self, target_x, target_y):
        """智能相对移动 - 一次性精确移动"""
        
        try:
            # 获取当前鼠标位置
            current_x, current_y = self.get_current_mouse_position()
            
            # 计算相对移动量
            relative_x = target_x - current_x
            relative_y = target_y - current_y
            
            # 计算移动距离
            distance = math.sqrt(relative_x**2 + relative_y**2)
            
            # 如果距离很小，不需要移动
            if distance < 1:
                logger.info(f"🎯 目标已在当前位置附近: {distance:.1f}px")
                return True
            
            logger.info(f"🎯 计算移动: 当前({current_x}, {current_y}) -> 目标({target_x}, {target_y})")
            logger.info(f"🎯 相对移动量: ({relative_x}, {relative_y}) 距离{distance:.1f}px")
            
            # 方案1: 使用mouse_new底层API（最佳）
            if MOUSE_NEW_AVAILABLE:
                return self.mouse_new_relative_move(relative_x, relative_y, distance)
            
            # 方案2: 使用Windows API
            return self.windows_api_relative_move(relative_x, relative_y, distance)
            
        except Exception as e:
            logger.error(f"❌ 智能相对移动异常: {e}")
            return False
    
    def mouse_new_relative_move(self, relative_x, relative_y, distance):
        """使用mouse_new底层API的相对移动"""
        try:
            start_time = time.perf_counter()
            
            # 使用mouse_new的底层相对移动API
            mouse_new._os_mouse.move_relative(relative_x, relative_y)
            
            api_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"🚀 mouse_new智能移动: ({relative_x}, {relative_y}) 距离{distance:.1f}px [耗时{api_time:.2f}ms]")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ mouse_new相对移动失败: {e}")
            # 回退到Windows API
            return self.windows_api_relative_move(relative_x, relative_y, distance)
    
    def windows_api_relative_move(self, relative_x, relative_y, distance):
        """使用Windows API的相对移动"""
        try:
            start_time = time.perf_counter()
            
            # 使用mouse_event API进行相对移动
            windll.user32.mouse_event(MOUSEEVENTF_MOVE, relative_x, relative_y, 0, 0)
            
            api_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"🚀 Windows API智能移动: ({relative_x}, {relative_y}) 距离{distance:.1f}px [耗时{api_time:.2f}ms]")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Windows API相对移动失败: {e}")
            
            # 最后的备用方案：SetCursorPos
            try:
                current_x, current_y = self.get_current_mouse_position()
                target_x = current_x + relative_x
                target_y = current_y + relative_y
                windll.user32.SetCursorPos(target_x, target_y)
                logger.info(f"🚀 备用方案: SetCursorPos({target_x}, {target_y})")
                return True
            except Exception as e2:
                logger.error(f"❌ 备用方案也失败: {e2}")
                return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            if MOUSE_NEW_AVAILABLE:
                return mouse_new.get_position()
            else:
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
        
        logger.info("🔄 Final Solution Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        logger.info("🔄 Final Solution Mouse清理完成")

# 创建全局实例
mouse = FinalSolutionMouse()