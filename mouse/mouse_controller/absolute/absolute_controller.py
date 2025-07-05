"""
绝对定位鼠标控制器 - 主要对外接口
"""

import time
import math
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass

from .crosshair_tracker import CrosshairPositionTracker
from .position_calculator import AbsolutePositionCalculator, TargetType, MovementStrategy
from ..algorithms.coordinate_mapping import CoordinateMapper, GameSettings, AdaptiveCoordinateMapper
from ..algorithms.pid_controller import VelocityAwarePIDController
from ..core.base_driver import BaseDriver
from ..utils.logger import setup_logger


@dataclass
class AbsoluteMovementResult:
    """绝对移动结果"""
    success: bool
    final_error: float          # 最终误差（像素）
    execution_time: float       # 执行时间（秒）
    movement_count: int         # 移动次数
    strategy_used: MovementStrategy
    confidence: float
    target_reached: bool        # 是否达到目标位置


@dataclass
class AbsoluteControllerConfig:
    """绝对控制器配置"""
    # 屏幕设置
    screen_width: int = 1920
    screen_height: int = 1080
    
    # 游戏设置
    dpi: int = 800
    sensitivity: float = 1.0
    fov_x: float = 90.0
    
    # 精度设置
    default_tolerance: float = 2.0      # 默认容差（像素）
    head_target_tolerance: float = 1.0  # 头部目标容差
    max_attempts: int = 3               # 最大尝试次数
    
    # 性能设置
    max_execution_time: float = 0.1     # 最大执行时间（秒）
    enable_prediction: bool = True      # 启用运动预测
    enable_adaptive_mapping: bool = True # 启用自适应映射
    
    # 调试设置
    debug_mode: bool = False
    log_movements: bool = False


class AbsoluteMouseController:
    """
    绝对定位鼠标控制器
    
    核心API：
    - move_to_absolute_position: 移动到绝对位置
    - aim_at_target: 瞄准目标（带目标类型）
    - calibrate_position: 校准当前位置
    """
    
    def __init__(self, config: Optional[AbsoluteControllerConfig] = None,
                 driver: Optional[BaseDriver] = None):
        """
        初始化绝对定位控制器
        
        Args:
            config: 控制器配置
            driver: 鼠标驱动（可选，稍后设置）
        """
        self.config = config or AbsoluteControllerConfig()
        self.driver = driver
        self.logger = setup_logger("AbsoluteMouseController")
        
        # 初始化组件
        self._initialize_components()
        
        # 状态管理
        self.is_ready = False
        self.last_move_time = 0.0
        self.calibration_required = False
        
        # 性能统计
        self.movement_stats = {
            'total_moves': 0,
            'successful_moves': 0,
            'average_error': 0.0,
            'average_time': 0.0,
            'calibration_count': 0
        }
        
        # 移动历史（用于学习和优化）
        self.movement_history: List[AbsoluteMovementResult] = []
        self.max_history_size = 100
    
    def _initialize_components(self):
        """初始化核心组件"""
        # 创建游戏设置
        game_settings = GameSettings(
            dpi=self.config.dpi,
            sensitivity=self.config.sensitivity,
            fov_x=self.config.fov_x,
            screen_width=self.config.screen_width,
            screen_height=self.config.screen_height
        )
        
        # 创建坐标映射器
        if self.config.enable_adaptive_mapping:
            self.coordinate_mapper = AdaptiveCoordinateMapper(game_settings)
        else:
            self.coordinate_mapper = CoordinateMapper(game_settings)
        
        # 创建准星位置跟踪器
        self.crosshair_tracker = CrosshairPositionTracker(
            self.config.screen_width,
            self.config.screen_height,
            self.coordinate_mapper
        )
        
        # 创建位置计算器
        self.position_calculator = AbsolutePositionCalculator(self.coordinate_mapper)
        
        # 创建PID控制器 - 集成成熟的1.56px精度算法
        self.pid_controller = VelocityAwarePIDController()
        
        self.logger.info("绝对定位控制器组件初始化完成")
    
    def set_driver(self, driver: BaseDriver):
        """
        设置鼠标驱动
        
        Args:
            driver: 鼠标驱动实例
        """
        self.driver = driver
        self.is_ready = driver is not None and driver.is_ready()
        
        if self.is_ready:
            # 针对驱动类型优化计算器
            driver_info = driver.get_driver_info()
            if driver_info:
                driver_type = driver_info.get('type', 'unknown')
                self.position_calculator.optimize_for_hardware(driver_type, {})
                self.logger.info(f"已设置驱动: {driver_type}")
    
    def move_to_absolute_position(self, target_x: float, target_y: float,
                                tolerance: Optional[float] = None,
                                max_attempts: Optional[int] = None) -> AbsoluteMovementResult:
        """
        核心API：直接移动到目标绝对位置
        
        Args:
            target_x: 目标屏幕X坐标
            target_y: 目标屏幕Y坐标
            tolerance: 容差（像素），默认使用配置值
            max_attempts: 最大尝试次数，默认使用配置值
            
        Returns:
            AbsoluteMovementResult: 移动结果
        """
        if not self.driver or not self.driver.is_ready():
            return AbsoluteMovementResult(
                success=False,
                final_error=float('inf'),
                execution_time=0.0,
                movement_count=0,
                strategy_used=MovementStrategy.DIRECT,
                confidence=0.0,
                target_reached=False
            )
        
        start_time = time.time()
        tolerance = tolerance or self.config.default_tolerance
        max_attempts = max_attempts or self.config.max_attempts
        
        # 获取当前准星位置
        current_x, current_y = self.crosshair_tracker.get_position()
        
        best_result = None
        
        # 计算相对偏移量
        pixel_offset_x = target_x - current_x
        pixel_offset_y = target_y - current_y
        
        # 转换为鼠标移动单位（使用改进的坐标映射）
        mouse_offset_x, mouse_offset_y = self.coordinate_mapper.screen_to_mouse_units(
            pixel_offset_x, pixel_offset_y
        )
        
        # 使用成熟的PID算法执行移动
        success, final_error, execution_time = self.pid_controller.move_to_relative_target(
            self.driver, 
            mouse_offset_x, 
            mouse_offset_y,
            tolerance=int(tolerance),
            max_iterations=max_attempts * 50,  # PID使用更多迭代
            is_head_target=False  # 在基本方法中使用默认设置
        )
        
        if success:
            # PID移动成功，更新准星位置
            # PID controller已经执行了所有移动，所以我们需要根据最终结果更新位置
            final_x = current_x + pixel_offset_x
            final_y = current_y + pixel_offset_y
            
            # 边界检查
            final_x = max(0, min(self.config.screen_width, final_x))
            final_y = max(0, min(self.config.screen_height, final_y))
            
            # 更新跟踪器位置
            self.crosshair_tracker.set_position(final_x, final_y, 0.95)
            
            result = AbsoluteMovementResult(
                success=True,
                final_error=final_error,
                execution_time=execution_time,
                movement_count=1,  # PID内部处理多次移动
                strategy_used=MovementStrategy.COMPENSATED,
                confidence=0.95,
                target_reached=final_error <= tolerance
            )
            
            # 记录精度数据
            pixel_distance = math.sqrt(pixel_offset_x**2 + pixel_offset_y**2)
            self.position_calculator.record_movement_accuracy(pixel_distance, final_error)
            
            self._record_movement_success(result)
            return result
        else:
            # PID移动失败，尝试备用方法
            self.logger.warning(f"PID移动失败，误差: {final_error:.2f}px")
        
        # 如果所有尝试都失败，返回最佳结果或失败结果
        if best_result:
            self._record_movement_result(best_result)
            return best_result
        else:
            execution_time = time.time() - start_time
            failure_result = AbsoluteMovementResult(
                success=False,
                final_error=float('inf'),
                execution_time=execution_time,
                movement_count=max_attempts,
                strategy_used=MovementStrategy.DIRECT,
                confidence=0.0,
                target_reached=False
            )
            self._record_movement_result(failure_result)
            return failure_result
    
    def aim_at_target(self, target_x: float, target_y: float,
                     target_type: TargetType = TargetType.GENERAL,
                     precision_mode: bool = False) -> AbsoluteMovementResult:
        """
        瞄准特定类型的目标
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            target_type: 目标类型
            precision_mode: 精度模式
            
        Returns:
            AbsoluteMovementResult: 瞄准结果
        """
        # 根据目标类型调整容差
        tolerance_map = {
            TargetType.HEAD: self.config.head_target_tolerance,
            TargetType.BODY: self.config.default_tolerance,
            TargetType.GENERAL: self.config.default_tolerance
        }
        
        tolerance = tolerance_map[target_type]
        if precision_mode:
            tolerance *= 0.5  # 精度模式下容差减半
        
        # 获取当前位置
        current_x, current_y = self.crosshair_tracker.get_position()
        
        # 计算相对偏移量
        pixel_offset_x = target_x - current_x
        pixel_offset_y = target_y - current_y
        
        # 转换为鼠标移动单位
        mouse_offset_x, mouse_offset_y = self.coordinate_mapper.screen_to_mouse_units(
            pixel_offset_x, pixel_offset_y
        )
        
        # 确定是否为头部目标
        is_head_target = (target_type == TargetType.HEAD)
        
        # 使用PID算法执行移动
        start_time = time.time()
        success, final_error, execution_time = self.pid_controller.move_to_relative_target(
            self.driver,
            mouse_offset_x,
            mouse_offset_y,
            tolerance=int(tolerance),
            max_iterations=150,  # 针对目标类型优化
            is_head_target=is_head_target
        )
        
        if success:
            # 更新准星位置
            final_x = current_x + pixel_offset_x
            final_y = current_y + pixel_offset_y
            
            # 边界检查
            final_x = max(0, min(self.config.screen_width, final_x))
            final_y = max(0, min(self.config.screen_height, final_y))
            
            self.crosshair_tracker.set_position(final_x, final_y, 0.95)
            
            result = AbsoluteMovementResult(
                success=True,
                final_error=final_error,
                execution_time=execution_time,
                movement_count=1,
                strategy_used=MovementStrategy.COMPENSATED,
                confidence=0.95,
                target_reached=final_error <= tolerance
            )
            
            self._record_movement_success(result)
            return result
        else:
            # 备用：使用基本绝对定位方法
            return self.move_to_absolute_position(target_x, target_y, tolerance)
    
    def _execute_multi_step_movement(self, target_x: float, target_y: float,
                                   target_type: TargetType, tolerance: float) -> AbsoluteMovementResult:
        """执行多步移动"""
        start_time = time.time()
        current_x, current_y = self.crosshair_tracker.get_position()
        
        # 计算多步移动
        movements = self.position_calculator.calculate_multi_step_movement(
            current_x, current_y, target_x, target_y, 3, target_type
        )
        
        total_movements = 0
        
        for movement in movements:
            success = self._execute_movement(movement.mouse_delta_x, movement.mouse_delta_y)
            total_movements += 1
            
            if success:
                self.crosshair_tracker.update_after_move(
                    movement.mouse_delta_x, movement.mouse_delta_y
                )
            else:
                break
        
        # 检查最终结果
        final_x, final_y = self.crosshair_tracker.get_position()
        final_error = math.sqrt((target_x - final_x)**2 + (target_y - final_y)**2)
        execution_time = time.time() - start_time
        
        result = AbsoluteMovementResult(
            success=final_error <= tolerance,
            final_error=final_error,
            execution_time=execution_time,
            movement_count=total_movements,
            strategy_used=MovementStrategy.COMPENSATED,
            confidence=0.9 if final_error <= tolerance else 0.6,
            target_reached=final_error <= tolerance
        )
        
        self._record_movement_result(result)
        return result
    
    def _execute_movement(self, mouse_dx: int, mouse_dy: int) -> bool:
        """执行单次移动"""
        try:
            if self.config.debug_mode:
                self.logger.debug(f"执行移动: dx={mouse_dx}, dy={mouse_dy}")
            
            success = self.driver.move_relative(mouse_dx, mouse_dy)
            self.last_move_time = time.time()
            
            if self.config.log_movements:
                self.logger.info(f"移动执行: {success}, dx={mouse_dx}, dy={mouse_dy}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"移动执行异常: {e}")
            return False
    
    def calibrate_position(self, known_x: float, known_y: float) -> bool:
        """
        校准当前位置
        
        Args:
            known_x: 已知的准确X坐标
            known_y: 已知的准确Y坐标
            
        Returns:
            bool: 校准是否成功
        """
        success = self.crosshair_tracker.calibrate_with_known_position(known_x, known_y)
        
        if success:
            self.movement_stats['calibration_count'] += 1
            self.calibration_required = False
            self.logger.info(f"位置校准完成: ({known_x}, {known_y})")
        
        return success
    
    def reset_position_to_center(self):
        """重置位置到屏幕中心"""
        self.crosshair_tracker.reset_to_center()
        self.calibration_required = False
        self.logger.info("位置已重置到屏幕中心")
    
    def get_current_position(self) -> Tuple[float, float]:
        """
        获取当前准星位置
        
        Returns:
            Tuple[float, float]: (x, y) 当前位置
        """
        return self.crosshair_tracker.get_position()
    
    def _record_movement_success(self, result: AbsoluteMovementResult):
        """记录成功的移动"""
        self.movement_stats['successful_moves'] += 1
        self._record_movement_result(result)
    
    def _record_movement_result(self, result: AbsoluteMovementResult):
        """记录移动结果"""
        self.movement_stats['total_moves'] += 1
        
        # 更新平均值
        total = self.movement_stats['total_moves']
        self.movement_stats['average_error'] = (
            (self.movement_stats['average_error'] * (total - 1) + result.final_error) / total
        )
        self.movement_stats['average_time'] = (
            (self.movement_stats['average_time'] * (total - 1) + result.execution_time) / total
        )
        
        # 添加到历史记录
        self.movement_history.append(result)
        if len(self.movement_history) > self.max_history_size:
            self.movement_history.pop(0)
    
    def get_performance_statistics(self) -> Dict:
        """
        获取性能统计信息
        
        Returns:
            Dict: 性能统计
        """
        success_rate = (self.movement_stats['successful_moves'] / 
                       max(1, self.movement_stats['total_moves']))
        
        # 最近10次移动的统计
        recent_movements = self.movement_history[-10:] if self.movement_history else []
        recent_success_rate = (sum(1 for m in recent_movements if m.success) / 
                              max(1, len(recent_movements)))
        recent_avg_error = (sum(m.final_error for m in recent_movements) / 
                           max(1, len(recent_movements)))
        
        return {
            'total_movements': self.movement_stats['total_moves'],
            'successful_movements': self.movement_stats['successful_moves'],
            'overall_success_rate': success_rate,
            'average_error_px': self.movement_stats['average_error'],
            'average_time_ms': self.movement_stats['average_time'] * 1000,
            'calibration_count': self.movement_stats['calibration_count'],
            'recent_success_rate': recent_success_rate,
            'recent_average_error': recent_avg_error,
            'position_confidence': self.crosshair_tracker.get_position_confidence(),
            'is_calibration_required': self.calibration_required,
            'crosshair_stats': self.crosshair_tracker.get_tracking_statistics(),
            'calculator_stats': self.position_calculator.get_calculation_statistics()
        }
    
    def update_configuration(self, config: AbsoluteControllerConfig):
        """
        更新配置
        
        Args:
            config: 新的配置
        """
        old_screen_size = (self.config.screen_width, self.config.screen_height)
        self.config = config
        
        # 如果屏幕分辨率变化，更新组件
        new_screen_size = (config.screen_width, config.screen_height)
        if old_screen_size != new_screen_size:
            self.crosshair_tracker.update_screen_resolution(
                config.screen_width, config.screen_height
            )
        
        # 更新游戏设置
        game_settings = GameSettings(
            dpi=config.dpi,
            sensitivity=config.sensitivity,
            fov_x=config.fov_x,
            screen_width=config.screen_width,
            screen_height=config.screen_height
        )
        
        # 重新初始化坐标映射器
        if config.enable_adaptive_mapping:
            self.coordinate_mapper = AdaptiveCoordinateMapper(game_settings)
        else:
            self.coordinate_mapper = CoordinateMapper(game_settings)
        
        # 更新组件引用
        self.crosshair_tracker.coordinate_mapper = self.coordinate_mapper
        self.position_calculator.coordinate_mapper = self.coordinate_mapper
        
        self.logger.info("配置已更新")
    
    def export_calibration_data(self) -> Dict:
        """
        导出校准数据
        
        Returns:
            Dict: 校准数据
        """
        return {
            'config': {
                'screen_width': self.config.screen_width,
                'screen_height': self.config.screen_height,
                'dpi': self.config.dpi,
                'sensitivity': self.config.sensitivity,
                'fov_x': self.config.fov_x
            },
            'crosshair_data': self.crosshair_tracker.export_calibration_data(),
            'movement_stats': self.movement_stats.copy(),
            'performance_stats': self.get_performance_statistics()
        }
    
    def import_calibration_data(self, data: Dict) -> bool:
        """
        导入校准数据
        
        Args:
            data: 校准数据
            
        Returns:
            bool: 导入是否成功
        """
        try:
            # 恢复配置
            if 'config' in data:
                config_data = data['config']
                self.config.screen_width = config_data['screen_width']
                self.config.screen_height = config_data['screen_height']
                self.config.dpi = config_data['dpi']
                self.config.sensitivity = config_data['sensitivity']
                self.config.fov_x = config_data['fov_x']
            
            # 恢复准星数据
            if 'crosshair_data' in data:
                self.crosshair_tracker.import_calibration_data(data['crosshair_data'])
            
            # 恢复统计数据
            if 'movement_stats' in data:
                self.movement_stats = data['movement_stats']
            
            self.logger.info("校准数据导入成功")
            return True
            
        except Exception as e:
            self.logger.error(f"校准数据导入失败: {e}")
            return False
    
    def is_controller_ready(self) -> bool:
        """
        检查控制器是否就绪
        
        Returns:
            bool: 是否就绪
        """
        return (self.is_ready and 
                self.driver is not None and 
                self.driver.is_ready() and
                self.crosshair_tracker.is_position_valid())
    
    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.cleanup()
        
        self.is_ready = False
        self.logger.info("绝对定位控制器已清理")