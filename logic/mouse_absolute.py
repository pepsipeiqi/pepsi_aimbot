"""
绝对移动鼠标控制器
使用mouse_new模块实现屏幕绝对坐标移动
将检测窗口内的坐标转换为屏幕绝对坐标，然后直接移动到目标位置
"""

import math
import time

from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# 尝试导入Windows API，如果失败则在非Windows环境中使用备用方案
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("win32api not available - running in compatibility mode")

# 导入mouse_new模块实现绝对移动
import sys
import os
mouse_new_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mouse_new')
if mouse_new_path not in sys.path:
    sys.path.insert(0, mouse_new_path)

# 确保导入的是mouse_new目录下的mouse模块
try:
    import mouse as mouse_new
    # 验证导入的模块是否有move函数
    if not hasattr(mouse_new, 'move'):
        logger.error("导入的mouse模块没有move函数，尝试重新导入")
        # 如果有冲突，直接导入具体的函数
        from mouse import move as mouse_move, get_position as mouse_get_position
        mouse_new = None
    else:
        logger.info("mouse_new模块导入成功")
except Exception as e:
    logger.error(f"mouse_new模块导入失败: {e}")
    mouse_new = None
    # 尝试直接导入函数
    try:
        from mouse import move as mouse_move, get_position as mouse_get_position
        logger.info("直接导入mouse函数成功")
    except Exception as e2:
        logger.error(f"直接导入mouse函数也失败: {e2}")
        mouse_move = None
        mouse_get_position = None

class AbsoluteMouse:
    """绝对移动鼠标控制器 - 简单直接的绝对坐标移动"""
    
    def __init__(self):
        self.initialize_settings()
        logger.info("🎯 AbsoluteMouse initialized - 使用绝对坐标移动")
        logger.info("="*80)
        logger.info("🚀 绝对移动系统启动: 检测坐标 -> 屏幕绝对坐标 -> 直接移动")
        logger.info("🔧 坐标转换: 检测窗口坐标 + 窗口偏移 = 屏幕绝对坐标")
        logger.info("⚡ 移动方式: mouse_new.move(x, y, absolute=True)")
        logger.info("🎯 预期效果: 直接移动到目标位置，无需相对移动计算")
        logger.info("="*80)
    
    def initialize_settings(self):
        """初始化基本设置"""
        # 屏幕和检测窗口设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 获取检测窗口在屏幕上的偏移位置
        self.update_detection_window_offset()
        
        # 安全设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)  # 屏幕像素单位
        self.min_move_distance = 2  # 最小移动距离，避免微小抖动
        
        # 移动历史记录（用于调试）
        self.last_movement_time = 0
        self.movement_count = 0
        
        logger.info(f"🎯 窗口设置: 检测窗口 {self.screen_width}x{self.screen_height}")
        logger.info(f"🎯 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
    
    def update_detection_window_offset(self):
        """更新检测窗口在屏幕上的偏移位置"""
        # 根据配置的捕获方式计算偏移
        if cfg.Bettercam_capture:
            # Bettercam使用calculate_screen_offset
            offset = capture.calculate_screen_offset()
            self.detection_window_left = offset[0]
            self.detection_window_top = offset[1]
        elif cfg.mss_capture:
            # MSS使用calculate_mss_offset
            offset = capture.calculate_mss_offset()
            self.detection_window_left = offset[0]
            self.detection_window_top = offset[1]
        else:
            # 默认计算方式：屏幕中心 - 检测窗口尺寸的一半
            primary_width, primary_height = capture.get_primary_display_resolution()
            self.detection_window_left = int(primary_width / 2 - self.screen_width / 2)
            self.detection_window_top = int(primary_height / 2 - self.screen_height / 2)
        
        logger.info(f"🔧 检测窗口偏移更新: ({self.detection_window_left}, {self.detection_window_top})")
    
    def detection_to_screen_coordinates(self, detection_x, detection_y):
        """
        将检测窗口内的坐标转换为屏幕绝对坐标
        
        Args:
            detection_x: 检测窗口内的X坐标
            detection_y: 检测窗口内的Y坐标
            
        Returns:
            (screen_x, screen_y): 屏幕绝对坐标
        """
        screen_x = self.detection_window_left + detection_x
        screen_y = self.detection_window_top + detection_y
        
        return int(screen_x), int(screen_y)
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """
        移动鼠标到目标位置 - 使用绝对坐标移动
        
        Args:
            target_x: 目标在检测窗口内的X坐标
            target_y: 目标在检测窗口内的Y坐标
            target_velocity: 目标移动速度（暂未使用）
            is_head_target: 是否为头部目标
            
        Returns:
            bool: 移动是否成功
        """
        # 计算距离检测窗口中心的偏移
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        pixel_distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 检查是否需要移动
        if pixel_distance < self.min_move_distance:
            logger.info(f"🎯 目标已在精度范围内: {pixel_distance:.1f}px")
            return True
        
        # 安全检查：限制过大的移动距离
        if pixel_distance > self.max_move_distance:
            logger.warning(f"⚠️ 移动距离过大: {pixel_distance:.1f}px > {self.max_move_distance}px，限制移动")
            scale = self.max_move_distance / pixel_distance
            target_x = self.center_x + offset_x * scale
            target_y = self.center_y + offset_y * scale
            pixel_distance = self.max_move_distance
        
        # 转换为屏幕绝对坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        # 记录移动信息
        target_type = "HEAD" if is_head_target else "BODY"
        self.movement_count += 1
        
        logger.info(f"🎯 绝对移动 #{self.movement_count}: {target_type}")
        logger.info(f"   检测坐标: ({target_x:.1f}, {target_y:.1f})")
        logger.info(f"   屏幕坐标: ({screen_x}, {screen_y})")
        logger.info(f"   移动距离: {pixel_distance:.1f}px")
        
        # 执行绝对移动
        success = self.execute_absolute_move(screen_x, screen_y)
        
        if success:
            self.last_movement_time = time.time()
            logger.info(f"✅ 绝对移动成功: 鼠标移动到屏幕坐标 ({screen_x}, {screen_y})")
        else:
            logger.error(f"❌ 绝对移动失败: 无法移动到 ({screen_x}, {screen_y})")
        
        # 可视化目标线（如果启用）
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def execute_absolute_move(self, screen_x, screen_y):
        """
        执行屏幕绝对坐标移动
        
        Args:
            screen_x: 屏幕绝对X坐标
            screen_y: 屏幕绝对Y坐标
            
        Returns:
            bool: 移动是否成功
        """
        try:
            # 优先使用mouse_new模块的绝对移动功能
            if mouse_new and hasattr(mouse_new, 'move'):
                mouse_new.move(screen_x, screen_y, absolute=True, duration=0)
                return True
            elif 'mouse_move' in globals() and mouse_move:
                mouse_move(screen_x, screen_y, absolute=True, duration=0)
                return True
            else:
                raise Exception("mouse模块的move函数不可用")
        except Exception as e:
            logger.error(f"❌ mouse_new绝对移动失败: {e}")
            
            # 备用方案：使用Windows API直接设置光标位置
            try:
                import ctypes
                ctypes.windll.user32.SetCursorPos(screen_x, screen_y)
                logger.info("✅ 使用Windows API备用移动成功")
                return True
            except Exception as e2:
                logger.error(f"❌ Windows API备用移动也失败: {e2}")
                return False
    
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
    
    def get_current_mouse_position(self):
        """获取当前鼠标的屏幕绝对坐标"""
        try:
            if mouse_new and hasattr(mouse_new, 'get_position'):
                return mouse_new.get_position()
            elif 'mouse_get_position' in globals() and mouse_get_position:
                return mouse_get_position()
            else:
                raise Exception("mouse模块的get_position函数不可用")
        except:
            # 备用方案：使用Windows API
            try:
                import ctypes
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                
                point = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
                return (point.x, point.y)
            except Exception as e:
                logger.error(f"获取鼠标位置失败: {e}")
                return (0, 0)
    
    def update_settings(self):
        """更新设置（热重载）"""
        logger.info("🔄 更新绝对移动鼠标设置")
        
        # 更新基本设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 更新检测窗口偏移
        self.update_detection_window_offset()
        
        # 更新限制
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)
        
        logger.info(f"🔄 设置更新完成: 窗口{self.screen_width}x{self.screen_height}, 偏移({self.detection_window_left}, {self.detection_window_top})")
    
    def cleanup(self):
        """清理资源"""
        logger.info("🔄 绝对移动鼠标控制器清理完成")


# 创建全局绝对移动鼠标控制器实例
mouse = AbsoluteMouse()