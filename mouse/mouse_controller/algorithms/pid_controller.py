"""
相对坐标PID控制器 - 专门用于游戏瞄准场景
基于累积移动量的相对坐标系统，无需屏幕坐标依赖
"""

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Dict, List, Optional


@dataclass
class VelocityPIDParams:
    """PID参数配置"""
    kp: float
    ki: float
    kd: float
    max_velocity: float = 50.0
    damping_factor: float = 1.0


class MovementIntent(Enum):
    """移动意图分类"""
    MICRO = "micro"          # <5px: 极精确微调
    PRECISION = "precision"   # 5-30px: 精确瞄准
    BALANCED = "balanced"     # 30-100px: 平衡模式
    FAST = "fast"            # 100-250px: 快速移动
    ULTRA_FAST = "ultra_fast" # >250px: 超快速移动


class RelativeMovementTracker:
    """相对移动量跟踪器 - 替代屏幕坐标依赖"""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        """重置跟踪器"""
        self.cumulative_x = 0  # 累积X移动量
        self.cumulative_y = 0  # 累积Y移动量
        self.total_distance = 0  # 总移动距离
        self.move_count = 0  # 移动次数
        
    def apply_movement(self, dx: int, dy: int):
        """应用一次移动"""
        self.cumulative_x += dx
        self.cumulative_y += dy
        self.total_distance += math.sqrt(dx*dx + dy*dy)
        self.move_count += 1
        
    def get_remaining_distance(self, target_x: int, target_y: int) -> float:
        """计算到目标的剩余距离"""
        return math.sqrt(
            (target_x - self.cumulative_x)**2 + 
            (target_y - self.cumulative_y)**2
        )
    
    def get_statistics(self) -> dict:
        """获取移动统计信息"""
        return {
            'total_moves': self.move_count,
            'total_distance': self.total_distance,
            'average_step': self.total_distance / max(1, self.move_count),
            'final_position': (self.cumulative_x, self.cumulative_y)
        }


class VelocityAwarePIDController:
    """
    相对坐标速度感知PID控制器
    保持原有算法优势，支持纯相对坐标移动
    """
    
    def __init__(self):
        # 针对离散PID系统优化的参数集
        base_params = VelocityPIDParams(
            kp=0.5,    # 保持响应速度
            ki=0.01,   # 降低积分系数，避免累积误差
            kd=0.005,  # 降低微分系数，减少震荡
            max_velocity=50.0, 
            damping_factor=1.0
        )
        
        # 为不同移动意图配置参数
        self.params = {intent: base_params for intent in MovementIntent}
        
        # 游戏优化参数
        self.head_target_params = VelocityPIDParams(
            kp=0.6, ki=0.008, kd=0.004,
            max_velocity=40.0, damping_factor=0.9
        )
        
        self.body_target_params = VelocityPIDParams(
            kp=0.5, ki=0.01, kd=0.005,
            max_velocity=50.0, damping_factor=1.0
        )
        
        self.reset()
    
    def reset(self):
        """重置PID状态"""
        self.previous_error_x = 0
        self.previous_error_y = 0
        self.integral_x = 0
        self.integral_y = 0
        self.velocity_history = []
        self.movement_intent = MovementIntent.BALANCED
        
    def detect_movement_intent(self, distance: float) -> MovementIntent:
        """基于相对距离检测移动意图"""
        if distance < 5:
            return MovementIntent.MICRO
        elif distance < 30:
            return MovementIntent.PRECISION  
        elif distance < 100:
            return MovementIntent.BALANCED
        elif distance < 250:
            return MovementIntent.FAST
        else:
            return MovementIntent.ULTRA_FAST
    
    def calculate_velocity_factor(self, distance: float, target_velocity: float) -> float:
        """速度感知调节因子"""
        if distance < 5:
            return 0.9
        elif distance < 30:
            return 1.0
        elif distance < 100:
            return 1.1
        elif distance < 250:
            return 1.2
        else:
            return 1.3
    
    def calculate_adaptive_movement_limit(self, distance: float) -> int:
        """基于剩余距离的自适应移动限制"""
        if distance > 200:
            return 80   # 大距离: 快速接近
        elif distance > 100:
            return 60   # 中距离: 平衡速度与精度
        elif distance > 50:
            return 40   # 接近目标: 提高精度
        elif distance > 20:
            return 25   # 精确调整: 小步长
        else:
            return 15   # 最终精调: 最小步长
    
    def compute_velocity_aware_output(self, target_x: float, target_y: float, current_x: float, current_y: float, is_head_target: bool = False):
        """计算速度感知PID输出"""
        # 计算距离和运动意图
        distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
        self.movement_intent = self.detect_movement_intent(distance)
        
        # 选择合适的参数集
        if is_head_target:
            params = self.head_target_params
        else:
            params = self.body_target_params
        
        # 计算误差
        error_x = target_x - current_x
        error_y = target_y - current_y
        
        # 如果误差非常小，直接返回0
        if abs(error_x) < 1e-6 and abs(error_y) < 1e-6:
            return 0.0, 0.0
        
        # 离散积分项计算
        self.integral_x += error_x
        self.integral_y += error_y
        
        # 积分限幅
        max_integral = 50.0
        self.integral_x = max(-max_integral, min(max_integral, self.integral_x))
        self.integral_y = max(-max_integral, min(max_integral, self.integral_y))
        
        # 离散微分项计算
        derivative_x = error_x - self.previous_error_x
        derivative_y = error_y - self.previous_error_y
        
        # PID输出计算(离散形式)
        output_x = (params.kp * error_x + 
                   params.ki * self.integral_x + 
                   params.kd * derivative_x)
        output_y = (params.kp * error_y + 
                   params.ki * self.integral_y + 
                   params.kd * derivative_y)
        
        # 速度感知调节
        current_velocity = math.sqrt(output_x**2 + output_y**2)
        velocity_factor = self.calculate_velocity_factor(distance, current_velocity)
        
        # 应用速度感知因子
        output_x *= velocity_factor
        output_y *= velocity_factor
        
        # 更新历史状态
        self.previous_error_x = error_x
        self.previous_error_y = error_y
        
        return output_x, output_y
    
    def move_to_relative_target(self, driver, target_offset_x: int, target_offset_y: int, 
                              tolerance: int = 2, max_iterations: int = 200, 
                              is_head_target: bool = False) -> Tuple[bool, float, float]:
        """
        相对坐标PID移动 - 核心重构方法
        
        Args:
            driver: 驱动对象
            target_offset_x: 目标X偏移量
            target_offset_y: 目标Y偏移量
            tolerance: 容差像素
            max_iterations: 最大迭代次数
            is_head_target: 是否为头部目标
            
        Returns:
            (成功标志, 最终误差, 耗时)
        """
        try:
            start_time = time.time()
            self.reset()
            
            # 初始化累积移动跟踪器
            tracker = RelativeMovementTracker()
            
            for iteration in range(max_iterations):
                # 使用累积移动量而非屏幕坐标
                current_x = tracker.cumulative_x
                current_y = tracker.cumulative_y
                
                # 检查是否到达目标
                distance = math.sqrt(
                    (target_offset_x - current_x)**2 + 
                    (target_offset_y - current_y)**2
                )
                
                if distance <= tolerance:
                    return True, distance, time.time() - start_time
                
                # 计算PID输出
                control_x, control_y = self.compute_velocity_aware_output(
                    target_offset_x, target_offset_y, current_x, current_y, is_head_target
                )
                
                # 自适应移动限制
                adaptive_limit = self.calculate_adaptive_movement_limit(distance)
                move_x = max(-adaptive_limit, min(adaptive_limit, int(round(control_x))))
                move_y = max(-adaptive_limit, min(adaptive_limit, int(round(control_y))))
                
                # 执行相对移动
                if move_x != 0 or move_y != 0:
                    if not driver.move_relative(move_x, move_y):
                        return False, distance, time.time() - start_time
                    
                    # 更新累积移动量
                    tracker.apply_movement(move_x, move_y)
                
                time.sleep(0.001)  # 保持原有延迟
            
            # 超时返回
            final_distance = math.sqrt(
                (target_offset_x - tracker.cumulative_x)**2 + 
                (target_offset_y - tracker.cumulative_y)**2
            )
            return False, final_distance, time.time() - start_time
            
        except Exception as e:
            return False, float('inf'), time.time() - start_time
    
    def get_performance_stats(self) -> dict:
        """获取性能统计信息"""
        return {
            'current_intent': self.movement_intent.value,
            'velocity_history_size': len(self.velocity_history),
            'integral_state': (self.integral_x, self.integral_y)
        }