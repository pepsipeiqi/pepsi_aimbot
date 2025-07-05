"""
简化版绝对移动鼠标控制器
直接使用Windows API实现屏幕绝对坐标移动，避免模块导入冲突
"""

import math
import time
import ctypes
from ctypes import wintypes

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

class SimpleAbsoluteMouse:
    """简化版绝对移动鼠标控制器 - 直接使用Windows API"""
    
    def __init__(self):
        self.initialize_settings()
        self.setup_windows_api()
        logger.info("🎯 SimpleAbsoluteMouse initialized - 使用Windows API绝对移动")
        logger.info("="*80)
        logger.info("🚀 简化绝对移动系统: 检测坐标 -> 屏幕坐标 -> SetCursorPos")
        logger.info("🔧 坐标转换: 检测窗口坐标 + 窗口偏移 = 屏幕绝对坐标")
        logger.info("⚡ 移动方式: ctypes.windll.user32.SetCursorPos(x, y)")
        logger.info("🎯 优势: 直接、快速、无依赖冲突")
        logger.info("="*80)
    
    def setup_windows_api(self):
        """设置Windows API"""
        try:
            # 设置Windows API函数签名
            self.user32 = ctypes.windll.user32
            
            # GetCursorPos函数
            self.user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
            self.user32.GetCursorPos.restype = wintypes.BOOL
            
            # SetCursorPos函数
            self.user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            self.user32.SetCursorPos.restype = wintypes.BOOL
            
            logger.info("✅ Windows API设置成功")
            self.api_available = True
        except Exception as e:
            logger.error(f"❌ Windows API设置失败: {e}")
            self.api_available = False
    
    def initialize_settings(self):
        """初始化基本设置"""
        # 屏幕和检测窗口设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 获取检测窗口在屏幕上的偏移位置
        self.update_detection_window_offset()
        
        # 鼠标偏移校正（解决检测窗口与游戏窗口不匹配问题）
        self.mouse_offset_x = getattr(cfg, 'mouse_offset_x', 0)  # X轴偏移校正
        self.mouse_offset_y = getattr(cfg, 'mouse_offset_y', 0)  # Y轴偏移校正
        
        # 安全设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)  # 屏幕像素单位
        self.min_move_distance = 2  # 最小移动距离，避免微小抖动
        
        # 移动历史记录（用于调试）
        self.last_movement_time = 0
        self.movement_count = 0
        
        logger.info(f"🎯 窗口设置: 检测窗口 {self.screen_width}x{self.screen_height}")
        logger.info(f"🎯 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        
        if self.mouse_offset_x != 0 or self.mouse_offset_y != 0:
            logger.info(f"🔧 鼠标校正偏移: ({self.mouse_offset_x}, {self.mouse_offset_y})")
    
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
        # 基础坐标转换
        screen_x = self.detection_window_left + detection_x
        screen_y = self.detection_window_top + detection_y
        
        # 应用鼠标偏移校正
        screen_x += self.mouse_offset_x
        screen_y += self.mouse_offset_y
        
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
        
        logger.info(f"🎯 简化绝对移动 #{self.movement_count}: {target_type}")
        logger.info(f"   检测坐标: ({target_x:.1f}, {target_y:.1f})")
        logger.info(f"   屏幕坐标: ({screen_x}, {screen_y})")
        logger.info(f"   移动距离: {pixel_distance:.1f}px")
        
        # 执行绝对移动
        success = self.execute_absolute_move(screen_x, screen_y)
        
        if success:
            self.last_movement_time = time.time()
            logger.info(f"✅ 简化绝对移动成功: 鼠标移动到屏幕坐标 ({screen_x}, {screen_y})")
        else:
            logger.error(f"❌ 简化绝对移动失败: 无法移动到 ({screen_x}, {screen_y})")
        
        # 可视化目标线（如果启用）
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def execute_absolute_move(self, screen_x, screen_y):
        """
        执行屏幕绝对坐标移动 - 直接使用Windows API
        
        Args:
            screen_x: 屏幕绝对X坐标
            screen_y: 屏幕绝对Y坐标
            
        Returns:
            bool: 移动是否成功
        """
        if not self.api_available:
            logger.error("❌ Windows API不可用")
            return False
        
        try:
            # 直接使用SetCursorPos设置鼠标位置
            result = self.user32.SetCursorPos(screen_x, screen_y)
            return bool(result)
        except Exception as e:
            logger.error(f"❌ SetCursorPos执行失败: {e}")
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
        if not self.api_available:
            return (0, 0)
        
        try:
            point = wintypes.POINT()
            result = self.user32.GetCursorPos(ctypes.byref(point))
            if result:
                return (point.x, point.y)
            else:
                logger.error("❌ GetCursorPos返回False")
                return (0, 0)
        except Exception as e:
            logger.error(f"❌ 获取鼠标位置失败: {e}")
            return (0, 0)
    
    def update_settings(self):
        """更新设置（热重载）"""
        logger.info("🔄 更新简化绝对移动鼠标设置")
        
        # 更新基本设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 更新检测窗口偏移
        self.update_detection_window_offset()
        
        # 更新限制和偏移校正
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)
        self.mouse_offset_x = getattr(cfg, 'mouse_offset_x', 0)
        self.mouse_offset_y = getattr(cfg, 'mouse_offset_y', 0)
        
        logger.info(f"🔄 设置更新完成: 窗口{self.screen_width}x{self.screen_height}, 偏移({self.detection_window_left}, {self.detection_window_top})")
        
        if self.mouse_offset_x != 0 or self.mouse_offset_y != 0:
            logger.info(f"🔧 鼠标校正偏移: ({self.mouse_offset_x}, {self.mouse_offset_y})")
    
    def cleanup(self):
        """清理资源"""
        logger.info("🔄 简化绝对移动鼠标控制器清理完成")


# 创建全局简化绝对移动鼠标控制器实例
mouse = SimpleAbsoluteMouse()