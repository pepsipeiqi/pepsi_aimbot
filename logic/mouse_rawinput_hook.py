"""
Raw Input钩子绝对移动鼠标控制器
通过低级别钩子拦截并注入鼠标消息来欺骗Raw Input系统
这是最有可能成功的方案：直接操作Raw Input数据流
"""

import math
import ctypes
from ctypes import wintypes, windll
import time
import threading
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
HC_ACTION = 0

# 钩子相关结构体
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class RawInputHookMouse:
    """Raw Input钩子绝对移动鼠标控制器 - 通过钩子欺骗Raw Input"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        # 钩子相关
        self.hook_installed = False
        self.hook_handle = None
        self.target_injection_x = None
        self.target_injection_y = None
        self.injection_active = False
        
        # 初始化钩子
        self.install_mouse_hook()
        
        logger.info("🎯 Raw Input Hook Mouse: 通过钩子欺骗Raw Input")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        if self.hook_installed:
            logger.info("🚀 低级别鼠标钩子已安装，准备拦截Raw Input")
        else:
            logger.error("❌ 钩子安装失败，将使用备用方案")
    
    def install_mouse_hook(self):
        """安装低级别鼠标钩子"""
        try:
            # 定义钩子过程
            self.hook_proc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)(self.mouse_hook_proc)
            
            # 获取当前模块句柄
            kernel32 = windll.kernel32
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            
            # 安装钩子
            self.hook_handle = windll.user32.SetWindowsHookExW(
                WH_MOUSE_LL,
                self.hook_proc,
                kernel32.GetModuleHandleW(None),
                0
            )
            
            if self.hook_handle:
                self.hook_installed = True
                logger.info("✅ 低级别鼠标钩子安装成功")
            else:
                logger.error("❌ 钩子安装失败")
                
        except Exception as e:
            logger.error(f"❌ 钩子安装异常: {e}")
    
    def mouse_hook_proc(self, nCode, wParam, lParam):
        """鼠标钩子过程 - 拦截并修改鼠标消息"""
        try:
            if nCode >= HC_ACTION and wParam == WM_MOUSEMOVE:
                # 获取鼠标数据
                mouse_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                
                # 如果我们正在执行注入，替换坐标
                if self.injection_active and self.target_injection_x is not None and self.target_injection_y is not None:
                    # 修改鼠标位置数据
                    mouse_data.pt.x = self.target_injection_x
                    mouse_data.pt.y = self.target_injection_y
                    
                    # 清除注入状态
                    self.injection_active = False
                    self.target_injection_x = None
                    self.target_injection_y = None
                    
                    logger.info(f"🎯 钩子注入: 替换鼠标位置为 ({mouse_data.pt.x}, {mouse_data.pt.y})")
        
        except Exception as e:
            logger.error(f"❌ 钩子过程异常: {e}")
        
        # 调用下一个钩子
        return windll.user32.CallNextHookEx(self.hook_handle, nCode, wParam, lParam)
    
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
        """移动到目标 - Raw Input钩子绝对移动"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用钩子注入绝对移动
        success = self.hook_injection_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ Raw Input钩子绝对移动成功")
        else:
            logger.error(f"❌ Raw Input钩子绝对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def hook_injection_move(self, target_x, target_y):
        """通过钩子注入绝对移动"""
        
        if not self.hook_installed:
            # 没有钩子，使用备用方案
            return self.fallback_move(target_x, target_y)
        
        try:
            # 方案1: 钩子注入 + 触发鼠标移动事件
            # 设置注入目标
            self.target_injection_x = target_x
            self.target_injection_y = target_y
            self.injection_active = True
            
            # 先移动光标到目标位置
            windll.user32.SetCursorPos(target_x, target_y)
            
            # 触发一个微小的鼠标移动来激活钩子
            # 这会被我们的钩子拦截并替换为目标坐标
            windll.user32.mouse_event(0x0001, 1, 0, 0, 0)  # 微小移动触发钩子
            
            # 给钩子一点时间处理
            time.sleep(0.001)
            
            logger.info(f"🚀 钩子注入移动: 目标({target_x}, {target_y}) + 钩子拦截替换")
            return True
            
        except Exception as e:
            logger.error(f"❌ 钩子注入移动失败: {e}")
            return self.fallback_move(target_x, target_y)
    
    def fallback_move(self, target_x, target_y):
        """备用移动方案"""
        try:
            windll.user32.SetCursorPos(target_x, target_y)
            logger.info(f"🚀 备用移动: SetCursorPos({target_x}, {target_y})")
            return True
        except Exception as e:
            logger.error(f"❌ 备用移动失败: {e}")
            return False
    
    def get_current_mouse_position(self):
        """获取鼠标位置"""
        try:
            point = POINT()
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
        
        logger.info("🔄 Raw Input Hook Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        # 卸载钩子
        if self.hook_installed and self.hook_handle:
            try:
                windll.user32.UnhookWindowsHookEx(self.hook_handle)
                logger.info("✅ 鼠标钩子已卸载")
            except Exception as e:
                logger.error(f"❌ 卸载钩子失败: {e}")
        
        logger.info("🔄 Raw Input Hook Mouse清理完成")

# 创建全局实例
mouse = RawInputHookMouse()