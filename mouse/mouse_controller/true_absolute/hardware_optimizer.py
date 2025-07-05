"""
硬件响应优化器
HardwareOptimizer

针对不同硬件特性进行动态优化
自动检测和补偿硬件响应特性
"""

import time
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .precision_coordinate_mapper import HardwareType


@dataclass
class HardwareResponseProfile:
    """硬件响应特性配置"""
    hardware_type: HardwareType
    latency_ms: float
    precision_rating: float
    linearity_rating: float
    x_axis_bias: float
    y_axis_bias: float
    distance_compensation: Dict[int, float]
    dpi_scaling_factor: float
    sensitivity_scaling_factor: float
    non_linearity_correction: Dict[str, float]
    last_updated: float


class HardwareOptimizer:
    """硬件响应优化器"""
    
    def __init__(self, hardware_type: HardwareType = HardwareType.MOUSE_CONTROL):
        self.hardware_type = hardware_type
        
        # 硬件特性数据库
        self.hardware_profiles = self._initialize_hardware_profiles()
        self.current_profile = self.hardware_profiles[hardware_type]
        
        # 动态优化参数
        self.optimization_history: List[Dict] = []
        self.learning_rate = 0.05
        self.max_history_length = 200
        
        # 性能监控
        self.response_monitor = {
            'total_operations': 0,
            'successful_operations': 0,
            'average_latency': 0.0,
            'average_accuracy': 0.0,
            'last_optimization': 0.0
        }
        
        # 自适应调整因子
        self.adaptive_factors = {
            'latency_compensation': 1.0,
            'precision_boost': 1.0,
            'linearity_correction': 1.0,
            'dpi_optimization': 1.0,
            'sensitivity_optimization': 1.0
        }
    
    def _initialize_hardware_profiles(self) -> Dict[HardwareType, HardwareResponseProfile]:
        """初始化硬件特性配置数据库"""
        return {
            HardwareType.MOUSE_CONTROL: HardwareResponseProfile(
                hardware_type=HardwareType.MOUSE_CONTROL,
                latency_ms=2.5,
                precision_rating=0.995,
                linearity_rating=0.998,
                x_axis_bias=1.0,
                y_axis_bias=1.0,
                distance_compensation={
                    50: 1.0,
                    100: 1.001,
                    200: 1.002,
                    500: 1.005,
                    1000: 1.012,
                    1500: 1.020,
                    2000: 1.030
                },
                dpi_scaling_factor=1.0,
                sensitivity_scaling_factor=1.0,
                non_linearity_correction={
                    'small_movements': 0.98,   # <100px
                    'medium_movements': 1.0,   # 100-500px
                    'large_movements': 1.02    # >500px
                },
                last_updated=time.time()
            ),
            
            HardwareType.GHUB: HardwareResponseProfile(
                hardware_type=HardwareType.GHUB,
                latency_ms=8.5,
                precision_rating=0.96,
                linearity_rating=0.992,
                x_axis_bias=1.02,
                y_axis_bias=0.98,
                distance_compensation={
                    50: 1.0,
                    100: 1.005,
                    200: 1.010,
                    500: 1.020,
                    1000: 1.040,
                    1500: 1.065,
                    2000: 1.085
                },
                dpi_scaling_factor=0.98,
                sensitivity_scaling_factor=1.02,
                non_linearity_correction={
                    'small_movements': 0.95,
                    'medium_movements': 1.0,
                    'large_movements': 1.05
                },
                last_updated=time.time()
            ),
            
            HardwareType.LOGITECH: HardwareResponseProfile(
                hardware_type=HardwareType.LOGITECH,
                latency_ms=12.0,
                precision_rating=0.94,
                linearity_rating=0.988,
                x_axis_bias=1.05,
                y_axis_bias=0.95,
                distance_compensation={
                    50: 1.0,
                    100: 1.008,
                    200: 1.015,
                    500: 1.030,
                    1000: 1.055,
                    1500: 1.080,
                    2000: 1.110
                },
                dpi_scaling_factor=0.96,
                sensitivity_scaling_factor=1.05,
                non_linearity_correction={
                    'small_movements': 0.92,
                    'medium_movements': 1.0,
                    'large_movements': 1.08
                },
                last_updated=time.time()
            )
        }
    
    def optimize_mouse_movement(self, mouse_dx: int, mouse_dy: int, 
                              pixel_distance: float, dpi: int, sensitivity: float) -> Tuple[int, int]:
        """
        优化鼠标移动量
        
        Args:
            mouse_dx: 原始鼠标X移动量
            mouse_dy: 原始鼠标Y移动量
            pixel_distance: 像素距离
            dpi: DPI设置
            sensitivity: 灵敏度设置
            
        Returns:
            Tuple[int, int]: 优化后的鼠标移动量
        """
        profile = self.current_profile
        
        # 应用硬件轴向偏差补偿
        compensated_dx = mouse_dx * profile.x_axis_bias * self.adaptive_factors['precision_boost']
        compensated_dy = mouse_dy * profile.y_axis_bias * self.adaptive_factors['precision_boost']
        
        # 应用精度补偿
        precision_factor = profile.precision_rating * self.adaptive_factors['precision_boost']
        compensated_dx /= precision_factor
        compensated_dy /= precision_factor
        
        # 应用线性度修正
        linearity_factor = profile.linearity_rating * self.adaptive_factors['linearity_correction']
        compensated_dx /= linearity_factor
        compensated_dy /= linearity_factor
        
        # 应用距离补偿
        distance_compensation = self._get_distance_compensation(pixel_distance)
        compensated_dx *= distance_compensation
        compensated_dy *= distance_compensation
        
        # 应用DPI优化
        dpi_factor = (dpi / 800.0) * profile.dpi_scaling_factor * self.adaptive_factors['dpi_optimization']
        compensated_dx /= dpi_factor
        compensated_dy /= dpi_factor
        
        # 应用灵敏度优化
        sensitivity_factor = sensitivity * profile.sensitivity_scaling_factor * self.adaptive_factors['sensitivity_optimization']
        compensated_dx /= sensitivity_factor
        compensated_dy /= sensitivity_factor
        
        # 应用非线性修正
        non_linearity_factor = self._get_non_linearity_correction(pixel_distance)
        compensated_dx *= non_linearity_factor
        compensated_dy *= non_linearity_factor
        
        # 转换为整数
        optimized_dx = int(round(compensated_dx))
        optimized_dy = int(round(compensated_dy))
        
        return optimized_dx, optimized_dy
    
    def _get_distance_compensation(self, distance: float) -> float:
        """获取距离补偿因子"""
        profile = self.current_profile
        distances = sorted(profile.distance_compensation.keys())
        
        if distance <= distances[0]:
            return profile.distance_compensation[distances[0]]
        
        if distance >= distances[-1]:
            return profile.distance_compensation[distances[-1]]
        
        # 线性插值
        for i in range(len(distances) - 1):
            d1, d2 = distances[i], distances[i + 1]
            if d1 <= distance <= d2:
                t = (distance - d1) / (d2 - d1)
                comp1 = profile.distance_compensation[d1]
                comp2 = profile.distance_compensation[d2]
                return comp1 + t * (comp2 - comp1)
        
        return 1.0
    
    def _get_non_linearity_correction(self, distance: float) -> float:
        """获取非线性修正因子"""
        profile = self.current_profile
        
        if distance < 100:
            return profile.non_linearity_correction['small_movements']
        elif distance < 500:
            return profile.non_linearity_correction['medium_movements']
        else:
            return profile.non_linearity_correction['large_movements']
    
    def record_operation_result(self, intended_movement: Tuple[int, int],
                              actual_result: Tuple[float, float],
                              expected_result: Tuple[float, float],
                              execution_time_ms: float,
                              pixel_distance: float) -> None:
        """
        记录操作结果用于动态优化
        
        Args:
            intended_movement: 预期鼠标移动量
            actual_result: 实际结果位置
            expected_result: 期望结果位置
            execution_time_ms: 执行时间
            pixel_distance: 像素距离
        """
        # 计算误差
        error_x = actual_result[0] - expected_result[0]
        error_y = actual_result[1] - expected_result[1]
        error_magnitude = math.sqrt(error_x**2 + error_y**2)
        
        # 计算精度
        if pixel_distance > 0:
            accuracy = max(0.0, 1.0 - error_magnitude / pixel_distance)
        else:
            accuracy = 1.0
        
        # 记录到历史
        operation_record = {
            'timestamp': time.time(),
            'intended_movement': intended_movement,
            'actual_result': actual_result,
            'expected_result': expected_result,
            'error_magnitude': error_magnitude,
            'accuracy': accuracy,
            'execution_time_ms': execution_time_ms,
            'pixel_distance': pixel_distance,
            'hardware_type': self.hardware_type.value
        }
        
        self.optimization_history.append(operation_record)
        
        # 保持历史长度
        if len(self.optimization_history) > self.max_history_length:
            self.optimization_history = self.optimization_history[-int(self.max_history_length * 0.8):]
        
        # 更新性能监控
        self.response_monitor['total_operations'] += 1
        
        # 判断操作是否成功（误差小于5%）
        if accuracy > 0.95:
            self.response_monitor['successful_operations'] += 1
        
        # 更新平均指标
        total_ops = self.response_monitor['total_operations']
        current_avg_latency = self.response_monitor['average_latency']
        current_avg_accuracy = self.response_monitor['average_accuracy']
        
        self.response_monitor['average_latency'] = (
            (current_avg_latency * (total_ops - 1) + execution_time_ms) / total_ops
        )
        self.response_monitor['average_accuracy'] = (
            (current_avg_accuracy * (total_ops - 1) + accuracy) / total_ops
        )
        
        # 定期进行自适应优化
        if total_ops % 20 == 0:
            self._perform_adaptive_optimization()
    
    def _perform_adaptive_optimization(self):
        """执行自适应优化"""
        if len(self.optimization_history) < 10:
            return
        
        recent_records = self.optimization_history[-50:]  # 最近50次操作
        
        # 分析误差模式
        x_errors = []
        y_errors = []
        distance_errors = {}
        
        for record in recent_records:
            error_x = record['actual_result'][0] - record['expected_result'][0]
            error_y = record['actual_result'][1] - record['expected_result'][1]
            
            x_errors.append(error_x)
            y_errors.append(error_y)
            
            # 按距离分组
            distance_bucket = int(record['pixel_distance'] // 100) * 100
            if distance_bucket not in distance_errors:
                distance_errors[distance_bucket] = []
            distance_errors[distance_bucket].append(record['error_magnitude'])
        
        # 计算系统性偏差
        avg_x_error = sum(x_errors) / len(x_errors)
        avg_y_error = sum(y_errors) / len(y_errors)
        
        # 调整轴向偏差补偿
        if abs(avg_x_error) > 2.0:  # 超过2像素的系统性偏差
            adjustment = -avg_x_error / 100.0 * self.learning_rate
            self.current_profile.x_axis_bias += adjustment
            self.current_profile.x_axis_bias = max(0.5, min(2.0, self.current_profile.x_axis_bias))
        
        if abs(avg_y_error) > 2.0:
            adjustment = -avg_y_error / 100.0 * self.learning_rate
            self.current_profile.y_axis_bias += adjustment
            self.current_profile.y_axis_bias = max(0.5, min(2.0, self.current_profile.y_axis_bias))
        
        # 调整距离补偿
        for distance_bucket, errors in distance_errors.items():
            if len(errors) >= 3:  # 至少3个样本
                avg_error = sum(errors) / len(errors)
                if distance_bucket in self.current_profile.distance_compensation:
                    if avg_error > 5.0:  # 误差过大，需要补偿
                        adjustment = avg_error / 1000.0 * self.learning_rate
                        self.current_profile.distance_compensation[distance_bucket] += adjustment
                        self.current_profile.distance_compensation[distance_bucket] = max(0.5, min(2.0, self.current_profile.distance_compensation[distance_bucket]))
        
        # 调整自适应因子
        overall_accuracy = self.response_monitor['average_accuracy']
        
        if overall_accuracy < 0.9:  # 精度不够，增强补偿
            self.adaptive_factors['precision_boost'] += 0.01
        elif overall_accuracy > 0.98:  # 精度过高，可能过度补偿
            self.adaptive_factors['precision_boost'] -= 0.005
        
        # 限制自适应因子范围
        for key in self.adaptive_factors:
            self.adaptive_factors[key] = max(0.5, min(2.0, self.adaptive_factors[key]))
        
        self.response_monitor['last_optimization'] = time.time()
        self.current_profile.last_updated = time.time()
    
    def get_latency_compensation(self) -> float:
        """获取延迟补偿时间"""
        base_latency = self.current_profile.latency_ms
        compensation_factor = self.adaptive_factors['latency_compensation']
        
        return base_latency * compensation_factor / 1000.0  # 转换为秒
    
    def get_hardware_quality_rating(self) -> Dict[str, float]:
        """获取硬件质量评级"""
        profile = self.current_profile
        
        # 基础质量评分
        precision_score = profile.precision_rating * 100
        linearity_score = profile.linearity_rating * 100
        latency_score = max(0, 100 - profile.latency_ms * 5)  # 延迟越低分数越高
        
        # 根据运行数据调整
        if self.response_monitor['total_operations'] > 50:
            runtime_accuracy = self.response_monitor['average_accuracy'] * 100
            runtime_latency = max(0, 100 - self.response_monitor['average_latency'] * 2)
            
            # 综合评分
            overall_score = (precision_score * 0.3 + 
                           linearity_score * 0.2 + 
                           latency_score * 0.2 + 
                           runtime_accuracy * 0.2 + 
                           runtime_latency * 0.1)
        else:
            overall_score = (precision_score * 0.4 + 
                           linearity_score * 0.3 + 
                           latency_score * 0.3)
        
        return {
            'overall_rating': overall_score,
            'precision_rating': precision_score,
            'linearity_rating': linearity_score,
            'latency_rating': latency_score,
            'runtime_accuracy': self.response_monitor['average_accuracy'] * 100,
            'success_rate': (self.response_monitor['successful_operations'] / 
                           max(1, self.response_monitor['total_operations'])) * 100
        }
    
    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []
        
        quality_rating = self.get_hardware_quality_rating()
        
        if quality_rating['precision_rating'] < 90:
            recommendations.append("考虑升级到MouseControl.dll以获得更高精度")
        
        if quality_rating['latency_rating'] < 70:
            recommendations.append("当前硬件延迟较高，建议减少预测时间")
        
        if quality_rating['runtime_accuracy'] < 85:
            recommendations.append("检查DPI和灵敏度设置，可能需要重新校准")
        
        if self.response_monitor['total_operations'] > 100:
            success_rate = quality_rating['success_rate']
            if success_rate < 80:
                recommendations.append("成功率较低，建议运行精度测试并重新校准")
        
        # 基于硬件类型的特定建议
        if self.hardware_type == HardwareType.GHUB:
            recommendations.append("确保G HUB软件为最新版本")
        elif self.hardware_type == HardwareType.LOGITECH:
            recommendations.append("建议升级到G HUB驱动以获得更好性能")
        
        if not recommendations:
            recommendations.append("硬件性能表现良好，无需额外优化")
        
        return recommendations
    
    def export_optimization_data(self) -> Dict[str, Any]:
        """导出优化数据"""
        return {
            'hardware_type': self.hardware_type.value,
            'current_profile': {
                'latency_ms': self.current_profile.latency_ms,
                'precision_rating': self.current_profile.precision_rating,
                'linearity_rating': self.current_profile.linearity_rating,
                'x_axis_bias': self.current_profile.x_axis_bias,
                'y_axis_bias': self.current_profile.y_axis_bias,
                'distance_compensation': self.current_profile.distance_compensation,
                'last_updated': self.current_profile.last_updated
            },
            'adaptive_factors': self.adaptive_factors,
            'performance_monitor': self.response_monitor,
            'quality_rating': self.get_hardware_quality_rating(),
            'optimization_recommendations': self.get_optimization_recommendations(),
            'optimization_history_summary': {
                'total_records': len(self.optimization_history),
                'recent_accuracy': self.response_monitor['average_accuracy'],
                'recent_latency': self.response_monitor['average_latency']
            }
        }
    
    def import_optimization_data(self, data: Dict[str, Any]) -> bool:
        """导入优化数据"""
        try:
            if 'current_profile' in data:
                profile_data = data['current_profile']
                self.current_profile.latency_ms = profile_data.get('latency_ms', self.current_profile.latency_ms)
                self.current_profile.precision_rating = profile_data.get('precision_rating', self.current_profile.precision_rating)
                self.current_profile.linearity_rating = profile_data.get('linearity_rating', self.current_profile.linearity_rating)
                self.current_profile.x_axis_bias = profile_data.get('x_axis_bias', self.current_profile.x_axis_bias)
                self.current_profile.y_axis_bias = profile_data.get('y_axis_bias', self.current_profile.y_axis_bias)
                
                if 'distance_compensation' in profile_data:
                    self.current_profile.distance_compensation.update(profile_data['distance_compensation'])
            
            if 'adaptive_factors' in data:
                self.adaptive_factors.update(data['adaptive_factors'])
            
            if 'performance_monitor' in data:
                self.response_monitor.update(data['performance_monitor'])
            
            return True
            
        except Exception as e:
            print(f"导入优化数据失败: {e}")
            return False
    
    def reset_optimization(self):
        """重置优化数据"""
        # 重置为默认配置
        self.current_profile = self.hardware_profiles[self.hardware_type]
        
        # 重置自适应因子
        self.adaptive_factors = {
            'latency_compensation': 1.0,
            'precision_boost': 1.0,
            'linearity_correction': 1.0,
            'dpi_optimization': 1.0,
            'sensitivity_optimization': 1.0
        }
        
        # 清空历史记录
        self.optimization_history.clear()
        
        # 重置性能监控
        self.response_monitor = {
            'total_operations': 0,
            'successful_operations': 0,
            'average_latency': 0.0,
            'average_accuracy': 0.0,
            'last_optimization': 0.0
        }