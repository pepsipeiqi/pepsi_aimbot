import time
import pyautogui
from typing import Callable, Optional
from ..core.base_driver import BaseDriver


class LinearMovement:
    @staticmethod
    def absolute_smooth_move(
        driver: BaseDriver,
        x_end: int,
        y_end: int,
        num_steps: int = 20,
        delay: float = 0.01
    ) -> bool:
        try:
            start_x, start_y = pyautogui.position()
            dx = (x_end - start_x) / num_steps
            dy = (y_end - start_y) / num_steps

            for i in range(1, num_steps + 1):
                next_x = int(start_x + dx * i)
                next_y = int(start_y + dy * i)
                
                if not driver.move_absolute(next_x, next_y):
                    return False
                
                time.sleep(delay)
            
            return True
        except Exception as e:
            print(f"Linear movement failed: {e}")
            return False
    
    @staticmethod
    def relative_smooth_move(
        driver: BaseDriver,
        r_x: int,
        r_y: int,
        num_steps: int = 20,
        delay: float = 0.01
    ) -> bool:
        try:
            r_y = -r_y
            dx = r_x / num_steps
            dy = r_y / num_steps
            
            for i in range(1, num_steps + 1):
                next_x = int(dx)
                next_y = int(dy)
                
                if not driver.move_relative(next_x, next_y):
                    return False
                
                time.sleep(delay)
            
            return True
        except Exception as e:
            print(f"Relative linear movement failed: {e}")
            return False
    
    @staticmethod
    def bezier_curve_move(
        driver: BaseDriver,
        x_end: int,
        y_end: int,
        control_x: Optional[int] = None,
        control_y: Optional[int] = None,
        num_steps: int = 50,
        delay: float = 0.01
    ) -> bool:
        try:
            start_x, start_y = pyautogui.position()
            
            if control_x is None:
                control_x = (start_x + x_end) // 2
            if control_y is None:
                control_y = min(start_y, y_end) - 50
            
            for i in range(num_steps + 1):
                t = i / num_steps
                
                x = int((1 - t) ** 2 * start_x + 
                       2 * (1 - t) * t * control_x + 
                       t ** 2 * x_end)
                y = int((1 - t) ** 2 * start_y + 
                       2 * (1 - t) * t * control_y + 
                       t ** 2 * y_end)
                
                if not driver.move_absolute(x, y):
                    return False
                
                time.sleep(delay)
            
            return True
        except Exception as e:
            print(f"Bezier curve movement failed: {e}")
            return False