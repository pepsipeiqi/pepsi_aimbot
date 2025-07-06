"""
简化的鼠标控制接口
为 frame_parser_simple.py 提供兼容性接口
基于 mouse_new_raw_input_fixed.py 但针对性能优化
"""

import time

# 全局鼠标控制器实例
_mouse_controller = None

def get_mouse_controller():
    """获取全局鼠标控制器实例"""
    global _mouse_controller
    if _mouse_controller is None:
        from logic.mouse_controller_manager import mouse_controller_manager
        _mouse_controller = mouse_controller_manager
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ✅ mouse_simple: 控制器管理器已初始化")
    return _mouse_controller

class MouseSimple:
    """简化的鼠标控制类 - 提供兼容性接口"""
    
    def __init__(self):
        self.controller = get_mouse_controller()
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ✅ mouse_simple: MouseSimple 接口已创建")
    
    def process_data(self, data):
        """处理YOLO检测数据 - 兼容性接口"""
        if hasattr(data, 'xyxy') and len(data.xyxy) > 0:
            # supervision格式，取第一个目标
            bbox = data.xyxy[0]
            target_x = (bbox[0] + bbox[2]) / 2
            target_y = (bbox[1] + bbox[3]) / 2
            target_w = bbox[2] - bbox[0]
            target_h = bbox[3] - bbox[1]
            target_cls = data.class_id[0] if len(data.class_id) > 0 else 0
            return self.controller.process_target(target_x, target_y, target_w, target_h, target_cls)
        else:
            return self.controller.handle_no_target()
    
    def process_target(self, target_x, target_y, target_w=0, target_h=0, target_cls=0):
        """处理检测到的目标 - 兼容性接口"""
        return self.controller.process_target(target_x, target_y, target_w, target_h, target_cls)
    
    def handle_no_target(self):
        """处理无目标情况 - 兼容性接口"""
        return self.controller.handle_no_target()
    
    @property
    def mouse_available(self):
        """检查鼠标是否可用 - 兼容性接口"""
        return self.controller.mouse_available
    
    @property
    def auto_aim(self):
        """自动瞄准状态 - 兼容性接口"""
        return self.controller.auto_aim
    
    @property
    def auto_shoot(self):
        """自动射击状态 - 兼容性接口"""
        return self.controller.auto_shoot
    
    def move_to_target(self, target_x, target_y, target_velocity, is_head_target):
        """移动到目标位置 - 兼容性接口"""
        # 获取屏幕中心坐标
        from logic.capture import capture
        center_x = capture.screen_x_center
        center_y = capture.screen_y_center
        
        # 计算偏移量
        offset_x = target_x - center_x
        offset_y = target_y - center_y
        
        # 确定目标类别（7=头部，0=身体）
        target_cls = 7 if is_head_target else 0
        
        # 调用底层移动方法
        return self.controller.move_to_target(offset_x, offset_y, target_cls)
    
    def get_shooting_key_state(self):
        """获取射击按键状态 - 兼容性接口"""
        # 从配置获取射击设置
        from logic.config_watcher import cfg
        
        # 返回当前的射击配置状态
        return {
            'auto_shoot': getattr(cfg, 'auto_shoot', True),
            'triggerbot': getattr(cfg, 'triggerbot', False),
            'force_click': getattr(cfg, 'force_click', False)
        }

# 创建全局鼠标实例供导入使用
mouse = MouseSimple()

# 模块初始化日志
print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ✅ mouse_simple: 模块已加载，全局mouse实例已创建")