import torch
import supervision as sv
import numpy as np
import math
import time
from collections import deque, defaultdict

from logic.hotkeys_watcher import hotkeys_watcher
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.mouse_pure import mouse
from logic.shooting import shooting
from logic.logger import logger

class SimpleTarget:
    """简化的目标类 - 只保留必要信息"""
    def __init__(self, x, y, w, h, cls, timestamp=None):
        self.x = x  # 中心X坐标
        self.y = y  # 中心Y坐标
        self.w = w  # 宽度
        self.h = h  # 高度
        self.cls = cls  # 类别 (7=头部)
        self.timestamp = timestamp or time.time()
        
        # 计算精确瞄准点
        self.aim_x, self.aim_y = self.calculate_aim_point()
        
        # 预测相关属性
        self.predicted_x = x
        self.predicted_y = y
        self.velocity_x = 0.0
        self.velocity_y = 0.0
    
    def calculate_aim_point(self):
        """Phase 3.9最终: 最终头部瞄准点 - 远距离20.7%，中距离31.8%，近距离38.8%向上调整"""
        if self.cls == 7:  # 头部目标
            # Phase 3: 智能头部瞄准点计算
            from logic.capture import capture
            center_x = capture.screen_x_center
            center_y = capture.screen_y_center
            distance_to_center = math.sqrt((self.x - center_x)**2 + (self.y - center_y)**2)
            
            # 基于距离动态调整瞄准点
            if distance_to_center > 50:  # 远距离 - 瞄准头部中心
                y_offset_ratio = 0.0793  # 0.081 - (0.081 * 0.02) = 0.0793，减少2%向下偏移（向上2%）
            elif distance_to_center > 20:  # 中距离 - 精确瞄准
                y_offset_ratio = 0.1143  # 0.1166 - (0.1166 * 0.02) = 0.1143，再向上2%
            else:  # 近距离 - 精准定位
                y_offset_ratio = 0.18   # 0.25 * 0.612 = 0.153，总共向上调整38.8%
            
            # 基于头部尺寸调整 - 更大的头部可以更精准
            size_factor = min(self.w, self.h) / 30.0  # 归一化到30像素基准
            size_factor = max(0.8, min(size_factor, 1.5))  # 限制范围
            
            aim_x = self.x  # X轴保持中心
            aim_y = self.y + (self.h * y_offset_ratio * size_factor)
            
            # 调试信息（仅远距离显示）
            if distance_to_center > 30:
                logger.info(f"🎯 Phase 3.9最终: 头部瞄准点最终调整 - 距离{distance_to_center:.0f}px, "
                           f"尺寸{self.w:.0f}x{self.h:.0f}, 偏移{y_offset_ratio*size_factor:.2f}")
        else:  # 身体目标
            # Phase 3.9再改: 身体目标再次微调偏移 - 再次降低一点
            aim_x = self.x  
            aim_y = self.y - (self.h * 0.162)  # 0.18 * 0.9 = 0.162，再次微调偏移
        
        return aim_x, aim_y

class TargetTracker:
    """简化的目标跟踪器 - 优先速度而非精度"""
    
    def __init__(self, max_history=2):  # 减少历史记录
        self.target_history = defaultdict(lambda: deque(maxlen=max_history))
        self.prediction_enabled = not cfg.disable_prediction if hasattr(cfg, 'disable_prediction') else True
        
    def update_target(self, target):
        """简化的目标更新"""
        # 简化目标key，减少计算
        target_key = f"{target.cls}_{int(target.x/100)}_{int(target.y/100)}"
        self.target_history[target_key].append({
            'x': target.x, 'y': target.y, 'timestamp': target.timestamp
        })
        return target_key
    
    def predict_position(self, target, prediction_time=0.03):  # 减少预测时间
        """简化的位置预测"""
        if not self.prediction_enabled:
            return target.x, target.y
            
        target_key = f"{target.cls}_{int(target.x/100)}_{int(target.y/100)}"
        history = self.target_history[target_key]
        
        if len(history) < 2:
            return target.x, target.y
        
        # 只使用最近的两个位置，避免复杂计算
        recent = history[-1]
        previous = history[-2]
        
        dt = recent['timestamp'] - previous['timestamp']
        if dt <= 0 or dt > 0.1:  # 过大的时间间隔不预测
            return target.x, target.y
        
        velocity_x = (recent['x'] - previous['x']) / dt
        velocity_y = (recent['y'] - previous['y']) / dt
        
        # 简单的速度限制（避免过大预测）
        max_velocity = 500  # 像素/秒
        if abs(velocity_x) > max_velocity or abs(velocity_y) > max_velocity:
            return target.x, target.y
        
        # 简单的线性预测
        predicted_x = target.x + velocity_x * prediction_time
        predicted_y = target.y + velocity_y * prediction_time
        
        # 存储速度信息
        target.velocity_x = velocity_x
        target.velocity_y = velocity_y
        
        # 简化的距离限制
        max_prediction_distance = 30  # 固定值，减少计算
        prediction_distance = math.sqrt((predicted_x - target.x)**2 + (predicted_y - target.y)**2)
        
        if prediction_distance > max_prediction_distance:
            scale = max_prediction_distance / prediction_distance
            predicted_x = target.x + (predicted_x - target.x) * scale
            predicted_y = target.y + (predicted_y - target.y) * scale
        
        # 减少日志输出
        if prediction_distance > 5:  # 只有在预测距离较大时才打印
            logger.info(f"🔮 简化预测: ({target.x:.0f},{target.y:.0f}) -> ({predicted_x:.0f},{predicted_y:.0f})")
        
        return predicted_x, predicted_y

class SimpleFrameParser:
    """简化的帧解析器 - 专注于快速准确的目标处理 + 预测瞄准"""
    
    def __init__(self):
        self.arch = self.get_arch()
        self.target_tracker = TargetTracker()
    
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
        
        is_head_target = (target.cls == 7)
        target_velocity = math.sqrt(target.velocity_x**2 + target.velocity_y**2) if hasattr(target, 'velocity_x') else 0
        
        logger.info(f"🎯 Target acquired: {'HEAD' if is_head_target else 'BODY'}, aim_point=({target.aim_x:.1f}, {target.aim_y:.1f})")
        
        # 简化直接移动，传递头部标识
        mouse.move_to_target(target.aim_x, target.aim_y, target_velocity, is_head_target)
        
        # 检查是否在射击范围内
        if self.is_target_in_scope(target):
            logger.info("🔥 Target in scope - 简单三连发")
            shooting.queue.put((True, mouse.get_shooting_key_state()))
        else:
            shooting.queue.put((False, mouse.get_shooting_key_state()))
    
    def find_best_target(self, frame):
        """优先头部，无头部时锁定身体的目标选择"""
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
        
        # 🚀 获取当前鼠标位置进行满意距离检查
        try:
            current_mouse_x, current_mouse_y = mouse.get_current_mouse_position()
        except:
            current_mouse_x, current_mouse_y = center_x, center_y
        
        # 计算到屏幕中心的距离
        distances_sq = torch.sum((boxes_array[:, :2] - center) ** 2, dim=1)
        
        # 🎯 优先选择头部目标
        head_mask = classes_tensor == 7
        body_mask = (classes_tensor == 0) | (classes_tensor == 1)  # player, bot
        
        nearest_idx = None
        target_type = None
        
        if head_mask.any():
            # 有头部目标，选择最近的头部
            head_distances = distances_sq[head_mask]
            nearest_head_idx = torch.argmin(head_distances)
            nearest_idx = torch.nonzero(head_mask)[nearest_head_idx].item()
            head_distance = math.sqrt(distances_sq[nearest_idx].item())
            target_type = "HEAD"
            
            logger.info(f"🎯 Selected HEAD target at distance {head_distance:.1f}px")
            
        elif body_mask.any():
            # 没有头部目标，选择最近的身体目标
            body_distances = distances_sq[body_mask]
            nearest_body_idx = torch.argmin(body_distances)
            nearest_idx = torch.nonzero(body_mask)[nearest_body_idx].item()
            body_distance = math.sqrt(distances_sq[nearest_idx].item())
            target_type = "BODY"
            
            logger.info(f"🎯 Selected BODY target at distance {body_distance:.1f}px")
        else:
            # 没有头部和身体目标
            logger.info("🎯 No HEAD or BODY targets found")
            return None
        
        
        # 创建目标对象
        target_data = boxes_array[nearest_idx, :4].cpu().numpy()
        target_class = classes_tensor[nearest_idx].item()
        
        target = SimpleTarget(*target_data, target_class, time.time())
        
        # 更新跟踪器并预测位置
        self.target_tracker.update_target(target)
        predicted_x, predicted_y = self.target_tracker.predict_position(target)
        
        # Phase 3: 使用预测位置更新瞄准点
        if self.target_tracker.prediction_enabled:
            # 更新目标位置为预测位置
            target.x = predicted_x
            target.y = predicted_y
            
            # 重新计算精确瞄准点（使用新的Phase 3算法）
            target.aim_x, target.aim_y = target.calculate_aim_point()
        
        return target
    
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