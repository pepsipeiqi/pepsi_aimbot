import time
import pyautogui
from typing import Optional, Tuple
from ..core.base_driver import BaseDriver


class PIDController:
    def __init__(self, kp: float = 0.25, ki: float = 0.01, kd: float = 0.01):
        self.kp = kp
        self.ki = ki  
        self.kd = kd
        self.reset()
    
    def reset(self):
        self.previous_error = 0
        self.integral = 0
        self.last_time = time.time()
    
    def compute(self, target: float, current: float) -> float:
        current_time = time.time()
        dt = current_time - self.last_time
        
        if dt <= 0:
            dt = 0.001
        
        error = target - current
        
        # 如果误差非常小，直接返回0
        if abs(error) < 1e-6:
            return 0.0
        
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt
        
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        self.previous_error = error
        self.last_time = current_time
        
        return output
    
    def move_to_target(
        self,
        driver: BaseDriver,
        target_x: int,
        target_y: int,
        tolerance: int = 3,
        max_iterations: int = 100,
        delay: float = 0.01
    ) -> bool:
        try:
            pid_x = PIDController(self.kp, self.ki, self.kd)
            pid_y = PIDController(self.kp, self.ki, self.kd)
            
            for i in range(max_iterations):
                current_x, current_y = pyautogui.position()
                
                if (abs(target_x - current_x) < tolerance and 
                    abs(target_y - current_y) < tolerance):
                    return True
                
                control_x = pid_x.compute(target_x, current_x)
                control_y = pid_y.compute(target_y, current_y)
                
                move_x = int(round(control_x))
                move_y = int(round(control_y))
                
                if move_x != 0 or move_y != 0:
                    if not driver.move_relative(move_x, move_y):
                        return False
                
                time.sleep(delay)
                
                _ = pyautogui.position()
            
            return False
        except Exception as e:
            print(f"PID control movement failed: {e}")
            return False


class SimplePID:
    def __init__(self, kp: float, ki: float, kd: float, setpoint: float = 0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.previous_error = 0
        self.integral = 0
    
    def __call__(self, current_value: float) -> float:
        error = self.setpoint - current_value
        
        # 如果误差为0，直接返回0
        if abs(error) < 1e-6:
            return 0.0
            
        self.integral += error
        derivative = error - self.previous_error
        
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        self.previous_error = error
        return output


def pid_mouse_move(
    driver: BaseDriver,
    target_x: int,
    target_y: int,
    tolerance: int = 3,
    max_iterations: int = 100
) -> bool:
    """
    优化的PID鼠标移动函数
    
    修复问题：
    1. 添加max_iterations限制，避免无限循环
    2. 复用PID实例，保持状态连续性
    3. 添加适当延迟，避免系统过载
    4. 优化PID参数，提高收敛速度
    """
    try:
        # 创建PID控制器实例（只创建一次）
        pid_x = SimplePID(0.5, 0.02, 0.01, setpoint=target_x)  # 增加kp提高响应速度
        pid_y = SimplePID(0.5, 0.02, 0.01, setpoint=target_y)
        
        for iteration in range(max_iterations):
            current_x, current_y = pyautogui.position()
            
            # 检查是否到达目标
            if (abs(target_x - current_x) < tolerance and 
                abs(target_y - current_y) < tolerance):
                return True
            
            # 计算PID输出
            next_x = pid_x(current_x)
            next_y = pid_y(current_y)
            
            # 限制单次移动幅度，避免过大跳跃
            move_x = max(-50, min(50, int(round(next_x))))
            move_y = max(-50, min(50, int(round(next_y))))
            
            # 如果移动量太小，直接跳到目标位置
            if abs(move_x) < 1 and abs(move_y) < 1:
                remaining_x = target_x - current_x
                remaining_y = target_y - current_y
                if abs(remaining_x) <= 10 and abs(remaining_y) <= 10:
                    driver.move_relative(remaining_x, remaining_y)
                    return True
            
            # 执行移动
            if move_x != 0 or move_y != 0:
                if not driver.move_relative(move_x, move_y):
                    return False
            
            # 添加短暂延迟，避免系统过载
            time.sleep(0.001)  # 1ms延迟
        
        # 达到最大迭代次数，检查是否足够接近
        current_x, current_y = pyautogui.position()
        final_error = ((target_x - current_x) ** 2 + (target_y - current_y) ** 2) ** 0.5
        return final_error <= tolerance * 2  # 允许稍大的误差
        
    except Exception as e:
        print(f"PID mouse movement failed: {e}")
        return False