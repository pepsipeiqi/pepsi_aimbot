"""
基础驱动抽象类 - 仅支持相对移动
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict


class BaseDriver(ABC):
    """鼠标驱动基类 - 专注于相对移动功能"""
    
    def __init__(self):
        self.is_initialized = False
        self.driver_info = {}
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化驱动
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def move_relative(self, dx: int, dy: int) -> bool:
        """
        相对移动鼠标
        
        Args:
            dx: X轴相对移动量
            dy: Y轴相对移动量
            
        Returns:
            bool: 移动是否成功
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """
        清理驱动资源
        
        Returns:
            bool: 清理是否成功
        """
        pass
    
    def get_driver_info(self) -> Optional[Dict]:
        """
        获取驱动信息
        
        Returns:
            Optional[Dict]: 驱动信息，如果未初始化则返回None
        """
        if self.is_initialized:
            return self.driver_info
        return None
    
    def is_ready(self) -> bool:
        """
        检查驱动是否就绪
        
        Returns:
            bool: 驱动是否已初始化并就绪
        """
        return self.is_initialized