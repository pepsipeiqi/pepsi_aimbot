"""
简化的统一绝对定位API接口
SimpleAbsoluteMouseController

为用户提供最简单易用的"一步到终点"鼠标控制接口
隐藏所有技术复杂性，专注于核心功能
"""

from typing import Tuple, Optional, Union, Dict, Any
from contextlib import contextmanager
import time

from .true_absolute_controller import TrueAbsoluteController, MovementResult, TargetType, MovementStats
from .precision_coordinate_mapper import HardwareType
from ..core.base_driver import BaseDriver
from ..core.mouse_control_driver import MouseControlDriver
from ..core.ghub_driver import GHubDriver
from ..core.logitech_driver import LogitechDriver
from ..core.mock_driver import MockDriver


class SimpleAbsoluteMouseController:
    """
    简化的绝对定位鼠标控制器
    
    核心理念：告诉我去哪里，我就一步到位
    
    使用示例:
    ```python
    # 最简单的使用方式
    with SimpleAbsoluteMouseController() as mouse:
        # 一步到位移动到屏幕坐标 (500, 300)
        mouse.move_to(500, 300)
        
        # 高精度头部瞄准
        mouse.headshot_move_to(800, 400)
        
        # 预测性移动（目标在移动）
        mouse.predictive_move_to(600, 350, target_speed=(100, -50))
    ```
    """
    
    def __init__(self, screen_width: int = 1920, screen_height: int = 1080,
                 dpi: int = 800, sensitivity: float = 1.0,
                 auto_detect_hardware: bool = True,
                 hardware_type: Optional[str] = None):
        """
        初始化简化绝对定位控制器
        
        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            dpi: 鼠标DPI
            sensitivity: 游戏内灵敏度
            auto_detect_hardware: 是否自动检测硬件
            hardware_type: 指定硬件类型 ('MouseControl', 'GHub', 'Logitech')
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dpi = dpi
        self.sensitivity = sensitivity
        self.auto_detect_hardware = auto_detect_hardware
        
        # 硬件类型映射
        self.hardware_type_map = {
            'mousecontrol': HardwareType.MOUSE_CONTROL,
            'ghub': HardwareType.GHUB,
            'logitech': HardwareType.LOGITECH
        }
        
        # 确定硬件类型
        if hardware_type:
            self.hardware_type = self.hardware_type_map.get(hardware_type.lower(), HardwareType.MOUSE_CONTROL)
        else:
            self.hardware_type = HardwareType.MOUSE_CONTROL  # 默认使用最佳硬件
        
        # 核心组件
        self.controller: Optional[TrueAbsoluteController] = None
        self.driver: Optional[BaseDriver] = None
        self.is_initialized = False
        
        # 性能统计
        self.session_stats = {
            'session_start_time': time.time(),
            'total_moves': 0,
            'successful_moves': 0,
            'failed_moves': 0
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()
    
    def initialize(self) -> bool:
        """
        初始化控制器和硬件驱动
        
        Returns:
            bool: 初始化是否成功
        """
        if self.is_initialized:
            return True
        
        try:
            # 初始化控制器
            self.controller = TrueAbsoluteController(
                screen_width=self.screen_width,
                screen_height=self.screen_height,
                dpi=self.dpi,
                sensitivity=self.sensitivity,
                hardware_type=self.hardware_type
            )
            
            # 初始化驱动
            if self.auto_detect_hardware:
                self.driver = self._auto_detect_driver()
            else:
                self.driver = self._initialize_specific_driver()
            
            if not self.driver:
                return False
            
            # 设置驱动
            self.controller.set_driver(self.driver)
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"初始化失败: {e}")
            return False
    
    def _auto_detect_driver(self) -> Optional[BaseDriver]:
        """
        自动检测并初始化最佳驱动
        
        Returns:
            BaseDriver: 初始化成功的驱动
        """
        driver_classes = [
            (MouseControlDriver, HardwareType.MOUSE_CONTROL),
            (GHubDriver, HardwareType.GHUB),
            (LogitechDriver, HardwareType.LOGITECH),
            (MockDriver, HardwareType.UNKNOWN)  # 兜底驱动
        ]
        
        for driver_class, hardware_type in driver_classes:
            try:
                driver = driver_class()
                if driver.initialize():
                    # 更新硬件类型
                    self.hardware_type = hardware_type
                    if self.controller:
                        self.controller.hardware_type = hardware_type
                        self.controller.coordinate_mapper.hardware_type = hardware_type
                        self.controller.coordinate_mapper.current_profile = self.controller.coordinate_mapper.hardware_profiles[hardware_type]
                    
                    print(f"成功初始化驱动: {driver_class.__name__}")
                    return driver
            except Exception as e:
                print(f"驱动 {driver_class.__name__} 初始化失败: {e}")
                continue
        
        return None
    
    def _initialize_specific_driver(self) -> Optional[BaseDriver]:
        """
        初始化指定的驱动
        
        Returns:
            BaseDriver: 初始化成功的驱动
        """
        driver_map = {
            HardwareType.MOUSE_CONTROL: MouseControlDriver,
            HardwareType.GHUB: GHubDriver,
            HardwareType.LOGITECH: LogitechDriver
        }
        
        driver_class = driver_map.get(self.hardware_type, MouseControlDriver)
        
        try:
            driver = driver_class()
            if driver.initialize():
                return driver
        except Exception as e:
            print(f"指定驱动初始化失败: {e}")
        
        return None
    
    def move_to(self, x: float, y: float) -> bool:
        """
        一步到位移动到指定坐标
        
        Args:
            x: 目标X坐标
            y: 目标Y坐标
            
        Returns:
            bool: 移动是否成功
        """
        if not self._ensure_initialized():
            return False
        
        stats = self.controller.move_to_absolute_position(x, y, TargetType.GENERAL)
        return self._process_movement_result(stats)
    
    def headshot_move_to(self, x: float, y: float) -> bool:
        """
        高精度头部瞄准移动
        
        Args:
            x: 目标X坐标
            y: 目标Y坐标
        
        Returns:
            bool: 移动是否成功
        """
        if not self._ensure_initialized():
            return False
        
        stats = self.controller.move_to_absolute_position(x, y, TargetType.HEAD)
        return self._process_movement_result(stats)
    
    def body_move_to(self, x: float, y: float) -> bool:
        """
        身体瞄准移动（速度与精度平衡）
        
        Args:
            x: 目标X坐标
            y: 目标Y坐标
        
        Returns:
            bool: 移动是否成功
        """
        if not self._ensure_initialized():
            return False
        
        stats = self.controller.move_to_absolute_position(x, y, TargetType.BODY)
        return self._process_movement_result(stats)
    
    def precise_move_to(self, x: float, y: float) -> bool:
        """
        超精确移动（最高精度）
        
        Args:
            x: 目标X坐标
            y: 目标Y坐标
        
        Returns:
            bool: 移动是否成功
        """
        if not self._ensure_initialized():
            return False
        
        stats = self.controller.move_to_absolute_position(x, y, TargetType.PRECISE)
        return self._process_movement_result(stats)
    
    def predictive_move_to(self, x: float, y: float, 
                          target_speed: Optional[Tuple[float, float]] = None,
                          prediction_time_ms: float = 50.0) -> bool:
        """
        预测性移动（适用于移动目标）
        
        Args:
            x: 当前目标X坐标
            y: 当前目标Y坐标
            target_speed: 目标移动速度 (vx, vy) 像素/秒
            prediction_time_ms: 预测时间（毫秒）
            
        Returns:
            bool: 移动是否成功
        """
        if not self._ensure_initialized():
            return False
        
        stats = self.controller.predictive_move_to_target(
            x, y, target_speed, prediction_time_ms, TargetType.GENERAL
        )
        return self._process_movement_result(stats)
    
    def move_by(self, offset_x: float, offset_y: float) -> bool:
        """
        相对移动（保持向后兼容）
        
        Args:
            offset_x: X轴偏移量
            offset_y: Y轴偏移量
        
        Returns:
            bool: 移动是否成功
        """
        if not self._ensure_initialized():
            return False
        
        stats = self.controller.move_to_relative_target(offset_x, offset_y, TargetType.GENERAL)
        return self._process_movement_result(stats)
    
    def get_position(self) -> Tuple[float, float]:
        """
        获取当前准星位置
        
        Returns:
            Tuple[float, float]: (x, y) 坐标
        """
        if not self._ensure_initialized():
            return 0.0, 0.0
        
        return self.controller.get_crosshair_position()
    
    def set_position(self, x: float, y: float):
        """
        设置当前准星位置（校准用）
        
        Args:
            x: X坐标
            y: Y坐标
        """
        if self._ensure_initialized():
            self.controller.set_crosshair_position(x, y)
    
    def calibrate_position(self, actual_x: float, actual_y: float):
        """
        校准准星位置（用于提高精度）
        
        Args:
            actual_x: 实际准星X坐标
            actual_y: 实际准星Y坐标
        """
        if self._ensure_initialized():
            self.controller.calibrate_position(actual_x, actual_y)
    
    def update_settings(self, dpi: Optional[int] = None, 
                       sensitivity: Optional[float] = None):
        """
        更新设置
        
        Args:
            dpi: 新的DPI设置
            sensitivity: 新的灵敏度设置
        """
        if dpi is not None:
            self.dpi = dpi
        
        if sensitivity is not None:
            self.sensitivity = sensitivity
        
        if self._ensure_initialized():
            self.controller.update_settings(dpi=dpi, sensitivity=sensitivity)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计数据
        """
        if not self._ensure_initialized():
            return {}
        
        # 获取控制器统计
        controller_stats = self.controller.get_performance_stats()
        
        # 添加会话统计
        session_duration = time.time() - self.session_stats['session_start_time']
        
        stats = {
            **controller_stats,
            'session_duration_seconds': session_duration,
            'session_total_moves': self.session_stats['total_moves'],
            'session_successful_moves': self.session_stats['successful_moves'],
            'session_failed_moves': self.session_stats['failed_moves'],
            'hardware_type': self.hardware_type.value,
            'dpi': self.dpi,
            'sensitivity': self.sensitivity
        }
        
        return stats
    
    def print_performance_summary(self):
        """
        打印性能摘要
        """
        stats = self.get_performance_stats()
        
        print("\n=== 绝对定位鼠标控制器性能摘要 ===")
        print(f"硬件类型: {stats.get('hardware_type', 'Unknown')}")
        print(f"DPI: {stats.get('dpi', 0)}, 灵敏度: {stats.get('sensitivity', 0)}")
        print(f"会话时长: {stats.get('session_duration_seconds', 0):.1f}秒")
        print(f"总移动次数: {stats.get('total_moves', 0)}")
        print(f"成功次数: {stats.get('successful_moves', 0)}")
        print(f"成功率: {stats.get('success_rate', 0)*100:.1f}%")
        print(f"平均执行时间: {stats.get('average_execution_time', 0):.1f}ms")
        print(f"平均精度: {stats.get('average_accuracy', 0)*100:.1f}%")
        
        if 'recent_success_rate' in stats:
            print(f"最近成功率: {stats['recent_success_rate']*100:.1f}%")
            print(f"最近平均时间: {stats.get('recent_average_time', 0):.1f}ms")
            print(f"最近平均精度: {stats.get('recent_average_accuracy', 0)*100:.1f}%")
        
        print("================================\n")
    
    def _ensure_initialized(self) -> bool:
        """
        确保控制器已初始化
        
        Returns:
            bool: 是否已初始化
        """
        if not self.is_initialized:
            return self.initialize()
        return True
    
    def _process_movement_result(self, stats: MovementStats) -> bool:
        """
        处理移动结果
        
        Args:
            stats: 移动统计信息
            
        Returns:
            bool: 移动是否成功
        """
        # 更新会话统计
        self.session_stats['total_moves'] += 1
        
        if stats.result == MovementResult.SUCCESS:
            self.session_stats['successful_moves'] += 1
            return True
        else:
            self.session_stats['failed_moves'] += 1
            return False
    
    def cleanup(self):
        """
        清理资源
        """
        if self.driver:
            try:
                self.driver.cleanup()
            except:
                pass
        
        self.is_initialized = False


# 便捷函数
@contextmanager
def absolute_mouse_control(screen_width: int = 1920, screen_height: int = 1080,
                          dpi: int = 800, sensitivity: float = 1.0):
    """
    便捷的上下文管理器
    
    使用示例:
    ```python
    with absolute_mouse_control() as mouse:
        mouse.move_to(500, 300)
        mouse.headshot_move_to(800, 400)
    ```
    
    Args:
        screen_width: 屏幕宽度
        screen_height: 屏幕高度
        dpi: 鼠标DPI
        sensitivity: 游戏内灵敏度
        
    Yields:
        SimpleAbsoluteMouseController: 鼠标控制器实例
    """
    controller = SimpleAbsoluteMouseController(
        screen_width=screen_width,
        screen_height=screen_height,
        dpi=dpi,
        sensitivity=sensitivity
    )
    
    try:
        controller.initialize()
        yield controller
    finally:
        controller.cleanup()


# 全局单例实例（可选）
_global_controller: Optional[SimpleAbsoluteMouseController] = None


def get_global_controller(**kwargs) -> SimpleAbsoluteMouseController:
    """
    获取全局控制器实例
    
    Args:
        **kwargs: 控制器初始化参数
        
    Returns:
        SimpleAbsoluteMouseController: 全局控制器实例
    """
    global _global_controller
    
    if _global_controller is None:
        _global_controller = SimpleAbsoluteMouseController(**kwargs)
        _global_controller.initialize()
    
    return _global_controller


def cleanup_global_controller():
    """
    清理全局控制器
    """
    global _global_controller
    
    if _global_controller:
        _global_controller.cleanup()
        _global_controller = None


# 简化的全局函数接口
def move_to(x: float, y: float) -> bool:
    """全局函数：移动到指定坐标"""
    return get_global_controller().move_to(x, y)


def headshot_move_to(x: float, y: float) -> bool:
    """全局函数：高精度头部瞄准"""
    return get_global_controller().headshot_move_to(x, y)


def predictive_move_to(x: float, y: float, target_speed: Optional[Tuple[float, float]] = None) -> bool:
    """全局函数：预测性移动"""
    return get_global_controller().predictive_move_to(x, y, target_speed)