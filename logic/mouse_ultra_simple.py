"""
Ultra Simple Mouse Controller - 最简化的鼠标控制逻辑
使用 mouse_new 库实现：YOLO检测 → 坐标计算 → 一步到位移动 → 锁定开枪

核心理念：
- 尽可能快速定位到敌人
- 一次移动到位，减少多次调整
- 简单直接的瞄准和开火逻辑
"""

import os
import sys

# 确保工作目录是项目根目录
if __name__ == "__main__":
    # 如果直接运行此文件，需要切换到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    print(f"Changed working directory to: {os.getcwd()}")

import supervision as sv
from logic.logger import logger

# 使用修复版的控制器
try:
    from logic.mouse_new_fixed import fixed_mouse_controller as mouse_controller
    logger.info("✅ Using fixed mouse controller")
except Exception as e:
    logger.error(f"❌ Failed to import fixed controller: {e}")
    # 回退到原版本
    try:
        from logic.mouse_new_controller import mouse_new_controller as mouse_controller
        logger.warning("⚠️ Using original controller (may have issues)")
    except Exception as e2:
        logger.error(f"❌ Failed to import any controller: {e2}")
        mouse_controller = None

class UltraSimpleMouse:
    """超简化鼠标控制 - 专注于快速精确锁定"""
    
    def __init__(self):
        self.controller = mouse_controller
        self.last_target_time = 0
        if mouse_controller:
            logger.info("🚀 UltraSimpleMouse initialized - using mouse_new library")
        else:
            logger.error("❌ UltraSimpleMouse initialized but no mouse controller available")
    
    def process_data(self, data):
        """
        处理YOLO检测数据
        
        Args:
            data: YOLO检测结果 (supervision.Detections 或 tuple)
        """
        try:
            # 解析检测数据
            if isinstance(data, sv.Detections):
                if len(data.xyxy) == 0:
                    self.handle_no_target()
                    return
                
                # 获取第一个检测目标
                bbox = data.xyxy[0]  # [x1, y1, x2, y2]
                target_x = (bbox[0] + bbox[2]) / 2  # 中心X
                target_y = (bbox[1] + bbox[3]) / 2  # 中心Y
                target_w = bbox[2] - bbox[0]        # 宽度
                target_h = bbox[3] - bbox[1]        # 高度
                target_cls = data.class_id[0] if len(data.class_id) > 0 else 0
            else:
                # 传统tuple格式
                target_x, target_y, target_w, target_h, target_cls = data
            
            # 处理目标
            self.process_target(target_x, target_y, target_w, target_h, target_cls)
            
        except Exception as e:
            logger.error(f"❌ Error processing detection data: {e}")
            self.handle_no_target()
    
    def process_target(self, target_x, target_y, target_w, target_h, target_cls):
        """
        处理单个目标
        
        Args:
            target_x: 目标中心X坐标
            target_y: 目标中心Y坐标
            target_w: 目标宽度
            target_h: 目标高度
            target_cls: 目标类别 (7=头部, 0=身体)
        """
        if not self.controller:
            logger.error("❌ No mouse controller available")
            return False
            
        target_type = "HEAD" if target_cls == 7 else "BODY"
        
        logger.info(f"🎯 Processing {target_type} target at ({target_x:.1f}, {target_y:.1f}), "
                   f"size=({target_w:.1f}x{target_h:.1f})")
        
        # 使用新的鼠标控制器处理目标
        success = self.controller.process_target(target_x, target_y, target_w, target_h, target_cls)
        
        if success:
            import time
            self.last_target_time = time.time()
        
        return success
    
    def handle_no_target(self):
        """处理无目标情况"""
        if self.controller:
            self.controller.handle_no_target()
    
    def update_settings(self):
        """更新设置"""
        if self.controller:
            self.controller.update_settings()

# 创建全局实例
ultra_simple_mouse = UltraSimpleMouse()