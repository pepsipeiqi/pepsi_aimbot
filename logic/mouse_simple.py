import win32con, win32api
import time
import math
import os

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
        """初始化基本设置"""
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
        
        # 分段速度控制系统
        self.speed_far = 4.0    # 远距离(>100px): 极速接近
        self.speed_medium = 3.0 # 中距离(50-100px): 平衡移动
        self.speed_close = 2.0  # 近距离(<50px): 精准微调
        
        # 距离阀值设置
        self.distance_threshold_far = 100  # 远距离阀值
        self.distance_threshold_close = 50 # 近距离阀值
        
        logger.info(f"🎯 SimpleMouse initialized: DPI={self.dpi}, Sensitivity={self.sensitivity}")
        logger.info(f"🚀 智能速度系统: 远距离{self.speed_far}x, 中距离{self.speed_medium}x, 近距离{self.speed_close}x")
    
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
    
    def move_to_target(self, target_x, target_y):
        """移动鼠标到目标位置 - 核心移动逻辑"""
        # 计算需要移动的像素距离
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        pixel_distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 限制最大移动距离（防止跳跃过大）
        if pixel_distance > self.max_move_distance:
            scale = self.max_move_distance / pixel_distance
            offset_x *= scale
            offset_y *= scale
            pixel_distance = self.max_move_distance
            logger.info(f"🎯 Movement clamped to max distance: {self.max_move_distance}px")
        
        # 转换像素移动为鼠标移动
        mouse_x, mouse_y = self.convert_pixel_to_mouse_movement(offset_x, offset_y)
        
        # 智能动态速度控制
        speed_multiplier = self.calculate_dynamic_speed(pixel_distance)
        mouse_x *= speed_multiplier
        mouse_y *= speed_multiplier
        
        logger.info(f"🎯 Moving to target: pixel_offset=({offset_x:.1f}, {offset_y:.1f}), "
                   f"mouse_move=({mouse_x:.1f}, {mouse_y:.1f}), distance={pixel_distance:.1f}px, speed={speed_multiplier}x")
        
        # 执行移动
        self.execute_mouse_move(int(mouse_x), int(mouse_y))
        
        # 可视化目标线
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7)  # 假设是头部目标
    
    def calculate_dynamic_speed(self, distance):
        """根据目标距离智能计算移动速度"""
        if distance > self.distance_threshold_far:
            # 远距离：极速接近
            speed = self.speed_far
            logger.info(f"🚀 远距离模式: {distance:.1f}px, 使用{speed}x速度")
        elif distance > self.distance_threshold_close:
            # 中距离：平衡移动
            speed = self.speed_medium
            logger.info(f"⚡ 中距离模式: {distance:.1f}px, 使用{speed}x速度")
        else:
            # 近距离：精准微调
            speed = self.speed_close
            logger.info(f"🎯 近距离模式: {distance:.1f}px, 使用{speed}x速度")
        
        return speed
    
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
        logger.info(f"🚀 智能速度系统更新: 远距离{self.speed_far}x, 中距离{self.speed_medium}x, 近距离{self.speed_close}x")
        
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