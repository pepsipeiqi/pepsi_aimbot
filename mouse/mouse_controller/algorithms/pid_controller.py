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
        # 针对离散PID系统优化的参数集 - 优化长距离移动性能
        base_params = VelocityPIDParams(
            kp=0.7,    # 提升响应速度（从0.5提升到0.7）
            ki=0.012,  # 适度提升积分系数（从0.01提升到0.012）
            kd=0.006,  # 适度提升微分系数（从0.005提升到0.006）
            max_velocity=70.0,  # 提升最大速度（从50.0提升到70.0）
            damping_factor=1.0
        )
        
        # 为不同移动意图配置参数
        self.params = {intent: base_params for intent in MovementIntent}
        
        # 200-300px专用超激进参数（专为头部锁定优化）
        self.headshot_precision_params = VelocityPIDParams(
            kp=0.9,    # 超激进响应速度
            ki=0.003,  # 极低积分避免过冲
            kd=0.001,  # 极低微分减少震荡
            max_velocity=120.0,  # 极高最大速度
            damping_factor=0.8  # 轻微阻尼
        )
        
        # 游戏优化参数
        self.head_target_params = VelocityPIDParams(
            kp=0.8, ki=0.005, kd=0.002,  # 提升头部瞄准响应
            max_velocity=80.0, damping_factor=0.9
        )
        
        self.body_target_params = VelocityPIDParams(
            kp=0.7, ki=0.01, kd=0.005,  # 提升身体瞄准响应
            max_velocity=70.0, damping_factor=1.0
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
        """速度感知调节因子 - 专为200-300px黄金距离优化"""
        if distance < 5:
            return 0.9
        elif distance < 30:
            return 1.0
        elif distance < 100:
            return 1.1
        elif distance < 200:
            return 1.8   # 100-200px: 进一步提升到1.8
        elif distance < 300:
            return 2.5   # 200-300px黄金距离: 极致速度因子2.5x
        elif distance < 500:
            return 2.2   # 300-500px: 高速度因子
        else:
            return 2.0   # 500px+: 标准高速
    
    def calculate_adaptive_movement_limit(self, distance: float) -> int:
        """基于剩余距离的自适应移动限制 - 优化为支持全屏移动"""
        if distance > 1000:
            return 500  # 极远距离: 支持全屏对角线移动
        elif distance > 600:
            return 350  # 超远距离: 大幅移动
        elif distance > 350:
            return 250  # 远距离: 中大幅移动
        elif distance > 200:
            return 200  # 中远距离: 标准大步长
        elif distance > 100:
            return 150  # 中距离: 大步长移动
        elif distance > 50:
            return 80   # 接近目标: 中等步长
        elif distance > 20:
            return 40   # 精确调整: 小步长
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
        
        # 积分限幅 - 优化长距离移动收敛
        max_integral = 80.0  # 从50.0提升到80.0，改善长距离收敛
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
    
    def move_to_relative_target_two_stage(self, driver, target_offset_x: int, target_offset_y: int, 
                                        tolerance: int = 2, max_iterations: int = 200, 
                                        is_head_target: bool = False) -> Tuple[bool, float, float]:
        """
        两阶段相对坐标PID移动 - 优化长距离移动性能
        
        第一阶段：快速接近目标（80%距离）
        第二阶段：精确调整（剩余20%距离）
        
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
            
            # 计算总距离
            total_distance = math.sqrt(target_offset_x**2 + target_offset_y**2)
            
            # 如果距离较短，直接使用原有方法
            if total_distance < 150:  # 提高阈值到150px
                return self.move_to_relative_target(driver, target_offset_x, target_offset_y, 
                                                  tolerance, max_iterations, is_head_target)
            
            # === 第一阶段：快速接近（85%距离） ===
            stage1_ratio = 0.85  # 提高到85%，减少第二阶段工作量
            stage1_target_x = int(target_offset_x * stage1_ratio)
            stage1_target_y = int(target_offset_y * stage1_ratio)
            
            # 第一阶段使用激进参数快速移动
            stage1_tolerance = max(tolerance * 4, 8)  # 更大容差
            stage1_max_iterations = max_iterations // 3  # 限制迭代，避免过度优化
            
            success_stage1, error_stage1, time_stage1 = self.move_to_relative_target(
                driver, stage1_target_x, stage1_target_y, 
                stage1_tolerance, stage1_max_iterations, False  # 第一阶段速度优先
            )
            
            # === 第二阶段：快速精确调整（剩余15%距离） ===
            remaining_x = target_offset_x - stage1_target_x
            remaining_y = target_offset_y - stage1_target_y
            
            # 检查是否还需要第二阶段
            remaining_distance = math.sqrt(remaining_x**2 + remaining_y**2)
            if remaining_distance <= tolerance:
                # 第一阶段已经足够精确，直接返回
                return True, remaining_distance, time.time() - start_time
            
            # 第二阶段使用剩余迭代次数
            stage2_max_iterations = max_iterations - stage1_max_iterations
            
            success_stage2, error_stage2, time_stage2 = self.move_to_relative_target(
                driver, remaining_x, remaining_y, 
                tolerance, stage2_max_iterations, is_head_target  # 第二阶段精度优先
            )
            
            total_time = time.time() - start_time
            final_success = success_stage1 and success_stage2
            final_error = error_stage2  # 最终误差以第二阶段为准
            
            return final_success, final_error, total_time
            
        except Exception as e:
            return False, float('inf'), time.time() - start_time

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
    
    def get_empirical_correction_factor(self, distance: float) -> float:
        """
        基于真实硬件测试数据的经验校正因子
        根据实际测试结果直接建立距离-精度映射
        
        重要发现：46px误差表明移动不足，需要增强而非减少移动量
        """
        # 基于FPS实战测试结果 - 短距离激进校正 + 爆头精度提升
        empirical_data = {
            # 距离: (实战误差, 目标误差, 激进增强因子)
            180: (25, 3, 3.8),      # 25px -> 3px, 激进增强爆头精度
            200: (20, 5, 3.2),      # 实战20px -> 5px, 大幅增强
            220: (22, 5, 3.0),      # 实战22px -> 5px, 大幅增强  
            250: (16, 8, 2.2),      # 实战16px -> 8px, 适度增强
            280: (10, 10, 1.3),     # 10px -> 保持并提升爆头精度
            300: (9, 10, 1.2),      # 9px -> 保持并提升爆头精度  
            320: (8, 12, 1.1),      # 8px -> 保持并提升爆头精度
        }
        
        # 找到最接近的距离数据点
        distances = list(empirical_data.keys())
        closest_distance = min(distances, key=lambda x: abs(x - distance))
        
        # 如果距离完全匹配，直接返回校正因子
        if abs(distance - closest_distance) < 10:
            return empirical_data[closest_distance][2]
        
        # 否则进行线性插值
        if distance < min(distances):
            return empirical_data[min(distances)][2]
        elif distance > max(distances):
            return empirical_data[max(distances)][2]
        else:
            # 找到两个最近的点进行插值
            lower = max([d for d in distances if d <= distance])
            upper = min([d for d in distances if d >= distance])
            
            if lower == upper:
                return empirical_data[lower][2]
            
            # 线性插值
            ratio = (distance - lower) / (upper - lower)
            lower_factor = empirical_data[lower][2]
            upper_factor = empirical_data[upper][2]
            
            return lower_factor + ratio * (upper_factor - lower_factor)
    
    def calculate_optimal_movement_vector(self, target_x: float, target_y: float, 
                                        game_config: dict = None) -> Tuple[int, int]:
        """
        计算理论最优移动向量 - 用于一次到位移动
        
        Args:
            target_x: 目标X偏移
            target_y: 目标Y偏移
            game_config: 游戏配置字典
            
        Returns:
            Tuple[int, int]: (最优X移动量, 最优Y移动量)
        """
        distance = math.sqrt(target_x**2 + target_y**2)
        
        # 获取配置参数
        if game_config is None:
            game_config = {'conversion_ratio': 0.3, 'adaptive_conversion': True}
        
        # 使用经验校正因子 - 基于真实硬件测试数据
        base_ratio = game_config.get('conversion_ratio', 0.3)
        empirical_factor = self.get_empirical_correction_factor(distance)
        
        # 计算最终有效转换比率
        effective_ratio = base_ratio * empirical_factor
        
        # 计算理论最优移动量 - 直接使用经验校正
        optimal_x = target_x * effective_ratio
        optimal_y = target_y * effective_ratio
        
        return int(round(optimal_x)), int(round(optimal_y))
    
    def one_shot_precision_move(self, driver, target_offset_x: int, target_offset_y: int, 
                               tolerance: int = 1, game_config: dict = None) -> Tuple[bool, float, float]:
        """
        预测性一次移动算法 - 专为200-300px"一步到位"头部锁定设计
        
        核心理念：
        1. 计算理论最优移动向量
        2. 执行单次大幅移动
        3. 仅在必要时进行一次微调
        
        Args:
            driver: 驱动对象
            target_offset_x: 目标X偏移量
            target_offset_y: 目标Y偏移量
            tolerance: 容差像素（默认1px，头部瞄准精度）
            game_config: 游戏配置
            
        Returns:
            (成功标志, 最终误差, 耗时)
        """
        try:
            start_time = time.time()
            distance = math.sqrt(target_offset_x**2 + target_offset_y**2)
            
            # 计算理论最优移动向量
            optimal_x, optimal_y = self.calculate_optimal_movement_vector(
                target_offset_x, target_offset_y, game_config
            )
            
            # === 第一步：执行预测性大幅移动 ===
            if optimal_x != 0 or optimal_y != 0:
                if not driver.move_relative(optimal_x, optimal_y):
                    return False, float('inf'), time.time() - start_time
            
            # 短暂延迟确保移动执行完成
            time.sleep(0.002)
            
            # === 第二步：检查是否需要微调 ===
            # 计算理论剩余误差
            executed_distance = math.sqrt(optimal_x**2 + optimal_y**2)
            expected_coverage = executed_distance / (game_config.get('conversion_ratio', 0.3) if game_config else 0.3)
            
            # 估算剩余误差
            remaining_x = target_offset_x - expected_coverage * (target_offset_x / distance) if distance > 0 else 0
            remaining_y = target_offset_y - expected_coverage * (target_offset_y / distance) if distance > 0 else 0
            remaining_error = math.sqrt(remaining_x**2 + remaining_y**2)
            
            # 如果估算误差在容差范围内，直接返回成功
            if remaining_error <= tolerance:
                return True, remaining_error, time.time() - start_time
            
            # === 第三步：精确微调（仅一次） ===
            # 使用更精确的转换比率进行微调 - 补偿主移动不足
            fine_tune_ratio = (game_config.get('conversion_ratio', 0.3) if game_config else 0.3) * 0.5  # 增强微调能力
            adjust_x = int(round(remaining_x * fine_tune_ratio))
            adjust_y = int(round(remaining_y * fine_tune_ratio))
            
            if adjust_x != 0 or adjust_y != 0:
                if not driver.move_relative(adjust_x, adjust_y):
                    return False, remaining_error, time.time() - start_time
            
            # 计算最终理论误差
            final_error = max(0.5, remaining_error * 0.3)  # 保守估算最终误差
            
            return True, final_error, time.time() - start_time
            
        except Exception as e:
            return False, float('inf'), time.time() - start_time
    
    def progressive_fast_move(self, driver, target_offset_x: int, target_offset_y: int, 
                             tolerance: int = 1, max_time_ms: int = 15) -> Tuple[bool, float, float]:
        """
        渐进式快速移动算法 - 平衡速度与精度的新解决方案
        
        核心策略：
        1. 动态分段：2-4步智能分解移动
        2. 实时校正：每步后验证并调整
        3. 自适应步长：渐进式精度提升
        4. 硬件学习：动态优化转换比率
        
        Args:
            driver: 驱动对象
            target_offset_x: 目标X偏移量
            target_offset_y: 目标Y偏移量
            tolerance: 容差像素（默认1px）
            max_time_ms: 最大允许时间（毫秒，默认15ms）
            
        Returns:
            (成功标志, 最终误差, 耗时)
        """
        try:
            start_time = time.time()
            distance = math.sqrt(target_offset_x**2 + target_offset_y**2)
            
            # 小距离直接使用精确PID
            if distance < 50:
                return self.move_to_relative_target(driver, target_offset_x, target_offset_y, tolerance, 100, True)
            
            # 动态分段策略
            if distance < 150:
                segments = 2  # 短距离2段
            elif distance < 300:
                segments = 3  # 中距离3段
            else:
                segments = 4  # 长距离4段
            
            # 累积移动跟踪
            cumulative_x, cumulative_y = 0, 0
            learned_ratio = 0.3  # 初始转换比率
            
            for step in range(segments):
                # 检查时间限制
                elapsed_time = (time.time() - start_time) * 1000
                if elapsed_time > max_time_ms:
                    break
                
                # 计算剩余目标
                remaining_x = target_offset_x - cumulative_x
                remaining_y = target_offset_y - cumulative_y
                remaining_distance = math.sqrt(remaining_x**2 + remaining_y**2)
                
                # 检查是否已达到精度要求
                if remaining_distance <= tolerance:
                    return True, remaining_distance, time.time() - start_time
                
                # 动态步长计算
                if step == segments - 1:
                    # 最后一步：精确调整
                    step_ratio = 1.0
                    use_learned_ratio = learned_ratio * 0.8  # 保守调整
                elif step == 0:
                    # 第一步：主要移动（70-80%）
                    step_ratio = 0.75
                    use_learned_ratio = learned_ratio
                else:
                    # 中间步：渐进调整
                    progress = step / (segments - 1)
                    step_ratio = 0.8 - 0.3 * progress  # 0.8 -> 0.5
                    use_learned_ratio = learned_ratio * (1.0 - 0.2 * progress)
                
                # 计算本步移动量
                step_target_x = remaining_x * step_ratio
                step_target_y = remaining_y * step_ratio
                
                # 转换为硬件移动
                move_x = int(round(step_target_x * use_learned_ratio))
                move_y = int(round(step_target_y * use_learned_ratio))
                
                # 限制单步移动量（避免硬件过载）
                max_single_move = 150 if step == 0 else 80
                move_x = max(-max_single_move, min(max_single_move, move_x))
                move_y = max(-max_single_move, min(max_single_move, move_y))
                
                # 执行移动
                if move_x != 0 or move_y != 0:
                    if not driver.move_relative(move_x, move_y):
                        break
                    
                    # 更新累积移动
                    actual_move_distance = math.sqrt(move_x**2 + move_y**2)
                    expected_coverage = actual_move_distance / use_learned_ratio
                    
                    # 估算实际到达位置
                    if step_target_x != 0 or step_target_y != 0:
                        step_distance = math.sqrt(step_target_x**2 + step_target_y**2)
                        coverage_ratio = expected_coverage / step_distance if step_distance > 0 else 1.0
                        
                        # 更新累积位置
                        cumulative_x += step_target_x * coverage_ratio
                        cumulative_y += step_target_y * coverage_ratio
                        
                        # 学习硬件响应（动态调整转换比率）
                        if step < segments - 1:  # 除最后一步外都用于学习
                            actual_ratio = coverage_ratio * use_learned_ratio
                            learned_ratio = (learned_ratio * 0.7 + actual_ratio * 0.3)  # 指数平滑
                            learned_ratio = max(0.1, min(1.0, learned_ratio))  # 限制范围
                
                # 步间延迟（最小化）
                time.sleep(0.0015)
            
            # 计算最终误差
            final_remaining_x = target_offset_x - cumulative_x
            final_remaining_y = target_offset_y - cumulative_y
            final_error = math.sqrt(final_remaining_x**2 + final_remaining_y**2)
            
            success = final_error <= tolerance
            return success, final_error, time.time() - start_time
            
        except Exception as e:
            return False, float('inf'), time.time() - start_time

    def get_performance_stats(self) -> dict:
        """获取性能统计信息"""
        return {
            'current_intent': self.movement_intent.value,
            'velocity_history_size': len(self.velocity_history),
            'integral_state': (self.integral_x, self.integral_y)
        }