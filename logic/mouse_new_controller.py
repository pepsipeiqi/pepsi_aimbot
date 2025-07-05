import sys
import os
import time
import math
import win32con, win32api

# 确保工作目录是项目根目录（如果直接运行）
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

# 添加 mouse_new 到路径并确保正确导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mouse_new_path = os.path.join(project_root, 'mouse_new')
sys.path.insert(0, mouse_new_path)

# 确保导入正确的mouse库
try:
    import mouse
    # 验证mouse库是否有move函数
    if not hasattr(mouse, 'move'):
        print(f"❌ Wrong mouse library imported: {mouse.__file__ if hasattr(mouse, '__file__') else 'unknown'}")
        # 尝试强制重新导入
        import importlib
        import sys
        if 'mouse' in sys.modules:
            del sys.modules['mouse']
        sys.path.insert(0, mouse_new_path)
        import mouse
    
    if hasattr(mouse, 'move'):
        print(f"✅ Correct mouse_new library loaded: {mouse.__file__ if hasattr(mouse, '__file__') else 'correct'}")
    else:
        print(f"❌ Still wrong mouse library after reload")
        
except Exception as e:
    print(f"❌ Failed to import mouse library: {e}")
    mouse = None

from logic.config_watcher import cfg
from logic.visual import visuals
from logic.shooting import shooting
from logic.buttons import Buttons
from logic.logger import logger

class MouseNewController:
    """
    使用 mouse_new 库的简化鼠标控制器
    核心理念：YOLO检测 → 计算目标坐标 → 一步到位移动 → 锁定开枪
    """
    
    def __init__(self):
        self.initialize_settings()
        logger.info("🚀 MouseNewController initialized with mouse_new library")
    
    def initialize_settings(self):
        """初始化基本设置"""
        # 屏幕和检测区域设置
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        # 鼠标设置
        self.dpi = cfg.mouse_dpi
        self.sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        
        # 瞄准设置
        self.body_y_offset = getattr(cfg, 'body_y_offset', 0.1)  # 身体Y轴偏移
        self.auto_aim = cfg.mouse_auto_aim
        self.auto_shoot = cfg.auto_shoot
        
        # 精度和移动设置
        self.aim_threshold = 10  # 瞄准精度阈值（像素）
        self.max_single_move = 200  # 单次最大移动距离
        
        # 目标锁定状态
        self.target_locked = False
        self.lock_start_time = 0
        self.lock_timeout = 2.0  # 锁定超时时间（秒）
        
        logger.info(f"🎯 Settings: DPI={self.dpi}, Sensitivity={self.sensitivity}")
        logger.info(f"🎯 Detection area: {self.screen_width}x{self.screen_height}, center=({self.center_x}, {self.center_y})")
    
    def process_target(self, target_x, target_y, target_w=0, target_h=0, target_cls=0):
        """
        处理检测到的目标
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标  
            target_w: 目标宽度
            target_h: 目标高度
            target_cls: 目标类别（7=头部, 0=身体）
        """
        # 应用身体Y轴偏移
        if target_cls != 7:  # 不是头部目标时应用偏移
            target_y += target_h * self.body_y_offset
        
        # 计算距离中心的偏移
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        # 可视化目标
        self.visualize_target(target_x, target_y, target_cls)
        
        # 检查是否需要移动
        if distance <= self.aim_threshold:
            if not self.target_locked:
                self.target_locked = True
                self.lock_start_time = time.time()
                logger.info(f"🎯 Target locked! Distance: {distance:.1f}px")
            
            # 检查开火条件
            self.check_and_fire(target_x, target_y, target_w, target_h)
            return True
        
        # 需要移动到目标
        if self.should_aim_at_target():
            success = self.move_to_target(offset_x, offset_y, target_cls)
            if success:
                logger.info(f"✅ Moved to target: offset=({offset_x:.1f}, {offset_y:.1f}), distance={distance:.1f}px")
            else:
                logger.warning("❌ Failed to move to target")
            return success
        
        return False
    
    def should_aim_at_target(self):
        """检查是否应该瞄准目标（按键检测）"""
        if not self.auto_aim:
            # 检查瞄准按键状态
            for key_name in cfg.hotkey_targeting_list:
                key_code = Buttons.KEY_CODES.get(key_name.strip())
                if key_code and self.is_key_pressed(key_code):
                    return True
            return False
        return True
    
    def is_key_pressed(self, key_code):
        """检查按键是否被按下"""
        if cfg.mouse_lock_target:
            return win32api.GetKeyState(key_code) < 0
        else:
            return win32api.GetAsyncKeyState(key_code) < 0
    
    def move_to_target(self, offset_x, offset_y, target_cls):
        """
        使用 mouse_new 库移动到目标位置
        
        Args:
            offset_x: X轴偏移（像素）
            offset_y: Y轴偏移（像素）
            target_cls: 目标类别
        
        Returns:
            bool: 移动是否成功
        """
        # 检查mouse库是否可用
        if mouse is None:
            logger.error("❌ Mouse library not available")
            return False
            
        if not hasattr(mouse, 'move'):
            logger.error(f"❌ Mouse library missing move function. Available: {dir(mouse)}")
            return False
        
        try:
            # 限制单次移动距离
            distance = math.sqrt(offset_x**2 + offset_y**2)
            if distance > self.max_single_move:
                scale = self.max_single_move / distance
                offset_x *= scale
                offset_y *= scale
                logger.info(f"🔧 Movement scaled down: {distance:.1f}px → {self.max_single_move}px")
            
            # 转换像素偏移为鼠标移动距离
            mouse_x, mouse_y = self.convert_pixel_to_mouse(offset_x, offset_y)
            
            # 使用 mouse_new 进行相对移动
            mouse.move(mouse_x, mouse_y, absolute=False)
            
            target_type = "HEAD" if target_cls == 7 else "BODY"
            logger.info(f"🎯 {target_type} target move: pixel_offset=({offset_x:.1f}, {offset_y:.1f}) → mouse_move=({mouse_x:.1f}, {mouse_y:.1f})")
            
            # 重置锁定状态（需要重新锁定）
            self.target_locked = False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Mouse movement failed: {e}")
            # 如果是属性错误，给出详细信息
            if "attribute" in str(e):
                logger.error(f"❌ Mouse library details: {type(mouse)}, file: {getattr(mouse, '__file__', 'unknown')}")
                logger.error(f"❌ Available functions: {[attr for attr in dir(mouse) if not attr.startswith('_')]}")
            return False
    
    def convert_pixel_to_mouse(self, pixel_x, pixel_y):
        """
        将像素偏移转换为鼠标移动距离
        
        Args:
            pixel_x: X轴像素偏移
            pixel_y: Y轴像素偏移
        
        Returns:
            tuple: (mouse_x, mouse_y) 鼠标移动距离
        """
        # 计算像素到度数的转换
        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height
        
        # 转换为度数
        degrees_x = pixel_x * degrees_per_pixel_x
        degrees_y = pixel_y * degrees_per_pixel_y
        
        # 转换为鼠标移动单位
        # 基于 DPI 和灵敏度计算
        mouse_x = (degrees_x / 360) * (self.dpi * (1 / self.sensitivity))
        mouse_y = (degrees_y / 360) * (self.dpi * (1 / self.sensitivity))
        
        return mouse_x, mouse_y
    
    def check_and_fire(self, target_x, target_y, target_w, target_h):
        """检查开火条件并执行射击"""
        if not self.auto_shoot:
            return
        
        # 检查目标是否在有效射击范围内
        in_scope = self.is_target_in_scope(target_x, target_y, target_w, target_h)
        
        if in_scope:
            # 发送射击信号
            shooting_state = self.should_aim_at_target()
            shooting.queue.put((True, shooting_state))
            logger.info("🔥 Target in scope - firing!")
        else:
            # 发送停火信号
            shooting.queue.put((False, False))
    
    def is_target_in_scope(self, target_x, target_y, target_w, target_h):
        """
        检查目标是否在瞄准镜范围内
        
        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            target_w: 目标宽度
            target_h: 目标高度
        
        Returns:
            bool: 是否在范围内
        """
        # 计算缩放后的目标边界
        bScope_multiplier = getattr(cfg, 'bScope_multiplier', 1.0)
        reduced_w = target_w * bScope_multiplier / 2
        reduced_h = target_h * bScope_multiplier / 2
        
        # 计算边界
        x1 = target_x - reduced_w
        x2 = target_x + reduced_w
        y1 = target_y - reduced_h
        y2 = target_y + reduced_h
        
        # 检查中心点是否在范围内
        in_scope = (self.center_x > x1 and self.center_x < x2 and 
                   self.center_y > y1 and self.center_y < y2)
        
        # 可视化瞄准范围
        if cfg.show_window and cfg.show_bScope_box:
            visuals.draw_bScope(x1, x2, y1, y2, in_scope)
        
        return in_scope
    
    def handle_no_target(self):
        """处理没有目标的情况"""
        # 检查锁定超时
        if self.target_locked:
            if time.time() - self.lock_start_time > self.lock_timeout:
                self.target_locked = False
                logger.info("🔄 Target lock timeout - resetting")
        
        # 发送停火信号
        shooting.queue.put((False, False))
    
    def visualize_target(self, target_x, target_y, target_cls):
        """可视化目标"""
        if (cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line):
            visuals.draw_target_line(target_x, target_y, target_cls)
    
    def update_settings(self):
        """更新配置（热重载支持）"""
        logger.info("🔄 Updating MouseNewController settings")
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        self.dpi = cfg.mouse_dpi
        self.sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.body_y_offset = getattr(cfg, 'body_y_offset', 0.1)
        self.auto_aim = cfg.mouse_auto_aim
        self.auto_shoot = cfg.auto_shoot
        
        logger.info(f"✅ Settings updated: DPI={self.dpi}, Sensitivity={self.sensitivity}")

# 创建全局实例
mouse_new_controller = MouseNewController()