"""
True Absolute Positioning System
真正的一步到位绝对定位系统

完全重写的绝对定位实现，不依赖PID控制器
实现真正的"一步到终点"鼠标控制
"""

from .precision_coordinate_mapper import PrecisionCoordinateMapper, HardwareType
from .adaptive_calibration_system import AdaptiveCalibrationSystem
from .hardware_optimizer import HardwareOptimizer
from .true_absolute_controller import TrueAbsoluteController, TargetType, MovementResult
from .predictive_movement import PredictiveMovement, MovementPattern
from .simple_absolute_controller import SimpleAbsoluteMouseController, absolute_mouse_control

__all__ = [
    'PrecisionCoordinateMapper',
    'AdaptiveCalibrationSystem', 
    'HardwareOptimizer',
    'TrueAbsoluteController',
    'PredictiveMovement',
    'SimpleAbsoluteMouseController',
    'absolute_mouse_control',
    'HardwareType',
    'TargetType',
    'MovementResult',
    'MovementPattern'
]

__version__ = '1.0.0'