import os
import time
from typing import Optional, List, Tuple, Type, Union
from enum import Enum

from .core.base_driver import BaseDriver, DriverType, MouseButton
from .core.mouse_control_driver import MouseControlDriver
from .core.ghub_driver import GHubDriver
from .core.logitech_driver import LogitechDriver
from .algorithms.linear_movement import LinearMovement
from .algorithms.pid_controller import PIDController, pid_mouse_move
from .algorithms.ladrc_controller import LADRCController, control_movimiento_raton
from .utils.config import Config, MouseControllerConfig
from .utils.logger import Logger
from .utils.position import Position, Point


class MovementAlgorithm(Enum):
    """
    鼠标移动算法枚举
    
    根据测试结果：
    - PID: 最高精度(平均误差2.38px)，最快速度(0.009s)，推荐用于精密操作
    - LINEAR: 直线移动，轨迹可预测，适合简单移动场景
    - BEZIER: 曲线移动，模拟人类行为，适合反检测场景
    - LADRC: 线性自抗扰控制，抗干扰能力强，适合复杂环境
    """
    LINEAR = "linear"   # 线性移动算法（保留但不推荐使用）
    BEZIER = "bezier"   # 贝塞尔曲线算法（保留但不推荐使用）
    PID = "pid"         # PID控制算法（推荐，高精度高速度）
    LADRC = "ladrc"     # 线性自抗扰控制算法（保留但不推荐使用）


class MouseController:
    def __init__(self, config_path: Optional[str] = None, driver_path: Optional[str] = None):
        self.config = Config(config_path)
        self.logger = Logger(self.config.get_logging_config())
        self.driver: Optional[BaseDriver] = None
        self.driver_path = driver_path
        self._available_drivers = []
        
        self.logger.info("MouseController initialized")
        self._detect_available_drivers()
    
    def _detect_available_drivers(self):
        base_path = self.driver_path or os.path.dirname(__file__)
        parent_path = os.path.dirname(base_path)
        drivers_path = os.path.join(parent_path, "drivers")
        
        driver_configs = [
            (MouseControlDriver, os.path.join(drivers_path, "MouseControl.dll")),
            (GHubDriver, os.path.join(drivers_path, "ghub_device.dll")),
            (LogitechDriver, os.path.join(drivers_path, "logitech.driver.dll"))
        ]
        
        self._available_drivers = []
        for driver_class, dll_path in driver_configs:
            if os.path.exists(dll_path):
                self._available_drivers.append((driver_class, dll_path))
                self.logger.info(f"Found driver: {driver_class.__name__} at {dll_path}")
        
        if not self._available_drivers:
            self.logger.warning("No drivers found")
    
    def initialize_driver(self, driver_type: Optional[DriverType] = None) -> bool:
        if self.driver and self.driver.available:
            self.logger.info("Driver already initialized")
            return True
        
        if driver_type is None:
            return self._auto_initialize_driver()
        
        driver_class_map = {
            DriverType.MOUSE_CONTROL: MouseControlDriver,
            DriverType.GHUB_DEVICE: GHubDriver,
            DriverType.LOGITECH_DRIVER: LogitechDriver
        }
        
        if driver_type not in driver_class_map:
            self.logger.error(f"Unknown driver type: {driver_type}")
            return False
        
        driver_class = driver_class_map[driver_type]
        
        for available_class, dll_path in self._available_drivers:
            if available_class == driver_class:
                return self._try_initialize_driver(available_class, dll_path)
        
        self.logger.error(f"Driver {driver_type} not available")
        return False
    
    def _auto_initialize_driver(self) -> bool:
        if not self._available_drivers:
            self.logger.error("No drivers available for auto-initialization")
            return False
        
        preferred = self.config.get_driver_config().preferred_driver.lower()
        
        if preferred != "auto":
            driver_preference = {
                "logitech": LogitechDriver,
                "ghub": GHubDriver,
                "mousecontrol": MouseControlDriver
            }
            
            if preferred in driver_preference:
                preferred_class = driver_preference[preferred]
                for driver_class, dll_path in self._available_drivers:
                    if driver_class == preferred_class:
                        if self._try_initialize_driver(driver_class, dll_path):
                            return True
        
        for driver_class, dll_path in self._available_drivers:
            if self._try_initialize_driver(driver_class, dll_path):
                return True
        
        self.logger.error("Failed to initialize any driver")
        return False
    
    def _try_initialize_driver(self, driver_class: Type[BaseDriver], dll_path: str) -> bool:
        try:
            self.driver = driver_class(dll_path)
            if self.driver.initialize():
                self.logger.log_initialization(f"{driver_class.__name__}", True)
                return True
            else:
                self.logger.log_initialization(f"{driver_class.__name__}", False, "Initialization failed")
                self.driver = None
                return False
        except Exception as e:
            self.logger.log_initialization(f"{driver_class.__name__}", False, str(e))
            self.driver = None
            return False
    
    def cleanup(self):
        if self.driver:
            self.driver.cleanup()
            self.driver = None
            self.logger.info("Driver cleaned up")
    
    def is_ready(self) -> bool:
        return self.driver is not None and self.driver.available
    
    def move_relative(self, x: int, y: int) -> bool:
        if not self.is_ready():
            self.logger.error("Driver not ready for relative move")
            return False
        
        success = self.driver.move_relative(x, y)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"move_relative({x}, {y})", 
            success
        )
        return success
    
    def move_absolute(self, x: int, y: int) -> bool:
        if not self.is_ready():
            self.logger.error("Driver not ready for absolute move")
            return False
        
        success = self.driver.move_absolute(x, y)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"move_absolute({x}, {y})", 
            success
        )
        return success
    
    def click(self, button: MouseButton = MouseButton.LEFT) -> bool:
        if not self.is_ready():
            self.logger.error("Driver not ready for click")
            return False
        
        success = self.driver.click(button)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"click({button.name})", 
            success
        )
        return success
    
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> bool:
        if not self.is_ready():
            return False
        
        success = self.driver.mouse_down(button)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"mouse_down({button.name})", 
            success
        )
        return success
    
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> bool:
        if not self.is_ready():
            return False
        
        success = self.driver.mouse_up(button)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"mouse_up({button.name})", 
            success
        )
        return success
    
    def key_click(self, key_code: int) -> bool:
        if not self.is_ready():
            return False
        
        success = self.driver.key_click(key_code)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"key_click({key_code})", 
            success
        )
        return success
    
    def scroll(self, direction: int) -> bool:
        if not self.is_ready():
            return False
        
        success = self.driver.scroll(direction)
        self.logger.log_driver_operation(
            self.driver.driver_type.value, 
            f"scroll({direction})", 
            success
        )
        return success
    
    def smooth_move_to(
        self, 
        x: int, 
        y: int, 
        algorithm: MovementAlgorithm = MovementAlgorithm.PID,  # 默认使用PID算法（高精度）
        **kwargs
    ) -> bool:
        if not self.is_ready():
            self.logger.error("Driver not ready for smooth move")
            return False
        
        start_pos = Position.get_current().to_tuple()
        start_time = time.time()
        
        try:
            # 算法分发逻辑：根据测试结果，PID算法精度最高(2.38px)，速度最快(0.009s)
            if algorithm == MovementAlgorithm.PID:
                # PID控制算法：推荐使用，高精度高速度
                success = self._pid_move(x, y, **kwargs)
            elif algorithm == MovementAlgorithm.LINEAR:
                # 线性移动算法：保留但不推荐，精度较差(15.03px)
                success = self._linear_move(x, y, **kwargs)
            elif algorithm == MovementAlgorithm.BEZIER:
                # 贝塞尔曲线算法：保留但不推荐，精度较差(15.03px)，速度慢(0.330s)
                success = self._bezier_move(x, y, **kwargs)
            elif algorithm == MovementAlgorithm.LADRC:
                # LADRC控制算法：保留但不推荐
                success = self._ladrc_move(x, y, **kwargs)
            else:
                self.logger.error(f"Unknown movement algorithm: {algorithm}")
                return False
            
            duration = time.time() - start_time
            self.logger.log_movement(
                algorithm.value, 
                start_pos, 
                (x, y), 
                success, 
                duration
            )
            return success
            
        except Exception as e:
            self.logger.error(f"Smooth move failed: {e}")
            return False
    
    def _linear_move(self, x: int, y: int, **kwargs) -> bool:
        """
        线性移动算法实现（不推荐使用）
        
        测试结果显示精度较差：
        - 平均误差：15.03像素
        - 平均耗时：0.214秒
        
        仅在特殊需求时使用（如需要直线轨迹）
        """
        num_steps = kwargs.get('num_steps', self.config.get_movement_config().default_steps)
        delay = kwargs.get('delay', self.config.get_movement_config().default_delay)
        
        return LinearMovement.absolute_smooth_move(
            self.driver, x, y, num_steps, delay
        )
    
    def _bezier_move(self, x: int, y: int, **kwargs) -> bool:
        """
        贝塞尔曲线移动算法实现（不推荐使用）
        
        测试结果显示性能较差：
        - 平均误差：15.03像素
        - 平均耗时：0.330秒（最慢）
        
        仅在需要模拟人类行为或反检测时使用
        """
        control_x = kwargs.get('control_x')
        control_y = kwargs.get('control_y')
        num_steps = kwargs.get('num_steps', 50)
        delay = kwargs.get('delay', self.config.get_movement_config().default_delay)
        
        return LinearMovement.bezier_curve_move(
            self.driver, x, y, control_x, control_y, num_steps, delay
        )
    
    def _pid_move(self, x: int, y: int, **kwargs) -> bool:
        """
        PID控制移动算法实现
        
        根据测试结果，PID算法具有最佳性能：
        - 平均误差：2.38像素（其他算法15.03像素）
        - 平均耗时：0.009秒（其他算法0.214-0.330秒）
        - 成功率：100%
        
        推荐作为默认算法使用
        """
        tolerance = kwargs.get('tolerance', self.config.get_movement_config().default_tolerance)
        max_iterations = kwargs.get('max_iterations', self.config.get_movement_config().max_iterations)
        
        return pid_mouse_move(self.driver, x, y, tolerance, max_iterations)
    
    def _ladrc_move(self, x: int, y: int, **kwargs) -> bool:
        """
        LADRC（线性自抗扰控制）移动算法实现（不推荐使用）
        
        该算法理论上具有抗干扰能力，但测试显示PID算法性能更优。
        仅在特殊的抗干扰需求场景下使用。
        """
        wc = kwargs.get('wc', self.config.get_movement_config().ladrc_wc)
        wo = kwargs.get('wo', self.config.get_movement_config().ladrc_wo)
        bo = kwargs.get('bo', self.config.get_movement_config().ladrc_bo)
        
        success, trajectory = control_movimiento_raton(self.driver, x, y, wc, wo, bo)
        return success
    
    def get_current_position(self) -> Tuple[int, int]:
        return Position.get_current().to_tuple()
    
    def get_screen_size(self) -> Tuple[int, int]:
        return Position.get_screen_size().to_tuple()
    
    def get_driver_info(self) -> Optional[dict]:
        if not self.driver:
            return None
        
        return {
            "type": self.driver.driver_type.value,
            "available": self.driver.available,
            "dll_path": self.driver.dll_path
        }
    
    def get_available_drivers(self) -> List[str]:
        return [driver_class.__name__ for driver_class, _ in self._available_drivers]
    
    def __enter__(self):
        if not self.initialize_driver():
            raise RuntimeError("Failed to initialize driver")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()