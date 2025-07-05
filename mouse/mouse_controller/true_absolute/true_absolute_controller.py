"""
真正的一步到位绝对定位控制器
TrueAbsoluteController

完全不依赖PID控制器，实现真正的"一步到终点"鼠标控制
核心理念：计算 -> 执行 -> 完成，无需迭代调整
"""

import time
import math
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .precision_coordinate_mapper import PrecisionCoordinateMapper, HardwareType
from ..core.base_driver import BaseDriver


class MovementResult(Enum):
    """移动结果状态"""
    SUCCESS = "success"
    FAILED = "failed"
    OUT_OF_BOUNDS = "out_of_bounds"
    HARDWARE_ERROR = "hardware_error"


class TargetType(Enum):
    """目标类型"""
    GENERAL = "general"
    HEAD = "head"
    BODY = "body"
    PRECISE = "precise"


@dataclass
class MovementStats:
    """移动统计信息"""
    result: MovementResult
    execution_time_ms: float
    pixel_distance: float
    mouse_distance: int
    theoretical_accuracy: float
    target_type: TargetType
    timestamp: float


@dataclass
class CrosshairPosition:
    """准星位置信息"""
    x: float
    y: float
    confidence: float
    last_updated: float


class TrueAbsoluteController:
    """真正的一步到位绝对定位控制器"""
    
    def __init__(self, screen_width: int = 1920, screen_height: int = 1080,
                 dpi: int = 800, sensitivity: float = 1.0,
                 hardware_type: HardwareType = HardwareType.MOUSE_CONTROL):
        
        # 基础配置
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dpi = dpi
        self.sensitivity = sensitivity
        self.hardware_type = hardware_type
        
        # 核心组件
        self.coordinate_mapper = PrecisionCoordinateMapper(
            dpi=dpi, 
            sensitivity=sensitivity, 
            hardware_type=hardware_type
        )
        
        # 准星位置跟踪
        self.crosshair_position = CrosshairPosition(
            x=screen_width / 2.0,
            y=screen_height / 2.0,
            confidence=1.0,
            last_updated=time.time()
        )
        
        # 边界约束
        self.boundary_margin = 10  # 屏幕边界边距
        self.max_single_move_distance = 2000  # 单次移动最大距离
        
        # 性能统计
        self.movement_history: List[MovementStats] = []
        self.performance_stats = {
            'total_moves': 0,
            'successful_moves': 0,
            'average_execution_time': 0.0,
            'average_accuracy': 0.0
        }
        
        # 驱动接口
        self.driver: Optional[BaseDriver] = None
        
        # 目标类型优化参数
        self.target_optimizations = {
            TargetType.GENERAL: {
                'precision_boost': 1.0,
                'confidence_threshold': 0.9
            },
            TargetType.HEAD: {
                'precision_boost': 1.15,  # 15%精度提升
                'confidence_threshold': 0.95  # 更高置信度要求
            },
            TargetType.BODY: {
                'precision_boost': 1.05,  # 5%精度提升
                'confidence_threshold': 0.92
            },
            TargetType.PRECISE: {
                'precision_boost': 1.25,  # 25%精度提升
                'confidence_threshold': 0.98  # 最高置信度要求
            }
        }
    
    def set_driver(self, driver: BaseDriver):
        """设置硬件驱动"""
        self.driver = driver
    
    def move_to_absolute_position(self, target_x: float, target_y: float,
                                 target_type: TargetType = TargetType.GENERAL) -> MovementStats:
        """
        一步到位移动到绝对位置
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            target_type: 目标类型
            
        Returns:
            MovementStats: 移动统计信息
        """
        start_time = time.time()
        
        # 验证输入
        if not self.driver:
            return self._create_movement_stats(
                MovementResult.HARDWARE_ERROR, 0, 0, 0, 0, target_type, start_time
            )
        
        # 边界检查
        if not self._is_position_valid(target_x, target_y):
            return self._create_movement_stats(
                MovementResult.OUT_OF_BOUNDS, 0, 0, 0, 0, target_type, start_time
            )
        
        # 获取当前准星位置
        current_x = self.crosshair_position.x
        current_y = self.crosshair_position.y
        
        # 计算像素距离
        pixel_distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
        
        # 检查是否需要移动
        if pixel_distance < 1.0:
            return self._create_movement_stats(
                MovementResult.SUCCESS, time.time() - start_time, pixel_distance, 0, 1.0, target_type, start_time
            )
        
        # 检查单次移动距离限制
        if pixel_distance > self.max_single_move_distance:
            # 对于超长距离，使用分步移动
            return self._execute_long_distance_move(target_x, target_y, target_type, start_time)
        
        # 计算精确移动量
        mouse_dx, mouse_dy = self.coordinate_mapper.calculate_precise_move(
            current_x, current_y, target_x, target_y
        )
        
        # 应用目标类型优化
        optimization = self.target_optimizations[target_type]
        precision_boost = optimization['precision_boost']
        
        # 精度提升调整
        if precision_boost != 1.0:
            mouse_dx = int(round(mouse_dx * precision_boost))
            mouse_dy = int(round(mouse_dy * precision_boost))
        
        # 执行移动
        try:
            success = self.driver.move_relative(mouse_dx, mouse_dy)
            
            if success:
                # 更新准星位置
                self.crosshair_position.x = target_x
                self.crosshair_position.y = target_y
                self.crosshair_position.confidence = optimization['confidence_threshold']
                self.crosshair_position.last_updated = time.time()
                
                # 计算理论精度
                mouse_distance = int(math.sqrt(mouse_dx**2 + mouse_dy**2))
                theoretical_accuracy = self._calculate_theoretical_accuracy(pixel_distance, target_type)
                
                execution_time = time.time() - start_time
                
                # 记录成功移动
                stats = self._create_movement_stats(
                    MovementResult.SUCCESS, execution_time, pixel_distance, 
                    mouse_distance, theoretical_accuracy, target_type, start_time
                )
                
                self._update_performance_stats(stats)
                return stats
            
            else:
                return self._create_movement_stats(
                    MovementResult.HARDWARE_ERROR, time.time() - start_time, 
                    pixel_distance, 0, 0, target_type, start_time
                )
                
        except Exception as e:
            return self._create_movement_stats(
                MovementResult.HARDWARE_ERROR, time.time() - start_time,
                pixel_distance, 0, 0, target_type, start_time
            )
    
    def move_to_relative_target(self, offset_x: float, offset_y: float,
                               target_type: TargetType = TargetType.GENERAL) -> MovementStats:
        """
        相对移动（保持兼容性）
        
        Args:
            offset_x: X轴偏移量
            offset_y: Y轴偏移量
            target_type: 目标类型
            
        Returns:
            MovementStats: 移动统计信息
        """
        target_x = self.crosshair_position.x + offset_x
        target_y = self.crosshair_position.y + offset_y
        
        return self.move_to_absolute_position(target_x, target_y, target_type)
    
    def predictive_move_to_target(self, target_x: float, target_y: float,
                                 target_velocity: Optional[Tuple[float, float]] = None,
                                 prediction_time_ms: float = 50.0,
                                 target_type: TargetType = TargetType.GENERAL) -> MovementStats:
        """
        预测性移动到目标位置
        
        Args:
            target_x: 当前目标X坐标
            target_y: 当前目标Y坐标
            target_velocity: 目标速度 (vx, vy) pixels/second
            prediction_time_ms: 预测时间（毫秒）
            target_type: 目标类型
            
        Returns:
            MovementStats: 移动统计信息
        """
        # 如果没有速度信息，直接移动到当前位置
        if not target_velocity:
            return self.move_to_absolute_position(target_x, target_y, target_type)
        
        # 计算移动执行时间
        current_x = self.crosshair_position.x
        current_y = self.crosshair_position.y
        distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
        
        # 估算移动执行时间（基于硬件特性）
        base_execution_time = self._estimate_execution_time(distance)
        total_prediction_time = (prediction_time_ms + base_execution_time) / 1000.0
        
        # 预测目标最终位置
        vx, vy = target_velocity
        predicted_x = target_x + vx * total_prediction_time
        predicted_y = target_y + vy * total_prediction_time
        
        # 边界约束预测位置
        predicted_x = max(self.boundary_margin, min(self.screen_width - self.boundary_margin, predicted_x))
        predicted_y = max(self.boundary_margin, min(self.screen_height - self.boundary_margin, predicted_y))
        
        # 移动到预测位置
        return self.move_to_absolute_position(predicted_x, predicted_y, target_type)
    
    def _execute_long_distance_move(self, target_x: float, target_y: float,
                                   target_type: TargetType, start_time: float) -> MovementStats:
        """
        执行超长距离移动（分步移动）
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            target_type: 目标类型
            start_time: 开始时间
            
        Returns:
            MovementStats: 移动统计信息
        """
        current_x = self.crosshair_position.x
        current_y = self.crosshair_position.y
        
        total_distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
        
        # 计算中间点
        direction_x = (target_x - current_x) / total_distance
        direction_y = (target_y - current_y) / total_distance
        
        # 第一步：移动到距离目标约80%的位置
        intermediate_distance = min(self.max_single_move_distance * 0.8, total_distance * 0.8)
        intermediate_x = current_x + direction_x * intermediate_distance
        intermediate_y = current_y + direction_y * intermediate_distance
        
        # 执行第一步移动
        first_step = self.move_to_absolute_position(intermediate_x, intermediate_y, TargetType.GENERAL)
        
        if first_step.result != MovementResult.SUCCESS:
            return first_step
        
        # 执行第二步移动到最终目标
        final_step = self.move_to_absolute_position(target_x, target_y, target_type)
        
        # 合并统计信息
        total_time = time.time() - start_time
        return self._create_movement_stats(
            final_step.result, total_time, total_distance,
            first_step.mouse_distance + final_step.mouse_distance,
            final_step.theoretical_accuracy, target_type, start_time
        )
    
    def _is_position_valid(self, x: float, y: float) -> bool:
        """
        检查位置是否在有效范围内
        
        Args:
            x: X坐标
            y: Y坐标
            
        Returns:
            bool: 位置是否有效
        """
        return (
            self.boundary_margin <= x <= self.screen_width - self.boundary_margin and
            self.boundary_margin <= y <= self.screen_height - self.boundary_margin
        )
    
    def _calculate_theoretical_accuracy(self, distance: float, target_type: TargetType) -> float:
        """
        计算理论精度
        
        Args:
            distance: 移动距离
            target_type: 目标类型
            
        Returns:
            float: 理论精度（0-1）
        """
        # 基于距离的基础精度
        if distance <= 50:
            base_accuracy = 0.99
        elif distance <= 100:
            base_accuracy = 0.98
        elif distance <= 200:
            base_accuracy = 0.96
        elif distance <= 500:
            base_accuracy = 0.94
        elif distance <= 1000:
            base_accuracy = 0.90
        else:
            base_accuracy = 0.85
        
        # 应用目标类型加成
        optimization = self.target_optimizations[target_type]
        precision_boost = optimization['precision_boost']
        
        # 计算最终理论精度
        theoretical_accuracy = min(1.0, base_accuracy * precision_boost)
        
        return theoretical_accuracy
    
    def _estimate_execution_time(self, distance: float) -> float:
        """
        估算移动执行时间（毫秒）
        
        Args:
            distance: 移动距离
            
        Returns:
            float: 估算执行时间（毫秒）
        """
        # 基于硬件类型的基础延迟
        if self.hardware_type == HardwareType.MOUSE_CONTROL:
            base_latency = 3.0
        elif self.hardware_type == HardwareType.GHUB:
            base_latency = 10.0
        else:
            base_latency = 15.0
        
        # 距离相关的额外时间
        distance_factor = min(5.0, distance / 200.0)
        
        return base_latency + distance_factor
    
    def _create_movement_stats(self, result: MovementResult, execution_time: float,
                              pixel_distance: float, mouse_distance: int,
                              theoretical_accuracy: float, target_type: TargetType,
                              timestamp: float) -> MovementStats:
        """
        创建移动统计信息
        
        Args:
            result: 移动结果
            execution_time: 执行时间
            pixel_distance: 像素距离
            mouse_distance: 鼠标移动距离
            theoretical_accuracy: 理论精度
            target_type: 目标类型
            timestamp: 时间戳
            
        Returns:
            MovementStats: 移动统计信息
        """
        stats = MovementStats(
            result=result,
            execution_time_ms=execution_time * 1000,
            pixel_distance=pixel_distance,
            mouse_distance=mouse_distance,
            theoretical_accuracy=theoretical_accuracy,
            target_type=target_type,
            timestamp=timestamp
        )
        
        # 记录到历史
        self.movement_history.append(stats)
        
        # 保持历史记录在合理范围内
        if len(self.movement_history) > 1000:
            self.movement_history = self.movement_history[-800:]
        
        return stats
    
    def _update_performance_stats(self, stats: MovementStats):
        """
        更新性能统计
        
        Args:
            stats: 移动统计信息
        """
        self.performance_stats['total_moves'] += 1
        
        if stats.result == MovementResult.SUCCESS:
            self.performance_stats['successful_moves'] += 1
        
        # 更新平均执行时间
        total_moves = self.performance_stats['total_moves']
        current_avg_time = self.performance_stats['average_execution_time']
        self.performance_stats['average_execution_time'] = (
            (current_avg_time * (total_moves - 1) + stats.execution_time_ms) / total_moves
        )
        
        # 更新平均精度
        if stats.result == MovementResult.SUCCESS:
            current_avg_accuracy = self.performance_stats['average_accuracy']
            successful_moves = self.performance_stats['successful_moves']
            self.performance_stats['average_accuracy'] = (
                (current_avg_accuracy * (successful_moves - 1) + stats.theoretical_accuracy) / successful_moves
            )
    
    def get_crosshair_position(self) -> Tuple[float, float]:
        """
        获取当前准星位置
        
        Returns:
            Tuple[float, float]: (x, y) 坐标
        """
        return self.crosshair_position.x, self.crosshair_position.y
    
    def set_crosshair_position(self, x: float, y: float, confidence: float = 1.0):
        """
        设置准星位置
        
        Args:
            x: X坐标
            y: Y坐标
            confidence: 置信度
        """
        if self._is_position_valid(x, y):
            self.crosshair_position.x = x
            self.crosshair_position.y = y
            self.crosshair_position.confidence = confidence
            self.crosshair_position.last_updated = time.time()
    
    def calibrate_position(self, actual_x: float, actual_y: float):
        """
        校准准星位置
        
        Args:
            actual_x: 实际X坐标
            actual_y: 实际Y坐标
        """
        expected_x = self.crosshair_position.x
        expected_y = self.crosshair_position.y
        
        # 更新坐标映射器的自适应系数
        distance = math.sqrt((expected_x - actual_x)**2 + (expected_y - actual_y)**2)
        self.coordinate_mapper.update_adaptive_coefficients(
            distance, (expected_x, expected_y), (actual_x, actual_y)
        )
        
        # 更新准星位置
        self.set_crosshair_position(actual_x, actual_y, 1.0)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计数据
        """
        stats = self.performance_stats.copy()
        
        # 添加成功率
        if stats['total_moves'] > 0:
            stats['success_rate'] = stats['successful_moves'] / stats['total_moves']
        else:
            stats['success_rate'] = 0.0
        
        # 添加最近移动统计
        recent_moves = self.movement_history[-50:] if len(self.movement_history) >= 50 else self.movement_history
        if recent_moves:
            recent_successful = [m for m in recent_moves if m.result == MovementResult.SUCCESS]
            if recent_successful:
                stats['recent_success_rate'] = len(recent_successful) / len(recent_moves)
                stats['recent_average_time'] = sum(m.execution_time_ms for m in recent_successful) / len(recent_successful)
                stats['recent_average_accuracy'] = sum(m.theoretical_accuracy for m in recent_successful) / len(recent_successful)
            else:
                stats['recent_success_rate'] = 0.0
                stats['recent_average_time'] = 0.0
                stats['recent_average_accuracy'] = 0.0
        
        return stats
    
    def get_movement_history(self) -> List[MovementStats]:
        """
        获取移动历史
        
        Returns:
            List[MovementStats]: 移动历史记录
        """
        return self.movement_history.copy()
    
    def reset_performance_stats(self):
        """
        重置性能统计
        """
        self.performance_stats = {
            'total_moves': 0,
            'successful_moves': 0,
            'average_execution_time': 0.0,
            'average_accuracy': 0.0
        }
        self.movement_history.clear()
        self.coordinate_mapper.reset_adaptive_learning()
    
    def update_settings(self, dpi: Optional[int] = None, sensitivity: Optional[float] = None,
                       hardware_type: Optional[HardwareType] = None):
        """
        更新设置
        
        Args:
            dpi: DPI设置
            sensitivity: 灵敏度设置
            hardware_type: 硬件类型
        """
        if dpi is not None:
            self.dpi = dpi
            self.coordinate_mapper.dpi = dpi
        
        if sensitivity is not None:
            self.sensitivity = sensitivity
            self.coordinate_mapper.sensitivity = sensitivity
        
        if hardware_type is not None:
            self.hardware_type = hardware_type
            self.coordinate_mapper.hardware_type = hardware_type
            self.coordinate_mapper.current_profile = self.coordinate_mapper.hardware_profiles[hardware_type]