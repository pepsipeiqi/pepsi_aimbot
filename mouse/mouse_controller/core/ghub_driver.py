"""
G HUB 驱动 - Logitech G HUB设备驱动
"""

import os
import ctypes
from ctypes import wintypes
from typing import Optional
from .base_driver import BaseDriver


class GHubDriver(BaseDriver):
    """Logitech G HUB 设备驱动"""
    
    def __init__(self):
        super().__init__()
        self.dll = None
        self.dll_path = None
        
    def initialize(self) -> bool:
        """初始化G HUB驱动"""
        try:
            # 查找DLL文件
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            dll_path = os.path.join(project_root, "drivers", "ghub_device.dll")
            
            if not os.path.exists(dll_path):
                return False
            
            # 加载DLL
            self.dll = ctypes.CDLL(dll_path)
            self.dll_path = dll_path
            
            # 设置函数签名
            self.dll.moveR.argtypes = [ctypes.c_int, ctypes.c_int]
            self.dll.moveR.restype = None
            
            self.is_initialized = True
            self.driver_info = {
                'type': 'GHub',
                'dll_path': dll_path,
                'description': 'Logitech G HUB游戏优化驱动'
            }
            
            return True
            
        except Exception as e:
            self.is_initialized = False
            return False
    
    def move_relative(self, dx: int, dy: int) -> bool:
        """
        使用G HUB驱动执行相对移动
        
        Args:
            dx: X轴相对移动量
            dy: Y轴相对移动量
            
        Returns:
            bool: 移动是否成功
        """
        if not self.is_initialized or not self.dll:
            return False
        
        try:
            self.dll.moveR(dx, dy)
            return True
        except Exception:
            return False
    
    def cleanup(self) -> bool:
        """清理驱动资源"""
        try:
            self.dll = None
            self.is_initialized = False
            return True
        except Exception:
            return False