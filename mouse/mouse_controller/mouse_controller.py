"""
MouseController 主类 - 纯相对坐标鼠标控制
专门用于游戏瞄准场景，无屏幕坐标依赖
"""

from typing import Optional, Tuple, Dict, List
from .core.base_driver import BaseDriver
from .core.mouse_control_driver import MouseControlDriver
from .core.ghub_driver import GHubDriver
from .core.logitech_driver import LogitechDriver
from .core.mock_driver import MockDriver
from .algorithms.pid_controller import VelocityAwarePIDController
from .utils.logger import setup_logger


class MouseController:
    """
    相对坐标鼠标控制器
    专门用于游戏瞄准，支持纯相对坐标移动
    """
    
    def __init__(self):
        self.driver: Optional[BaseDriver] = None
        self.pid_controller = VelocityAwarePIDController()
        self.logger = setup_logger("MouseController")
        self.game_config = {
            'sensitivity': 1.0,
            'dpi': 800,
            'conversion_ratio': 0.3
        }
        
    def initialize_driver(self) -> bool:
        """
        自动检测并初始化最佳驱动
        优先级: MouseControl.dll > ghub_device.dll > logitech.driver.dll
        
        Returns:
            bool: 初始化是否成功
        """
        drivers_to_try = [
            MouseControlDriver,
            GHubDriver,
            LogitechDriver,
            MockDriver  # 添加模拟驱动作为兜底选项
        ]
        
        for driver_class in drivers_to_try:
            try:
                driver = driver_class()
                if driver.initialize():
                    self.driver = driver
                    driver_info = driver.get_driver_info()
                    if driver_info:
                        self.logger.info(f"成功初始化驱动: {driver_info['type']}")
                    return True
            except Exception as e:
                self.logger.warning(f"驱动 {driver_class.__name__} 初始化失败: {e}")
                continue
        
        self.logger.error("所有驱动初始化失败")
        return False
    
    def move_relative_to_target(self, offset_x: int, offset_y: int, 
                              tolerance: int = 2, max_iterations: int = 200,
                              is_head_target: bool = False) -> bool:
        """
        基于相对偏移的精确移动 - 核心API
        
        Args:
            offset_x: 相对于当前位置的X偏移（游戏坐标）
            offset_y: 相对于当前位置的Y偏移（游戏坐标）
            tolerance: 容差像素（默认2px，保持高精度）
            max_iterations: 最大迭代次数（默认200）
            is_head_target: 是否为头部目标（使用更精确的参数）
            
        Returns:
            bool: 是否成功到达目标（在容差范围内）
        """
        if not self.driver or not self.driver.is_ready():
            self.logger.error("驱动未初始化")
            return False
        
        success, final_error, duration = self.pid_controller.move_to_relative_target(
            self.driver, offset_x, offset_y, tolerance, max_iterations, is_head_target
        )
        
        if success:
            self.logger.debug(f"移动成功: 偏移({offset_x}, {offset_y}), 误差{final_error:.2f}px, 耗时{duration*1000:.1f}ms")
        else:
            self.logger.warning(f"移动失败: 偏移({offset_x}, {offset_y}), 最终误差{final_error:.2f}px")
        
        return success
    
    def fast_move_to_target(self, offset_x: int, offset_y: int, 
                           tolerance: int = 2) -> Tuple[bool, float, float]:
        """
        快速移动到目标 - 返回详细结果
        
        Args:
            offset_x: X偏移量
            offset_y: Y偏移量
            tolerance: 容差
            
        Returns:
            Tuple[bool, float, float]: (成功标志, 最终误差, 耗时)
        """
        if not self.driver or not self.driver.is_ready():
            return False, float('inf'), 0.0
        
        return self.pid_controller.move_to_relative_target(
            self.driver, offset_x, offset_y, tolerance
        )
    
    def configure_for_game(self, game_sensitivity: float, 
                          game_dpi: int, conversion_ratio: float = 0.3):
        """
        游戏特定配置
        
        Args:
            game_sensitivity: 游戏内灵敏度设置
            game_dpi: 游戏DPI设置  
            conversion_ratio: 像素到鼠标单位转换比率
        """
        self.game_config.update({
            'sensitivity': game_sensitivity,
            'dpi': game_dpi,
            'conversion_ratio': conversion_ratio
        })
        self.logger.info(f"游戏配置已更新: {self.game_config}")
    
    def reset_position_tracking(self):
        """
        重置位置跟踪
        
        使用场景：
        - 游戏重启时
        - 切换武器时
        - 游戏窗口位置变化时
        """
        self.pid_controller.reset()
        self.logger.info("位置跟踪已重置")
    
    def get_movement_statistics(self) -> dict:
        """
        获取移动性能统计
        
        Returns:
            dict: 包含精度、速度、成功率等统计信息
        """
        stats = self.pid_controller.get_performance_stats()
        stats.update({
            'driver_ready': self.driver.is_ready() if self.driver else False,
            'game_config': self.game_config.copy()
        })
        return stats
    
    def get_pid_stats(self) -> Optional[Dict]:
        """获取PID统计信息（兼容现有测试）"""
        return self.pid_controller.get_performance_stats()
    
    def get_driver_info(self) -> Optional[Dict]:
        """
        获取当前驱动信息
        
        Returns:
            Optional[Dict]: 驱动信息，如果未初始化则返回None
        """
        if self.driver:
            return self.driver.get_driver_info()
        return None
    
    def is_ready(self) -> bool:
        """
        检查控制器是否就绪
        
        Returns:
            bool: 是否已初始化并就绪
        """
        return self.driver is not None and self.driver.is_ready()
    
    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.cleanup()
            self.driver = None
        self.logger.info("MouseController已清理")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()