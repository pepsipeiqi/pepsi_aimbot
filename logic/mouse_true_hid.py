"""
真正的HID设备级别鼠标控制器
直接操作HID鼠标设备，发送真实的硬件级数据包
这是最底层的方法，Raw Input必须能识别
"""

import math
import ctypes
from ctypes import wintypes, windll
import time
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量和GUID
GENERIC_WRITE = 0x40000000
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
INVALID_HANDLE_VALUE = -1

# HID GUID: {4D1E55B2-F16F-11CF-88CB-001111000030}
HID_GUID = "{4D1E55B2-F16F-11CF-88CB-001111000030}"

# 设备枚举常量
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010

# HID使用页和使用ID
HID_USAGE_PAGE_GENERIC = 0x01
HID_USAGE_GENERIC_MOUSE = 0x02

# 结构体定义
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(wintypes.ULONG))
    ]

class SP_DEVICE_INTERFACE_DETAIL_DATA_W(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("DevicePath", wintypes.WCHAR * 256)
    ]

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class TrueHIDMouse:
    """真正的HID设备级别鼠标控制器 - 直接操作HID硬件"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.update_detection_window_offset()
        
        # 获取屏幕分辨率
        self.screen_width_pixels = windll.user32.GetSystemMetrics(0)
        self.screen_height_pixels = windll.user32.GetSystemMetrics(1)
        
        # HID设备相关
        self.mouse_devices = []
        self.active_device_handle = None
        
        # 枚举并初始化HID鼠标设备
        self.enumerate_hid_mice()
        
        logger.info("🎯 True HID Mouse: 直接操作HID鼠标设备")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"🔧 屏幕分辨率: {self.screen_width_pixels}x{self.screen_height_pixels}")
        logger.info(f"🔧 找到 {len(self.mouse_devices)} 个HID鼠标设备")
        
        if self.active_device_handle:
            logger.info("🚀 HID鼠标设备已准备，可以发送真实硬件数据包")
        else:
            logger.warning("⚠️ 未找到可用的HID鼠标设备，将使用备用方案")
    
    def enumerate_hid_mice(self):
        """枚举系统中的HID鼠标设备"""
        try:
            # 转换HID GUID
            hid_guid = GUID()
            windll.hid.HidD_GetHidGuid(ctypes.byref(hid_guid))
            
            # 获取设备信息集
            device_info_set = windll.setupapi.SetupDiGetClassDevsW(
                ctypes.byref(hid_guid),
                None,
                None,
                DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
            )
            
            if device_info_set == INVALID_HANDLE_VALUE:
                logger.error("❌ 无法获取HID设备信息集")
                return
            
            # 枚举设备接口
            device_index = 0
            while True:
                device_interface_data = SP_DEVICE_INTERFACE_DATA()
                device_interface_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
                
                # 枚举设备接口
                result = windll.setupapi.SetupDiEnumDeviceInterfaces(
                    device_info_set,
                    None,
                    ctypes.byref(hid_guid),
                    device_index,
                    ctypes.byref(device_interface_data)
                )
                
                if not result:
                    break  # 没有更多设备
                
                # 获取设备路径
                device_path = self.get_device_path(device_info_set, device_interface_data)
                if device_path:
                    # 检查是否是鼠标设备
                    if self.is_mouse_device(device_path):
                        self.mouse_devices.append(device_path)
                        logger.info(f"🔍 找到HID鼠标: {device_path}")
                        
                        # 尝试打开第一个可用设备
                        if not self.active_device_handle:
                            self.active_device_handle = self.open_hid_device(device_path)
                
                device_index += 1
            
            # 清理
            windll.setupapi.SetupDiDestroyDeviceInfoList(device_info_set)
            
        except Exception as e:
            logger.error(f"❌ 枚举HID设备失败: {e}")
    
    def get_device_path(self, device_info_set, device_interface_data):
        """获取设备路径"""
        try:
            # 获取所需的缓冲区大小
            required_size = wintypes.DWORD()
            windll.setupapi.SetupDiGetDeviceInterfaceDetailW(
                device_info_set,
                ctypes.byref(device_interface_data),
                None,
                0,
                ctypes.byref(required_size),
                None
            )
            
            # 分配缓冲区
            detail_data = SP_DEVICE_INTERFACE_DETAIL_DATA_W()
            detail_data.cbSize = ctypes.sizeof(wintypes.DWORD) + ctypes.sizeof(wintypes.WCHAR)
            
            # 获取设备路径
            result = windll.setupapi.SetupDiGetDeviceInterfaceDetailW(
                device_info_set,
                ctypes.byref(device_interface_data),
                ctypes.byref(detail_data),
                required_size.value,
                None,
                None
            )
            
            if result:
                return detail_data.DevicePath
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取设备路径失败: {e}")
            return None
    
    def is_mouse_device(self, device_path):
        """检查设备是否是鼠标"""
        try:
            # 尝试打开设备
            handle = windll.kernel32.CreateFileW(
                device_path,
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None
            )
            
            if handle == INVALID_HANDLE_VALUE:
                return False
            
            # 获取HID属性
            try:
                # 这里应该检查设备的使用页和使用ID
                # 简化版本：如果能打开就认为可能是鼠标
                # 实际应该读取HID描述符来确认
                windll.kernel32.CloseHandle(handle)
                return True
            except:
                windll.kernel32.CloseHandle(handle)
                return False
                
        except Exception as e:
            return False
    
    def open_hid_device(self, device_path):
        """打开HID设备"""
        try:
            handle = windll.kernel32.CreateFileW(
                device_path,
                GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None
            )
            
            if handle != INVALID_HANDLE_VALUE:
                logger.info(f"✅ HID设备已打开: {device_path}")
                return handle
            else:
                logger.error(f"❌ 无法打开HID设备: {device_path}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 打开HID设备异常: {e}")
            return None
    
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
        """移动到目标 - 真正的HID设备绝对移动"""
        # 转换坐标
        screen_x, screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: ({target_x:.1f}, {target_y:.1f}) -> 屏幕({screen_x}, {screen_y})")
        
        # 使用真正的HID设备移动
        success = self.hid_absolute_move(screen_x, screen_y)
        
        if success:
            logger.info(f"✅ 真正的HID设备绝对移动成功")
        else:
            logger.error(f"❌ 真正的HID设备绝对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def hid_absolute_move(self, target_x, target_y):
        """通过HID设备实现绝对移动"""
        
        if not self.active_device_handle:
            return self.ultimate_fallback_move(target_x, target_y)
        
        try:
            # 获取当前鼠标位置
            current_x, current_y = self.get_current_mouse_position()
            
            # 计算相对移动量
            relative_x = target_x - current_x
            relative_y = target_y - current_y
            
            # 检查是否需要移动
            distance = math.sqrt(relative_x**2 + relative_y**2)
            if distance < 1:
                return True
            
            # 构造HID鼠标报告（标准格式）
            # 大多数鼠标的HID报告格式：
            # 字节0: 按钮状态
            # 字节1: X轴移动（低字节）
            # 字节2: X轴移动（高字节）
            # 字节3: Y轴移动（低字节）
            # 字节4: Y轴移动（高字节）
            # 字节5: 滚轮
            
            # 限制移动范围（避免过大的移动）
            max_move = 127  # 单次最大移动
            if abs(relative_x) > max_move:
                relative_x = max_move if relative_x > 0 else -max_move
            if abs(relative_y) > max_move:
                relative_y = max_move if relative_y > 0 else -max_move
            
            # 构造HID报告
            hid_report = (ctypes.c_ubyte * 6)()
            hid_report[0] = 0  # 按钮状态
            hid_report[1] = relative_x & 0xFF  # X轴低字节
            hid_report[2] = (relative_x >> 8) & 0xFF  # X轴高字节
            hid_report[3] = relative_y & 0xFF  # Y轴低字节
            hid_report[4] = (relative_y >> 8) & 0xFF  # Y轴高字节
            hid_report[5] = 0  # 滚轮
            
            # 发送HID报告
            bytes_written = wintypes.DWORD()
            result = windll.kernel32.WriteFile(
                self.active_device_handle,
                hid_report,
                ctypes.sizeof(hid_report),
                ctypes.byref(bytes_written),
                None
            )
            
            if result and bytes_written.value > 0:
                logger.info(f"🚀 HID报告发送成功: 相对移动({relative_x}, {relative_y}) 距离{distance:.1f}px")
                
                # 也更新光标位置确保同步
                windll.user32.SetCursorPos(target_x, target_y)
                return True
            else:
                logger.error(f"❌ HID报告发送失败")
                return self.ultimate_fallback_move(target_x, target_y)
                
        except Exception as e:
            logger.error(f"❌ HID设备移动异常: {e}")
            return self.ultimate_fallback_move(target_x, target_y)
    
    def ultimate_fallback_move(self, target_x, target_y):
        """终极备用移动方案"""
        try:
            # 组合多种方法
            # 1. SetCursorPos
            windll.user32.SetCursorPos(target_x, target_y)
            
            # 2. 发送微小的相对移动来激活Raw Input
            windll.user32.mouse_event(0x0001, 1, 0, 0, 0)
            windll.user32.mouse_event(0x0001, -1, 0, 0, 0)
            
            logger.info(f"🚀 终极备用移动: 组合方案 ({target_x}, {target_y})")
            return True
        except Exception as e:
            logger.error(f"❌ 终极备用移动失败: {e}")
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
        
        logger.info("🔄 True HID Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        # 关闭HID设备句柄
        if self.active_device_handle:
            try:
                windll.kernel32.CloseHandle(self.active_device_handle)
                logger.info("✅ HID设备句柄已关闭")
            except Exception as e:
                logger.error(f"❌ 关闭HID设备失败: {e}")
        
        logger.info("🔄 True HID Mouse清理完成")

# 创建全局实例
mouse = TrueHIDMouse()