import ctypes
import os
from typing import Optional
from .base_driver import BaseDriver, DriverType, MouseButton


class MouseControlDriver(BaseDriver):
    def __init__(self, dll_path: Optional[str] = None):
        if dll_path is None:
            dll_path = os.path.join(os.path.dirname(__file__), "..", "..", "drivers", "MouseControl.dll")
        super().__init__(dll_path)
    
    def initialize(self) -> bool:
        try:
            self.driver = ctypes.CDLL(self.dll_path)
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"Failed to load MouseControl.dll: {e}")
            self.is_initialized = False
            return False
    
    def cleanup(self):
        self.driver = None
        self.is_initialized = False
    
    def move_relative(self, x: int, y: int) -> bool:
        if not self.is_initialized:
            return False
        try:
            self.driver.move_R(int(x), int(y))
            return True
        except Exception as e:
            print(f"Failed to move mouse relatively: {e}")
            return False
    
    def move_absolute(self, x: int, y: int) -> bool:
        if not self.is_initialized:
            return False
        try:
            self.driver.move_Abs(int(x), int(y))
            return True
        except Exception as e:
            print(f"Failed to move mouse absolutely: {e}")
            return False
    
    def mouse_down(self, button: MouseButton) -> bool:
        if not self.is_initialized:
            return False
        try:
            if button == MouseButton.LEFT:
                self.driver.click_Left_down()
            elif button == MouseButton.RIGHT:
                self.driver.click_Right_down()
            else:
                return False
            return True
        except Exception as e:
            print(f"Failed to press mouse button: {e}")
            return False
    
    def mouse_up(self, button: MouseButton) -> bool:
        if not self.is_initialized:
            return False
        try:
            if button == MouseButton.LEFT:
                self.driver.click_Left_up()
            elif button == MouseButton.RIGHT:
                self.driver.click_Right_up()
            else:
                return False
            return True
        except Exception as e:
            print(f"Failed to release mouse button: {e}")
            return False
    
    def key_down(self, key_code: int) -> bool:
        return False
    
    def key_up(self, key_code: int) -> bool:
        return False
    
    def scroll(self, direction: int) -> bool:
        return False
    
    @property
    def driver_type(self) -> DriverType:
        return DriverType.MOUSE_CONTROL