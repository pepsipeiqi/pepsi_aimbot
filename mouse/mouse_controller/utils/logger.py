import logging
import sys
from typing import Optional
from datetime import datetime
from .config import LoggingConfig


class Logger:
    _instance = None
    _logger = None
    
    def __new__(cls, config: Optional[LoggingConfig] = None):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize(config)
        return cls._instance
    
    def _initialize(self, config: Optional[LoggingConfig] = None):
        if self._logger is not None:
            return
        
        if config is None:
            config = LoggingConfig()
        
        self._logger = logging.getLogger('MouseController')
        self._logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
        
        if config.file_path:
            try:
                file_handler = logging.FileHandler(config.file_path, encoding='utf-8')
                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)
            except Exception as e:
                self._logger.warning(f"Failed to create file handler: {e}")
        
        self._logger.info("Logger initialized")
    
    def debug(self, message: str):
        if self._logger:
            self._logger.debug(message)
    
    def info(self, message: str):
        if self._logger:
            self._logger.info(message)
    
    def warning(self, message: str):
        if self._logger:
            self._logger.warning(message)
    
    def error(self, message: str):
        if self._logger:
            self._logger.error(message)
    
    def critical(self, message: str):
        if self._logger:
            self._logger.critical(message)
    
    def log_driver_operation(self, driver_type: str, operation: str, success: bool, **kwargs):
        status = "SUCCESS" if success else "FAILED"
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"[{driver_type}] {operation} - {status}"
        if extra_info:
            message += f" | {extra_info}"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    def log_movement(self, algorithm: str, start_pos: tuple, end_pos: tuple, success: bool, duration: float = None):
        status = "SUCCESS" if success else "FAILED"
        message = f"[MOVEMENT] {algorithm} from {start_pos} to {end_pos} - {status}"
        if duration is not None:
            message += f" | Duration: {duration:.3f}s"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    def log_initialization(self, component: str, success: bool, error_msg: str = None):
        status = "SUCCESS" if success else "FAILED"
        message = f"[INIT] {component} - {status}"
        if not success and error_msg:
            message += f" | Error: {error_msg}"
        
        if success:
            self.info(message)
        else:
            self.error(message)
    
    @classmethod
    def get_instance(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance