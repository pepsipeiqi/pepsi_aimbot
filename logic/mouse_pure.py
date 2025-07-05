"""
纯净鼠标控制器
只使用mouse_new模块，实现丝滑的绝对移动
"""

import math
import time
import sys
import os

from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# 安全导入mouse_new模块，避免名称冲突
mouse_new_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mouse_new')
if mouse_new_path not in sys.path:
    sys.path.insert(0, mouse_new_path)

# 清除可能的模块缓存
if 'mouse' in sys.modules:
    del sys.modules['mouse']

try:
    # 使用importlib进行更安全的导入
    import importlib.util
    mouse_spec = importlib.util.spec_from_file_location(
        "mouse_new_module", 
        os.path.join(mouse_new_path, "mouse", "__init__.py")
    )
    mouse_new = importlib.util.module_from_spec(mouse_spec)
    mouse_spec.loader.exec_module(mouse_new)
    
    # 验证关键函数是否存在
    if hasattr(mouse_new, 'get_position') and hasattr(mouse_new, 'move'):
        logger.info("✅ mouse_new模块安全加载成功")
        logger.info(f"✅ 可用函数: get_position={hasattr(mouse_new, 'get_position')}, move={hasattr(mouse_new, 'move')}")
    else:
        logger.error("❌ mouse_new模块缺少必要函数")
        mouse_new = None
        
except Exception as e:
    logger.error(f"❌ mouse_new模块安全导入失败: {e}")
    # 备用导入方案
    try:
        import mouse as mouse_new
        if hasattr(mouse_new, 'get_position'):
            logger.info("✅ mouse_new备用导入成功")
        else:
            logger.error("❌ 备用导入的模块也缺少get_position函数")
            mouse_new = None
    except Exception as e2:
        logger.error(f"❌ 备用导入也失败: {e2}")
        mouse_new = None

# 尝试导入按键状态检查
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class PureMouse:
    """纯净鼠标控制器 - 使用mouse_new底层相对移动，Raw Input真正兼容"""
    
    def __init__(self):
        self.initialize_settings()
        logger.info("🎯 PureMouse initialized - HEAD ONLY Raw Input真实移动模式")
        logger.info("="*80)
        logger.info("🎯 HEAD ONLY: 只锁定头部目标，忽略所有身体目标")
        logger.info("⚡ Raw Input瞬移: mouse_event相对移动，头部目标直接一步到位")
        logger.info("🔒 移动锁定: 移动后锁定250ms，彻底消除频繁微调")
        logger.info("✅ 满意距离: 30px内停止追踪，避免过度精确导致抖动")
        logger.info("🚀 Raw Input兼容: 底层mouse_event API，游戏准心完美跟随")
        logger.info("="*80)
    
    def initialize_settings(self):
        """初始化基本设置"""
        # 屏幕和检测窗口设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 获取检测窗口在屏幕上的偏移位置
        self.update_detection_window_offset()
        
        # 鼠标偏移校正
        self.mouse_offset_x = getattr(cfg, 'mouse_offset_x', 0)
        self.mouse_offset_y = getattr(cfg, 'mouse_offset_y', 0)
        
        # 移动设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)
        self.min_move_distance = getattr(cfg, 'min_move_distance', 1)  # 降低到1px极限精度
        
        # 移动历史记录
        self.last_movement_time = 0
        self.movement_count = 0
        self.last_target_x = None
        self.last_target_y = None
        
        # 🎯 HEAD ONLY 移动锁定机制 - 防止频繁微调
        self.movement_lock_duration = getattr(cfg, 'mouse_movement_lock', 0.25)  # 移动后锁定250ms
        self.movement_lock_end_time = 0
        self.satisfied_distance = getattr(cfg, 'mouse_satisfied_distance', 30)  # 30px内认为满意，停止追踪
        
        # 🚀 验证mouse_new底层相对移动可用性
        if mouse_new and hasattr(mouse_new, '_os_mouse') and hasattr(mouse_new._os_mouse, 'move_relative'):
            logger.info("⚡ mouse_new底层相对移动API就绪 - Raw Input真正兼容")
        else:
            logger.error("❌ mouse_new底层相对移动API不可用")
        
        # 性能监控设置
        self.show_timing = getattr(cfg, 'mouse_show_timing', True)
        
        logger.info(f"🎯 窗口设置: 检测窗口 {self.screen_width}x{self.screen_height}")
        logger.info(f"🎯 窗口偏移: ({self.detection_window_left}, {self.detection_window_top})")
        logger.info(f"⚡ 极限精度: {self.min_move_distance}px")
        logger.info(f"🔒 移动锁定: {self.movement_lock_duration*1000:.0f}ms，满意距离: {self.satisfied_distance}px")
        logger.info(f"🚀 HEAD ONLY: 只锁定头部目标，Raw Input相对移动一步到位")
        
        if self.mouse_offset_x != 0 or self.mouse_offset_y != 0:
            logger.info(f"🔧 鼠标校正偏移: ({self.mouse_offset_x}, {self.mouse_offset_y})")
    
    def update_detection_window_offset(self):
        """更新检测窗口在屏幕上的偏移位置"""
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
        """将检测窗口内的坐标转换为屏幕绝对坐标"""
        screen_x = self.detection_window_left + detection_x + self.mouse_offset_x
        screen_y = self.detection_window_top + detection_y + self.mouse_offset_y
        return int(screen_x), int(screen_y)
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """
        移动鼠标到目标位置 - HEAD ONLY 极速锁定
        
        Args:
            target_x: 目标在检测窗口内的X坐标
            target_y: 目标在检测窗口内的Y坐标
            target_velocity: 目标移动速度（暂未使用）
            is_head_target: 是否为头部目标
            
        Returns:
            bool: 移动是否成功
        """
        # 🎯 开始计时
        move_start_time = time.perf_counter()
        
        if not mouse_new:
            logger.error("❌ mouse_new模块不可用")
            return False
        
        # 转换为屏幕绝对坐标
        target_screen_x, target_screen_y = self.detection_to_screen_coordinates(target_x, target_y)
        
        # 获取当前鼠标位置
        try:
            current_x, current_y = mouse_new.get_position()
            get_pos_time = time.perf_counter()
        except Exception as e:
            logger.error(f"❌ 获取鼠标位置失败: {e}")
            return False
        
        # 计算移动距离
        move_distance = math.sqrt((target_screen_x - current_x)**2 + (target_screen_y - current_y)**2)
        
        # 🎯 移动锁定检查 - 防止频繁微调
        current_time_ms = time.perf_counter()
        if current_time_ms < self.movement_lock_end_time:
            total_time = (current_time_ms - move_start_time) * 1000
            remaining_lock = (self.movement_lock_end_time - current_time_ms) * 1000
            logger.info(f"🔒 移动锁定中: {move_distance:.1f}px [剩余锁定{remaining_lock:.0f}ms]")
            return True
        
        # 🎯 满意距离检查 - 距离足够小时停止追踪
        if move_distance < self.satisfied_distance:
            total_time = (current_time_ms - move_start_time) * 1000
            logger.info(f"✅ 距离满意: {move_distance:.1f}px < {self.satisfied_distance}px [停止追踪]")
            return True
        
        # 检查是否需要移动
        if move_distance < self.min_move_distance:
            total_time = (current_time_ms - move_start_time) * 1000
            logger.info(f"🎯 目标已在精度范围内: {move_distance:.1f}px [耗时{total_time:.1f}ms]")
            return True
        
        # HEAD ONLY 模式：执行真正的一步到位移动
        self.movement_count += 1
        
        logger.info(f"🎯 HEAD ONLY 移动 #{self.movement_count}")
        logger.info(f"   📍 当前位置: ({current_x}, {current_y})")
        logger.info(f"   🎯 目标位置: ({target_screen_x}, {target_screen_y})")
        logger.info(f"   📏 移动距离: {move_distance:.1f}px")
        
        # 执行极速移动
        move_exec_start = time.perf_counter()
        success = self.execute_instant_move(target_screen_x, target_screen_y, current_x, current_y, move_distance)
        move_exec_time = (time.perf_counter() - move_exec_start) * 1000
        
        # 总时间统计
        total_time = (time.perf_counter() - move_start_time) * 1000
        get_pos_overhead = (get_pos_time - move_start_time) * 1000
        
        if success:
            # 🔒 设置移动锁定期间，防止频繁微调
            self.movement_lock_end_time = time.perf_counter() + self.movement_lock_duration
            
            self.last_movement_time = time.perf_counter()
            self.last_target_x = target_screen_x
            self.last_target_y = target_screen_y
            
            if self.show_timing:
                logger.info(f"⚡ HEAD ONLY Raw Input移动完成: 总耗时{total_time:.2f}ms [获取位置{get_pos_overhead:.2f}ms + 执行移动{move_exec_time:.2f}ms]")
                logger.info(f"🔒 移动锁定启动: {self.movement_lock_duration*1000:.0f}ms内禁止微调")
            else:
                logger.info(f"⚡ HEAD ONLY Raw Input移动完成: {move_distance:.1f}px 总耗时{total_time:.2f}ms [锁定{self.movement_lock_duration*1000:.0f}ms]")
        else:
            logger.error(f"❌ HEAD ONLY 移动失败: 总耗时{total_time:.2f}ms")
        
        # 可视化目标线
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def execute_instant_move(self, target_x, target_y, current_x, current_y, distance):
        """
        执行极速瞬移 - HEAD ONLY 专用超快移动
        使用mouse_new底层相对移动API，Raw Input真正兼容
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            current_x: 当前X坐标
            current_y: 当前Y坐标
            distance: 移动距离
            
        Returns:
            bool: 移动是否成功
        """
        if not mouse_new:
            logger.error("❌ mouse_new模块不可用")
            return False
        
        # 计算相对移动量
        relative_x = target_x - current_x
        relative_y = target_y - current_y
        
        try:
            # 🚀 极速瞬移：使用mouse_new底层相对移动，Raw Input真正识别
            if self.show_timing:
                api_start = time.perf_counter()
                # 直接调用底层相对移动API，使用mouse_event而不是SetCursorPos
                mouse_new._os_mouse.move_relative(relative_x, relative_y)
                api_time = (time.perf_counter() - api_start) * 1000
                logger.info(f"🚀 Raw Input相对瞬移: ({relative_x}, {relative_y}), 距离{distance:.1f}px [API耗时{api_time:.3f}ms]")
            else:
                mouse_new._os_mouse.move_relative(relative_x, relative_y)
                logger.info(f"🚀 Raw Input相对瞬移: ({relative_x}, {relative_y}), 距离{distance:.1f}px")
            
            return True
        except Exception as e:
            logger.error(f"❌ Raw Input相对瞬移失败: {e}")
            return False
    
    
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
    
    def get_current_mouse_position(self):
        """获取当前鼠标的屏幕绝对坐标"""
        # 方法1：尝试使用mouse_new
        if mouse_new and hasattr(mouse_new, 'get_position'):
            try:
                return mouse_new.get_position()
            except Exception as e:
                logger.error(f"❌ mouse_new获取位置失败: {e}")
        
        # 方法2：使用Windows API备用方案
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            point = wintypes.POINT()
            result = user32.GetCursorPos(ctypes.byref(point))
            if result:
                return (point.x, point.y)
            else:
                logger.error("❌ Windows API GetCursorPos失败")
                return (0, 0)
        except Exception as e:
            logger.error(f"❌ Windows API获取位置失败: {e}")
            return (0, 0)
    
    def update_settings(self):
        """更新设置（热重载）"""
        logger.info("🔄 更新HEAD ONLY设置")
        
        # 更新基本设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 更新检测窗口偏移
        self.update_detection_window_offset()
        
        # 更新关键设置
        self.max_move_distance = getattr(cfg, 'max_move_distance', 500)
        self.mouse_offset_x = getattr(cfg, 'mouse_offset_x', 0)
        self.mouse_offset_y = getattr(cfg, 'mouse_offset_y', 0)
        self.min_move_distance = getattr(cfg, 'min_move_distance', 1)
        self.show_timing = getattr(cfg, 'mouse_show_timing', True)
        
        # 更新移动锁定设置
        self.movement_lock_duration = getattr(cfg, 'mouse_movement_lock', 0.25)
        self.satisfied_distance = getattr(cfg, 'mouse_satisfied_distance', 30)
        
        logger.info(f"🔄 HEAD ONLY Raw Input移动设置更新完成")
        logger.info(f"🔒 移动锁定: {self.movement_lock_duration*1000:.0f}ms，满意距离: {self.satisfied_distance}px")
        
        if self.mouse_offset_x != 0 or self.mouse_offset_y != 0:
            logger.info(f"🔧 鼠标校正偏移: ({self.mouse_offset_x}, {self.mouse_offset_y})")
    
    def cleanup(self):
        """清理资源"""
        logger.info("🔄 纯净鼠标控制器清理完成")


# 创建全局纯净鼠标控制器实例
mouse = PureMouse()