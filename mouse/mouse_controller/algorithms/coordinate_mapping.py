"""
坐标映射算法 - 屏幕坐标到鼠标单位的精确转换
"""

import math
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class GameSettings:
    """游戏设置参数"""
    dpi: int = 800
    sensitivity: float = 1.0
    fov_x: float = 90.0  # 水平视野角度
    fov_y: float = 0.0   # 垂直视野角度（自动计算）
    screen_width: int = 1920
    screen_height: int = 1080
    aspect_ratio: float = 16.0/9.0  # 自动计算


class CoordinateMapper:
    """坐标映射器 - 核心转换算法"""
    
    def __init__(self, game_settings: GameSettings):
        self.settings = game_settings
        self._calculate_derived_values()
    
    def _calculate_derived_values(self):
        """计算派生值"""
        # 计算纵横比
        self.settings.aspect_ratio = self.settings.screen_width / self.settings.screen_height
        
        # 计算垂直FOV（如果未设置）
        if self.settings.fov_y == 0.0:
            self.settings.fov_y = math.degrees(
                2 * math.atan(math.tan(math.radians(self.settings.fov_x / 2)) / self.settings.aspect_ratio)
            )
        
        # 计算每像素对应的角度
        self.angle_per_pixel_x = self.settings.fov_x / self.settings.screen_width
        self.angle_per_pixel_y = self.settings.fov_y / self.settings.screen_height
        
        # 计算鼠标单位转换系数
        # 基于360度转一圈的标准计算
        self.mouse_units_per_degree = (self.settings.dpi * self.settings.sensitivity) / 360.0
    
    def screen_to_mouse_units(self, pixel_delta_x: float, pixel_delta_y: float) -> Tuple[int, int]:
        """
        将屏幕像素偏移转换为鼠标移动单位
        
        使用基于实际测试数据的自适应校准算法
        
        Args:
            pixel_delta_x: 屏幕X轴像素偏移
            pixel_delta_y: 屏幕Y轴像素偏移
            
        Returns:
            Tuple[int, int]: (mouse_delta_x, mouse_delta_y)
        """
        # 计算距离用于校准
        pixel_distance = math.sqrt(pixel_delta_x**2 + pixel_delta_y**2)
        
        # 基于实际测试数据的分段校准
        calibration_factor = self._get_distance_based_calibration(pixel_distance)
        
        # 基础转换系数
        base_ratio = 0.111
        dpi_factor = self.settings.dpi / 800.0
        sensitivity_factor = self.settings.sensitivity
        
        # 应用校准后的转换系数
        conversion_factor = base_ratio * dpi_factor * sensitivity_factor * calibration_factor
        
        # 转换为鼠标单位
        mouse_x = pixel_delta_x * conversion_factor
        mouse_y = pixel_delta_y * conversion_factor
        
        # 硬件特定优化
        hw_compensation = self._get_hardware_compensation()
        mouse_x *= hw_compensation
        mouse_y *= hw_compensation
        
        return int(round(mouse_x)), int(round(mouse_y))
    
    def mouse_to_screen_units(self, mouse_delta_x: int, mouse_delta_y: int) -> Tuple[float, float]:
        """
        将鼠标移动单位转换为屏幕像素偏移
        
        注意：这是screen_to_mouse_units的逆运算，但由于校准因子依赖于距离，
        我们需要进行迭代求解来准确反转换
        
        Args:
            mouse_delta_x: 鼠标X轴移动单位
            mouse_delta_y: 鼠标Y轴移动单位
            
        Returns:
            Tuple[float, float]: (pixel_delta_x, pixel_delta_y)
        """
        # 基础转换参数
        base_ratio = 0.111
        dpi_factor = self.settings.dpi / 800.0
        sensitivity_factor = self.settings.sensitivity
        hw_compensation = self._get_hardware_compensation()
        
        # 基础转换系数（不含校准）
        base_conversion_factor = base_ratio * dpi_factor * sensitivity_factor * hw_compensation
        
        # 初始估算（不考虑校准）
        initial_pixel_x = mouse_delta_x / base_conversion_factor
        initial_pixel_y = mouse_delta_y / base_conversion_factor
        initial_distance = math.sqrt(initial_pixel_x**2 + initial_pixel_y**2)
        
        # 获取对应距离的校准因子
        calibration_factor = self._get_distance_based_calibration(initial_distance)
        
        # 考虑校准因子的反向转换
        pixel_x = mouse_delta_x / (base_conversion_factor * calibration_factor)
        pixel_y = mouse_delta_y / (base_conversion_factor * calibration_factor)
        
        # 验证和精炼（可选的迭代改进）
        # 对于高精度要求，可以进行一次验证
        verify_distance = math.sqrt(pixel_x**2 + pixel_y**2)
        if abs(verify_distance - initial_distance) > 10:  # 如果距离差异较大，重新校准
            refined_calibration = self._get_distance_based_calibration(verify_distance)
            pixel_x = mouse_delta_x / (base_conversion_factor * refined_calibration)
            pixel_y = mouse_delta_y / (base_conversion_factor * refined_calibration)
        
        return pixel_x, pixel_y
    
    def _get_distance_based_calibration(self, pixel_distance: float) -> float:
        """
        基于实际测试数据的距离校准系数
        
        根据真实硬件测试结果，发现坐标映射在长距离时精度显著下降：
        - 100px: 0.90px误差 (优秀)
        - 500px: 4.50px误差 (良好)  
        - 1000px: 36.04px误差 (较差)
        - 1500px: 94.59px误差 (极差)
        
        使用分段线性校准修正这些精度损失
        
        Args:
            pixel_distance: 像素距离
            
        Returns:
            float: 校准因子
        """
        # 基于实际测试数据的校准映射表
        calibration_points = [
            (0, 1.0),        # 起点无校准
            (100, 1.0),      # 100px: 0.90px误差，无需校准
            (500, 1.02),     # 500px: 4.50px误差，轻微校准
            (1000, 1.12),    # 1000px: 36.04px误差，需要12%增强
            (1500, 1.35),    # 1500px: 94.59px误差，需要35%增强
            (2000, 1.45)     # 2000px+: 外推最大校准
        ]
        
        # 线性插值计算校准因子
        for i in range(len(calibration_points) - 1):
            distance1, factor1 = calibration_points[i]
            distance2, factor2 = calibration_points[i + 1]
            
            if distance1 <= pixel_distance <= distance2:
                # 在区间内，进行线性插值
                ratio = (pixel_distance - distance1) / (distance2 - distance1)
                return factor1 + ratio * (factor2 - factor1)
        
        # 超出范围时使用边界值
        if pixel_distance < calibration_points[0][0]:
            return calibration_points[0][1]
        else:
            return calibration_points[-1][1]
    
    def _get_distance_compensation(self, pixel_distance: float) -> float:
        """
        根据移动距离计算补偿系数 (已弃用，由_get_distance_based_calibration替代)
        
        Args:
            pixel_distance: 像素距离
            
        Returns:
            float: 补偿系数
        """
        # 距离补偿映射 - 基于实验数据优化
        if pixel_distance < 50:
            return 1.0      # 短距离：无补偿
        elif pixel_distance < 150:
            return 1.02     # 中短距离：轻微增强
        elif pixel_distance < 300:
            return 1.05     # 中距离：适度增强
        elif pixel_distance < 500:
            return 1.08     # 长距离：明显增强
        else:
            return 1.12     # 极长距离：最大增强
    
    def _get_hardware_compensation(self) -> float:
        """
        获取硬件特定补偿系数
        
        Returns:
            float: 硬件补偿系数
        """
        # 默认硬件补偿 - 可以通过calibration调整
        return getattr(self, 'hardware_compensation', 1.0)
    
    def set_hardware_compensation(self, compensation: float):
        """
        设置硬件补偿系数
        
        Args:
            compensation: 补偿系数
        """
        self.hardware_compensation = max(0.5, min(2.0, compensation))
    
    def get_mapping_info(self) -> dict:
        """
        获取映射信息用于调试
        
        Returns:
            dict: 映射参数信息
        """
        return {
            'dpi': self.settings.dpi,
            'sensitivity': self.settings.sensitivity,
            'fov_x': self.settings.fov_x,
            'fov_y': self.settings.fov_y,
            'screen_resolution': (self.settings.screen_width, self.settings.screen_height),
            'aspect_ratio': self.settings.aspect_ratio,
            'angle_per_pixel_x': self.angle_per_pixel_x,
            'angle_per_pixel_y': self.angle_per_pixel_y,
            'mouse_units_per_degree': self.mouse_units_per_degree
        }
    
    def calibrate_with_test_point(self, target_pixel_x: float, target_pixel_y: float, 
                                 actual_pixel_x: float, actual_pixel_y: float) -> float:
        """
        使用测试点校准映射精度
        
        Args:
            target_pixel_x: 目标像素X坐标
            target_pixel_y: 目标像素Y坐标
            actual_pixel_x: 实际到达像素X坐标  
            actual_pixel_y: 实际到达像素Y坐标
            
        Returns:
            float: 校准因子
        """
        # 计算误差
        error_x = abs(target_pixel_x - actual_pixel_x)
        error_y = abs(target_pixel_y - actual_pixel_y)
        
        # 计算整体误差
        total_error = math.sqrt(error_x**2 + error_y**2)
        target_distance = math.sqrt(target_pixel_x**2 + target_pixel_y**2)
        
        if target_distance > 0:
            # 计算校准因子
            calibration_factor = (target_distance - total_error) / target_distance
            return max(0.5, min(1.5, calibration_factor))  # 限制校准范围
        
        return 1.0


class AdaptiveCoordinateMapper(CoordinateMapper):
    """自适应坐标映射器 - 支持动态调整和学习"""
    
    def __init__(self, game_settings: GameSettings):
        super().__init__(game_settings)
        self.calibration_history = []
        self.adaptive_factor = 1.0
        self.learning_rate = 0.1
    
    def add_calibration_data(self, target_x: float, target_y: float, 
                           actual_x: float, actual_y: float):
        """
        添加校准数据点
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            actual_x: 实际X坐标
            actual_y: 实际Y坐标
        """
        calibration_factor = self.calibrate_with_test_point(target_x, target_y, actual_x, actual_y)
        self.calibration_history.append(calibration_factor)
        
        # 保持历史记录长度
        if len(self.calibration_history) > 10:
            self.calibration_history.pop(0)
        
        # 更新自适应因子
        if len(self.calibration_history) >= 3:
            recent_avg = sum(self.calibration_history[-3:]) / 3
            self.adaptive_factor += (recent_avg - self.adaptive_factor) * self.learning_rate
    
    def screen_to_mouse_units(self, pixel_delta_x: float, pixel_delta_y: float) -> Tuple[int, int]:
        """
        自适应版本的坐标转换
        
        Args:
            pixel_delta_x: 屏幕X轴像素偏移
            pixel_delta_y: 屏幕Y轴像素偏移
            
        Returns:
            Tuple[int, int]: 校准后的鼠标移动单位
        """
        # 使用改进的基础转换
        base_x, base_y = super().screen_to_mouse_units(pixel_delta_x, pixel_delta_y)
        
        # 应用自适应调整（基于学习的校准历史）
        adaptive_x = base_x * self.adaptive_factor
        adaptive_y = base_y * self.adaptive_factor
        
        # 额外的精度补偿（基于校准历史）
        if len(self.calibration_history) >= 3:
            recent_performance = sum(self.calibration_history[-3:]) / 3
            # 如果最近性能较差，增加补偿
            if recent_performance < 0.8:
                adaptive_x *= 1.05
                adaptive_y *= 1.05
        
        return int(round(adaptive_x)), int(round(adaptive_y))
    
    def get_adaptive_info(self) -> dict:
        """
        获取自适应信息
        
        Returns:
            dict: 自适应参数信息
        """
        base_info = self.get_mapping_info()
        base_info.update({
            'adaptive_factor': self.adaptive_factor,
            'calibration_points': len(self.calibration_history),
            'recent_calibration': self.calibration_history[-3:] if len(self.calibration_history) >= 3 else self.calibration_history
        })
        return base_info