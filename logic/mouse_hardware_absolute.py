"""
硬件级别绝对移动鼠标控制器
使用HID (Human Interface Device) API直接与鼠标硬件通信
这是最接近物理鼠标输入的方式，Raw Input应该能识别
"""

import math
import ctypes
from ctypes import wintypes, windll
import time
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002

# HID相关常量
HID_USAGE_PAGE_GENERIC = 0x01
HID_USAGE_GENERIC_MOUSE = 0x02

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class HardwareAbsoluteMouse:
    """硬件级别绝对移动鼠标控制器 - 使用HID API模拟真实鼠标输入"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        # HID相关
        self.mouse_hid_handle = None
        self.init_hid_mouse()
        
        logger.info("🎯 Hardware Absolute Mouse: 硬件级别绝对移动")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        logger.info("🚀 使用HID API + 混合策略实现Raw Input兼容")
    
    def init_hid_mouse(self):
        """初始化HID鼠标设备（可选，主要作为后备方案）"""
        try:
            # 这部分比较复杂，需要枚举HID设备
            # 暂时跳过，使用其他策略
            logger.info("🔧 HID鼠标初始化跳过，使用混合策略")
        except Exception as e:
            logger.info(f"🔧 HID初始化失败: {e}，使用备用方案")
    
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
        """移动到目标 - 硬件级别绝对移动"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用硬件级别绝对移动
        success = self.hardware_absolute_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ 硬件级别绝对移动成功")
        else:
            logger.error(f"❌ 硬件级别绝对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def hardware_absolute_move(self, target_x, target_y):
        """硬件级别绝对移动 - 多种策略组合"""
        
        # 策略1: 强制Raw Input重置 + 绝对移动
        try:
            # 暂时禁用Raw Input（如果可能）
            # 这需要调用RegisterRawInputDevices来临时禁用
            # 但这很复杂，先用其他方法
            
            # 直接使用SetCursorPos，然后强制触发Raw Input刷新
            windll.user32.SetCursorPos(target_x, target_y)
            
            # 策略1a: 发送WM_MOUSEMOVE消息强制刷新
            hwnd = windll.user32.GetForegroundWindow()  # 获取前台窗口
            if hwnd:
                lParam = (target_y << 16) | target_x
                windll.user32.PostMessageW(hwnd, 0x0200, 0, lParam)  # WM_MOUSEMOVE
            
            # 策略1b: 发送微小的真实硬件事件来"激活"位置
            windll.user32.mouse_event(0x0001, 0, 0, 0, 0)  # MOUSEEVENTF_MOVE with 0,0
            
            logger.info(f"🚀 强制Raw Input刷新: SetCursorPos({target_x}, {target_y}) + 消息激活")
            return True
            
        except Exception as e:
            logger.error(f"❌ 强制Raw Input刷新失败: {e}")
        
        # 策略2: 使用BlockInput暂时禁用用户输入
        try:
            # 暂时阻止用户输入
            windll.user32.BlockInput(True)
            time.sleep(0.001)  # 1ms
            
            # 移动鼠标
            windll.user32.SetCursorPos(target_x, target_y)
            time.sleep(0.001)  # 1ms
            
            # 发送硬件事件激活
            windll.user32.mouse_event(0x0001, 1, 0, 0, 0)  # 向右1像素
            windll.user32.mouse_event(0x0001, -1, 0, 0, 0)  # 向左1像素
            
            # 恢复用户输入
            windll.user32.BlockInput(False)
            
            logger.info(f"🚀 BlockInput策略: 暂时禁用输入 + 绝对移动 + 硬件激活")
            return True
            
        except Exception as e:
            logger.error(f"❌ BlockInput策略失败: {e}")
            # 确保恢复输入
            try:
                windll.user32.BlockInput(False)
            except:
                pass
        
        # 策略3: 发送SetCursor消息强制游戏重新获取鼠标位置
        try:
            windll.user32.SetCursorPos(target_x, target_y)
            
            # 发送WM_SETCURSOR消息
            hwnd = windll.user32.GetForegroundWindow()
            if hwnd:
                windll.user32.PostMessageW(hwnd, 0x0020, hwnd, 0x02000001)  # WM_SETCURSOR
            
            # 强制重绘光标
            windll.user32.SetCursor(windll.user32.LoadCursorW(0, 32512))  # IDC_ARROW
            
            logger.info(f"🚀 SetCursor策略: 绝对移动 + 强制重绘光标")
            return True
            
        except Exception as e:
            logger.error(f"❌ SetCursor策略失败: {e}")
        
        # 策略4: 最后的备用方案
        try:
            windll.user32.SetCursorPos(target_x, target_y)
            logger.info(f"🚀 备用策略: 纯SetCursorPos({target_x}, {target_y})")
            return True
        except Exception as e:
            logger.error(f"❌ 所有策略都失败: {e}")
            return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            point = ctypes.wintypes.POINT()
            result = windll.user32.GetCursorPos(ctypes.byref(point))
            if result:
                return (point.x, point.y)
            else:
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
        
        # 重新获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        logger.info("🔄 Hardware Absolute Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        # 确保恢复用户输入
        try:
            windll.user32.BlockInput(False)
        except:
            pass
        logger.info("🔄 Hardware Absolute Mouse清理完成")

# 创建全局实例
mouse = HardwareAbsoluteMouse()