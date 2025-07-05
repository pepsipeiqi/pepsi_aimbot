"""
极简版帧解析器
功能：检测到头部就瞄头部，没有头部就瞄身体，一步到位
移除所有复杂功能：锁定、预测、调整等
"""

import torch
import supervision as sv
import numpy as np
import math
import time

from logic.hotkeys_watcher import hotkeys_watcher
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.shooting import shooting
from logic.logger import logger

# 导入纯相对移动鼠标控制器（最简单方案）
from logic.mouse_pure_relative import mouse

class UltraSimpleTarget:
    """极简目标类"""
    def __init__(self, x, y, w, h, cls):
        self.x = x  # 中心X坐标
        self.y = y  # 中心Y坐标
        self.w = w  # 宽度
        self.h = h  # 高度
        self.cls = cls  # 类别
        self.is_head = (cls == 7)
        
        # 简单瞄准点：就是目标中心
        self.aim_x = x
        self.aim_y = y

class UltraSimpleFrameParser:
    """极简帧解析器 - 只做基本的检测和瞄准"""
    
    def __init__(self):
        self.arch = self.get_arch()
        logger.info("🎯 UltraSimple Parser: 头部优先，没有头部瞄身体，一步到位")
    
    def parse(self, result):
        """解析检测结果"""
        if isinstance(result, sv.Detections):
            self._process_sv_detections(result)
        else:
            self._process_yolo_detections(result)
    
    def _process_sv_detections(self, detections):
        """处理supervision格式检测"""
        if detections.xyxy.any():
            visuals.draw_helpers(detections)
            target = self.find_target(detections)
            if target:
                self.aim_and_shoot(target)
        else:
            visuals.clear()
            if cfg.auto_shoot or cfg.triggerbot:
                shooting.shoot(False, False)
    
    def _process_yolo_detections(self, results):
        """处理YOLO格式检测"""
        for frame in results:
            if frame.boxes:
                target = self.find_target(frame)
                if target:
                    self.aim_and_shoot(target)
                self._visualize_frame(frame)
    
    def find_target(self, frame):
        """极简目标选择：头部优先，没有头部选身体"""
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
        
        # 计算到中心的距离
        distances_sq = torch.sum((boxes_array[:, :2] - center) ** 2, dim=1)
        
        # 1. 优先寻找头部目标
        head_mask = classes_tensor == 7
        if head_mask.any():
            head_distances = distances_sq[head_mask]
            nearest_head_idx = torch.argmin(head_distances)
            nearest_idx = torch.nonzero(head_mask)[nearest_head_idx].item()
            logger.info("🎯 目标：HEAD")
        else:
            # 2. 没有头部，寻找身体目标
            body_mask = (classes_tensor == 0) | (classes_tensor == 1)  # player, bot
            if body_mask.any():
                body_distances = distances_sq[body_mask]
                nearest_body_idx = torch.argmin(body_distances)
                nearest_idx = torch.nonzero(body_mask)[nearest_body_idx].item()
                logger.info("🎯 目标：BODY")
            else:
                return None
        
        # 创建目标
        target_data = boxes_array[nearest_idx, :4].cpu().numpy()
        target_class = classes_tensor[nearest_idx].item()
        target = UltraSimpleTarget(*target_data, target_class)
        
        return target
    
    def aim_and_shoot(self, target):
        """瞄准和射击"""
        # 检查目标类别是否激活
        if hotkeys_watcher.clss is None:
            hotkeys_watcher.active_classes()
        
        if target.cls not in hotkeys_watcher.clss:
            return
        
        # 直接移动到目标
        logger.info(f"🎯 瞄准{'头部' if target.is_head else '身体'}: ({target.aim_x:.1f}, {target.aim_y:.1f})")
        mouse.move_to_target(target.aim_x, target.aim_y, 0, target.is_head)
        
        # 检查是否射击
        if self.should_shoot(target):
            shooting.queue.put((True, mouse.get_shooting_key_state()))
        else:
            shooting.queue.put((False, mouse.get_shooting_key_state()))
    
    def should_shoot(self, target):
        """简单射击判断"""
        center_x = capture.screen_x_center
        center_y = capture.screen_y_center
        
        # 简单范围检查
        scope_size = min(target.w, target.h) * 0.8
        distance_to_target = math.sqrt((center_x - target.aim_x)**2 + (center_y - target.aim_y)**2)
        
        in_scope = distance_to_target < scope_size
        
        # 强制射击模式
        if hasattr(cfg, 'force_click') and cfg.force_click:
            in_scope = True
        
        return in_scope
    
    def _convert_sv_to_tensor(self, frame):
        """转换supervision检测结果"""
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
        """可视化"""
        if cfg.show_window or cfg.show_overlay:
            if cfg.show_boxes or cfg.overlay_show_boxes:
                visuals.draw_helpers(frame.boxes)
            
            if cfg.show_window and cfg.show_detection_speed:
                visuals.draw_speed(frame.speed['preprocess'], frame.speed['inference'], frame.speed['postprocess'])
        
        if not frame.boxes and (cfg.auto_shoot or cfg.triggerbot):
            shooting.shoot(False, False)
        
        if (cfg.show_window or cfg.show_overlay) and not frame.boxes:
            visuals.clear()
    
    def get_arch(self):
        """获取设备架构"""
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        elif 'cpu' in cfg.AI_device:
            return 'cpu'
        else:
            return f'cuda:{cfg.AI_device}'

# 创建全局实例
ultraSimpleFrameParser = UltraSimpleFrameParser()