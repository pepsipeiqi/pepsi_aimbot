"""
准星位置跟踪器 - 实时维护准星在屏幕上的绝对位置
"""

import time
import math
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from ..algorithms.coordinate_mapping import CoordinateMapper, GameSettings


@dataclass
class PositionSnapshot:
    """位置快照"""
    x: float
    y: float
    timestamp: float
    confidence: float = 1.0  # 位置置信度


class CrosshairPositionTracker:
    """
    准星位置跟踪器
    
    核心功能：
    1. 实时维护准星绝对位置
    2. 移动后自动同步位置
    3. 防止位置漂移
    4. 提供校准和重置功能
    """
    
    def __init__(self, screen_width: int, screen_height: int, 
                 coordinate_mapper: Optional[CoordinateMapper] = None):
        """
        初始化准星位置跟踪器
        
        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            coordinate_mapper: 坐标映射器
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 初始化准星位置为屏幕中心
        self.current_x = screen_width / 2.0
        self.current_y = screen_height / 2.0
        
        # 坐标映射器
        self.coordinate_mapper = coordinate_mapper
        if self.coordinate_mapper is None:
            # 创建默认映射器
            default_settings = GameSettings(
                screen_width=screen_width,
                screen_height=screen_height
            )
            self.coordinate_mapper = CoordinateMapper(default_settings)
        
        # 位置历史记录
        self.position_history: List[PositionSnapshot] = []
        self.max_history_size = 100
        
        # 漂移检测和校正
        self.drift_threshold = 5.0  # 漂移阈值（像素）
        self.last_calibration_time = time.time()
        self.calibration_interval = 60.0  # 校准间隔（秒）
        
        # 边界检查 - 减少边距允许全屏移动
        self.boundary_margin = 5  # 边界边距（减少到5像素允许真正全屏移动）
        
        # 统计信息
        self.total_moves = 0
        self.total_drift_corrections = 0
        self.accuracy_stats = {
            'total_error': 0.0,
            'max_error': 0.0,
            'move_count': 0
        }
    
    def get_position(self) -> Tuple[float, float]:
        """
        获取当前准星位置
        
        Returns:
            Tuple[float, float]: (x, y) 当前准星位置
        """
        return self.current_x, self.current_y
    
    def update_after_move(self, mouse_delta_x: int, mouse_delta_y: int) -> bool:
        """
        鼠标移动后更新准星位置
        
        Args:
            mouse_delta_x: 鼠标X轴移动量
            mouse_delta_y: 鼠标Y轴移动量
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 将鼠标移动量转换为屏幕像素移动量
            pixel_delta_x, pixel_delta_y = self.coordinate_mapper.mouse_to_screen_units(
                mouse_delta_x, mouse_delta_y
            )
            
            # 更新位置
            new_x = self.current_x + pixel_delta_x
            new_y = self.current_y + pixel_delta_y
            
            # 改进的边界检查 - 更平滑的边界处理
            new_x = self._apply_boundary_constraints(new_x, self.screen_width)
            new_y = self._apply_boundary_constraints(new_y, self.screen_height)
            
            # 记录位置历史
            self._record_position_snapshot(new_x, new_y)
            
            # 更新当前位置
            self.current_x = new_x
            self.current_y = new_y
            
            self.total_moves += 1
            
            # 定期检查漂移
            if time.time() - self.last_calibration_time > self.calibration_interval:
                self._check_and_correct_drift()
                self.last_calibration_time = time.time()
            
            return True
            
        except Exception as e:
            print(f"位置更新失败: {e}")
            return False
    
    def move_to_absolute_position(self, target_x: float, target_y: float) -> Tuple[int, int]:
        """
        计算移动到绝对位置所需的鼠标移动量
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            
        Returns:
            Tuple[int, int]: (mouse_delta_x, mouse_delta_y) 所需的鼠标移动量
        """
        # 计算像素偏移
        pixel_delta_x = target_x - self.current_x
        pixel_delta_y = target_y - self.current_y
        
        # 转换为鼠标移动单位
        mouse_delta_x, mouse_delta_y = self.coordinate_mapper.screen_to_mouse_units(
            pixel_delta_x, pixel_delta_y
        )
        
        return mouse_delta_x, mouse_delta_y
    
    def set_position(self, x: float, y: float, confidence: float = 1.0):
        """
        直接设置准星位置（用于校准）
        
        Args:
            x: X坐标
            y: Y坐标
            confidence: 位置置信度
        """
        # 边界检查
        x = self._apply_boundary_constraints(x, self.screen_width)
        y = self._apply_boundary_constraints(y, self.screen_height)
        
        self.current_x = x
        self.current_y = y
        
        # 记录高置信度位置
        self._record_position_snapshot(x, y, confidence)
    
    def reset_to_center(self):
        """重置准星位置到屏幕中心"""
        self.current_x = self.screen_width / 2.0
        self.current_y = self.screen_height / 2.0
        
        # 清空历史记录
        self.position_history.clear()
        
        # 重置统计信息
        self.total_moves = 0
        self.total_drift_corrections = 0
        self.accuracy_stats = {
            'total_error': 0.0,
            'max_error': 0.0,
            'move_count': 0
        }
    
    def calibrate_with_known_position(self, known_x: float, known_y: float):
        """
        使用已知位置校准准星跟踪
        
        Args:
            known_x: 已知的准确X坐标
            known_y: 已知的准确Y坐标
        """
        # 计算偏差
        drift_x = known_x - self.current_x
        drift_y = known_y - self.current_y
        drift_distance = math.sqrt(drift_x**2 + drift_y**2)
        
        # 如果偏差超过阈值，进行校正
        if drift_distance > self.drift_threshold:
            self.current_x = known_x
            self.current_y = known_y
            self.total_drift_corrections += 1
            
            # 记录校准位置
            self._record_position_snapshot(known_x, known_y, 1.0)
            
            return True
        
        return False
    
    def _record_position_snapshot(self, x: float, y: float, confidence: float = 1.0):
        """记录位置快照"""
        snapshot = PositionSnapshot(
            x=x,
            y=y,
            timestamp=time.time(),
            confidence=confidence
        )
        
        self.position_history.append(snapshot)
        
        # 保持历史记录大小
        if len(self.position_history) > self.max_history_size:
            self.position_history.pop(0)
    
    def _check_and_correct_drift(self):
        """检查并校正位置漂移"""
        if len(self.position_history) < 5:
            return
        
        # 分析最近的位置历史
        recent_positions = self.position_history[-5:]
        
        # 计算位置变化趋势
        x_trend = sum(pos.x for pos in recent_positions) / len(recent_positions)
        y_trend = sum(pos.y for pos in recent_positions) / len(recent_positions)
        
        # 检查是否存在系统性偏移
        current_drift = math.sqrt(
            (x_trend - self.current_x)**2 + 
            (y_trend - self.current_y)**2
        )
        
        if current_drift > self.drift_threshold:
            # 进行漂移校正
            self.current_x = x_trend
            self.current_y = y_trend
            self.total_drift_corrections += 1
    
    def _apply_boundary_constraints(self, coordinate: float, screen_dimension: int) -> float:
        """
        应用改进的边界约束
        
        Args:
            coordinate: 坐标值
            screen_dimension: 屏幕尺寸（宽度或高度）
            
        Returns:
            float: 约束后的坐标
        """
        # 硬边界
        min_bound = 0
        max_bound = screen_dimension
        
        # 软边界（考虑边距）
        soft_min = self.boundary_margin
        soft_max = screen_dimension - self.boundary_margin
        
        # 首先应用硬边界
        if coordinate < min_bound:
            return min_bound
        elif coordinate > max_bound:
            return max_bound
        
        # 对于软边界附近的坐标，应用渐进约束
        if coordinate < soft_min:
            # 在边距内的坐标，应用轻微的向内拉力
            pull_factor = (soft_min - coordinate) / self.boundary_margin
            return coordinate + pull_factor * 2  # 轻微向内调整
        elif coordinate > soft_max:
            # 在边距内的坐标，应用轻微的向内拉力
            pull_factor = (coordinate - soft_max) / self.boundary_margin
            return coordinate - pull_factor * 2  # 轻微向内调整
        
        return coordinate
    
    def _check_boundary_safety(self, x: float, y: float) -> Tuple[bool, float]:
        """
        检查位置的边界安全性
        
        Args:
            x: X坐标
            y: Y坐标
            
        Returns:
            Tuple[bool, float]: (是否安全, 风险评分)
        """
        # 计算到边界的最小距离
        min_distance_to_edge = min(
            x, y,
            self.screen_width - x,
            self.screen_height - y
        )
        
        # 基于距离计算风险评分
        if min_distance_to_edge > self.boundary_margin:
            return True, 0.0  # 完全安全
        elif min_distance_to_edge > self.boundary_margin / 2:
            risk = 1.0 - (min_distance_to_edge / self.boundary_margin)
            return True, risk  # 轻微风险
        else:
            risk = 1.0 - (min_distance_to_edge / (self.boundary_margin / 2))
            return False, risk  # 高风险
    
    def is_position_valid(self) -> bool:
        """
        检查当前位置是否有效
        
        Returns:
            bool: 位置是否在有效范围内
        """
        return (self.boundary_margin <= self.current_x <= self.screen_width - self.boundary_margin and 
                self.boundary_margin <= self.current_y <= self.screen_height - self.boundary_margin)
    
    def get_position_confidence(self) -> float:
        """
        获取当前位置的置信度
        
        Returns:
            float: 置信度分数 (0.0-1.0)
        """
        if len(self.position_history) < 3:
            return 0.5
        
        # 基于最近移动的一致性计算置信度
        recent_moves = self.position_history[-3:]
        
        # 计算位置变化的一致性
        position_variance = 0.0
        for i in range(1, len(recent_moves)):
            distance = math.sqrt(
                (recent_moves[i].x - recent_moves[i-1].x)**2 + 
                (recent_moves[i].y - recent_moves[i-1].y)**2
            )
            position_variance += distance
        
        # 转换为置信度分数
        if position_variance < 10:
            return 0.9
        elif position_variance < 50:
            return 0.7
        else:
            return 0.3
    
    def get_tracking_statistics(self) -> Dict:
        """
        获取跟踪统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        confidence = self.get_position_confidence()
        
        return {
            'current_position': (self.current_x, self.current_y),
            'total_moves': self.total_moves,
            'drift_corrections': self.total_drift_corrections,
            'position_confidence': confidence,
            'is_valid_position': self.is_position_valid(),
            'history_size': len(self.position_history),
            'screen_bounds': (self.screen_width, self.screen_height),
            'drift_threshold': self.drift_threshold,
            'last_calibration': self.last_calibration_time,
            'accuracy_stats': self.accuracy_stats.copy()
        }
    
    def update_screen_resolution(self, width: int, height: int):
        """
        更新屏幕分辨率
        
        Args:
            width: 新的屏幕宽度
            height: 新的屏幕高度
        """
        # 按比例调整当前位置
        x_ratio = width / self.screen_width
        y_ratio = height / self.screen_height
        
        self.current_x *= x_ratio
        self.current_y *= y_ratio
        
        # 更新屏幕尺寸
        self.screen_width = width
        self.screen_height = height
        
        # 更新坐标映射器
        if hasattr(self.coordinate_mapper, 'settings'):
            self.coordinate_mapper.settings.screen_width = width
            self.coordinate_mapper.settings.screen_height = height
            self.coordinate_mapper._calculate_derived_values()
    
    def export_calibration_data(self) -> Dict:
        """
        导出校准数据
        
        Returns:
            Dict: 校准数据
        """
        return {
            'current_position': (self.current_x, self.current_y),
            'screen_resolution': (self.screen_width, self.screen_height),
            'position_history': [
                {
                    'x': pos.x,
                    'y': pos.y,
                    'timestamp': pos.timestamp,
                    'confidence': pos.confidence
                }
                for pos in self.position_history
            ],
            'mapping_info': self.coordinate_mapper.get_mapping_info(),
            'statistics': self.get_tracking_statistics()
        }
    
    def import_calibration_data(self, data: Dict) -> bool:
        """
        导入校准数据
        
        Args:
            data: 校准数据字典
            
        Returns:
            bool: 导入是否成功
        """
        try:
            # 恢复位置
            self.current_x, self.current_y = data['current_position']
            
            # 恢复历史记录
            self.position_history = []
            for pos_data in data.get('position_history', []):
                snapshot = PositionSnapshot(
                    x=pos_data['x'],
                    y=pos_data['y'],
                    timestamp=pos_data['timestamp'],
                    confidence=pos_data['confidence']
                )
                self.position_history.append(snapshot)
            
            # 恢复统计信息
            if 'statistics' in data:
                stats = data['statistics']
                self.total_moves = stats.get('total_moves', 0)
                self.total_drift_corrections = stats.get('drift_corrections', 0)
                self.accuracy_stats = stats.get('accuracy_stats', self.accuracy_stats)
            
            return True
            
        except Exception as e:
            print(f"导入校准数据失败: {e}")
            return False