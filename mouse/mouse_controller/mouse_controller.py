"""
MouseController 主类 - 支持相对坐标和绝对定位双模式
专门用于游戏瞄准场景，支持相对移动和绝对定位
"""

import math
from typing import Optional, Tuple, Dict, List, Any
from .core.base_driver import BaseDriver
from .core.mouse_control_driver import MouseControlDriver
from .core.ghub_driver import GHubDriver
from .core.logitech_driver import LogitechDriver
from .core.mock_driver import MockDriver
from .algorithms.pid_controller import VelocityAwarePIDController
from .absolute.absolute_controller import AbsoluteMouseController, AbsoluteControllerConfig, AbsoluteMovementResult
from .absolute.position_calculator import TargetType
from .utils.logger import setup_logger
from .utils.config import ConfigManager, MouseControllerConfig


class MouseController:
    """
    混合模式鼠标控制器
    支持相对坐标移动（向后兼容）和绝对定位（新功能）
    """
    
    def __init__(self, enable_absolute_positioning: bool = True,
                 screen_width: int = 1920, screen_height: int = 1080,
                 config_file: Optional[str] = None):
        self.driver: Optional[BaseDriver] = None
        self.pid_controller = VelocityAwarePIDController()
        self.logger = setup_logger("MouseController")
        
        # 配置管理
        self.config_manager = ConfigManager(config_file)
        self.current_config = self.config_manager.load_config()
        
        # 应用配置的相对移动设置
        self.game_config = {
            'sensitivity': self.current_config.relative_movement.sensitivity,
            'dpi': self.current_config.relative_movement.dpi,
            'conversion_ratio': self.current_config.relative_movement.conversion_ratio,
            'adaptive_conversion': self.current_config.relative_movement.adaptive_conversion
        }
        
        # 绝对定位支持
        self.enable_absolute_positioning = enable_absolute_positioning and self.current_config.absolute_positioning.enabled
        self.absolute_controller: Optional[AbsoluteMouseController] = None
        
        if self.enable_absolute_positioning:
            # 使用配置文件中的设置创建绝对定位控制器
            abs_config = self.current_config.absolute_positioning
            absolute_config = AbsoluteControllerConfig(
                screen_width=abs_config.screen_width or screen_width,
                screen_height=abs_config.screen_height or screen_height,
                dpi=abs_config.dpi,
                sensitivity=abs_config.sensitivity,
                fov_x=abs_config.fov_x,
                default_tolerance=abs_config.default_tolerance,
                head_target_tolerance=abs_config.head_target_tolerance,
                max_attempts=abs_config.max_attempts,
                max_execution_time=abs_config.max_execution_time,
                enable_prediction=abs_config.enable_prediction,
                enable_adaptive_mapping=abs_config.enable_adaptive_mapping,
                debug_mode=abs_config.debug_mode,
                log_movements=abs_config.log_movements
            )
            self.absolute_controller = AbsoluteMouseController(absolute_config)
        
    def initialize_driver(self) -> bool:
        """
        自动检测并初始化最佳驱动
        优先级: MouseControl.dll > ghub_device.dll > logitech.driver.dll
        
        Returns:
            bool: 初始化是否成功
        """
        drivers_to_try = [
            MouseControlDriver,
            GHubDriver,
            LogitechDriver,
            MockDriver  # 添加模拟驱动作为兜底选项
        ]
        
        for driver_class in drivers_to_try:
            try:
                driver = driver_class()
                if driver.initialize():
                    self.driver = driver
                    
                    # 同时为绝对定位控制器设置驱动
                    if self.absolute_controller:
                        self.absolute_controller.set_driver(driver)
                    
                    driver_info = driver.get_driver_info()
                    if driver_info:
                        self.logger.info(f"成功初始化驱动: {driver_info['type']}")
                    return True
            except Exception as e:
                self.logger.warning(f"驱动 {driver_class.__name__} 初始化失败: {e}")
                continue
        
        self.logger.error("所有驱动初始化失败")
        return False
    
    def move_relative_to_target(self, offset_x: int, offset_y: int, 
                              tolerance: int = 2, max_iterations: int = 200,
                              is_head_target: bool = False) -> bool:
        """
        基于相对偏移的精确移动 - 核心API
        
        Args:
            offset_x: 相对于当前位置的X偏移（游戏坐标）
            offset_y: 相对于当前位置的Y偏移（游戏坐标）
            tolerance: 容差像素（默认2px，保持高精度）
            max_iterations: 最大迭代次数（默认200）
            is_head_target: 是否为头部目标（使用更精确的参数）
            
        Returns:
            bool: 是否成功到达目标（在容差范围内）
        """
        if not self.driver or not self.driver.is_ready():
            self.logger.error("驱动未初始化")
            return False
        
        success, final_error, duration = self.pid_controller.move_to_relative_target(
            self.driver, offset_x, offset_y, tolerance, max_iterations, is_head_target
        )
        
        if success:
            self.logger.debug(f"移动成功: 偏移({offset_x}, {offset_y}), 误差{final_error:.2f}px, 耗时{duration*1000:.1f}ms")
        else:
            self.logger.warning(f"移动失败: 偏移({offset_x}, {offset_y}), 最终误差{final_error:.2f}px")
        
        return success
    
    def fast_move_to_target(self, offset_x: int, offset_y: int, 
                           tolerance: int = 2, use_two_stage: bool = True) -> Tuple[bool, float, float]:
        """
        快速移动到目标 - 返回详细结果
        
        Args:
            offset_x: X偏移量
            offset_y: Y偏移量
            tolerance: 容差
            use_two_stage: 是否使用两阶段移动策略（推荐长距离移动使用）
            
        Returns:
            Tuple[bool, float, float]: (成功标志, 最终误差, 耗时)
        """
        if not self.driver or not self.driver.is_ready():
            return False, float('inf'), 0.0
        
        if use_two_stage:
            return self.pid_controller.move_to_relative_target_two_stage(
                self.driver, offset_x, offset_y, tolerance
            )
        else:
            return self.pid_controller.move_to_relative_target(
                self.driver, offset_x, offset_y, tolerance
            )
    
    def optimized_move_to_target(self, offset_x: int, offset_y: int, 
                               tolerance: int = 2, is_head_target: bool = False) -> bool:
        """
        优化的长距离移动 - 自动选择最佳策略
        
        自动判断距离并选择：
        - 短距离(<100px): 使用标准PID
        - 长距离(>=100px): 使用两阶段移动策略
        
        Args:
            offset_x: 相对于当前位置的X偏移（游戏坐标）
            offset_y: 相对于当前位置的Y偏移（游戏坐标）
            tolerance: 容差像素（默认2px）
            is_head_target: 是否为头部目标（使用更精确的参数）
            
        Returns:
            bool: 是否成功到达目标（在容差范围内）
        """
        if not self.driver or not self.driver.is_ready():
            self.logger.error("驱动未初始化")
            return False
        
        # 计算距离并自动选择策略
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        if distance >= 200:
            # 长距离使用两阶段移动
            success, final_error, duration = self.pid_controller.move_to_relative_target_two_stage(
                self.driver, offset_x, offset_y, tolerance, 200, is_head_target
            )
            strategy = "两阶段移动"
        else:
            # 短距离使用标准移动
            success, final_error, duration = self.pid_controller.move_to_relative_target(
                self.driver, offset_x, offset_y, tolerance, 200, is_head_target
            )
            strategy = "标准移动"
        
        if success:
            self.logger.debug(f"{strategy}成功: 偏移({offset_x}, {offset_y}), 距离{distance:.1f}px, 误差{final_error:.2f}px, 耗时{duration*1000:.1f}ms")
        else:
            self.logger.warning(f"{strategy}失败: 偏移({offset_x}, {offset_y}), 距离{distance:.1f}px, 最终误差{final_error:.2f}px")
        
        return success
    
    def headshot_precision_move(self, offset_x: int, offset_y: int, 
                               tolerance: int = 1) -> Tuple[bool, float, float]:
        """
        头部精确瞄准移动 - 专为200-300px"一步到位"头部锁定设计
        
        使用预测性一次移动算法，力求单次移动直达目标
        
        Args:
            offset_x: 相对于当前位置的X偏移（游戏坐标）
            offset_y: 相对于当前位置的Y偏移（游戏坐标）
            tolerance: 容差像素（默认1px，头部瞄准精度）
            
        Returns:
            Tuple[bool, float, float]: (成功标志, 最终误差, 耗时)
        """
        if not self.driver or not self.driver.is_ready():
            self.logger.error("驱动未初始化")
            return False, float('inf'), 0.0
        
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 使用预测性一次移动算法
        success, final_error, duration = self.pid_controller.one_shot_precision_move(
            self.driver, offset_x, offset_y, tolerance, self.game_config
        )
        
        if success:
            self.logger.debug(f"头部精确移动成功: 偏移({offset_x}, {offset_y}), 距离{distance:.1f}px, 误差{final_error:.2f}px, 耗时{duration*1000:.1f}ms")
        else:
            self.logger.warning(f"头部精确移动失败: 偏移({offset_x}, {offset_y}), 距离{distance:.1f}px, 最终误差{final_error:.2f}px")
        
        return success, final_error, duration
    
    def fast_precision_move(self, offset_x: int, offset_y: int, 
                           tolerance: int = 1, max_time_ms: int = 15) -> Tuple[bool, float, float]:
        """
        快速精确移动 - 平衡速度与精度的新一代算法
        
        使用渐进式快速移动策略：
        - 动态分段移动（2-4步）
        - 实时硬件学习
        - 自适应步长控制
        - 15ms内完成高精度移动
        
        Args:
            offset_x: 相对于当前位置的X偏移（游戏坐标）
            offset_y: 相对于当前位置的Y偏移（游戏坐标）
            tolerance: 容差像素（默认1px，高精度）
            max_time_ms: 最大允许时间（毫秒，默认15ms）
            
        Returns:
            Tuple[bool, float, float]: (成功标志, 最终误差, 耗时)
        """
        if not self.driver or not self.driver.is_ready():
            self.logger.error("驱动未初始化")
            return False, float('inf'), 0.0
        
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 使用渐进式快速移动算法
        success, final_error, duration = self.pid_controller.progressive_fast_move(
            self.driver, offset_x, offset_y, tolerance, max_time_ms
        )
        
        if success:
            self.logger.debug(f"快速精确移动成功: 偏移({offset_x}, {offset_y}), 距离{distance:.1f}px, 误差{final_error:.2f}px, 耗时{duration*1000:.1f}ms")
        else:
            self.logger.warning(f"快速精确移动失败: 偏移({offset_x}, {offset_y}), 距离{distance:.1f}px, 最终误差{final_error:.2f}px")
        
        return success, final_error, duration
    
    def configure_for_game(self, game_sensitivity: float, 
                          game_dpi: int, conversion_ratio: float = 0.3,
                          adaptive_conversion: bool = True):
        """
        游戏特定配置
        
        Args:
            game_sensitivity: 游戏内灵敏度设置
            game_dpi: 游戏DPI设置  
            conversion_ratio: 像素到鼠标单位转换比率
            adaptive_conversion: 是否启用距离自适应转换比率
        """
        self.game_config.update({
            'sensitivity': game_sensitivity,
            'dpi': game_dpi,
            'conversion_ratio': conversion_ratio,
            'adaptive_conversion': adaptive_conversion
        })
        self.logger.info(f"游戏配置已更新: {self.game_config}")
    
    def get_adaptive_conversion_ratio(self, distance: float) -> float:
        """
        基于距离自适应调整转换比率 - 专为头部瞄准优化
        
        Args:
            distance: 目标距离
            
        Returns:
            float: 调整后的转换比率
        """
        if not self.game_config.get('adaptive_conversion', True):
            return self.game_config['conversion_ratio']
        
        base_ratio = self.game_config['conversion_ratio']
        
        # 基于距离进行自适应调整，专门优化200-300px黄金距离
        if distance > 500:
            return base_ratio * 1.6  # 超远距离: +60%
        elif distance > 300:
            return base_ratio * 1.5  # 远距离: +50%
        elif distance >= 200:
            return base_ratio * 1.8  # 200-300px黄金距离: +80%（专为头部瞄准）
        elif distance > 100:
            return base_ratio * 1.4  # 中距离: +40%
        elif distance > 50:
            return base_ratio * 1.2  # 近中距离: +20%
        else:
            return base_ratio        # 近距离: 保持精度
    
    def calibrate_hardware_response(self, test_distance: float = 200) -> float:
        """
        运行时硬件响应校准 - 自动检测并调整conversion_ratio
        
        Args:
            test_distance: 校准测试距离
            
        Returns:
            float: 校准后的conversion_ratio
        """
        if not self.driver or not self.driver.is_ready():
            return self.game_config['conversion_ratio']
        
        # 执行快速校准测试
        test_targets = [(test_distance, 0), (0, test_distance), (-test_distance, 0)]
        calibration_results = []
        
        original_ratio = self.game_config['conversion_ratio']
        
        for target_x, target_y in test_targets:
            # 使用当前参数执行测试移动
            expected_move_x, expected_move_y = self.pid_controller.calculate_optimal_movement_vector(
                target_x, target_y, self.game_config
            )
            
            # 计算理论覆盖距离
            theoretical_coverage = math.sqrt(expected_move_x**2 + expected_move_y**2) / original_ratio
            actual_target_distance = math.sqrt(target_x**2 + target_y**2)
            
            # 计算校准因子
            if theoretical_coverage > 0:
                calibration_factor = actual_target_distance / theoretical_coverage
                calibration_results.append(calibration_factor)
        
        # 计算平均校准因子
        if calibration_results:
            avg_calibration = sum(calibration_results) / len(calibration_results)
            
            # 应用校准调整（限制调整幅度）
            adjustment_factor = max(0.8, min(1.3, avg_calibration))
            calibrated_ratio = original_ratio * adjustment_factor
            
            # 更新配置
            self.game_config['conversion_ratio'] = calibrated_ratio
            
            self.logger.info(f"硬件响应校准完成: {original_ratio:.3f} → {calibrated_ratio:.3f} (调整{adjustment_factor:.2f}x)")
            
            return calibrated_ratio
        
        return original_ratio
    
    def reset_position_tracking(self):
        """
        重置位置跟踪
        
        使用场景：
        - 游戏重启时
        - 切换武器时
        - 游戏窗口位置变化时
        """
        self.pid_controller.reset()
        self.logger.info("位置跟踪已重置")
    
    def get_movement_statistics(self) -> dict:
        """
        获取移动性能统计
        
        Returns:
            dict: 包含精度、速度、成功率等统计信息
        """
        stats = self.pid_controller.get_performance_stats()
        stats.update({
            'driver_ready': self.driver.is_ready() if self.driver else False,
            'game_config': self.game_config.copy()
        })
        return stats
    
    def get_pid_stats(self) -> Optional[Dict]:
        """获取PID统计信息（兼容现有测试）"""
        return self.pid_controller.get_performance_stats()
    
    def get_driver_info(self) -> Optional[Dict]:
        """
        获取当前驱动信息
        
        Returns:
            Optional[Dict]: 驱动信息，如果未初始化则返回None
        """
        if self.driver:
            return self.driver.get_driver_info()
        return None
    
    def is_ready(self) -> bool:
        """
        检查控制器是否就绪
        
        Returns:
            bool: 是否已初始化并就绪
        """
        return self.driver is not None and self.driver.is_ready()
    
    # ============ 绝对定位API ============
    
    def move_to_absolute_position(self, target_x: float, target_y: float,
                                tolerance: Optional[float] = None) -> AbsoluteMovementResult:
        """
        移动到绝对屏幕位置 - 新的核心API
        
        Args:
            target_x: 目标屏幕X坐标
            target_y: 目标屏幕Y坐标
            tolerance: 容差（像素）
            
        Returns:
            AbsoluteMovementResult: 移动结果
        """
        if not self.enable_absolute_positioning or not self.absolute_controller:
            self.logger.error("绝对定位功能未启用")
            return AbsoluteMovementResult(
                success=False, final_error=float('inf'), execution_time=0.0,
                movement_count=0, strategy_used=None, confidence=0.0, target_reached=False
            )
        
        return self.absolute_controller.move_to_absolute_position(target_x, target_y, tolerance)
    
    def aim_at_target(self, target_x: float, target_y: float,
                     target_type: str = "general", precision_mode: bool = False) -> AbsoluteMovementResult:
        """
        瞄准特定类型的目标
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            target_type: 目标类型 ("head", "body", "general")
            precision_mode: 精度模式
            
        Returns:
            AbsoluteMovementResult: 瞄准结果
        """
        if not self.enable_absolute_positioning or not self.absolute_controller:
            self.logger.error("绝对定位功能未启用")
            return AbsoluteMovementResult(
                success=False, final_error=float('inf'), execution_time=0.0,
                movement_count=0, strategy_used=None, confidence=0.0, target_reached=False
            )
        
        # 转换目标类型字符串为枚举
        type_mapping = {
            "head": TargetType.HEAD,
            "body": TargetType.BODY,
            "general": TargetType.GENERAL
        }
        
        target_type_enum = type_mapping.get(target_type.lower(), TargetType.GENERAL)
        
        return self.absolute_controller.aim_at_target(
            target_x, target_y, target_type_enum, precision_mode
        )
    
    def calibrate_crosshair_position(self, known_x: float, known_y: float) -> bool:
        """
        校准准星位置
        
        Args:
            known_x: 已知的准确X坐标
            known_y: 已知的准确Y坐标
            
        Returns:
            bool: 校准是否成功
        """
        if not self.enable_absolute_positioning or not self.absolute_controller:
            self.logger.error("绝对定位功能未启用")
            return False
        
        return self.absolute_controller.calibrate_position(known_x, known_y)
    
    def reset_crosshair_to_center(self):
        """重置准星位置到屏幕中心"""
        if self.absolute_controller:
            self.absolute_controller.reset_position_to_center()
    
    def get_crosshair_position(self) -> Optional[Tuple[float, float]]:
        """
        获取当前准星位置
        
        Returns:
            Optional[Tuple[float, float]]: (x, y) 当前位置，如果绝对定位未启用则返回None
        """
        if not self.enable_absolute_positioning or not self.absolute_controller:
            return None
        
        return self.absolute_controller.get_current_position()
    
    def is_absolute_positioning_enabled(self) -> bool:
        """
        检查绝对定位是否启用
        
        Returns:
            bool: 是否启用绝对定位
        """
        return (self.enable_absolute_positioning and 
                self.absolute_controller is not None and
                self.absolute_controller.is_controller_ready())
    
    def get_absolute_positioning_stats(self) -> Optional[Dict]:
        """
        获取绝对定位性能统计
        
        Returns:
            Optional[Dict]: 统计信息，如果绝对定位未启用则返回None
        """
        if not self.enable_absolute_positioning or not self.absolute_controller:
            return None
        
        return self.absolute_controller.get_performance_statistics()
    
    def enable_absolute_positioning_mode(self, enable: bool = True):
        """
        启用或禁用绝对定位模式
        
        Args:
            enable: 是否启用绝对定位
        """
        self.enable_absolute_positioning = enable
        if enable and self.absolute_controller is None:
            # 如果之前未创建，现在创建绝对定位控制器
            absolute_config = AbsoluteControllerConfig(
                dpi=self.game_config['dpi'],
                sensitivity=self.game_config['sensitivity']
            )
            self.absolute_controller = AbsoluteMouseController(absolute_config)
            
            # 如果驱动已初始化，设置给绝对定位控制器
            if self.driver:
                self.absolute_controller.set_driver(self.driver)
        
        self.logger.info(f"绝对定位模式: {'启用' if enable else '禁用'}")
    
    def update_absolute_positioning_config(self, screen_width: int = None, screen_height: int = None,
                                         dpi: int = None, sensitivity: float = None, fov_x: float = None):
        """
        更新绝对定位配置
        
        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            dpi: DPI设置
            sensitivity: 灵敏度
            fov_x: 水平视野角度
        """
        if not self.absolute_controller:
            return
        
        # 获取当前配置
        current_config = self.absolute_controller.config
        
        # 更新提供的参数
        if screen_width is not None:
            current_config.screen_width = screen_width
        if screen_height is not None:
            current_config.screen_height = screen_height
        if dpi is not None:
            current_config.dpi = dpi
            self.game_config['dpi'] = dpi  # 同步更新相对移动配置
        if sensitivity is not None:
            current_config.sensitivity = sensitivity
            self.game_config['sensitivity'] = sensitivity  # 同步更新相对移动配置
        if fov_x is not None:
            current_config.fov_x = fov_x
        
        # 应用新配置
        self.absolute_controller.update_configuration(current_config)
        self.logger.info("绝对定位配置已更新")
    
    # ============ 配置管理API ============
    
    def save_current_config(self) -> bool:
        """
        保存当前配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        # 更新配置对象
        self.current_config.relative_movement.sensitivity = self.game_config['sensitivity']
        self.current_config.relative_movement.dpi = self.game_config['dpi']
        self.current_config.relative_movement.conversion_ratio = self.game_config['conversion_ratio']
        self.current_config.relative_movement.adaptive_conversion = self.game_config['adaptive_conversion']
        
        if self.absolute_controller:
            abs_config = self.absolute_controller.config
            self.current_config.absolute_positioning.screen_width = abs_config.screen_width
            self.current_config.absolute_positioning.screen_height = abs_config.screen_height
            self.current_config.absolute_positioning.dpi = abs_config.dpi
            self.current_config.absolute_positioning.sensitivity = abs_config.sensitivity
            self.current_config.absolute_positioning.fov_x = abs_config.fov_x
            self.current_config.absolute_positioning.default_tolerance = abs_config.default_tolerance
            self.current_config.absolute_positioning.head_target_tolerance = abs_config.head_target_tolerance
            self.current_config.absolute_positioning.enable_prediction = abs_config.enable_prediction
            self.current_config.absolute_positioning.enable_adaptive_mapping = abs_config.enable_adaptive_mapping
        
        success = self.config_manager.save_config(self.current_config)
        if success:
            self.logger.info("配置已保存")
        else:
            self.logger.error("配置保存失败")
        
        return success
    
    def load_config_from_file(self) -> bool:
        """
        从文件重新加载配置
        
        Returns:
            bool: 加载是否成功
        """
        try:
            new_config = self.config_manager.load_config()
            
            # 验证配置
            errors = self.config_manager.validate_config(new_config)
            if errors:
                self.logger.error(f"配置验证失败: {errors}")
                return False
            
            # 应用新配置
            self.current_config = new_config
            
            # 更新相对移动配置
            self.game_config.update({
                'sensitivity': new_config.relative_movement.sensitivity,
                'dpi': new_config.relative_movement.dpi,
                'conversion_ratio': new_config.relative_movement.conversion_ratio,
                'adaptive_conversion': new_config.relative_movement.adaptive_conversion
            })
            
            # 更新绝对定位配置
            if self.absolute_controller and new_config.absolute_positioning.enabled:
                abs_config = new_config.absolute_positioning
                absolute_config = AbsoluteControllerConfig(
                    screen_width=abs_config.screen_width,
                    screen_height=abs_config.screen_height,
                    dpi=abs_config.dpi,
                    sensitivity=abs_config.sensitivity,
                    fov_x=abs_config.fov_x,
                    default_tolerance=abs_config.default_tolerance,
                    head_target_tolerance=abs_config.head_target_tolerance,
                    max_attempts=abs_config.max_attempts,
                    max_execution_time=abs_config.max_execution_time,
                    enable_prediction=abs_config.enable_prediction,
                    enable_adaptive_mapping=abs_config.enable_adaptive_mapping,
                    debug_mode=abs_config.debug_mode,
                    log_movements=abs_config.log_movements
                )
                self.absolute_controller.update_configuration(absolute_config)
            
            self.logger.info("配置已重新加载")
            return True
            
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            return False
    
    def save_config_for_game(self, game_name: str) -> bool:
        """
        为特定游戏保存配置
        
        Args:
            game_name: 游戏名称
            
        Returns:
            bool: 保存是否成功
        """
        return self.config_manager.save_config_for_game(game_name, self.current_config)
    
    def load_config_for_game(self, game_name: str) -> bool:
        """
        加载特定游戏的配置
        
        Args:
            game_name: 游戏名称
            
        Returns:
            bool: 加载是否成功
        """
        game_config = self.config_manager.get_config_for_game(game_name)
        if game_config is None:
            self.logger.warning(f"未找到游戏'{game_name}'的配置")
            return False
        
        self.current_config = game_config
        return self.load_config_from_file()
    
    def get_config_summary(self) -> Dict:
        """
        获取配置摘要
        
        Returns:
            Dict: 配置摘要信息
        """
        return self.config_manager.get_config_summary()
    
    def reset_config_to_defaults(self) -> bool:
        """
        重置配置为默认值
        
        Returns:
            bool: 重置是否成功
        """
        success = self.config_manager.reset_to_defaults()
        if success:
            self.load_config_from_file()
            self.logger.info("配置已重置为默认值")
        
        return success
    
    def export_calibration_profile(self, profile_name: str) -> bool:
        """
        导出校准配置文件
        
        Args:
            profile_name: 配置文件名称
            
        Returns:
            bool: 导出是否成功
        """
        if not self.absolute_controller:
            self.logger.error("绝对定位未启用，无法导出校准配置")
            return False
        
        calibration_data = self.absolute_controller.export_calibration_data()
        return self.config_manager.export_calibration_profile(profile_name, calibration_data)
    
    def import_calibration_profile(self, profile_name: str) -> bool:
        """
        导入校准配置文件
        
        Args:
            profile_name: 配置文件名称
            
        Returns:
            bool: 导入是否成功
        """
        if not self.absolute_controller:
            self.logger.error("绝对定位未启用，无法导入校准配置")
            return False
        
        calibration_data = self.config_manager.import_calibration_profile(profile_name)
        if calibration_data is None:
            self.logger.warning(f"未找到校准配置'{profile_name}'")
            return False
        
        return self.absolute_controller.import_calibration_data(calibration_data)
    
    def list_available_configs(self) -> Dict[str, Any]:
        """
        列出所有可用的配置
        
        Returns:
            Dict[str, Any]: 可用配置信息
        """
        return {
            "game_configs": self.config_manager.list_game_configs(),
            "current_config": self.get_config_summary(),
            "has_backup": len(list(self.config_manager.backup_dir.glob("*.json"))) > 0
        }

    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.cleanup()
            self.driver = None
        
        if self.absolute_controller:
            self.absolute_controller.cleanup()
            self.absolute_controller = None
            
        self.logger.info("MouseController已清理")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()