"""
Raw Input兼容的绝对移动鼠标控制器
使用mouse驱动系统中的TrueAbsoluteController实现
解决Raw Input游戏中鼠标移动但准心不响应的问题
"""

import math
import time
from typing import Optional
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# 导入新的绝对移动控制器
from mouse.mouse_controller.mouse_controller import MouseController
from mouse.mouse_controller.true_absolute.true_absolute_controller import TrueAbsoluteController, TargetType
from mouse.mouse_controller.true_absolute.precision_coordinate_mapper import HardwareType

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class DriverAbsoluteMouse:
    """Raw Input兼容的绝对移动鼠标控制器"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 初始化鼠标控制器
        self.mouse_controller = None
        self.abs_controller = None
        self._initialized = False
        
        # 获取屏幕分辨率
        self.screen_width_pixels = capture.get_primary_display_resolution()[0]
        self.screen_height_pixels = capture.get_primary_display_resolution()[1]
        
        logger.info("🎯 Driver Absolute Mouse: 使用驱动绝对移动，Raw Input兼容")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        
        # 初始化绝对移动系统
        self.initialize_absolute_system()
    
    def initialize_absolute_system(self) -> bool:
        """初始化绝对移动系统"""
        try:
            # 1. 创建基础控制器
            self.mouse_controller = MouseController()
            if not self.mouse_controller.initialize_driver():
                logger.error("❌ 鼠标驱动初始化失败")
                return False
            
            # 2. 从配置获取参数
            dpi = getattr(cfg, 'mouse_dpi', 1600)
            sensitivity = getattr(cfg, 'mouse_sensitivity', 2.0)
            
            # 获取硬件类型配置
            hardware_type_str = getattr(cfg, 'mouse_hardware_type', 'MouseControl')
            hardware_type_mapping = {
                'MouseControl': HardwareType.MOUSE_CONTROL,
                'GHub': HardwareType.GHUB,
                'Logitech': HardwareType.LOGITECH,
                'Unknown': HardwareType.UNKNOWN
            }
            hardware_type = hardware_type_mapping.get(hardware_type_str, HardwareType.MOUSE_CONTROL)
            
            # 3. 创建绝对移动控制器
            self.abs_controller = TrueAbsoluteController(
                screen_width=self.screen_width_pixels,
                screen_height=self.screen_height_pixels,
                dpi=dpi,
                sensitivity=sensitivity,
                hardware_type=hardware_type
            )
            
            # 4. 设置驱动
            self.abs_controller.set_driver(self.mouse_controller.driver)
            
            self._initialized = True
            
            # 获取驱动信息进行调试
            driver_info = self.mouse_controller.driver.get_driver_info() if self.mouse_controller.driver else None
            driver_type = driver_info.get('type', 'Unknown') if driver_info else 'None'
            
            logger.info("✅ 绝对移动系统初始化成功")
            logger.info(f"🔧 参数: DPI={dpi}, 灵敏度={sensitivity}, 硬件类型={hardware_type_str}")
            logger.info(f"🎮 当前使用驱动: {driver_type}")
            
            # 警告：如果使用Mock驱动
            if driver_type == 'MockDriver':
                logger.warning("⚠️ 警告：当前使用模拟驱动，鼠标不会真实移动！")
                logger.warning("⚠️ 请检查：1) 运行权限 2) DLL文件 3) 硬件连接")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 绝对移动系统初始化失败: {e}")
            return False
    
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
        """移动到目标 - 使用驱动绝对移动"""
        if not self._initialized:
            logger.error("❌ 绝对移动系统未初始化")
            return False
        
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用驱动绝对移动
        success = self.driver_absolute_move(screen_x, screen_y, is_head_target)
        
        if success:
            logger.info(f"✅ 驱动绝对移动成功")
        else:
            logger.error(f"❌ 驱动绝对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def driver_absolute_move(self, target_x, target_y, is_head_target=False):
        """驱动绝对移动实现"""
        try:
            # 检查驱动类型，如果是Mock驱动则直接使用备用方案
            driver_info = self.mouse_controller.driver.get_driver_info() if self.mouse_controller.driver else None
            driver_type = driver_info.get('type', 'Unknown') if driver_info else 'None'
            
            if driver_type == 'MockDriver':
                logger.warning("🔄 检测到Mock驱动，使用Windows API备用方案")
                return self.fallback_move(target_x, target_y)
            
            # 选择目标类型
            if is_head_target:
                target_type = TargetType.HEAD  # 头部目标 - 最高精度
            else:
                # 从配置获取精度等级
                precision_level = getattr(cfg, 'mouse_precision_level', 'BODY')
                precision_mapping = {
                    'HEAD': TargetType.HEAD,
                    'BODY': TargetType.BODY,
                    'GENERAL': TargetType.GENERAL
                }
                target_type = precision_mapping.get(precision_level, TargetType.BODY)
            
            start_time = time.perf_counter()
            
            # 执行绝对移动
            result = self.abs_controller.move_to_absolute_position(target_x, target_y, target_type)
            
            move_time = (time.perf_counter() - start_time) * 1000
            
            # 检查结果
            if hasattr(result, 'result') and result.result.value == "success":
                logger.info(f"🚀 驱动绝对移动: 目标({target_x}, {target_y}) 类型={target_type.value} [耗时{move_time:.2f}ms]")
                return True
            else:
                logger.error(f"❌ 驱动绝对移动失败: {result}")
                return self.fallback_move(target_x, target_y)
                
        except Exception as e:
            logger.error(f"❌ 驱动绝对移动异常: {e}")
            
            # 备用方案：使用Windows API
            return self.fallback_move(target_x, target_y)
    
    def fallback_move(self, target_x, target_y):
        """备用移动方案"""
        try:
            import ctypes
            ctypes.windll.user32.SetCursorPos(target_x, target_y)
            logger.info(f"🚀 备用移动: SetCursorPos({target_x}, {target_y})")
            return True
        except Exception as e:
            logger.error(f"❌ 备用移动失败: {e}")
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
    
    def update_settings(self):
        """更新设置"""
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 重新获取屏幕分辨率
        self.screen_width_pixels = capture.get_primary_display_resolution()[0]
        self.screen_height_pixels = capture.get_primary_display_resolution()[1]
        
        # 重新初始化绝对移动系统
        if self._initialized:
            self.initialize_absolute_system()
        
        logger.info("🔄 Driver Absolute Mouse设置已更新")
    
    def cleanup(self):
        """清理资源"""
        if self.mouse_controller:
            self.mouse_controller.cleanup()
        self._initialized = False
        logger.info("🔄 Driver Absolute Mouse清理完成")

# 创建全局实例
mouse = DriverAbsoluteMouse()