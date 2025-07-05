"""
纯粹绝对移动鼠标控制器
使用SendInput API发送绝对坐标的硬件事件
同时满足：绝对移动 + Raw Input游戏兼容
"""

import math
import ctypes
from ctypes import wintypes, windll
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
INPUT_MOUSE = 0

# Windows API结构体
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG), 
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT)
    ]

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class PureAbsoluteMouse:
    """纯粹绝对移动鼠标控制器 - 使用SendInput发送绝对坐标硬件事件"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        
        logger.info("🎯 Pure Absolute Mouse: 纯粹绝对移动 + Raw Input兼容")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        logger.info("🚀 使用多种底层API发送绝对坐标硬件事件：mouse_event > 组合方式 > SendInput")
    
    def update_detection_window_offset(self):
        """计算检测窗口偏移"""
        if cfg.Bettercam_capture:
            offset = capture.calculate_screen_offset()
            self.detection_window_left = offset[0]
            self.detection_window_top = offset[1]
        elif cfg.mss_capture:
            offset = capture.calculate_mss_offset()
            self.detection_window_left = offset[0]
            self.detection_window_top = offset[1]
        else:
            primary_width, primary_height = capture.get_primary_display_resolution()
            self.detection_window_left = int(primary_width / 2 - self.screen_width / 2)
            self.detection_window_top = int(primary_height / 2 - self.screen_height / 2)
    
    def detection_to_screen_coordinates(self, detection_x, detection_y):
        """检测坐标转屏幕坐标"""
        screen_x = self.detection_window_left + detection_x
        screen_y = self.detection_window_top + detection_y
        return int(screen_x), int(screen_y)
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """移动到目标 - 纯粹绝对移动"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用纯粹绝对移动
        success = self.send_absolute_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ 纯粹绝对移动成功")
        else:
            logger.error(f"❌ 纯粹绝对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def send_absolute_move(self, target_x, target_y):
        """发送绝对移动硬件事件 - 多种底层API尝试"""
        
        # 方案1: mouse_event API绝对坐标（最底层，Raw Input最可能识别）
        try:
            # mouse_event使用0-65535归一化坐标
            normalized_x = int((target_x * 65535) / self.screen_width_pixels)
            normalized_y = int((target_y * 65535) / self.screen_height_pixels)
            
            # 使用mouse_event的绝对坐标模式
            windll.user32.mouse_event(
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                normalized_x, normalized_y, 0, 0
            )
            
            logger.info(f"🚀 mouse_event绝对移动: 屏幕({target_x}, {target_y}) -> 归一化({normalized_x}, {normalized_y})")
            return True
            
        except Exception as e:
            logger.error(f"❌ mouse_event绝对移动失败: {e}")
        
        # 方案2: 组合方式 - SetCursorPos + 微小硬件事件（激活Raw Input）
        try:
            # 先设置光标位置
            windll.user32.SetCursorPos(target_x, target_y)
            
            # 立即发送一个微小的相对移动事件来"激活"硬件事件流
            # 这可能让Raw Input识别位置变化
            windll.user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)  # 向右1像素
            windll.user32.mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, 0)  # 向左1像素回到原位
            
            logger.info(f"🚀 组合移动: SetCursorPos({target_x}, {target_y}) + 微小硬件激活")
            return True
            
        except Exception as e:
            logger.error(f"❌ 组合移动失败: {e}")
        
        # 方案3: SendInput备用（已知可能不被Raw Input识别，但保留）
        try:
            normalized_x = int((target_x * 65535) / self.screen_width_pixels)
            normalized_y = int((target_y * 65535) / self.screen_height_pixels)
            
            mouse_input = MOUSEINPUT()
            mouse_input.dx = normalized_x
            mouse_input.dy = normalized_y
            mouse_input.mouseData = 0
            mouse_input.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
            mouse_input.time = 0
            mouse_input.dwExtraInfo = None
            
            input_struct = INPUT()
            input_struct.type = INPUT_MOUSE
            input_struct.mi = mouse_input
            
            result = windll.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
            
            if result == 1:
                logger.info(f"🚀 SendInput备用移动: 屏幕({target_x}, {target_y})")
                return True
            else:
                logger.error(f"❌ SendInput备用失败: 返回值 {result}")
                
        except Exception as e:
            logger.error(f"❌ SendInput备用异常: {e}")
        
        # 最终备用: 纯SetCursorPos
        try:
            windll.user32.SetCursorPos(target_x, target_y)
            logger.info(f"🚀 最终备用: SetCursorPos({target_x}, {target_y})")
            return True
        except Exception as e:
            logger.error(f"❌ 所有移动方案都失败: {e}")
            return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            point = POINT()
            result = windll.user32.GetCursorPos(ctypes.byref(point))
            if result:
                return (point.x, point.y)
            else:
                logger.error("❌ GetCursorPos失败")
                return (0, 0)
        except Exception as e:
            logger.error(f"❌ 获取鼠标位置失败: {e}")
            return (0, 0)
    
    def get_shooting_key_state(self):
        """检查射击键状态"""
        if not WIN32_AVAILABLE:
            return False
            
        if not hasattr(cfg, 'hotkey_targeting_list'):
            return False
            
        for key_name in cfg.hotkey_targeting_list:
            key_code = Buttons.KEY_CODES.get(key_name.strip())
            if key_code:
                key_state = win32api.GetAsyncKeyState(key_code) if not cfg.mouse_lock_target else win32api.GetKeyState(key_code)
                if key_state < 0:
                    return True
        return False
    
    def update_settings(self):
        """更新设置"""
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 重新获取屏幕分辨率（可能改变）
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        logger.info("🔄 Pure Absolute Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        logger.info("🔄 Pure Absolute Mouse清理完成")

# 创建全局实例
mouse = PureAbsoluteMouse()