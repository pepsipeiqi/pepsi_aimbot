import pyautogui
import math
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int
    
    def __add__(self, other):
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        return Point(self.x + other, self.y + other)
    
    def __sub__(self, other):
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        return Point(self.x - other, self.y - other)
    
    def __mul__(self, scalar):
        return Point(int(self.x * scalar), int(self.y * scalar))
    
    def __truediv__(self, scalar):
        return Point(int(self.x / scalar), int(self.y / scalar))
    
    def distance_to(self, other) -> float:
        if isinstance(other, Point):
            return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
        return math.sqrt(self.x ** 2 + self.y ** 2)
    
    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    @classmethod
    def from_tuple(cls, pos: Tuple[int, int]) -> 'Point':
        return cls(pos[0], pos[1])


class Position:
    @staticmethod
    def get_current() -> Point:
        x, y = pyautogui.position()
        return Point(x, y)
    
    @staticmethod
    def get_screen_size() -> Point:
        return Point(*pyautogui.size())
    
    @staticmethod
    def is_valid_position(x: int, y: int) -> bool:
        screen_size = Position.get_screen_size()
        return 0 <= x < screen_size.x and 0 <= y < screen_size.y
    
    @staticmethod
    def clamp_to_screen(x: int, y: int) -> Point:
        screen_size = Position.get_screen_size()
        clamped_x = max(0, min(x, screen_size.x - 1))
        clamped_y = max(0, min(y, screen_size.y - 1))
        return Point(clamped_x, clamped_y)
    
    @staticmethod
    def calculate_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)
    
    @staticmethod
    def calculate_angle(start: Tuple[int, int], end: Tuple[int, int]) -> float:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        return math.atan2(dy, dx)
    
    @staticmethod
    def interpolate_points(start: Point, end: Point, num_points: int) -> List[Point]:
        if num_points <= 1:
            return [end]
        
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            x = int(start.x + (end.x - start.x) * t)
            y = int(start.y + (end.y - start.y) * t)
            points.append(Point(x, y))
        
        return points
    
    @staticmethod
    def generate_bezier_curve(start: Point, end: Point, control: Point, num_points: int) -> List[Point]:
        points = []
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            x = int((1 - t) ** 2 * start.x + 
                   2 * (1 - t) * t * control.x + 
                   t ** 2 * end.x)
            y = int((1 - t) ** 2 * start.y + 
                   2 * (1 - t) * t * control.y + 
                   t ** 2 * end.y)
            
            points.append(Point(x, y))
        
        return points
    
    @staticmethod
    def generate_smooth_curve(start: Point, end: Point, num_points: int = 50) -> List[Point]:
        mid_x = (start.x + end.x) // 2
        mid_y = min(start.y, end.y) - 50
        control = Point(mid_x, mid_y)
        
        return Position.generate_bezier_curve(start, end, control, num_points)
    
    @staticmethod
    def is_within_tolerance(current: Tuple[int, int], target: Tuple[int, int], tolerance: int) -> bool:
        return (abs(current[0] - target[0]) <= tolerance and 
                abs(current[1] - target[1]) <= tolerance)
    
    @staticmethod
    def normalize_relative_movement(dx: int, dy: int, max_step: int = 127) -> Tuple[int, int]:
        if abs(dx) <= max_step and abs(dy) <= max_step:
            return dx, dy
        
        factor = max_step / max(abs(dx), abs(dy))
        return int(dx * factor), int(dy * factor)