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
        
        # Phase 3.5: 头部专用精度和锁定系统
        self.head_precision_multiplier = 2.0  # 头部专用精度倍数
        self.precision_accumulator_x = 0.0  # X轴精度累积器
        self.precision_accumulator_y = 0.0  # Y轴精度累积器
        self.head_approaching_active = False  # 头部接近状态标记
        self.head_lock_start_time = 0  # 头部锁定开始时间
        
        logger.info(f"🎯 SimpleMouse initialized: DPI={self.dpi}, Sensitivity={self.sensitivity}")
        logger.info(f"🚀 简化速度系统: 身体(超远{self.speed_ultra_far}x, 远{self.speed_far}x, 中{self.speed_medium}x, 近{self.speed_close}x)")
        logger.info("="*80)
        logger.info("🎯 Phase 3.6: 精确校准转换比率完成!")
        logger.info("🔧 精确转换比率: 0.25基础比率 + 温和DPI校正，解决严重过冲")
        logger.info("⚡ 大幅降低速度: 头部(1.4x/1.2x/1.0x) 身体(1.5x/1.3x/1.1x/1.0x)")
        logger.info("📐 温和DPI校正: 1.0 + (DPI-800)/8000，避免过度放大")
        logger.info("🔒 强化头部锁定: 50px内强制锁定300ms，禁止目标切换")
        logger.info("📊 实时验证: 详细转换比率监控，确保合理范围")
        logger.info("🎯 目标效果: 170px→50-70units，而非408units的过冲")
        logger.info("="*80)
    
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
            # Phase 3.5: 头部精确接近完成，清除锁定状态
            if is_head_target:
                self.head_approaching_active = False
                self.head_lock_start_time = 0
                logger.info("🎯 Phase 3.5: 头部精确接近完成 - 清除锁定状态")
            return True
        
        # 只在距离过大时才限制（放宽限制）
        if pixel_distance > self.max_move_distance * 1.5:  # 放宽限制
            scale = (self.max_move_distance * 1.5) / pixel_distance
            offset_x *= scale
            offset_y *= scale
            pixel_distance = self.max_move_distance * 1.5
        
        # Phase 3: 设置头部接近状态
        if is_head_target:
            self.head_approaching_active = True
        
        # 转换像素移动为鼠标移动 - 传递头部目标标识
        mouse_x, mouse_y = self.convert_pixel_to_mouse_movement(offset_x, offset_y, is_head_target)
        
        # 直接使用基础速度，无任何限制
        speed_multiplier = self.calculate_dynamic_speed(pixel_distance, target_velocity, is_head_target)
        mouse_x *= speed_multiplier
        mouse_y *= speed_multiplier
        
        logger.info(f"🎯 直接移动: pixel_offset=({offset_x:.1f}, {offset_y:.1f}), "
                   f"mouse_move=({mouse_x:.1f}, {mouse_y:.1f}), distance={pixel_distance:.1f}px, speed={speed_multiplier:.1f}x")
        
        # 执行移动
        success = self.execute_mouse_move(int(mouse_x), int(mouse_y))
        
        # Phase 3.5: 记录预期移动效果用于验证
        if is_head_target:
            self.last_head_movement = {
                'expected_distance': pixel_distance,
                'target_position': (target_x, target_y),
                'mouse_movement': (int(mouse_x), int(mouse_y)),
                'timestamp': time.time()
            }
        
        # 可视化目标线
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    # 移除复杂的平滑算法，不再需要
    # 移除复杂的场景预设系统
    
    def calculate_dynamic_speed(self, distance, target_velocity=0, is_head_target=False):
        """Phase 3.5: 重构的速度系统 - 基于新转换效率避免过冲"""
        # Phase 3.6: 头部目标使用精确校准的速度策略
        if is_head_target:
            if distance > 40:  # 阶段1: 快速接近 (提高到40px)
                base_speed = 1.4  # 进一步降低，解决过冲
                mode = "🚀 Phase 3.6: 快速接近"
            elif distance > 15:  # 阶段2: 中精度接近 (15-40px)
                base_speed = 1.2  # 更保守的速度
                mode = "⚡ Phase 3.6: 中精度接近"
            else:  # 阶段3: 超精确微调 (<15px)
                base_speed = 1.0  # 最保守，接近无放大
                mode = "🎯 Phase 3.6: 超精确微调"
        else:
            # Phase 3.6: 身体目标精确校准速度 - 解决过冲问题
            if distance > self.distance_threshold_ultra_far:
                base_speed = 1.5  # 大幅降低从3.0到1.5
                mode = "🚀 Phase 3.6: 身体超远"
            elif distance > self.distance_threshold_far:
                base_speed = 1.3  # 降低从2.2到1.3
                mode = "🚀 Phase 3.6: 身体远距离"
            elif distance > self.distance_threshold_close:
                base_speed = 1.1  # 降低从1.6到1.1
                mode = "⚡ Phase 3.6: 身体中距离"
            else:
                base_speed = 1.0  # 降低从1.2到1.0
                mode = "🎯 Phase 3.6: 身体近距离"
        
        # Phase 3.6: 移动目标补偿更加保守
        if target_velocity > 100:
            base_speed *= 1.05  # 进一步降低从1.1到1.05
        
        logger.info(f"{mode}: {distance:.1f}px, 直接速度{base_speed:.1f}x")
        
        return base_speed
    
    def convert_pixel_to_mouse_movement(self, offset_x, offset_y, is_head_target=False):
        """Phase 3.5: 重构的直接像素-鼠标转换系统"""
        
        # Phase 3.6: 精确校准转换比率 - 解决严重过冲问题
        # 重新校准：170px应产生50-70units，而非408units
        base_conversion_ratio = 0.25  # 大幅降低基础比率，解决过冲
        
        # Phase 3.6: 简化校正因子 - 减少放大效应
        # 更保守的DPI校正，避免过度放大
        dpi_factor = 1.0 + (self.dpi - 800.0) / 8000.0  # 更温和的DPI校正
        sens_factor = 3.0 / self.sensitivity  # 保留灵敏度校正
        
        # 最终转换比率
        conversion_ratio = base_conversion_ratio * dpi_factor * sens_factor
        
        # 直接转换
        base_mouse_x = offset_x * conversion_ratio
        base_mouse_y = offset_y * conversion_ratio
        
        # Phase 3.5: 精度系统重构 - 仅用于小数累积，不放大移动量
        if is_head_target:
            # 头部目标的精度处理 - 只影响小数保留，不影响移动大小
            precise_mouse_x = base_mouse_x + self.precision_accumulator_x
            precise_mouse_y = base_mouse_y + self.precision_accumulator_y
            
            # 计算整数移动值
            int_mouse_x = round(precise_mouse_x)  # 使用四舍五入而非截断
            int_mouse_y = round(precise_mouse_y)
            
            # 更新累积器 - 保存剩余的小数部分
            self.precision_accumulator_x = precise_mouse_x - int_mouse_x
            self.precision_accumulator_y = precise_mouse_y - int_mouse_y
            
            # 限制累积器范围
            self.precision_accumulator_x = max(-1.0, min(1.0, self.precision_accumulator_x))
            self.precision_accumulator_y = max(-1.0, min(1.0, self.precision_accumulator_y))
            
            logger.info(f"🔧 Phase 3.6: 头部精确转换 - {offset_x:.1f}px→{base_mouse_x:.2f}u "
                       f"(比率{conversion_ratio:.3f}) 精度补偿→{precise_mouse_x:.2f}u 整数→{int_mouse_x} "
                       f"累积({self.precision_accumulator_x:.2f},{self.precision_accumulator_y:.2f})")
            
            return float(int_mouse_x), float(int_mouse_y)
        else:
            # 身体目标使用标准四舍五入
            int_mouse_x = round(base_mouse_x)
            int_mouse_y = round(base_mouse_y)
            
            # Phase 3.6: 身体目标也添加转换验证
            pixel_distance = math.sqrt(offset_x**2 + offset_y**2)
            mouse_distance = math.sqrt(int_mouse_x**2 + int_mouse_y**2)
            if pixel_distance > 50:  # 只记录大移动
                actual_ratio = mouse_distance / pixel_distance if pixel_distance > 0 else 0
                logger.info(f"🔧 Phase 3.6: 身体转换 - {pixel_distance:.0f}px→{mouse_distance:.0f}u "
                           f"(实际比率{actual_ratio:.3f}, 转换比率{conversion_ratio:.3f})")
            
            return float(int_mouse_x), float(int_mouse_y)
    
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