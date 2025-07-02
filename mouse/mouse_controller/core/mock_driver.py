"""
模拟驱动 - 用于测试和开发环境
"""

import time
from .base_driver import BaseDriver


class MockDriver(BaseDriver):
    """模拟驱动 - 用于测试相对坐标功能"""
    
    def __init__(self):
        super().__init__()
        self.total_moves = 0
        self.cumulative_x = 0
        self.cumulative_y = 0
        
    def initialize(self) -> bool:
        """初始化模拟驱动"""
        try:
            self.is_initialized = True
            self.driver_info = {
                'type': 'Mock',
                'dll_path': 'N/A (模拟驱动)',
                'description': '测试用模拟驱动'
            }
            return True
        except Exception:
            self.is_initialized = False
            return False
    
    def move_relative(self, dx: int, dy: int) -> bool:
        """
        模拟相对移动
        
        Args:
            dx: X轴相对移动量
            dy: Y轴相对移动量
            
        Returns:
            bool: 始终返回True
        """
        if not self.is_initialized:
            return False
        
        # 模拟移动延迟
        time.sleep(0.001)
        
        # 记录移动
        self.cumulative_x += dx
        self.cumulative_y += dy
        self.total_moves += 1
        
        return True
    
    def cleanup(self) -> bool:
        """清理驱动资源"""
        try:
            self.is_initialized = False
            return True
        except Exception:
            return False
    
    def get_move_statistics(self) -> dict:
        """获取移动统计"""
        return {
            'total_moves': self.total_moves,
            'cumulative_position': (self.cumulative_x, self.cumulative_y)
        }