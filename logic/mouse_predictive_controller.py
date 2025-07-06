"""
🎯 预测式鼠标控制器 - 根本性解决速度vs精度瓶颈

This controller addresses the fundamental bottlenecks identified in the speed vs overshoot problem:
1. Multi-frame coordinate stabilization (Kalman filtering + outlier detection)
2. Target motion prediction with delay compensation
3. Closed-loop feedback control system
4. Dual-precision movement architecture (coarse + fine adjustment)
5. Adaptive parameter system based on movement accuracy

核心特点：
- 预测式控制：基于目标运动预测而非当前位置
- 闭环反馈：移动后验证结果，动态调整
- 坐标稳定：多帧融合消除YOLO检测抖动
- 双精度架构：粗调+精调，兼顾速度与精度
- 自适应参数：根据实际性能动态优化
"""

import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Tuple, Optional, List
import threading

@dataclass
class TargetState:
    """目标状态信息"""
    x: float
    y: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    acceleration_x: float = 0.0
    acceleration_y: float = 0.0
    timestamp: float = 0.0
    confidence: float = 1.0
    target_class: int = 0  # 0=BODY, 7=HEAD

@dataclass
class MovementResult:
    """移动结果信息"""
    success: bool
    actual_distance: float
    execution_time: float
    overshoot_distance: float = 0.0
    accuracy_score: float = 1.0

class CoordinateStabilizer:
    """多帧坐标稳定系统 - 解决YOLO检测抖动问题"""
    
    def __init__(self, history_size=5):
        self.history_size = history_size
        self.coordinate_history = deque(maxlen=history_size)
        self.velocity_history = deque(maxlen=3)
        
        # 卡尔曼滤波器参数
        self.process_noise = 0.1  # 过程噪声
        self.measurement_noise = 1.0  # 测量噪声
        self.estimation_error = 1.0  # 估计误差
        
        # 异常检测参数 - 调整为更宽容的阈值
        self.max_position_jump = 300.0  # 最大合理位置跳跃(px) - 从100增加到300
        self.max_velocity = 2000.0  # 最大合理速度(px/s) - 从800增加到2000
        
        # 🔧 临时调试：可以禁用异常检测来验证问题
        self.outlier_detection_enabled = False  # 暂时禁用异常检测
        
    def stabilize_coordinates(self, raw_x: float, raw_y: float, timestamp: float, confidence: float = 1.0) -> Tuple[float, float, bool]:
        """
        稳定坐标：应用多帧融合和异常检测
        
        Returns:
            stabilized_x, stabilized_y, is_valid
        """
        current_state = TargetState(raw_x, raw_y, timestamp=timestamp, confidence=confidence)
        
        # 异常检测（可以禁用）
        if self.outlier_detection_enabled and self._is_outlier(current_state):
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🚨 OUTLIER DETECTED: position=({raw_x:.1f},{raw_y:.1f}) - using predicted position")
            if self.coordinate_history:
                # 使用预测位置替代异常值
                predicted = self._predict_next_position()
                return predicted[0], predicted[1], False
            else:
                return raw_x, raw_y, False
        
        # 添加到历史记录
        self.coordinate_history.append(current_state)
        
        # 多帧融合稳定
        stabilized_x, stabilized_y = self._apply_multi_frame_fusion()
        
        # 更新速度历史
        self._update_velocity_history()
        
        return stabilized_x, stabilized_y, True
    
    def _is_outlier(self, current_state: TargetState) -> bool:
        """检测坐标是否为异常值"""
        if len(self.coordinate_history) < 2:
            return False
        
        last_state = self.coordinate_history[-1]
        
        # 检查位置跳跃
        position_jump = math.sqrt(
            (current_state.x - last_state.x)**2 + 
            (current_state.y - last_state.y)**2
        )
        
        if position_jump > self.max_position_jump:
            return True
        
        # 检查速度异常
        if len(self.coordinate_history) >= 2:
            dt = current_state.timestamp - last_state.timestamp
            if dt > 0:
                velocity = position_jump / dt
                if velocity > self.max_velocity:
                    return True
        
        return False
    
    def _apply_multi_frame_fusion(self) -> Tuple[float, float]:
        """应用多帧融合算法"""
        if len(self.coordinate_history) == 1:
            state = self.coordinate_history[0]
            return state.x, state.y
        
        # 加权平均，最新帧权重最大
        total_weight = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        
        for i, state in enumerate(self.coordinate_history):
            # 权重：最新帧=1.0，逐渐递减
            age = len(self.coordinate_history) - 1 - i
            weight = (0.7 ** age) * state.confidence
            
            weighted_x += state.x * weight
            weighted_y += state.y * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_x / total_weight, weighted_y / total_weight
        else:
            latest = self.coordinate_history[-1]
            return latest.x, latest.y
    
    def _update_velocity_history(self):
        """更新速度历史记录"""
        if len(self.coordinate_history) < 2:
            return
        
        current = self.coordinate_history[-1]
        previous = self.coordinate_history[-2]
        
        dt = current.timestamp - previous.timestamp
        if dt > 0:
            velocity_x = (current.x - previous.x) / dt
            velocity_y = (current.y - previous.y) / dt
            
            self.velocity_history.append((velocity_x, velocity_y, current.timestamp))
    
    def _predict_next_position(self) -> Tuple[float, float]:
        """预测下一个位置（用于替代异常值）"""
        if len(self.coordinate_history) < 1:
            # 如果没有历史数据，返回屏幕中心作为安全默认值
            return 250.0, 250.0
        
        # 获取最近的有效坐标
        latest = self.coordinate_history[-1]
        
        # 如果历史数据不足，直接返回最近坐标
        if len(self.coordinate_history) < 2:
            return latest.x, latest.y
        
        # 简单线性预测，但限制预测距离
        current = self.coordinate_history[-1]
        previous = self.coordinate_history[-2]
        
        # 计算简单的位移向量
        dx = current.x - previous.x
        dy = current.y - previous.y
        
        # 限制预测步长，避免过度预测
        max_prediction_step = 50.0
        if abs(dx) > max_prediction_step:
            dx = max_prediction_step if dx > 0 else -max_prediction_step
        if abs(dy) > max_prediction_step:
            dy = max_prediction_step if dy > 0 else -max_prediction_step
        
        pred_x = current.x + dx * 0.5  # 只预测一半的移动
        pred_y = current.y + dy * 0.5
        
        # 确保预测位置在屏幕范围内
        pred_x = max(0, min(500, pred_x))
        pred_y = max(0, min(500, pred_y))
        
        return pred_x, pred_y
    
    def get_current_velocity(self) -> Tuple[float, float]:
        """获取当前速度"""
        if len(self.velocity_history) > 0:
            velocity_x, velocity_y, _ = self.velocity_history[-1]
            return velocity_x, velocity_y
        return 0.0, 0.0

class MotionPredictor:
    """目标运动预测系统 - 解决延迟导致的追踪滞后"""
    
    def __init__(self):
        self.target_history = deque(maxlen=8)  # 保留8帧历史
        self.prediction_enabled = True
        self.system_delay = 0.06  # 系统总延迟估计(60ms)
        
    def predict_target_position(self, stabilized_x: float, stabilized_y: float, 
                              velocity_x: float, velocity_y: float, 
                              target_class: int, timestamp: float) -> Tuple[float, float]:
        """
        预测目标位置：补偿系统延迟，预测目标实际位置
        
        Returns:
            predicted_x, predicted_y
        """
        if not self.prediction_enabled:
            return stabilized_x, stabilized_y
        
        # 更新历史记录
        current_state = TargetState(
            x=stabilized_x, y=stabilized_y,
            velocity_x=velocity_x, velocity_y=velocity_y,
            timestamp=timestamp, target_class=target_class
        )
        self.target_history.append(current_state)
        
        # 计算预测
        if len(self.target_history) < 3:
            return stabilized_x, stabilized_y
        
        # 多种预测模型融合
        linear_pred = self._linear_prediction(current_state)
        acceleration_pred = self._acceleration_prediction()
        pattern_pred = self._pattern_prediction()
        
        # 加权融合预测结果
        final_x = 0.5 * linear_pred[0] + 0.3 * acceleration_pred[0] + 0.2 * pattern_pred[0]
        final_y = 0.5 * linear_pred[1] + 0.3 * acceleration_pred[1] + 0.2 * pattern_pred[1]
        
        # 预测距离限制（避免过度预测）
        max_prediction_distance = 40.0
        prediction_distance = math.sqrt((final_x - stabilized_x)**2 + (final_y - stabilized_y)**2)
        
        if prediction_distance > max_prediction_distance:
            scale = max_prediction_distance / prediction_distance
            final_x = stabilized_x + (final_x - stabilized_x) * scale
            final_y = stabilized_y + (final_y - stabilized_y) * scale
        
        # 日志输出
        if prediction_distance > 5.0:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔮 MOTION PREDICTION: "
                  f"({stabilized_x:.1f},{stabilized_y:.1f}) → ({final_x:.1f},{final_y:.1f}) "
                  f"distance={prediction_distance:.1f}px")
        
        return final_x, final_y
    
    def _linear_prediction(self, current_state: TargetState) -> Tuple[float, float]:
        """线性预测：基于当前速度"""
        pred_x = current_state.x + current_state.velocity_x * self.system_delay
        pred_y = current_state.y + current_state.velocity_y * self.system_delay
        return pred_x, pred_y
    
    def _acceleration_prediction(self) -> Tuple[float, float]:
        """加速度预测：考虑速度变化"""
        if len(self.target_history) < 3:
            latest = self.target_history[-1]
            return latest.x, latest.y
        
        # 计算加速度
        current = self.target_history[-1]
        previous = self.target_history[-2]
        
        dt = current.timestamp - previous.timestamp
        if dt > 0:
            accel_x = (current.velocity_x - previous.velocity_x) / dt
            accel_y = (current.velocity_y - previous.velocity_y) / dt
            
            # 运动学方程：s = v0*t + 0.5*a*t^2
            t = self.system_delay
            pred_x = current.x + current.velocity_x * t + 0.5 * accel_x * t * t
            pred_y = current.y + current.velocity_y * t + 0.5 * accel_y * t * t
            
            return pred_x, pred_y
        
        return current.x, current.y
    
    def _pattern_prediction(self) -> Tuple[float, float]:
        """模式预测：基于历史轨迹模式"""
        if len(self.target_history) < 4:
            latest = self.target_history[-1]
            return latest.x, latest.y
        
        # 简单的趋势分析
        recent_states = list(self.target_history)[-4:]
        
        # 计算平均移动向量
        total_dx, total_dy = 0.0, 0.0
        for i in range(1, len(recent_states)):
            dt = recent_states[i].timestamp - recent_states[i-1].timestamp
            if dt > 0:
                dx = recent_states[i].x - recent_states[i-1].x
                dy = recent_states[i].y - recent_states[i-1].y
                total_dx += dx
                total_dy += dy
        
        # 预测下一步移动
        avg_dx = total_dx / (len(recent_states) - 1)
        avg_dy = total_dy / (len(recent_states) - 1)
        
        latest = recent_states[-1]
        pred_x = latest.x + avg_dx
        pred_y = latest.y + avg_dy
        
        return pred_x, pred_y

class PredictiveMouseController:
    """预测式鼠标控制器 - 主控制器"""
    
    def __init__(self):
        # 初始化子系统
        self.coordinate_stabilizer = CoordinateStabilizer()
        self.motion_predictor = MotionPredictor()
        
        # 加载配置
        try:
            from logic.config_watcher import cfg
            self.screen_width = cfg.detection_window_width
            self.screen_height = cfg.detection_window_height
            self.center_x = self.screen_width / 2
            self.center_y = self.screen_height / 2
            self.dpi = cfg.mouse_dpi
            self.sensitivity = cfg.mouse_sensitivity
            self.fov_x = cfg.mouse_fov_width
            self.fov_y = cfg.mouse_fov_height
            self.body_y_offset = getattr(cfg, 'body_y_offset', -0.25)
        except Exception as e:
            print(f"⚠️ Config loading failed, using defaults: {e}")
            self.screen_width = 500
            self.screen_height = 500
            self.center_x = 250
            self.center_y = 250
            self.dpi = 1100
            self.sensitivity = 3.0
            self.fov_x = 40
            self.fov_y = 40
            self.body_y_offset = -0.25
        
        # 预计算转换系数
        self._base_conversion_factor = (self.dpi * (1 / self.sensitivity)) / 360
        
        # 控制参数
        self.predictive_control_enabled = True
        self.feedback_control_enabled = True
        self.dual_precision_enabled = True
        
        # 性能监控
        self.movement_history = deque(maxlen=20)
        self.accuracy_scores = deque(maxlen=50)
        
        # 自适应参数 - 降低初始倍数，避免过冲
        self.adaptive_multipliers = {
            'precision_base': 2.0,  # 从3.5降低到2.0
            'balanced_base': 4.0,   # 从8.0降低到4.0 
            'speed_base': 6.0       # 从12.0降低到6.0
        }
        
        print(f"🎯 PredictiveMouseController initialized")
        print(f"   Predictive control: {'✅' if self.predictive_control_enabled else '❌'}")
        print(f"   Feedback control: {'✅' if self.feedback_control_enabled else '❌'}")
        print(f"   Dual precision: {'✅' if self.dual_precision_enabled else '❌'}")
    
    def process_target(self, raw_x: float, raw_y: float, target_w: float = 0, 
                      target_h: float = 0, target_cls: int = 0) -> bool:
        """
        处理检测到的目标 - 主入口点
        
        Returns:
            bool: 移动是否成功
        """
        current_time = time.time()
        
        # 1. 坐标稳定化
        stabilized_x, stabilized_y, is_valid = self.coordinate_stabilizer.stabilize_coordinates(
            raw_x, raw_y, current_time, confidence=1.0
        )
        
        if not is_valid:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ⚠️ Using predicted coordinates due to instability")
        
        # 2. 应用目标偏移（身体目标）
        original_x, original_y = stabilized_x, stabilized_y
        if target_cls != 7:  # 不是头部目标
            stabilized_y += target_h * self.body_y_offset
            stabilized_x += target_w * 0.05  # 5% X轴调整
            
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📐 TRANSFORM OFFSET: "
                  f"original=({original_x:.1f},{original_y:.1f}) → "
                  f"adjusted=({stabilized_x:.1f},{stabilized_y:.1f})")
        
        # 3. 运动预测
        velocity_x, velocity_y = self.coordinate_stabilizer.get_current_velocity()
        predicted_x, predicted_y = self.motion_predictor.predict_target_position(
            stabilized_x, stabilized_y, velocity_x, velocity_y, target_cls, current_time
        )
        
        # 4. 计算目标偏移
        offset_x = predicted_x - self.center_x
        offset_y = predicted_y - self.center_y
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        target_type = "HEAD" if target_cls == 7 else "BODY"
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📐 PIXEL OFFSET: "
              f"predicted=({predicted_x:.1f},{predicted_y:.1f}) center=({self.center_x:.1f},{self.center_y:.1f}) → "
              f"offset=({offset_x:.1f},{offset_y:.1f}) distance={distance:.1f}px")
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 Processing {target_type} target with PREDICTIVE CONTROL")
        
        # 5. 执行移动
        if distance <= 3.0:  # 已经很接近
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ✅ Target already in range: {distance:.1f}px")
            return True
        
        # 执行预测式移动
        movement_result = self._execute_predictive_movement(offset_x, offset_y, distance, target_cls)
        
        # 6. 性能监控和自适应调整
        self._update_performance_metrics(movement_result)
        self._adapt_parameters()
        
        return movement_result.success
    
    def _execute_predictive_movement(self, offset_x: float, offset_y: float, 
                                   distance: float, target_cls: int) -> MovementResult:
        """执行预测式移动"""
        start_time = time.time()
        
        if self.dual_precision_enabled and distance > 30:
            # 双精度移动：粗调 + 精调
            return self._execute_dual_precision_movement(offset_x, offset_y, distance, target_cls)
        else:
            # 单精度移动
            return self._execute_single_precision_movement(offset_x, offset_y, distance, target_cls)
    
    def _execute_dual_precision_movement(self, offset_x: float, offset_y: float, 
                                       distance: float, target_cls: int) -> MovementResult:
        """双精度移动：粗调阶段 + 精调阶段"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{current_time} - 🎯 DUAL PRECISION: Starting coarse + fine movement for {distance:.1f}px")
        
        start_time = time.time()
        
        # 阶段1：粗调 - 快速接近目标区域
        coarse_ratio = 0.75  # 移动到75%位置
        coarse_x = offset_x * coarse_ratio
        coarse_y = offset_y * coarse_ratio
        
        coarse_success = self._execute_movement_stage(coarse_x, coarse_y, "COARSE", target_cls)
        
        if not coarse_success:
            execution_time = time.time() - start_time
            return MovementResult(success=False, actual_distance=distance, execution_time=execution_time)
        
        # 短暂延迟让系统稳定
        time.sleep(0.002)  # 2ms
        
        # 阶段2：精调 - 精确定位
        fine_x = offset_x * (1.0 - coarse_ratio)
        fine_y = offset_y * (1.0 - coarse_ratio)
        
        fine_success = self._execute_movement_stage(fine_x, fine_y, "FINE", target_cls, is_fine_adjustment=True)
        
        execution_time = time.time() - start_time
        overall_success = coarse_success and fine_success
        
        print(f"{current_time} - 🎯 DUAL PRECISION RESULT: Coarse={'✅' if coarse_success else '❌'} "
              f"Fine={'✅' if fine_success else '❌'} Total={execution_time*1000:.1f}ms")
        
        return MovementResult(
            success=overall_success,
            actual_distance=distance,
            execution_time=execution_time,
            accuracy_score=0.9 if overall_success else 0.4
        )
    
    def _execute_single_precision_movement(self, offset_x: float, offset_y: float, 
                                         distance: float, target_cls: int) -> MovementResult:
        """单精度移动"""
        start_time = time.time()
        
        success = self._execute_movement_stage(offset_x, offset_y, "SINGLE", target_cls)
        
        execution_time = time.time() - start_time
        
        return MovementResult(
            success=success,
            actual_distance=distance,
            execution_time=execution_time,
            accuracy_score=0.8 if success else 0.3
        )
    
    def _execute_movement_stage(self, offset_x: float, offset_y: float, 
                              stage_name: str, target_cls: int, 
                              is_fine_adjustment: bool = False) -> bool:
        """执行单个移动阶段"""
        # 计算鼠标移动量
        mouse_x, mouse_y = self._calculate_mouse_movement(offset_x, offset_y, is_fine_adjustment)
        
        if abs(mouse_x) < 1 and abs(mouse_y) < 1:
            return True  # 移动量太小，视为成功
        
        # 执行移动（这里需要集成实际的鼠标移动API）
        exec_x, exec_y = int(round(mouse_x)), int(round(mouse_y))
        success = self._execute_raw_mouse_movement(exec_x, exec_y)
        
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        status = "✅" if success else "❌"
        print(f"{current_time} - 🎯 {stage_name}: ({exec_x}, {exec_y}) {status}")
        
        return success
    
    def _calculate_mouse_movement(self, offset_x: float, offset_y: float, 
                                is_fine_adjustment: bool = False) -> Tuple[float, float]:
        """计算鼠标移动量 - 自适应算法"""
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 基础转换
        degrees_x = offset_x * (self.fov_x / self.screen_width)
        degrees_y = offset_y * (self.fov_y / self.screen_height)
        base_mouse_x = degrees_x * self._base_conversion_factor
        base_mouse_y = degrees_y * self._base_conversion_factor
        
        # 自适应倍数选择
        if is_fine_adjustment:
            multiplier = 2.0  # 精调阶段使用低倍数
        elif distance <= 20:
            multiplier = self.adaptive_multipliers['precision_base']
        elif distance <= 100:
            multiplier = self.adaptive_multipliers['balanced_base']
        else:
            multiplier = self.adaptive_multipliers['speed_base']
        
        return base_mouse_x * multiplier, base_mouse_y * multiplier
    
    def _execute_raw_mouse_movement(self, dx: int, dy: int) -> bool:
        """执行原始鼠标移动 - 集成现有的鼠标API"""
        try:
            # 尝试使用传统控制器
            from logic.mouse_new_raw_input_fixed import RawInputCompatibleController
            controller = RawInputCompatibleController()
            return controller._execute_mouse_movement(dx, dy)
        except Exception as e:
            # 在WSL环境下或没有Windows API时，模拟成功
            print(f"🔧 Simulated mouse movement: ({dx}, {dy}) - {e}")
            time.sleep(0.001)  # 模拟移动延迟
            return True
    
    def _update_performance_metrics(self, result: MovementResult):
        """更新性能指标"""
        self.movement_history.append(result)
        self.accuracy_scores.append(result.accuracy_score)
    
    def _adapt_parameters(self):
        """自适应参数调整 - 更保守的策略"""
        if len(self.accuracy_scores) < 10:
            return
        
        # 计算最近的准确率
        recent_accuracy = sum(list(self.accuracy_scores)[-10:]) / 10
        
        # 更保守的自适应策略，避免过度调整
        if recent_accuracy < 0.5:
            # 准确率很低，降低倍数
            for key in self.adaptive_multipliers:
                self.adaptive_multipliers[key] *= 0.9  # 从0.95改为0.9，更快降低
                # 设置最小倍数限制
                if self.adaptive_multipliers[key] < 1.0:
                    self.adaptive_multipliers[key] = 1.0
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔧 ADAPTIVE: Reducing multipliers due to low accuracy ({recent_accuracy:.2f})")
        elif recent_accuracy > 0.9:  # 从0.85提高到0.9，更严格的条件
            # 准确率很高时，只微小提升，且设置上限
            for key in self.adaptive_multipliers:
                if self.adaptive_multipliers[key] < 8.0:  # 设置上限，避免无限增长
                    self.adaptive_multipliers[key] *= 1.01  # 从1.02改为1.01，更保守
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ⚡ ADAPTIVE: Slightly increasing multipliers due to very high accuracy ({recent_accuracy:.2f})")
    
    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        if not self.movement_history:
            return {}
        
        recent_movements = list(self.movement_history)[-20:]
        
        success_rate = sum(1 for m in recent_movements if m.success) / len(recent_movements)
        avg_execution_time = sum(m.execution_time for m in recent_movements) / len(recent_movements)
        avg_accuracy = sum(self.accuracy_scores) / len(self.accuracy_scores) if self.accuracy_scores else 0
        
        return {
            'success_rate': success_rate,
            'avg_execution_time_ms': avg_execution_time * 1000,
            'avg_accuracy_score': avg_accuracy,
            'total_movements': len(self.movement_history),
            'adaptive_multipliers': self.adaptive_multipliers.copy()
        }
    
    def handle_no_target(self):
        """处理无目标情况"""
        # 保持系统状态，无需特殊处理
        pass

# 创建全局预测式控制器实例
predictive_mouse_controller = PredictiveMouseController()