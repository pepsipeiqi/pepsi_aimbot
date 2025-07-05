"""
纯相对移动鼠标控制器
直接使用相对移动，不模拟绝对移动
这是最简单、最直接、最有效的Raw Input解决方案
"""

import math
import time
import ctypes
from ctypes import windll
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.logger import logger

# Windows API常量
MOUSEEVENTF_MOVE = 0x0001

# 尝试导入Windows API
try:
    import win32api
    from logic.buttons import Buttons
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class PureRelativeMouse:
    """纯相对移动鼠标控制器 - 最简单最直接的方案"""
    
    def __init__(self):
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        
        # 屏幕中心（检测窗口中心）
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 相对移动比例（检测像素 → 鼠标移动量）
        # 这个比例决定了瞄准的敏感度
        self.move_scale = getattr(cfg, 'mouse_relative_scale', 2.0)
        
        logger.info("🎯 Pure Relative Mouse: 纯相对移动，最简单直接")
        logger.info(f"🔧 检测窗口: {self.screen_width}x{self.screen_height}")
        logger.info(f"🔧 窗口中心: ({self.center_x}, {self.center_y})")
        logger.info(f"🔧 移动比例: {self.move_scale}")
        logger.info("💡 直接计算相对偏移，无需坐标转换")
    
    def move_to_target(self, target_x, target_y, target_velocity=0, is_head_target=False):
        """移动到目标 - 纯相对移动版本"""
        
        # 计算目标相对于中心的偏移
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        
        # 计算距离
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        target_type = "HEAD" if is_head_target else "BODY"
        logger.info(f"🎯 移动到{target_type}: 目标({target_x:.1f}, {target_y:.1f}) 中心偏移({offset_x:.1f}, {offset_y:.1f}) 距离{distance:.1f}px")
        
        # 如果已经在中心附近，不需要移动
        if distance < 3:
            logger.info("🎯 目标已在中心，无需移动")
            return True
        
        # 计算鼠标移动量
        mouse_move_x = int(offset_x * self.move_scale)
        mouse_move_y = int(offset_y * self.move_scale)
        
        # 执行相对移动
        success = self.relative_move(mouse_move_x, mouse_move_y)
        
        if success:
            logger.info(f"✅ 纯相对移动成功")
        else:
            logger.error(f"❌ 纯相对移动失败")
        
        # 可视化
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, 7 if is_head_target else 0)
        
        return success
    
    def relative_move(self, delta_x, delta_y):
        """执行相对移动"""
        try:
            start_time = time.perf_counter()
            
            # 限制单次移动的最大值
            max_move = 200
            
            if abs(delta_x) > max_move or abs(delta_y) > max_move:
                # 分步移动大距离
                steps = max(abs(delta_x) // max_move, abs(delta_y) // max_move) + 1
                step_x = delta_x // steps
                step_y = delta_y // steps
                
                logger.info(f"🔄 分步移动: {steps}步, 每步({step_x}, {step_y})")
                
                for i in range(steps):
                    if i == steps - 1:
                        # 最后一步移动剩余距离
                        remaining_x = delta_x - step_x * i
                        remaining_y = delta_y - step_y * i
                        windll.user32.mouse_event(MOUSEEVENTF_MOVE, remaining_x, remaining_y, 0, 0)
                    else:
                        windll.user32.mouse_event(MOUSEEVENTF_MOVE, step_x, step_y, 0, 0)
                    
                    time.sleep(0.001)  # 短暂延迟
            else:
                # 单步移动
                windll.user32.mouse_event(MOUSEEVENTF_MOVE, delta_x, delta_y, 0, 0)
            
            move_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"🚀 相对移动: ({delta_x}, {delta_y}) [耗时{move_time:.2f}ms]")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 相对移动失败: {e}")
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
    
    def update_settings(self):
        """更新设置"""
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        self.move_scale = getattr(cfg, 'mouse_relative_scale', 2.0)
        
        logger.info("🔄 Pure Relative Mouse设置已更新")
    
    def cleanup(self):
        """清理"""
        logger.info("🔄 Pure Relative Mouse清理完成")

# 创建全局实例
mouse = PureRelativeMouse()