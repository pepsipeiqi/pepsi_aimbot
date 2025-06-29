import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class DriverConfig:
    mouse_control_dll: str = "MouseControl.dll"
    ghub_device_dll: str = "ghub_device.dll"
    logitech_driver_dll: str = "logitech.driver.dll"
    preferred_driver: str = "auto"
    retry_count: int = 3


@dataclass
class MovementConfig:
    default_delay: float = 0.01
    default_steps: int = 20
    default_tolerance: int = 3
    max_iterations: int = 100
    pid_kp: float = 0.25
    pid_ki: float = 0.01
    pid_kd: float = 0.01
    ladrc_wc: float = 1.0
    ladrc_wo: float = 1.0
    ladrc_bo: float = 0.7


@dataclass
class LoggingConfig:
    enabled: bool = True
    level: str = "INFO"
    file_path: Optional[str] = None
    console_output: bool = True


@dataclass
class MouseControllerConfig:
    driver: DriverConfig = None
    movement: MovementConfig = None
    logging: LoggingConfig = None
    
    def __post_init__(self):
        if self.driver is None:
            self.driver = DriverConfig()
        if self.movement is None:
            self.movement = MovementConfig()
        if self.logging is None:
            self.logging = LoggingConfig()


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "mouse_controller_config.json"
        self.config = MouseControllerConfig()
        self.load()
    
    def load(self) -> bool:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._update_config_from_dict(data)
                return True
        except Exception as e:
            print(f"Failed to load config: {e}")
        return False
    
    def save(self) -> bool:
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    def _update_config_from_dict(self, data: Dict[str, Any]):
        if "driver" in data:
            driver_data = data["driver"]
            self.config.driver = DriverConfig(**{k: v for k, v in driver_data.items() if hasattr(DriverConfig, k)})
        
        if "movement" in data:
            movement_data = data["movement"]
            self.config.movement = MovementConfig(**{k: v for k, v in movement_data.items() if hasattr(MovementConfig, k)})
        
        if "logging" in data:
            logging_data = data["logging"]
            self.config.logging = LoggingConfig(**{k: v for k, v in logging_data.items() if hasattr(LoggingConfig, k)})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver": asdict(self.config.driver),
            "movement": asdict(self.config.movement),
            "logging": asdict(self.config.logging)
        }
    
    def get_driver_config(self) -> DriverConfig:
        return self.config.driver
    
    def get_movement_config(self) -> MovementConfig:
        return self.config.movement
    
    def get_logging_config(self) -> LoggingConfig:
        return self.config.logging
    
    def update_driver_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config.driver, key):
                setattr(self.config.driver, key, value)
    
    def update_movement_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config.movement, key):
                setattr(self.config.movement, key, value)
    
    def update_logging_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config.logging, key):
                setattr(self.config.logging, key, value)