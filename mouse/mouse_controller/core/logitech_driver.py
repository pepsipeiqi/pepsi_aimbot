"""
Logitech 通用驱动 - logitech.driver.dll
"""

import os
import ctypes
from ctypes import wintypes
from typing import Optional
from .base_driver import BaseDriver


class LogitechDriver(BaseDriver):
    """Logitech 通用驱动"""
    
    def __init__(self):
        super().__init__()
        self.dll = None
        self.dll_path = None
        
    def initialize(self) -> bool:
        """初始化Logitech通用驱动"""
        try:
            # 查找DLL文件
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            dll_path = os.path.join(project_root, "drivers", "logitech.driver.dll")
            
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
                'type': 'Logitech',
                'dll_path': dll_path,
                'description': 'Logitech通用目的驱动'
            }
            
            return True
            
        except Exception as e:
            self.is_initialized = False
            return False
    
    def move_relative(self, dx: int, dy: int) -> bool:
        """
        使用Logitech驱动执行相对移动
        
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
            return False
        except Exception:
            return False