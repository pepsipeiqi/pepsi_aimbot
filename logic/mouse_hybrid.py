"""
混合移动鼠标控制器
计算绝对目标位置，但使用相对移动事件
解决游戏Raw Input导致的绝对移动无效问题
"""

import math
import time
import ctypes
from ctypes import wintypes

from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# 尝试导入Windows API
try:
    import win32api
    import win32con
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("win32api not available - running in compatibility mode")

class HybridMouse:
    """混合移动鼠标控制器 - 绝对目标计算 + 相对移动执行"""
    
    def __init__(self):
        self.initialize_settings()
        self.setup_windows_api()
        logger.info("🎯 HybridMouse initialized - 绝对计算+相对移动")
        logger.info("="*80)
        logger.info("🚀 混合移动系统: 绝对目标计算 -> 相对移动量 -> 相对移动事件")
        logger.info("🔧 解决Raw Input游戏: 计算到目标的相对移动量")
        logger.info("⚡ 移动方式: mouse_event(MOUSEEVENTF_MOVE, dx, dy)")
        logger.info("🎯 优势: 兼容Raw Input游戏，准心跟随移动")
        logger.info("="*80)
    
    def setup_windows_api(self):
        """设置Windows API"""
        try:
            self.user32 = ctypes.windll.user32
            
            # GetCursorPos函数
            self.user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
            self.user32.GetCursorPos.restype = wintypes.BOOL
            
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
        
        # 鼠标偏移校正
        self.mouse_offset_x = getattr(cfg, 'mouse_offset_x', 0)
        self.mouse_offset_y = getattr(cfg, 'mouse_offset_y', 0)
        
        # 移动设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)
        self.min_move_distance = 2
        
        # 相对移动缩放因子（可调节）
        self.relative_move_scale = getattr(cfg, 'relative_move_scale', 1.0)
        
        # 移动历史记录
        self.last_movement_time = 0
        self.movement_count = 0
        
        logger.info(f"🎯 窗口设置: 检测窗口 {self.screen_width}x{self.screen_height}")
        logger.info(f"🎯 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🎯 相对移动缩放: {self.relative_move_scale}")
        
        if self.mouse_offset_x != 0 or self.mouse_offset_y != 0:
            logger.info(f"🔧 鼠标校正偏移: ({self.mouse_offset_x}, {self.mouse_offset_y})")
    
    def update_detection_window_offset(self):
        """更新检测窗口在屏幕上的偏移位置"""
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
        
        logger.info(f"🔧 检测窗口偏移更新: ({self.detection_window_left}, {self.detection_window_top})")
    
    def detection_to_screen_coordinates(self, detection_x, detection_y):
        """将检测窗口内的坐标转换为屏幕绝对坐标"""
        screen_x = self.detection_window_left + detection_x + self.mouse_offset_x
        screen_y = self.detection_window_top + detection_y + self.mouse_offset_y
        return int(screen_x), int(screen_y)
    
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
                return (0, 0)
        except Exception as e:
            logger.error(f"❌ 获取鼠标位置失败: {e}")
            return (0, 0)
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """
        移动鼠标到目标位置 - 使用混合移动方式
        
        Args:
            target_x: 目标在检测窗口内的X坐标
            target_y: 目标在检测窗口内的Y坐标
            target_velocity: 目标移动速度（暂未使用）
            is_head_target: 是否为头部目标
            
        Returns:
            bool: 移动是否成功
        """
        # 1. 获取当前鼠标位置
        current_x, current_y = self.get_current_mouse_position()
        
        # 2. 计算目标的屏幕绝对坐标
        target_screen_x, target_screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        # 3. 计算需要的相对移动量
        relative_x = target_screen_x - current_x
        relative_y = target_screen_y - current_y
        pixel_distance = math.sqrt(relative_x**2 + relative_y**2)
        
        # 4. 检查是否需要移动
        if pixel_distance < self.min_move_distance:
            logger.info(f"🎯 目标已在精度范围内: {pixel_distance:.1f}px")
            return True
        
        # 5. 安全检查：限制过大的移动距离
        if pixel_distance > self.max_move_distance:
            logger.warning(f"⚠️ 移动距离过大: {pixel_distance:.1f}px > {self.max_move_distance}px，限制移动")
            scale = self.max_move_distance / pixel_distance
            relative_x *= scale
            relative_y *= scale
            pixel_distance = self.max_move_distance
        
        # 6. 应用缩放因子
        scaled_relative_x = relative_x * self.relative_move_scale
        scaled_relative_y = relative_y * self.relative_move_scale
        
        # 7. 记录移动信息
        target_type = "HEAD" if is_head_target else "BODY"
        self.movement_count += 1
        
        logger.info(f"🎯 混合移动 #{self.movement_count}: {target_type}")
        logger.info(f"   当前鼠标位置: ({current_x}, {current_y})")
        logger.info(f"   目标屏幕坐标: ({target_screen_x}, {target_screen_y})")
        logger.info(f"   相对移动量: ({relative_x:.1f}, {relative_y:.1f})")
        logger.info(f"   缩放后移动量: ({scaled_relative_x:.1f}, {scaled_relative_y:.1f})")
        logger.info(f"   移动距离: {pixel_distance:.1f}px")
        
        # 8. 执行相对移动
        success = self.execute_relative_move(int(scaled_relative_x), int(scaled_relative_y))
        
        if success:
            self.last_movement_time = time.time()
            logger.info(f"✅ 混合移动成功: 相对移动 ({int(scaled_relative_x)}, {int(scaled_relative_y)})")
        else:
            logger.error(f"❌ 混合移动失败")
        
        # 9. 可视化目标线
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def execute_relative_move(self, relative_x, relative_y):
        """
        执行相对移动 - 使用多种方法确保游戏响应
        
        Args:
            relative_x: 相对X移动量
            relative_y: 相对Y移动量
            
        Returns:
            bool: 移动是否成功
        """
        if relative_x == 0 and relative_y == 0:
            return True
        
        success = False
        
        try:
            # 方法1：Win32 API相对移动（最兼容Raw Input）
            if WIN32_AVAILABLE:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, relative_x, relative_y, 0, 0)
                success = True
                logger.info(f"✅ Win32相对移动: ({relative_x}, {relative_y})")
            
            # 方法2：如果配置了其他驱动，也尝试使用
            elif cfg.mouse_ghub:
                # G HUB可能需要特殊处理
                from logic.ghub import gHub
                gHub.mouse_xy(relative_x, relative_y)
                success = True
                logger.info(f"✅ G HUB相对移动: ({relative_x}, {relative_y})")
            
            elif cfg.arduino_move:
                # Arduino移动
                from logic.arduino import arduino
                arduino.move(relative_x, relative_y)
                success = True
                logger.info(f"✅ Arduino相对移动: ({relative_x}, {relative_y})")
            
            elif cfg.mouse_rzr:
                # Razer移动
                from logic.rzctl import RZCONTROL
                if hasattr(self, 'rzr'):
                    self.rzr.mouse_move(relative_x, relative_y, True)
                    success = True
                    logger.info(f"✅ Razer相对移动: ({relative_x}, {relative_y})")
            
            else:
                # 备用方案：直接使用ctypes
                ctypes.windll.user32.mouse_event(1, relative_x, relative_y, 0, 0)
                success = True
                logger.info(f"✅ ctypes相对移动: ({relative_x}, {relative_y})")
                
        except Exception as e:
            logger.error(f"❌ 相对移动执行失败: {e}")
            success = False
        
        return success
    
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
        """更新设置（热重载）"""
        logger.info("🔄 更新混合移动鼠标设置")
        
        # 更新基本设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 更新检测窗口偏移
        self.update_detection_window_offset()
        
        # 更新移动设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)
        self.mouse_offset_x = getattr(cfg, 'mouse_offset_x', 0)
        self.mouse_offset_y = getattr(cfg, 'mouse_offset_y', 0)
        self.relative_move_scale = getattr(cfg, 'relative_move_scale', 1.0)
        
        logger.info(f"🔄 设置更新完成: 窗口{self.screen_width}x{self.screen_height}")
        logger.info(f"🔄 偏移({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔄 缩放因子: {self.relative_move_scale}")
        
        if self.mouse_offset_x != 0 or self.mouse_offset_y != 0:
            logger.info(f"🔧 鼠标校正偏移: ({self.mouse_offset_x}, {self.mouse_offset_y})")
    
    def cleanup(self):
        """清理资源"""
        logger.info("🔄 混合移动鼠标控制器清理完成")


# 创建全局混合移动鼠标控制器实例
mouse = HybridMouse()