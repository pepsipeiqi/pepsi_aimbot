import torch
import supervision as sv
import numpy as np
import math

from logic.hotkeys_watcher import hotkeys_watcher
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.mouse_simple import mouse
from logic.shooting import shooting
from logic.logger import logger

class SimpleTarget:
    """简化的目标类 - 只保留必要信息"""
    def __init__(self, x, y, w, h, cls):
        self.x = x  # 中心X坐标
        self.y = y  # 中心Y坐标
        self.w = w  # 宽度
        self.h = h  # 高度
        self.cls = cls  # 类别 (7=头部)
        
        # 计算精确瞄准点
        self.aim_x, self.aim_y = self.calculate_aim_point()
    
    def calculate_aim_point(self):
        """计算最佳瞄准点坐标"""
        if self.cls == 7:  # 头部目标
            # 瞄准头部中心偏下30%的位置
            aim_x = self.x
            aim_y = self.y + (self.h * 0.3)
        else:  # 身体目标
            # 瞄准身体中心偏上位置
            aim_x = self.x  
            aim_y = self.y - (self.h * 0.2)
        
        return aim_x, aim_y

class SimpleFrameParser:
    """简化的帧解析器 - 专注于快速准确的目标处理"""
    
    def __init__(self):
        self.arch = self.get_arch()
    
    def parse(self, result):
        """解析检测结果并执行瞄准"""
        if isinstance(result, sv.Detections):
            self._process_sv_detections(result)
        else:
            self._process_yolo_detections(result)
    
    def _process_sv_detections(self, detections):
        """处理supervision格式的检测结果"""
        if detections.xyxy.any():
            # 绘制检测框
            visuals.draw_helpers(detections)
            
            # 找到最佳目标
            target = self.find_best_target(detections)
            
            if target:
                self._execute_aim_and_shoot(target)
        else:
            # 无目标时清理显示
            visuals.clear()
            # 停止射击
            if cfg.auto_shoot or cfg.triggerbot:
                shooting.shoot(False, False)
    
    def _process_yolo_detections(self, results):
        """处理YOLO格式的检测结果"""
        for frame in results:
            if frame.boxes:
                target = self.find_best_target(frame)
                if target:
                    self._execute_aim_and_shoot(target)
                self._visualize_frame(frame)
    
    def _execute_aim_and_shoot(self, target):
        """执行瞄准和射击 - 核心逻辑"""
        # 检查是否是活跃的目标类别
        if hotkeys_watcher.clss is None:
            hotkeys_watcher.active_classes()
        
        if target.cls not in hotkeys_watcher.clss:
            return
        
        logger.info(f"🎯 Target acquired: cls={target.cls}, aim_point=({target.aim_x:.1f}, {target.aim_y:.1f})")
        
        # 直接移动鼠标到目标位置
        mouse.move_to_target(target.aim_x, target.aim_y)
        
        # 检查是否在射击范围内
        if self.is_target_in_scope(target):
            logger.info("🔥 Target in scope - shooting")
            shooting.queue.put((True, mouse.get_shooting_key_state()))
        else:
            shooting.queue.put((False, mouse.get_shooting_key_state()))
    
    def find_best_target(self, frame):
        """找到最佳瞄准目标 - 优先头部，选择最近的"""
        if isinstance(frame, sv.Detections):
            boxes_array, classes_tensor = self._convert_sv_to_tensor(frame)
        else:
            boxes_array = frame.boxes.xywh.to(self.arch)
            classes_tensor = frame.boxes.cls.to(self.arch)
        
        if not classes_tensor.numel():
            return None
        
        # 屏幕中心
        center_x = capture.screen_x_center
        center_y = capture.screen_y_center
        center = torch.tensor([center_x, center_y], device=self.arch)
        
        # 计算到屏幕中心的距离
        distances_sq = torch.sum((boxes_array[:, :2] - center) ** 2, dim=1)
        
        # 头部目标优先级更高
        head_mask = classes_tensor == 7
        
        if head_mask.any():
            # 选择最近的头部目标
            head_distances = distances_sq[head_mask]
            nearest_head_idx = torch.argmin(head_distances)
            nearest_idx = torch.nonzero(head_mask)[nearest_head_idx].item()
            logger.info(f"🎯 Selected HEAD target at distance {math.sqrt(distances_sq[nearest_idx].item()):.1f}px")
        else:
            # 没有头部目标时选择最近的身体目标
            nearest_idx = torch.argmin(distances_sq)
            logger.info(f"🎯 Selected BODY target at distance {math.sqrt(distances_sq[nearest_idx].item()):.1f}px")
        
        # 创建目标对象
        target_data = boxes_array[nearest_idx, :4].cpu().numpy()
        target_class = classes_tensor[nearest_idx].item()
        
        return SimpleTarget(*target_data, target_class)
    
    def is_target_in_scope(self, target):
        """检查目标是否在瞄准镜范围内"""
        center_x = capture.screen_x_center
        center_y = capture.screen_y_center
        
        # 使用缩小的目标框来判断
        scope_reduction = cfg.bScope_multiplier if hasattr(cfg, 'bScope_multiplier') else 0.8
        reduced_w = target.w * scope_reduction / 2
        reduced_h = target.h * scope_reduction / 2
        
        # 瞄准镜范围
        scope_left = target.aim_x - reduced_w
        scope_right = target.aim_x + reduced_w
        scope_top = target.aim_y - reduced_h
        scope_bottom = target.aim_y + reduced_h
        
        # 检查准星是否在范围内
        in_scope = (center_x > scope_left and center_x < scope_right and 
                   center_y > scope_top and center_y < scope_bottom)
        
        # 强制射击模式
        if hasattr(cfg, 'force_click') and cfg.force_click:
            in_scope = True
        
        # 绘制瞄准范围（如果启用）
        if cfg.show_window and hasattr(cfg, 'show_bScope_box') and cfg.show_bScope_box:
            visuals.draw_bScope(scope_left, scope_right, scope_top, scope_bottom, in_scope)
        
        return in_scope
    
    def _convert_sv_to_tensor(self, frame):
        """转换supervision检测结果为tensor格式"""
        xyxy = frame.xyxy
        xywh = torch.tensor([
            (xyxy[:, 0] + xyxy[:, 2]) / 2,  # x center
            (xyxy[:, 1] + xyxy[:, 3]) / 2,  # y center
            xyxy[:, 2] - xyxy[:, 0],        # width
            xyxy[:, 3] - xyxy[:, 1]         # height
        ], dtype=torch.float32).to(self.arch).T
        
        classes_tensor = torch.from_numpy(np.array(frame.class_id, dtype=np.float32)).to(self.arch)
        return xywh, classes_tensor
    
    def _visualize_frame(self, frame):
        """可视化检测结果"""
        if cfg.show_window or cfg.show_overlay:
            if cfg.show_boxes or cfg.overlay_show_boxes:
                visuals.draw_helpers(frame.boxes)
            
            if cfg.show_window and cfg.show_detection_speed:
                visuals.draw_speed(frame.speed['preprocess'], frame.speed['inference'], frame.speed['postprocess'])
        
        # 处理无检测情况
        if not frame.boxes:
            if cfg.auto_shoot or cfg.triggerbot:
                shooting.shoot(False, False)
        
        if cfg.show_window or cfg.show_overlay:
            if not frame.boxes:
                visuals.clear()
    
    def get_arch(self):
        """获取计算设备架构"""
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        elif 'cpu' in cfg.AI_device:
            return 'cpu'
        else:
            return f'cuda:{cfg.AI_device}'

# 创建全局简化帧解析器实例
simpleFrameParser = SimpleFrameParser()