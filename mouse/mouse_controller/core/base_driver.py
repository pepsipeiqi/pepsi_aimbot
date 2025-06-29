from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple
import ctypes
import os


class DriverType(Enum):
    MOUSE_CONTROL = "MouseControl"
    GHUB_DEVICE = "GHubDevice"
    LOGITECH_DRIVER = "LogitechDriver"


class MouseButton(Enum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3


class BaseDriver(ABC):
    def __init__(self, dll_path: str):
        self.dll_path = dll_path
        self.driver = None
        self.is_initialized = False
        self._validate_dll_path()
    
    def _validate_dll_path(self):
        if not os.path.exists(self.dll_path):
            raise FileNotFoundError(f"DLL file not found: {self.dll_path}")
    
    @abstractmethod
    def initialize(self) -> bool:
        pass
    
    @abstractmethod
    def cleanup(self):
        pass
    
    @abstractmethod
    def move_relative(self, x: int, y: int) -> bool:
        pass
    
    @abstractmethod
    def move_absolute(self, x: int, y: int) -> bool:
        pass
    
    @abstractmethod
    def mouse_down(self, button: MouseButton) -> bool:
        pass
    
    @abstractmethod
    def mouse_up(self, button: MouseButton) -> bool:
        pass
    
    def click(self, button: MouseButton) -> bool:
        if self.mouse_down(button):
            return self.mouse_up(button)
        return False
    
    @abstractmethod
    def key_down(self, key_code: int) -> bool:
        pass
    
    @abstractmethod
    def key_up(self, key_code: int) -> bool:
        pass
    
    def key_click(self, key_code: int) -> bool:
        if self.key_down(key_code):
            return self.key_up(key_code)
        return False
    
    @abstractmethod
    def scroll(self, direction: int) -> bool:
        pass
    
    def __enter__(self):
        if not self.initialize():
            raise RuntimeError("Failed to initialize driver")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    @property
    @abstractmethod
    def driver_type(self) -> DriverType:
        pass
    
    @property
    def available(self) -> bool:
        return self.is_initialized