"""
极简鼠标控制器
功能：直接移动到目标位置，无任何复杂逻辑
移除：锁定、预测、满意距离、所有复杂功能
"""

import math
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

# 导入mouse_new模块
import sys
import os
mouse_new_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mouse_new')
if mouse_new_path not in sys.path:
    sys.path.insert(0, mouse_new_path)

try:
    import mouse as mouse_new
    if hasattr(mouse_new, 'move') and hasattr(mouse_new, 'get_position'):
        logger.info("✅ mouse_new模块加载成功")
    else:
        mouse_new = None
        logger.error("❌ mouse_new模块缺少必要函数")
except Exception as e:
    logger.error(f"❌ mouse_new模块导入失败: {e}")
    mouse_new = None

class UltraSimpleMouse:
    """极简鼠标控制器 - 只做一件事：移动到目标位置"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        logger.info("🎯 UltraSimple Mouse: 直接移动到目标，无复杂逻辑")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
    
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
        """移动到目标 - 极简版本"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用Raw Input兼容的移动方式
        success = self.raw_input_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ 移动成功")
        else:
            logger.error(f"❌ 移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def raw_input_move(self, target_x, target_y):
        """Raw Input兼容的移动方式"""
        try:
            # 获取当前位置
            current_x, current_y = self.get_current_mouse_position()
            
            # 计算相对移动量
            relative_x = target_x - current_x
            relative_y = target_y - current_y
            
            # 距离检查
            distance = math.sqrt(relative_x**2 + relative_y**2)
            if distance < 1:  # 1像素内不移动
                return True
            
            logger.info(f"🚀 Raw Input移动: ({relative_x}, {relative_y}) 距离{distance:.1f}px")
            
            # 使用mouse_new底层API
            if mouse_new and hasattr(mouse_new, '_os_mouse') and hasattr(mouse_new._os_mouse, 'move_relative'):
                mouse_new._os_mouse.move_relative(relative_x, relative_y)
                return True
            else:
                # 备用方案：Windows API
                import ctypes
                ctypes.windll.user32.mouse_event(1, relative_x, relative_y, 0, 0)  # MOUSEEVENTF_MOVE=1
                return True
                
        except Exception as e:
            logger.error(f"❌ Raw Input移动失败: {e}")
            # 最终备用：SetCursorPos
            try:
                import ctypes
                ctypes.windll.user32.SetCursorPos(target_x, target_y)
                logger.info("✅ 使用SetCursorPos备用方案")
                return True
            except Exception as e2:
                logger.error(f"❌ 备用移动也失败: {e2}")
                return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            if mouse_new and hasattr(mouse_new, 'get_position'):
                return mouse_new.get_position()
            else:
                # Windows API备用
                import ctypes
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                
                point = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
                return (point.x, point.y)
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
        logger.info("🔄 UltraSimple Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        logger.info("🔄 UltraSimple Mouse清理完成")

# 创建全局实例
mouse = UltraSimpleMouse()