"""
预测性移动功能模块
PredictiveMovement

专门处理移动目标的预测和拦截
实现智能的运动预测和弹道计算
"""

import math
import time
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class MovementPattern(Enum):
    """移动模式"""
    LINEAR = "linear"              # 线性移动
    CURVED = "curved"              # 曲线移动
    OSCILLATING = "oscillating"    # 振荡移动
    ACCELERATING = "accelerating"  # 加速移动
    RANDOM = "random"              # 随机移动
    STATIONARY = "stationary"      # 静止


@dataclass
class TargetState:
    """目标状态"""
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    acceleration: Tuple[float, float]
    timestamp: float
    confidence: float


@dataclass
class PredictionResult:
    """预测结果"""
    predicted_position: Tuple[float, float]
    interception_point: Tuple[float, float]
    time_to_intercept: float
    prediction_confidence: float
    movement_pattern: MovementPattern
    recommended_aim_adjustment: Tuple[float, float]


class PredictiveMovement:
    """预测性移动系统"""
    
    def __init__(self, screen_width: int = 1920, screen_height: int = 1080):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 目标跟踪历史
        self.target_history: List[TargetState] = []
        self.max_history_length = 20
        
        # 预测参数
        self.prediction_accuracy = 0.95
        self.max_prediction_time = 1.0  # 最大预测时间（秒）
        self.min_velocity_threshold = 10.0  # 最小速度阈值（像素/秒）
        
        # 系统延迟补偿
        self.system_latency_ms = 8.0
        self.processing_latency_ms = 3.0
        self.hardware_latency_ms = 5.0
        
        # 移动模式检测
        self.pattern_detection_window = 10
        self.current_pattern = MovementPattern.STATIONARY
        
        # 性能统计
        self.prediction_stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'average_accuracy': 0.0,
            'pattern_distribution': {pattern: 0 for pattern in MovementPattern}
        }
    
    def update_target_state(self, position: Tuple[float, float], 
                          timestamp: Optional[float] = None) -> TargetState:
        """
        更新目标状态
        
        Args:
            position: 目标位置
            timestamp: 时间戳
            
        Returns:
            TargetState: 更新后的目标状态
        """
        if timestamp is None:
            timestamp = time.time()
        
        # 计算速度和加速度
        velocity = (0.0, 0.0)
        acceleration = (0.0, 0.0)
        confidence = 1.0
        
        if len(self.target_history) >= 1:
            # 计算速度
            last_state = self.target_history[-1]
            dt = timestamp - last_state.timestamp
            
            if dt > 0:
                velocity = (
                    (position[0] - last_state.position[0]) / dt,
                    (position[1] - last_state.position[1]) / dt
                )
            
            # 计算加速度
            if len(self.target_history) >= 2:
                dt2 = last_state.timestamp - self.target_history[-2].timestamp
                if dt2 > 0:
                    acceleration = (
                        (velocity[0] - last_state.velocity[0]) / dt,
                        (velocity[1] - last_state.velocity[1]) / dt
                    )
        
        # 创建新状态
        new_state = TargetState(
            position=position,
            velocity=velocity,
            acceleration=acceleration,
            timestamp=timestamp,
            confidence=confidence
        )
        
        # 添加到历史
        self.target_history.append(new_state)
        
        # 保持历史长度
        if len(self.target_history) > self.max_history_length:
            self.target_history.pop(0)
        
        # 检测移动模式
        self.current_pattern = self._detect_movement_pattern()
        
        return new_state
    
    def predict_target_position(self, prediction_time: float) -> PredictionResult:
        """
        预测目标位置
        
        Args:
            prediction_time: 预测时间（秒）
            
        Returns:
            PredictionResult: 预测结果
        """
        if not self.target_history:
            return PredictionResult(
                predicted_position=(0, 0),
                interception_point=(0, 0),
                time_to_intercept=0,
                prediction_confidence=0,
                movement_pattern=MovementPattern.STATIONARY,
                recommended_aim_adjustment=(0, 0)
            )
        
        current_state = self.target_history[-1]
        
        # 根据移动模式选择预测方法
        if self.current_pattern == MovementPattern.LINEAR:
            predicted_pos = self._predict_linear_movement(current_state, prediction_time)
        elif self.current_pattern == MovementPattern.CURVED:
            predicted_pos = self._predict_curved_movement(current_state, prediction_time)
        elif self.current_pattern == MovementPattern.ACCELERATING:
            predicted_pos = self._predict_accelerated_movement(current_state, prediction_time)
        elif self.current_pattern == MovementPattern.OSCILLATING:
            predicted_pos = self._predict_oscillating_movement(current_state, prediction_time)
        else:  # STATIONARY or RANDOM
            predicted_pos = current_state.position
        
        # 边界约束
        predicted_pos = self._constrain_to_screen(predicted_pos)
        
        # 计算拦截点
        interception_point = self._calculate_interception_point(current_state, predicted_pos, prediction_time)
        
        # 计算预测置信度
        confidence = self._calculate_prediction_confidence()
        
        # 计算瞄准调整建议
        aim_adjustment = self._calculate_aim_adjustment(interception_point, current_state.position)
        
        result = PredictionResult(
            predicted_position=predicted_pos,
            interception_point=interception_point,
            time_to_intercept=prediction_time,
            prediction_confidence=confidence,
            movement_pattern=self.current_pattern,
            recommended_aim_adjustment=aim_adjustment
        )
        
        # 更新统计
        self.prediction_stats['total_predictions'] += 1
        self.prediction_stats['pattern_distribution'][self.current_pattern] += 1
        
        return result
    
    def predict_interception(self, mouse_response_time: float = 0.05) -> PredictionResult:
        """
        预测拦截点
        
        Args:
            mouse_response_time: 鼠标响应时间（秒）
            
        Returns:
            PredictionResult: 拦截预测结果
        """
        # 计算总延迟时间
        total_latency = (
            self.system_latency_ms + 
            self.processing_latency_ms + 
            self.hardware_latency_ms
        ) / 1000.0 + mouse_response_time
        
        return self.predict_target_position(total_latency)
    
    def _detect_movement_pattern(self) -> MovementPattern:
        """
        检测移动模式
        
        Returns:
            MovementPattern: 检测到的移动模式
        """
        if len(self.target_history) < 3:
            return MovementPattern.STATIONARY
        
        recent_states = self.target_history[-self.pattern_detection_window:]
        
        # 计算总体速度
        velocities = [math.sqrt(s.velocity[0]**2 + s.velocity[1]**2) for s in recent_states]
        avg_velocity = sum(velocities) / len(velocities)
        
        if avg_velocity < self.min_velocity_threshold:
            return MovementPattern.STATIONARY
        
        # 分析速度变化
        velocity_changes = []
        for i in range(1, len(velocities)):
            velocity_changes.append(abs(velocities[i] - velocities[i-1]))
        
        avg_velocity_change = sum(velocity_changes) / len(velocity_changes) if velocity_changes else 0
        
        # 分析方向变化
        directions = []
        for state in recent_states:
            if state.velocity[0] != 0 or state.velocity[1] != 0:
                direction = math.atan2(state.velocity[1], state.velocity[0])
                directions.append(direction)
        
        direction_changes = []
        for i in range(1, len(directions)):
            change = abs(directions[i] - directions[i-1])
            # 处理角度环绕
            if change > math.pi:
                change = 2 * math.pi - change
            direction_changes.append(change)
        
        avg_direction_change = sum(direction_changes) / len(direction_changes) if direction_changes else 0
        
        # 分析加速度
        accelerations = [math.sqrt(s.acceleration[0]**2 + s.acceleration[1]**2) for s in recent_states]
        avg_acceleration = sum(accelerations) / len(accelerations)
        
        # 模式判断
        if avg_velocity_change < avg_velocity * 0.1 and avg_direction_change < 0.2:
            return MovementPattern.LINEAR
        elif avg_acceleration > avg_velocity * 0.5:
            return MovementPattern.ACCELERATING
        elif avg_direction_change > 1.0:
            return MovementPattern.OSCILLATING
        elif avg_direction_change > 0.3:
            return MovementPattern.CURVED
        else:
            return MovementPattern.RANDOM
    
    def _predict_linear_movement(self, state: TargetState, time_delta: float) -> Tuple[float, float]:
        """
        预测线性移动
        
        Args:
            state: 当前状态
            time_delta: 时间增量
            
        Returns:
            Tuple[float, float]: 预测位置
        """
        predicted_x = state.position[0] + state.velocity[0] * time_delta
        predicted_y = state.position[1] + state.velocity[1] * time_delta
        
        return predicted_x, predicted_y
    
    def _predict_curved_movement(self, state: TargetState, time_delta: float) -> Tuple[float, float]:
        """
        预测曲线移动
        
        Args:
            state: 当前状态
            time_delta: 时间增量
            
        Returns:
            Tuple[float, float]: 预测位置
        """
        # 使用二次预测模型
        predicted_x = (state.position[0] + 
                      state.velocity[0] * time_delta + 
                      0.5 * state.acceleration[0] * time_delta**2)
        
        predicted_y = (state.position[1] + 
                      state.velocity[1] * time_delta + 
                      0.5 * state.acceleration[1] * time_delta**2)
        
        return predicted_x, predicted_y
    
    def _predict_accelerated_movement(self, state: TargetState, time_delta: float) -> Tuple[float, float]:
        """
        预测加速移动
        
        Args:
            state: 当前状态
            time_delta: 时间增量
            
        Returns:
            Tuple[float, float]: 预测位置
        """
        # 考虑更强的加速度影响
        acceleration_factor = 1.2  # 加速度权重增加
        
        predicted_x = (state.position[0] + 
                      state.velocity[0] * time_delta + 
                      acceleration_factor * 0.5 * state.acceleration[0] * time_delta**2)
        
        predicted_y = (state.position[1] + 
                      state.velocity[1] * time_delta + 
                      acceleration_factor * 0.5 * state.acceleration[1] * time_delta**2)
        
        return predicted_x, predicted_y
    
    def _predict_oscillating_movement(self, state: TargetState, time_delta: float) -> Tuple[float, float]:
        """
        预测振荡移动
        
        Args:
            state: 当前状态
            time_delta: 时间增量
            
        Returns:
            Tuple[float, float]: 预测位置
        """
        # 对于振荡移动，减少预测距离
        damping_factor = 0.7
        
        predicted_x = state.position[0] + state.velocity[0] * time_delta * damping_factor
        predicted_y = state.position[1] + state.velocity[1] * time_delta * damping_factor
        
        return predicted_x, predicted_y
    
    def _constrain_to_screen(self, position: Tuple[float, float]) -> Tuple[float, float]:
        """
        将位置约束到屏幕范围内
        
        Args:
            position: 原始位置
            
        Returns:
            Tuple[float, float]: 约束后的位置
        """
        x, y = position
        x = max(0, min(self.screen_width, x))
        y = max(0, min(self.screen_height, y))
        return x, y
    
    def _calculate_interception_point(self, current_state: TargetState, 
                                    predicted_pos: Tuple[float, float],
                                    time_delta: float) -> Tuple[float, float]:
        """
        计算拦截点
        
        Args:
            current_state: 当前状态
            predicted_pos: 预测位置
            time_delta: 时间增量
            
        Returns:
            Tuple[float, float]: 拦截点
        """
        # 简单的拦截点计算：预测位置的权重平均
        weight_current = 0.3
        weight_predicted = 0.7
        
        intercept_x = (current_state.position[0] * weight_current + 
                      predicted_pos[0] * weight_predicted)
        intercept_y = (current_state.position[1] * weight_current + 
                      predicted_pos[1] * weight_predicted)
        
        return intercept_x, intercept_y
    
    def _calculate_prediction_confidence(self) -> float:
        """
        计算预测置信度
        
        Returns:
            float: 置信度 (0-1)
        """
        if len(self.target_history) < 3:
            return 0.5
        
        # 基于历史数据一致性计算置信度
        recent_states = self.target_history[-5:]
        
        # 速度一致性
        velocities = [math.sqrt(s.velocity[0]**2 + s.velocity[1]**2) for s in recent_states]
        if len(velocities) > 1:
            velocity_variance = sum((v - sum(velocities)/len(velocities))**2 for v in velocities) / len(velocities)
            velocity_consistency = 1.0 / (1.0 + velocity_variance / 100.0)
        else:
            velocity_consistency = 0.5
        
        # 数据新鲜度
        current_time = time.time()
        last_update = self.target_history[-1].timestamp
        data_freshness = max(0.0, 1.0 - (current_time - last_update) / 0.5)  # 0.5秒内的数据认为是新鲜的
        
        # 移动模式置信度
        pattern_confidence = {
            MovementPattern.LINEAR: 0.9,
            MovementPattern.CURVED: 0.8,
            MovementPattern.ACCELERATING: 0.75,
            MovementPattern.OSCILLATING: 0.6,
            MovementPattern.RANDOM: 0.3,
            MovementPattern.STATIONARY: 0.95
        }.get(self.current_pattern, 0.5)
        
        # 综合置信度
        confidence = (velocity_consistency * 0.4 + 
                     data_freshness * 0.3 + 
                     pattern_confidence * 0.3)
        
        return min(1.0, max(0.0, confidence))
    
    def _calculate_aim_adjustment(self, target_pos: Tuple[float, float], 
                                current_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        计算瞄准调整建议
        
        Args:
            target_pos: 目标位置
            current_pos: 当前位置
            
        Returns:
            Tuple[float, float]: 瞄准调整量
        """
        adjustment_x = target_pos[0] - current_pos[0]
        adjustment_y = target_pos[1] - current_pos[1]
        
        return adjustment_x, adjustment_y
    
    def get_movement_analysis(self) -> Dict[str, Any]:
        """
        获取移动分析报告
        
        Returns:
            Dict[str, Any]: 移动分析数据
        """
        if not self.target_history:
            return {
                'current_pattern': MovementPattern.STATIONARY.value,
                'confidence': 0.0,
                'analysis': '无数据'
            }
        
        current_state = self.target_history[-1]
        velocity_magnitude = math.sqrt(current_state.velocity[0]**2 + current_state.velocity[1]**2)
        acceleration_magnitude = math.sqrt(current_state.acceleration[0]**2 + current_state.acceleration[1]**2)
        
        return {
            'current_pattern': self.current_pattern.value,
            'confidence': self._calculate_prediction_confidence(),
            'velocity_magnitude': velocity_magnitude,
            'acceleration_magnitude': acceleration_magnitude,
            'data_points': len(self.target_history),
            'prediction_stats': self.prediction_stats,
            'recommended_prediction_time': self._get_optimal_prediction_time()
        }
    
    def _get_optimal_prediction_time(self) -> float:
        """
        获取最优预测时间
        
        Returns:
            float: 最优预测时间（秒）
        """
        if not self.target_history:
            return 0.05
        
        # 基于移动模式和速度确定最优预测时间
        current_state = self.target_history[-1]
        velocity_magnitude = math.sqrt(current_state.velocity[0]**2 + current_state.velocity[1]**2)
        
        base_time = {
            MovementPattern.LINEAR: 0.1,
            MovementPattern.CURVED: 0.08,
            MovementPattern.ACCELERATING: 0.06,
            MovementPattern.OSCILLATING: 0.04,
            MovementPattern.RANDOM: 0.03,
            MovementPattern.STATIONARY: 0.02
        }.get(self.current_pattern, 0.05)
        
        # 根据速度调整
        if velocity_magnitude > 500:  # 高速移动
            base_time *= 1.5
        elif velocity_magnitude < 50:  # 低速移动
            base_time *= 0.5
        
        return min(self.max_prediction_time, max(0.01, base_time))
    
    def reset_tracking(self):
        """
        重置跟踪数据
        """
        self.target_history.clear()
        self.current_pattern = MovementPattern.STATIONARY
        
        # 重置统计
        self.prediction_stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'average_accuracy': 0.0,
            'pattern_distribution': {pattern: 0 for pattern in MovementPattern}
        }
    
    def update_prediction_accuracy(self, actual_position: Tuple[float, float], 
                                 predicted_position: Tuple[float, float]):
        """
        更新预测精度统计
        
        Args:
            actual_position: 实际位置
            predicted_position: 预测位置
        """
        error = math.sqrt(
            (actual_position[0] - predicted_position[0])**2 + 
            (actual_position[1] - predicted_position[1])**2
        )
        
        # 判断是否成功（误差小于50像素）
        if error < 50:
            self.prediction_stats['successful_predictions'] += 1
        
        # 更新平均精度
        current_avg = self.prediction_stats['average_accuracy']
        total_predictions = self.prediction_stats['total_predictions']
        
        if total_predictions > 0:
            accuracy = max(0, 1.0 - error / 100.0)  # 100像素误差对应0精度
            new_avg = (current_avg * (total_predictions - 1) + accuracy) / total_predictions
            self.prediction_stats['average_accuracy'] = new_avg