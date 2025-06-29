import ctypes
import os
from typing import Optional
from .base_driver import BaseDriver, DriverType, MouseButton


class LogitechDriver(BaseDriver):
    def __init__(self, dll_path: Optional[str] = None):
        if dll_path is None:
            dll_path = os.path.join(os.path.dirname(__file__), "..", "..", "drivers", "logitech.driver.dll")
        super().__init__(dll_path)
        self.device_ok = False
    
    def initialize(self) -> bool:
        try:
            self.driver = ctypes.CDLL(self.dll_path)
            self.device_ok = self.driver.device_open() == 1
            if not self.device_ok:
                print('Error, GHUB or LGS driver not found')
                self.is_initialized = False
                return False
            print('Logitech驱动初始化成功!')
            self.is_initialized = True
            return True
        except FileNotFoundError:
            print('Error, Logitech DLL file not found')
            self.is_initialized = False
            return False
        except Exception as e:
            print(f"Failed to load logitech.driver.dll: {e}")
            self.is_initialized = False
            return False
    
    def cleanup(self):
        self.driver = None
        self.device_ok = False
        self.is_initialized = False
    
    def move_relative(self, x: int, y: int) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        if x == 0 and y == 0:
            return True
        try:
            self.driver.moveR(int(x), int(y), False)
            return True
        except Exception as e:
            print(f"Failed to move mouse relatively: {e}")
            return False
    
    def move_absolute(self, x: int, y: int) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        try:
            self.driver.moveR(int(x), int(y), True)
            return True
        except Exception as e:
            print(f"Failed to move mouse absolutely: {e}")
            return False
    
    def mouse_down(self, button: MouseButton) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        try:
            self.driver.mouse_down(button.value)
            return True
        except Exception as e:
            print(f"Failed to press mouse button: {e}")
            return False
    
    def mouse_up(self, button: MouseButton) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        try:
            self.driver.mouse_up(button.value)
            return True
        except Exception as e:
            print(f"Failed to release mouse button: {e}")
            return False
    
    def key_down(self, key_code: int) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        try:
            self.driver.key_down(key_code)
            return True
        except Exception as e:
            print(f"Failed to press key: {e}")
            return False
    
    def key_up(self, key_code: int) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        try:
            self.driver.key_up(key_code)
            return True
        except Exception as e:
            print(f"Failed to release key: {e}")
            return False
    
    def scroll(self, direction: int) -> bool:
        if not self.is_initialized or not self.device_ok:
            return False
        try:
            self.driver.scroll(direction)
            return True
        except Exception as e:
            print(f"Failed to scroll: {e}")
            return False
    
    @property
    def driver_type(self) -> DriverType:
        return DriverType.LOGITECH_DRIVER