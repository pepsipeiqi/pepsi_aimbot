"""
自适应校准系统
AdaptiveCalibrationSystem

智能学习系统，自动优化鼠标移动精度
基于实际移动结果持续改进映射系数
"""

import time
import math
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
from pathlib import Path


@dataclass
class CalibrationDataPoint:
    """校准数据点"""
    intended_target: Tuple[float, float]
    actual_result: Tuple[float, float]
    mouse_movement: Tuple[int, int]
    pixel_distance: float
    error_magnitude: float
    error_direction: float  # 误差方向（角度）
    timestamp: float
    hardware_type: str
    dpi: int
    sensitivity: float
    confidence: float = 1.0


@dataclass
class CalibrationZone:
    """校准区域"""
    center_x: float
    center_y: float
    radius: float
    sample_count: int
    average_error: float
    correction_factor_x: float
    correction_factor_y: float
    confidence: float
    last_updated: float


class AdaptiveCalibrationSystem:
    """自适应校准系统"""
    
    def __init__(self, screen_width: int = 1920, screen_height: int = 1080,
                 max_data_points: int = 10000, auto_save: bool = True):
        
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.max_data_points = max_data_points
        self.auto_save = auto_save
        
        # 校准数据存储
        self.calibration_data: List[CalibrationDataPoint] = []
        
        # 分区域校准映射
        self.calibration_zones: Dict[str, CalibrationZone] = {}
        self.zone_size = 200  # 每个校准区域的大小
        
        # 距离分段校准
        self.distance_calibration: Dict[int, Dict[str, float]] = defaultdict(lambda: {
            'correction_x': 1.0,
            'correction_y': 1.0,
            'sample_count': 0,
            'confidence': 0.5
        })
        
        # 学习参数
        self.learning_rate = 0.1
        self.min_samples_for_confidence = 5
        self.confidence_threshold = 0.8
        self.max_correction_factor = 2.0
        self.min_correction_factor = 0.5
        
        # 性能统计
        self.calibration_stats = {
            'total_calibrations': 0,
            'successful_calibrations': 0,
            'average_improvement': 0.0,
            'last_calibration_time': 0.0
        }
        
        # 数据持久化
        self.data_file_path = Path("calibration_data.json")
        self.zones_file_path = Path("calibration_zones.json")
        
        # 线程安全
        self._lock = threading.Lock()
        
        # 加载历史数据
        if auto_save:
            self.load_calibration_data()
    
    def record_movement_result(self, intended_target: Tuple[float, float],
                             actual_result: Tuple[float, float],
                             mouse_movement: Tuple[int, int],
                             hardware_type: str = "Unknown",
                             dpi: int = 800,
                             sensitivity: float = 1.0) -> bool:
        """
        记录移动结果并更新校准数据
        
        Args:
            intended_target: 预期目标位置
            actual_result: 实际到达位置
            mouse_movement: 鼠标移动量
            hardware_type: 硬件类型
            dpi: DPI设置
            sensitivity: 灵敏度设置
            
        Returns:
            bool: 记录是否成功
        """
        try:
            with self._lock:
                # 计算误差
                error_x = actual_result[0] - intended_target[0]
                error_y = actual_result[1] - intended_target[1]
                error_magnitude = math.sqrt(error_x**2 + error_y**2)
                
                # 计算误差方向
                if error_magnitude > 0:
                    error_direction = math.atan2(error_y, error_x)
                else:
                    error_direction = 0.0
                
                # 计算移动距离
                pixel_distance = math.sqrt(
                    (intended_target[0] - actual_result[0] + error_x)**2 + 
                    (intended_target[1] - actual_result[1] + error_y)**2
                )
                
                # 创建数据点
                data_point = CalibrationDataPoint(
                    intended_target=intended_target,
                    actual_result=actual_result,
                    mouse_movement=mouse_movement,
                    pixel_distance=pixel_distance,
                    error_magnitude=error_magnitude,
                    error_direction=error_direction,
                    timestamp=time.time(),
                    hardware_type=hardware_type,
                    dpi=dpi,
                    sensitivity=sensitivity,
                    confidence=self._calculate_data_confidence(error_magnitude, pixel_distance)
                )
                
                # 添加到数据集
                self.calibration_data.append(data_point)
                
                # 保持数据量在限制内
                if len(self.calibration_data) > self.max_data_points:
                    # 移除最旧的数据，但保留高置信度数据
                    self.calibration_data.sort(key=lambda x: (x.confidence, x.timestamp))
                    self.calibration_data = self.calibration_data[int(self.max_data_points * 0.2):]
                
                # 更新校准映射
                self._update_calibration_mappings(data_point)
                
                # 更新统计
                self.calibration_stats['total_calibrations'] += 1
                if error_magnitude < pixel_distance * 0.05:  # 5%误差以内认为成功
                    self.calibration_stats['successful_calibrations'] += 1
                
                self.calibration_stats['last_calibration_time'] = time.time()
                
                # 自动保存
                if self.auto_save and self.calibration_stats['total_calibrations'] % 10 == 0:
                    self.save_calibration_data()
                
                return True
                
        except Exception as e:
            print(f"记录校准数据失败: {e}")
            return False
    
    def _calculate_data_confidence(self, error_magnitude: float, pixel_distance: float) -> float:
        """
        计算数据点置信度
        
        Args:
            error_magnitude: 误差大小
            pixel_distance: 移动距离
            
        Returns:
            float: 置信度 (0-1)
        """
        if pixel_distance == 0:
            return 0.0
        
        # 基于相对误差计算置信度
        relative_error = error_magnitude / pixel_distance
        
        if relative_error < 0.01:  # <1% 误差
            return 1.0
        elif relative_error < 0.05:  # <5% 误差
            return 0.9
        elif relative_error < 0.1:  # <10% 误差
            return 0.7
        elif relative_error < 0.2:  # <20% 误差
            return 0.5
        else:
            return 0.2
    
    def _update_calibration_mappings(self, data_point: CalibrationDataPoint):
        """
        更新校准映射
        
        Args:
            data_point: 校准数据点
        """
        # 更新区域校准
        self._update_zone_calibration(data_point)
        
        # 更新距离校准
        self._update_distance_calibration(data_point)
    
    def _update_zone_calibration(self, data_point: CalibrationDataPoint):
        """
        更新区域校准映射
        
        Args:
            data_point: 校准数据点
        """
        target_x, target_y = data_point.intended_target
        
        # 计算所属区域
        zone_x = int(target_x // self.zone_size)
        zone_y = int(target_y // self.zone_size)
        zone_key = f"{zone_x}_{zone_y}"
        
        # 创建或更新区域
        if zone_key not in self.calibration_zones:
            self.calibration_zones[zone_key] = CalibrationZone(
                center_x=(zone_x + 0.5) * self.zone_size,
                center_y=(zone_y + 0.5) * self.zone_size,
                radius=self.zone_size / 2,
                sample_count=0,
                average_error=0.0,
                correction_factor_x=1.0,
                correction_factor_y=1.0,
                confidence=0.0,
                last_updated=0.0
            )
        
        zone = self.calibration_zones[zone_key]
        
        # 计算修正因子
        if data_point.mouse_movement[0] != 0:
            actual_efficiency_x = (data_point.actual_result[0] - target_x) / data_point.mouse_movement[0]
            target_efficiency_x = (data_point.intended_target[0] - target_x) / data_point.mouse_movement[0]
            if actual_efficiency_x != 0:
                correction_x = target_efficiency_x / actual_efficiency_x
            else:
                correction_x = 1.0
        else:
            correction_x = 1.0
        
        if data_point.mouse_movement[1] != 0:
            actual_efficiency_y = (data_point.actual_result[1] - target_y) / data_point.mouse_movement[1]
            target_efficiency_y = (data_point.intended_target[1] - target_y) / data_point.mouse_movement[1]
            if actual_efficiency_y != 0:
                correction_y = target_efficiency_y / actual_efficiency_y
            else:
                correction_y = 1.0
        else:
            correction_y = 1.0
        
        # 限制修正因子范围
        correction_x = max(self.min_correction_factor, min(self.max_correction_factor, correction_x))
        correction_y = max(self.min_correction_factor, min(self.max_correction_factor, correction_y))
        
        # 应用学习率更新
        zone.correction_factor_x += self.learning_rate * (correction_x - zone.correction_factor_x)
        zone.correction_factor_y += self.learning_rate * (correction_y - zone.correction_factor_y)
        
        # 更新统计信息
        zone.sample_count += 1
        zone.average_error = (zone.average_error * (zone.sample_count - 1) + data_point.error_magnitude) / zone.sample_count
        zone.confidence = min(1.0, zone.sample_count / self.min_samples_for_confidence * data_point.confidence)
        zone.last_updated = time.time()
    
    def _update_distance_calibration(self, data_point: CalibrationDataPoint):
        """
        更新距离校准映射
        
        Args:
            data_point: 校准数据点
        """
        # 距离分段
        distance_bucket = int(data_point.pixel_distance // 100) * 100
        
        # 计算修正因子
        if data_point.pixel_distance > 0:
            intended_distance = math.sqrt(
                (data_point.intended_target[0])**2 + (data_point.intended_target[1])**2
            )
            actual_distance = math.sqrt(
                (data_point.actual_result[0])**2 + (data_point.actual_result[1])**2
            )
            
            if actual_distance > 0:
                distance_correction = intended_distance / actual_distance
            else:
                distance_correction = 1.0
        else:
            distance_correction = 1.0
        
        # 限制修正范围
        distance_correction = max(self.min_correction_factor, min(self.max_correction_factor, distance_correction))
        
        # 更新距离校准
        calibration = self.distance_calibration[distance_bucket]
        
        # 应用学习率
        calibration['correction_x'] += self.learning_rate * (distance_correction - calibration['correction_x'])
        calibration['correction_y'] += self.learning_rate * (distance_correction - calibration['correction_y'])
        calibration['sample_count'] += 1
        calibration['confidence'] = min(1.0, calibration['sample_count'] / self.min_samples_for_confidence)
    
    def get_zone_correction(self, target_x: float, target_y: float) -> Tuple[float, float]:
        """
        获取区域修正因子
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            
        Returns:
            Tuple[float, float]: (correction_x, correction_y)
        """
        zone_x = int(target_x // self.zone_size)
        zone_y = int(target_y // self.zone_size)
        zone_key = f"{zone_x}_{zone_y}"
        
        if zone_key in self.calibration_zones:
            zone = self.calibration_zones[zone_key]
            if zone.confidence >= self.confidence_threshold:
                return zone.correction_factor_x, zone.correction_factor_y
        
        # 寻找邻近区域
        nearby_corrections_x = []
        nearby_corrections_y = []
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nearby_zone_key = f"{zone_x + dx}_{zone_y + dy}"
                if nearby_zone_key in self.calibration_zones:
                    nearby_zone = self.calibration_zones[nearby_zone_key]
                    if nearby_zone.confidence >= 0.5:
                        nearby_corrections_x.append(nearby_zone.correction_factor_x)
                        nearby_corrections_y.append(nearby_zone.correction_factor_y)
        
        if nearby_corrections_x and nearby_corrections_y:
            return (
                sum(nearby_corrections_x) / len(nearby_corrections_x),
                sum(nearby_corrections_y) / len(nearby_corrections_y)
            )
        
        return 1.0, 1.0
    
    def get_distance_correction(self, distance: float) -> Tuple[float, float]:
        """
        获取距离修正因子
        
        Args:
            distance: 移动距离
            
        Returns:
            Tuple[float, float]: (correction_x, correction_y)
        """
        distance_bucket = int(distance // 100) * 100
        
        if distance_bucket in self.distance_calibration:
            calibration = self.distance_calibration[distance_bucket]
            if calibration['confidence'] >= self.confidence_threshold:
                return calibration['correction_x'], calibration['correction_y']
        
        # 寻找邻近距离段
        nearby_buckets = [distance_bucket - 100, distance_bucket + 100]
        corrections_x = []
        corrections_y = []
        
        for bucket in nearby_buckets:
            if bucket in self.distance_calibration:
                calibration = self.distance_calibration[bucket]
                if calibration['confidence'] >= 0.5:
                    corrections_x.append(calibration['correction_x'])
                    corrections_y.append(calibration['correction_y'])
        
        if corrections_x and corrections_y:
            return (
                sum(corrections_x) / len(corrections_x),
                sum(corrections_y) / len(corrections_y)
            )
        
        return 1.0, 1.0
    
    def get_combined_correction(self, target_x: float, target_y: float, 
                              distance: float) -> Tuple[float, float]:
        """
        获取综合修正因子
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            distance: 移动距离
            
        Returns:
            Tuple[float, float]: (correction_x, correction_y)
        """
        # 获取区域修正
        zone_corr_x, zone_corr_y = self.get_zone_correction(target_x, target_y)
        
        # 获取距离修正
        dist_corr_x, dist_corr_y = self.get_distance_correction(distance)
        
        # 综合修正（加权平均）
        weight_zone = 0.6
        weight_distance = 0.4
        
        combined_x = zone_corr_x * weight_zone + dist_corr_x * weight_distance
        combined_y = zone_corr_y * weight_zone + dist_corr_y * weight_distance
        
        return combined_x, combined_y
    
    def get_calibration_quality(self) -> Dict[str, Any]:
        """
        获取校准质量报告
        
        Returns:
            Dict[str, Any]: 校准质量报告
        """
        with self._lock:
            if not self.calibration_data:
                return {
                    'overall_quality': 0.0,
                    'sample_count': 0,
                    'coverage': 0.0
                }
            
            # 计算整体质量
            recent_data = self.calibration_data[-100:] if len(self.calibration_data) >= 100 else self.calibration_data
            
            if recent_data:
                avg_confidence = sum(d.confidence for d in recent_data) / len(recent_data)
                avg_error = sum(d.error_magnitude for d in recent_data) / len(recent_data)
                avg_distance = sum(d.pixel_distance for d in recent_data) / len(recent_data)
                
                if avg_distance > 0:
                    relative_accuracy = 1.0 - min(1.0, avg_error / avg_distance)
                else:
                    relative_accuracy = 0.0
                
                overall_quality = (avg_confidence + relative_accuracy) / 2.0
            else:
                overall_quality = 0.0
            
            # 计算覆盖率
            total_zones = (self.screen_width // self.zone_size) * (self.screen_height // self.zone_size)
            covered_zones = len([z for z in self.calibration_zones.values() if z.confidence >= 0.5])
            coverage = covered_zones / total_zones if total_zones > 0 else 0.0
            
            return {
                'overall_quality': overall_quality,
                'sample_count': len(self.calibration_data),
                'coverage': coverage,
                'zones_calibrated': covered_zones,
                'total_zones': total_zones,
                'distance_buckets_calibrated': len([d for d in self.distance_calibration.values() if d['confidence'] >= 0.5]),
                'average_confidence': avg_confidence if recent_data else 0.0,
                'calibration_stats': self.calibration_stats
            }
    
    def save_calibration_data(self, file_path: Optional[str] = None) -> bool:
        """
        保存校准数据到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with self._lock:
                data_file = Path(file_path) if file_path else self.data_file_path
                zones_file = data_file.with_name(data_file.stem + "_zones.json")
                
                # 保存校准数据
                data_to_save = {
                    'calibration_data': [asdict(d) for d in self.calibration_data[-1000:]],  # 只保存最近1000条
                    'calibration_stats': self.calibration_stats,
                    'settings': {
                        'screen_width': self.screen_width,
                        'screen_height': self.screen_height,
                        'zone_size': self.zone_size,
                        'learning_rate': self.learning_rate
                    }
                }
                
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                # 保存区域数据
                zones_to_save = {
                    'calibration_zones': {k: asdict(v) for k, v in self.calibration_zones.items()},
                    'distance_calibration': dict(self.distance_calibration)
                }
                
                with open(zones_file, 'w', encoding='utf-8') as f:
                    json.dump(zones_to_save, f, indent=2, ensure_ascii=False)
                
                return True
                
        except Exception as e:
            print(f"保存校准数据失败: {e}")
            return False
    
    def load_calibration_data(self, file_path: Optional[str] = None) -> bool:
        """
        从文件加载校准数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            data_file = Path(file_path) if file_path else self.data_file_path
            zones_file = data_file.with_name(data_file.stem + "_zones.json")
            
            # 加载校准数据
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                # 恢复校准数据
                if 'calibration_data' in saved_data:
                    self.calibration_data = [
                        CalibrationDataPoint(**d) for d in saved_data['calibration_data']
                    ]
                
                if 'calibration_stats' in saved_data:
                    self.calibration_stats.update(saved_data['calibration_stats'])
            
            # 加载区域数据
            if zones_file.exists():
                with open(zones_file, 'r', encoding='utf-8') as f:
                    zones_data = json.load(f)
                
                if 'calibration_zones' in zones_data:
                    self.calibration_zones = {
                        k: CalibrationZone(**v) for k, v in zones_data['calibration_zones'].items()
                    }
                
                if 'distance_calibration' in zones_data:
                    self.distance_calibration = defaultdict(lambda: {
                        'correction_x': 1.0,
                        'correction_y': 1.0,
                        'sample_count': 0,
                        'confidence': 0.5
                    })
                    for k, v in zones_data['distance_calibration'].items():
                        self.distance_calibration[int(k)] = v
            
            return True
            
        except Exception as e:
            print(f"加载校准数据失败: {e}")
            return False
    
    def reset_calibration(self):
        """
        重置所有校准数据
        """
        with self._lock:
            self.calibration_data.clear()
            self.calibration_zones.clear()
            self.distance_calibration.clear()
            self.calibration_stats = {
                'total_calibrations': 0,
                'successful_calibrations': 0,
                'average_improvement': 0.0,
                'last_calibration_time': 0.0
            }
    
    def export_calibration_report(self, file_path: str) -> bool:
        """
        导出校准报告
        
        Args:
            file_path: 报告文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            quality_report = self.get_calibration_quality()
            
            report = {
                'timestamp': time.time(),
                'quality_report': quality_report,
                'zone_details': {k: asdict(v) for k, v in self.calibration_zones.items()},
                'distance_details': dict(self.distance_calibration),
                'recent_samples': [asdict(d) for d in self.calibration_data[-50:]]  # 最近50个样本
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"导出校准报告失败: {e}")
            return False