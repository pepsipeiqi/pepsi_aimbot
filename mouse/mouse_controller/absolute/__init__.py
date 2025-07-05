"""
绝对定位鼠标控制模块

从相对移动系统迁移到绝对定位系统，实现真正的"一步到位"瞄准
"""

from .crosshair_tracker import CrosshairPositionTracker
from .position_calculator import AbsolutePositionCalculator
from .absolute_controller import AbsoluteMouseController

__all__ = [
    'CrosshairPositionTracker',
    'AbsolutePositionCalculator',
    'AbsoluteMouseController'
]