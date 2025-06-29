import win32con, win32api
import time
import math
import os
from collections import deque

from logic.config_watcher import cfg
from logic.visual import visuals
from logic.buttons import Buttons
from logic.logger import logger

# Import PID mouse controller for precision
from mouse.mouse_controller import MouseController, MovementAlgorithm

if cfg.mouse_rzr:
    from logic.rzctl import RZCONTROL

if cfg.arduino_move or cfg.arduino_shoot:
    from logic.arduino import arduino

class SimpleMouse:
    """简化的鼠标控制器 - 专注于快速精确的瞄准"""
    
    def __init__(self):
        self.initialize_settings()
        self.setup_hardware()
    
    def initialize_settings(self):
        """初始化基本设置 - 简化版本"""
        # 鼠标设置
        self.dpi = cfg.mouse_dpi
        self.sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        
        # 屏幕设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 智能动态移动速度设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 300)  # 最大单次移动距离
        
        # 简化的身体目标速度设置
        self.speed_ultra_far = 6.0   # 身体超远距离
        self.speed_far = 4.0         # 身体远距离
        self.speed_medium = 2.5      # 身体中距离
        self.speed_close = 1.5       # 身体近距离（提高了一些）
        
        # 距离阈值设置
        self.distance_threshold_ultra_far = 150  # 超远距离阈值
        self.distance_threshold_far = 100       # 远距离阈值
        self.distance_threshold_close = 50      # 近距离阈值
        
        # 简化移动设置 - 移除加速度限制
        self.movement_smoothing = False  # 禁用平滑以提高响应速度
        self.last_movement_time = 0
        
        logger.info(f"🎯 SimpleMouse initialized: DPI={self.dpi}, Sensitivity={self.sensitivity}")
        logger.info(f"🚀 简化速度系统: 身体(超远{self.speed_ultra_far}x, 远{self.speed_far}x, 中{self.speed_medium}x, 近{self.speed_close}x)")
        logger.info(f"🎯 头部专用速度: 8.0x/6.0x/4.0x/2.0x - 无加速度限制")
    
    def setup_hardware(self):
        """设置硬件驱动"""
        # Logitech G HUB
        if cfg.mouse_ghub:
            from logic.ghub import gHub
            self.ghub = gHub
            logger.info("🖱️ G HUB driver enabled")
        
        # Razer
        if cfg.mouse_rzr:
            dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rzctl.dll")
            self.rzr = RZCONTROL(dll_path)
            if not self.rzr.init():
                logger.error("Failed to initialize Razer driver")
            else:
                logger.info("🖱️ Razer driver enabled")
        
        # PID Controller for precision
        try:
            self.mouse_controller = MouseController()
            if self.mouse_controller.initialize_driver():
                self.pid_enabled = True
                logger.info("🎯 PID controller enabled")
            else:
                self.pid_enabled = False
                logger.warning("PID controller failed, using legacy methods")
        except Exception as e:
            logger.error(f"PID controller error: {e}")
            self.pid_enabled = False
            self.mouse_controller = None
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """简化直接的鼠标移动 - 无平滑无限制"""
        # 计算需要移动的像素距离
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        pixel_distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 提高最小移动阈值，减少微调
        min_distance = 5 if is_head_target else 3
        if pixel_distance < min_distance:
            logger.info(f"🎯 目标已在精度范围内: {pixel_distance:.1f}px")
            return True
        
        # 只在距离过大时才限制（放宽限制）
        if pixel_distance > self.max_move_distance * 1.5:  # 放宽限制
            scale = (self.max_move_distance * 1.5) / pixel_distance
            offset_x *= scale
            offset_y *= scale
            pixel_distance = self.max_move_distance * 1.5
        
        # 转换像素移动为鼠标移动
        mouse_x, mouse_y = self.convert_pixel_to_mouse_movement(offset_x, offset_y)
        
        # 直接使用基础速度，无任何限制
        speed_multiplier = self.calculate_dynamic_speed(pixel_distance, target_velocity, is_head_target)
        mouse_x *= speed_multiplier
        mouse_y *= speed_multiplier
        
        logger.info(f"🎯 直接移动: pixel_offset=({offset_x:.1f}, {offset_y:.1f}), "
                   f"mouse_move=({mouse_x:.1f}, {mouse_y:.1f}), distance={pixel_distance:.1f}px, speed={speed_multiplier:.1f}x")
        
        # 执行移动
        success = self.execute_mouse_move(int(mouse_x), int(mouse_y))
        
        # 可视化目标线
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    # 移除复杂的平滑算法，不再需要
    # 移除复杂的场景预设系统
    
    def calculate_dynamic_speed(self, distance, target_velocity=0, is_head_target=False):
        """简化的直接速度计算 - 无加速度限制"""
        # 头部目标使用更激进的速度
        if is_head_target:
            if distance > self.distance_threshold_ultra_far:
                base_speed = 8.0  # 头部超远距离极速
                mode = "🎯 头部超远模式"
            elif distance > self.distance_threshold_far:
                base_speed = 6.0  # 头部远距离快速
                mode = "🎯 头部远距离模式"
            elif distance > self.distance_threshold_close:
                base_speed = 4.0  # 头部中距离
                mode = "🎯 头部中距离模式"
            else:
                base_speed = 2.0  # 头部近距离精准
                mode = "🎯 头部近距离模式"
        else:
            # 身体目标使用相对保守的速度
            if distance > self.distance_threshold_ultra_far:
                base_speed = self.speed_ultra_far  # 6.0
                mode = "🚀 身体超远模式"
            elif distance > self.distance_threshold_far:
                base_speed = self.speed_far  # 4.0
                mode = "🚀 身体远距离模式"
            elif distance > self.distance_threshold_close:
                base_speed = self.speed_medium  # 2.5
                mode = "⚡ 身体中距离模式"
            else:
                base_speed = self.speed_close  # 1.2
                mode = "🎯 身体近距离模式"
        
        # 移动目标的轻微补偿（保持简单）
        if target_velocity > 100:
            base_speed *= 1.2  # 仅轻微增加
        
        logger.info(f"{mode}: {distance:.1f}px, 直接速度{base_speed:.1f}x")
        
        return base_speed
    
    def convert_pixel_to_mouse_movement(self, offset_x, offset_y):
        """将像素偏移转换为鼠标移动量"""
        # 计算每像素对应的角度
        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height
        
        # 转换为角度
        angle_x = offset_x * degrees_per_pixel_x
        angle_y = offset_y * degrees_per_pixel_y
        
        # 转换为鼠标移动单位
        mouse_x = (angle_x / 360) * (self.dpi * (1 / self.sensitivity))
        mouse_y = (angle_y / 360) * (self.dpi * (1 / self.sensitivity))
        
        return mouse_x, mouse_y
    
    def execute_mouse_move(self, x, y):
        """执行鼠标移动 - 支持多种驱动"""
        if x == 0 and y == 0:
            return True
        
        success = False
        
        # 优先使用PID控制器（最精确）
        if self.pid_enabled and self.mouse_controller:
            try:
                success = self.mouse_controller.move_relative(x, y)
                if success:
                    logger.info(f"✅ PID move successful: ({x}, {y})")
                    return True
                else:
                    logger.warning("PID move failed, falling back")
            except Exception as e:
                logger.error(f"PID move error: {e}, falling back")
        
        # 回退到其他驱动
        try:
            if cfg.mouse_ghub:
                self.ghub.mouse_xy(x, y)
                success = True
                logger.info(f"✅ G HUB move: ({x}, {y})")
            elif cfg.arduino_move:
                arduino.move(x, y)
                success = True
                logger.info(f"✅ Arduino move: ({x}, {y})")
            elif cfg.mouse_rzr:
                self.rzr.mouse_move(x, y, True)
                success = True
                logger.info(f"✅ Razer move: ({x}, {y})")
            else:
                # Windows API
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y, 0, 0)
                success = True
                logger.info(f"✅ Win32 move: ({x}, {y})")
        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            success = False
        
        return success
    
    def get_shooting_key_state(self):
        """检查射击键状态"""
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
        logger.info("🔄 Updating mouse settings")
        self.dpi = cfg.mouse_dpi
        self.sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 更新动态速度设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 300)
        
        # 重新加载基本设置
        self.sensitivity = cfg.mouse_sensitivity
        
        logger.info(f"🚀 简化速度系统更新: 身体(超远{self.speed_ultra_far}x, 远{self.speed_far}x, 中{self.speed_medium}x, 近{self.speed_close}x)")
        
        # 重新初始化PID控制器
        if hasattr(self, 'mouse_controller') and self.mouse_controller:
            try:
                self.mouse_controller.cleanup()
                self.mouse_controller = MouseController()
                if self.mouse_controller.initialize_driver():
                    self.pid_enabled = True
                    logger.info("🎯 PID controller reinitialized")
                else:
                    self.pid_enabled = False
            except Exception as e:
                logger.error(f"PID reinit error: {e}")
                self.pid_enabled = False
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'mouse_controller') and self.mouse_controller:
            try:
                self.mouse_controller.cleanup()
                logger.info("🎯 Mouse controller cleaned up")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

# 创建全局简化鼠标控制器实例
mouse = SimpleMouse()