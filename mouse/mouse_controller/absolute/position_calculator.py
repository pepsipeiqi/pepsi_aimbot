"""
绝对定位计算器 - 计算从当前位置到目标位置的精确移动量
"""

import math
import time
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
from ..algorithms.coordinate_mapping import CoordinateMapper, GameSettings


class TargetType(Enum):
    """目标类型"""
    HEAD = "head"           # 头部目标 - 高精度
    BODY = "body"           # 身体目标 - 平衡模式
    GENERAL = "general"     # 一般目标 - 标准模式


class MovementStrategy(Enum):
    """移动策略"""
    DIRECT = "direct"           # 直接移动
    PREDICTIVE = "predictive"   # 预测性移动
    COMPENSATED = "compensated" # 补偿性移动


@dataclass
class MovementCalculation:
    """移动计算结果"""
    mouse_delta_x: int
    mouse_delta_y: int
    pixel_distance: float
    movement_strategy: MovementStrategy
    target_type: TargetType
    calculation_time: float
    confidence: float = 1.0


@dataclass
class TargetPrediction:
    """目标预测"""
    predicted_x: float
    predicted_y: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    prediction_time: float = 0.0


class AbsolutePositionCalculator:
    """
    绝对定位计算器
    
    核心功能：
    1. 计算精确的移动量
    2. 基于目标类型优化移动策略
    3. 集成运动预测算法
    4. 提供误差补偿和精度验证
    """
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        """
        初始化计算器
        
        Args:
            coordinate_mapper: 坐标映射器
        """
        self.coordinate_mapper = coordinate_mapper
        
        # 计算统计
        self.calculation_count = 0
        self.total_calculation_time = 0.0
        self.accuracy_history: List[float] = []
        
        # 预测参数
        self.prediction_time_ms = 50  # 预测时间窗口(毫秒)
        self.velocity_smoothing = 0.3  # 速度平滑因子
        
        # 补偿参数
        self.hardware_latency_ms = 5   # 硬件延迟补偿
        self.system_latency_ms = 10    # 系统延迟补偿
        
        # 精度参数 - 基于实际性能优化
        self.distance_precision_map = {
            (0, 50): 0.98,     # 近距离 - 高精度，但不是完美
            (50, 150): 0.95,   # 中近距离 - 良好精度
            (150, 300): 0.92,  # 中距离 - 可接受精度
            (300, 500): 0.88,  # 远距离 - 降低期望
            (500, float('inf')): 0.82  # 极远距离 - 基础精度
        }
        
        # 目标特定参数
        self.target_compensation = {
            TargetType.HEAD: {
                'precision_bonus': 0.1,
                'speed_factor': 0.9,    # 稍慢但更精确
                'overshoot_tolerance': 0.5
            },
            TargetType.BODY: {
                'precision_bonus': 0.05,
                'speed_factor': 1.0,    # 标准速度
                'overshoot_tolerance': 1.0
            },
            TargetType.GENERAL: {
                'precision_bonus': 0.0,
                'speed_factor': 1.1,    # 稍快
                'overshoot_tolerance': 1.5
            }
        }
    
    def calculate_move_to_target(self, current_x: float, current_y: float,
                               target_x: float, target_y: float,
                               target_type: TargetType = TargetType.GENERAL,
                               target_velocity: Optional[Tuple[float, float]] = None) -> MovementCalculation:
        """
        计算到达目标所需的移动量
        
        Args:
            current_x: 当前X坐标
            current_y: 当前Y坐标
            target_x: 目标X坐标
            target_y: 目标Y坐标
            target_type: 目标类型
            target_velocity: 目标速度 (vx, vy)，可选
            
        Returns:
            MovementCalculation: 移动计算结果
        """
        start_time = time.time()
        
        # 基础距离计算
        pixel_delta_x = target_x - current_x
        pixel_delta_y = target_y - current_y
        pixel_distance = math.sqrt(pixel_delta_x**2 + pixel_delta_y**2)
        
        # 选择移动策略
        strategy = self._select_movement_strategy(pixel_distance, target_velocity)
        
        # 应用策略计算
        if strategy == MovementStrategy.PREDICTIVE and target_velocity:
            adjusted_x, adjusted_y = self._calculate_predictive_target(
                target_x, target_y, target_velocity
            )
            pixel_delta_x = adjusted_x - current_x
            pixel_delta_y = adjusted_y - current_y
        elif strategy == MovementStrategy.COMPENSATED:
            pixel_delta_x, pixel_delta_y = self._apply_compensation(
                pixel_delta_x, pixel_delta_y, target_type, pixel_distance
            )
        
        # 应用目标类型特定调整
        pixel_delta_x, pixel_delta_y = self._apply_target_type_adjustment(
            pixel_delta_x, pixel_delta_y, target_type, pixel_distance
        )
        
        # 转换为鼠标移动单位
        mouse_delta_x, mouse_delta_y = self.coordinate_mapper.screen_to_mouse_units(
            pixel_delta_x, pixel_delta_y
        )
        
        # 计算置信度
        confidence = self._calculate_movement_confidence(pixel_distance, target_type)
        
        # 记录统计
        calculation_time = time.time() - start_time
        self._record_calculation_stats(calculation_time)
        
        return MovementCalculation(
            mouse_delta_x=mouse_delta_x,
            mouse_delta_y=mouse_delta_y,
            pixel_distance=pixel_distance,
            movement_strategy=strategy,
            target_type=target_type,
            calculation_time=calculation_time,
            confidence=confidence
        )
    
    def calculate_multi_step_movement(self, current_x: float, current_y: float,
                                    target_x: float, target_y: float,
                                    max_steps: int = 3,
                                    target_type: TargetType = TargetType.GENERAL) -> List[MovementCalculation]:
        """
        计算多步骤移动（用于极远距离或高精度要求）
        
        Args:
            current_x: 当前X坐标
            current_y: 当前Y坐标
            target_x: 目标X坐标
            target_y: 目标Y坐标
            max_steps: 最大步骤数
            target_type: 目标类型
            
        Returns:
            List[MovementCalculation]: 分步移动计算结果
        """
        pixel_distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
        
        # 如果距离较小，直接使用单步移动
        if pixel_distance < 200 or max_steps <= 1:
            return [self.calculate_move_to_target(current_x, current_y, target_x, target_y, target_type)]
        
        # 计算分步移动
        movements = []
        step_x = current_x
        step_y = current_y
        
        for i in range(max_steps):
            # 计算这一步的目标位置
            progress = (i + 1) / max_steps
            
            # 使用非线性进度函数，前期快速移动，后期精确调整
            if i < max_steps - 1:
                # 前期使用更大的步长
                progress = progress ** 0.7
            else:
                # 最后一步确保到达精确位置
                progress = 1.0
            
            step_target_x = current_x + (target_x - current_x) * progress
            step_target_y = current_y + (target_y - current_y) * progress
            
            # 计算这一步的移动
            movement = self.calculate_move_to_target(
                step_x, step_y, step_target_x, step_target_y, target_type
            )
            
            movements.append(movement)
            
            # 更新下一步的起始位置
            pixel_delta_x, pixel_delta_y = self.coordinate_mapper.mouse_to_screen_units(
                movement.mouse_delta_x, movement.mouse_delta_y
            )
            step_x += pixel_delta_x
            step_y += pixel_delta_y
        
        return movements
    
    def _select_movement_strategy(self, distance: float, 
                                target_velocity: Optional[Tuple[float, float]]) -> MovementStrategy:
        """选择移动策略"""
        if target_velocity and (abs(target_velocity[0]) > 5 or abs(target_velocity[1]) > 5):
            return MovementStrategy.PREDICTIVE
        elif distance > 300:
            return MovementStrategy.COMPENSATED
        else:
            return MovementStrategy.DIRECT
    
    def _calculate_predictive_target(self, target_x: float, target_y: float,
                                   velocity: Tuple[float, float]) -> Tuple[float, float]:
        """计算预测目标位置"""
        vx, vy = velocity
        
        # 考虑总延迟时间
        total_latency = (self.prediction_time_ms + self.hardware_latency_ms + self.system_latency_ms) / 1000.0
        
        # 预测目标位置
        predicted_x = target_x + vx * total_latency
        predicted_y = target_y + vy * total_latency
        
        return predicted_x, predicted_y
    
    def _apply_compensation(self, delta_x: float, delta_y: float,
                          target_type: TargetType, distance: float) -> Tuple[float, float]:
        """应用补偿调整"""
        # 距离补偿 - 远距离需要更大的移动量
        if distance > 400:
            distance_factor = 1.02  # 2% 增加
        elif distance > 200:
            distance_factor = 1.01  # 1% 增加
        else:
            distance_factor = 1.0
        
        # 方向补偿 - 对角线移动的精度调整
        angle = math.atan2(delta_y, delta_x)
        diagonal_compensation = 1.0
        
        # 在45度角附近增加少量补偿
        angle_deg = math.degrees(angle) % 90
        if 40 <= angle_deg <= 50:
            diagonal_compensation = 1.005  # 0.5% 增加
        
        return (delta_x * distance_factor * diagonal_compensation,
                delta_y * distance_factor * diagonal_compensation)
    
    def _apply_target_type_adjustment(self, delta_x: float, delta_y: float,
                                    target_type: TargetType, distance: float) -> Tuple[float, float]:
        """应用目标类型特定调整"""
        adjustment = self.target_compensation[target_type]
        speed_factor = adjustment['speed_factor']
        
        # 对于头部目标，在中等距离时增加精度补偿
        if target_type == TargetType.HEAD and 100 <= distance <= 300:
            precision_bonus = adjustment['precision_bonus']
            speed_factor *= (1.0 + precision_bonus)
        
        return delta_x * speed_factor, delta_y * speed_factor
    
    def _calculate_movement_confidence(self, distance: float, target_type: TargetType) -> float:
        """计算移动置信度"""
        # 基于距离的基础置信度
        base_confidence = 1.0
        for (min_dist, max_dist), precision in self.distance_precision_map.items():
            if min_dist <= distance < max_dist:
                base_confidence = precision
                break
        
        # 目标类型调整
        type_bonus = self.target_compensation[target_type]['precision_bonus']
        
        # 历史精度调整
        history_factor = 1.0
        if len(self.accuracy_history) >= 5:
            recent_accuracy = sum(self.accuracy_history[-5:]) / 5
            history_factor = min(1.2, max(0.8, recent_accuracy))
        
        return min(1.0, base_confidence + type_bonus) * history_factor
    
    def _record_calculation_stats(self, calculation_time: float):
        """记录计算统计"""
        self.calculation_count += 1
        self.total_calculation_time += calculation_time
    
    def validate_movement_result(self, calculation: MovementCalculation,
                               expected_precision: float = 2.0) -> bool:
        """
        验证移动计算结果
        
        Args:
            calculation: 移动计算结果
            expected_precision: 期望精度（像素）
            
        Returns:
            bool: 计算结果是否满足精度要求
        """
        # 严格的置信度要求
        min_confidence = 0.8  # 提高到0.8，确保高质量计算
        if calculation.confidence < min_confidence:
            return False
        
        # 更严格的距离合理性检查
        max_screen_diagonal = math.sqrt(1920**2 + 1080**2)  # 约2203px
        if calculation.pixel_distance > max_screen_diagonal * 1.1:  # 允许10%余量
            return False
        
        # 更严格的移动量合理性检查
        max_reasonable_move = 1500  # 降低最大鼠标移动量限制
        if (abs(calculation.mouse_delta_x) > max_reasonable_move or 
            abs(calculation.mouse_delta_y) > max_reasonable_move):
            return False
        
        # 检查零移动情况
        if (abs(calculation.mouse_delta_x) < 1 and abs(calculation.mouse_delta_y) < 1 
            and calculation.pixel_distance > expected_precision):
            return False  # 距离大但移动量为零，计算有误
        
        # 检查移动效率 - 移动量应该与像素距离成比例
        if calculation.pixel_distance > 10:  # 只对较大移动检查
            mouse_magnitude = math.sqrt(calculation.mouse_delta_x**2 + calculation.mouse_delta_y**2)
            efficiency = mouse_magnitude / calculation.pixel_distance
            
            # 效率应该在合理范围内（0.5-3.0）
            if efficiency < 0.5 or efficiency > 3.0:
                return False
        
        return True
    
    def optimize_for_hardware(self, hardware_type: str, settings: Dict):
        """
        针对特定硬件优化计算参数
        
        Args:
            hardware_type: 硬件类型 ("mousecontrol", "ghub", "logitech")
            settings: 硬件特定设置
        """
        if hardware_type.lower() == "mousecontrol":
            # MouseControl.dll 优化
            self.hardware_latency_ms = 2
            self.system_latency_ms = 5
        elif hardware_type.lower() == "ghub":
            # G HUB 优化
            self.hardware_latency_ms = 8
            self.system_latency_ms = 12
        elif hardware_type.lower() == "logitech":
            # Logitech 驱动优化
            self.hardware_latency_ms = 10
            self.system_latency_ms = 15
        
        # 应用自定义设置
        if 'latency_compensation' in settings:
            self.hardware_latency_ms = settings['latency_compensation']
        if 'prediction_time' in settings:
            self.prediction_time_ms = settings['prediction_time']
    
    def get_calculation_statistics(self) -> Dict:
        """
        获取计算统计信息
        
        Returns:
            Dict: 统计信息
        """
        avg_calculation_time = (self.total_calculation_time / max(1, self.calculation_count))
        avg_accuracy = sum(self.accuracy_history) / max(1, len(self.accuracy_history))
        
        return {
            'total_calculations': self.calculation_count,
            'average_calculation_time_ms': avg_calculation_time * 1000,
            'average_accuracy': avg_accuracy,
            'accuracy_samples': len(self.accuracy_history),
            'hardware_latency_ms': self.hardware_latency_ms,
            'system_latency_ms': self.system_latency_ms,
            'prediction_window_ms': self.prediction_time_ms,
            'coordinate_mapper_info': self.coordinate_mapper.get_mapping_info()
        }
    
    def record_movement_accuracy(self, target_distance: float, actual_error: float):
        """
        记录移动精度
        
        Args:
            target_distance: 目标距离
            actual_error: 实际误差
        """
        if target_distance > 0:
            accuracy = max(0.0, 1.0 - (actual_error / target_distance))
            self.accuracy_history.append(accuracy)
            
            # 保持历史记录长度
            if len(self.accuracy_history) > 50:
                self.accuracy_history.pop(0)
    
    def reset_statistics(self):
        """重置统计信息"""
        self.calculation_count = 0
        self.total_calculation_time = 0.0
        self.accuracy_history.clear()
    
    def create_target_prediction(self, current_position: Tuple[float, float],
                               previous_positions: List[Tuple[float, float, float]]) -> TargetPrediction:
        """
        基于历史位置创建目标预测
        
        Args:
            current_position: 当前位置 (x, y)
            previous_positions: 历史位置列表 [(x, y, timestamp), ...]
            
        Returns:
            TargetPrediction: 目标预测结果
        """
        if len(previous_positions) < 2:
            return TargetPrediction(
                predicted_x=current_position[0],
                predicted_y=current_position[1]
            )
        
        # 计算速度
        recent_pos = previous_positions[-2:]
        dt = recent_pos[1][2] - recent_pos[0][2]
        
        if dt > 0:
            vx = (recent_pos[1][0] - recent_pos[0][0]) / dt
            vy = (recent_pos[1][1] - recent_pos[0][1]) / dt
            
            # 应用速度平滑
            if len(previous_positions) >= 3:
                prev_dt = recent_pos[0][2] - previous_positions[-3][2]
                if prev_dt > 0:
                    prev_vx = (recent_pos[0][0] - previous_positions[-3][0]) / prev_dt
                    prev_vy = (recent_pos[0][1] - previous_positions[-3][1]) / prev_dt
                    
                    vx = vx * self.velocity_smoothing + prev_vx * (1 - self.velocity_smoothing)
                    vy = vy * self.velocity_smoothing + prev_vy * (1 - self.velocity_smoothing)
        else:
            vx = vy = 0.0
        
        # 预测未来位置
        prediction_time_s = self.prediction_time_ms / 1000.0
        predicted_x = current_position[0] + vx * prediction_time_s
        predicted_y = current_position[1] + vy * prediction_time_s
        
        return TargetPrediction(
            predicted_x=predicted_x,
            predicted_y=predicted_y,
            velocity_x=vx,
            velocity_y=vy,
            prediction_time=prediction_time_s
        )