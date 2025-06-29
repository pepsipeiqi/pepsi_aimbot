import torch
import supervision as sv
import numpy as np
import time
import math

from logic.hotkeys_watcher import hotkeys_watcher
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.mouse import mouse
from logic.shooting import shooting
from logic.logger import logger

class Target:
    def __init__(self, x, y, w, h, cls):
        self.w = w
        self.h = h
        self.cls = cls
        
        # Calculate precise targeting coordinates based on target type
        if cls == 7:  # Head target
            # For head targets, aim for the center-lower area for better hit probability
            head_offset_y = getattr(cfg, 'head_targeting_offset_y', 0.3)  # 30% down from center
            self.x = x  # Keep x at center
            self.y = y + (h * head_offset_y)  # Offset slightly down from center
        else:  # Body target
            # For body targets, use the existing body offset logic
            body_y_offset = getattr(cfg, 'body_y_offset', 0.2)
            self.x = x
            self.y = y - (body_y_offset * h)
        
        # Store original coordinates for debugging
        self.original_x = x
        self.original_y = y
    
    def get_precise_coordinates(self):
        """
        Get the most precise targeting coordinates for this target type.
        Returns (x, y) tuple optimized for the specific target class.
        """
        return (self.x, self.y)
    
    def get_distance_from_center(self, center_x, center_y):
        """Calculate distance from screen center for priority sorting."""
        return math.sqrt((self.x - center_x)**2 + (self.y - center_y)**2)

class FrameParser:
    def __init__(self):
        self.arch = self.get_arch()
        self.last_target_time = 0
        self.movement_cooldown = getattr(cfg, 'movement_cooldown_ms', 25) / 1000.0  # Reduced to 25ms for less blocking
        self.max_blocking_time = 5.0  # Max 5 seconds of continuous blocking before forcing detection

    def parse(self, result):
        if isinstance(result, sv.Detections):
            self._process_sv_detections(result)
        else:
            self._process_yolo_detections(result)

    def _process_sv_detections(self, detections):
        if detections.xyxy.any():
            visuals.draw_helpers(detections)
            target = self.sort_targets(detections)
            self._handle_target(target)
        else:
            visuals.clear()
            # 处理无目标情况 - 清理快速瞄准状态
            mouse.handle_no_target()
            if cfg.auto_shoot or cfg.triggerbot:
                shooting.shoot(False, False)

    def _process_yolo_detections(self, results):
        for frame in results:
            if frame.boxes:
                target = self.sort_targets(frame)
                self._handle_target(target)
                self._visualize_frame(frame)

    def _handle_target(self, target):
        if target:
            if hotkeys_watcher.clss is None:
                hotkeys_watcher.active_classes()
            
            if target.cls in hotkeys_watcher.clss:
                # Check movement coordination before issuing new mouse command
                current_time = time.time()
                time_since_last_target = current_time - self.last_target_time
                
                # Detailed blocking check with logging - more permissive
                movement_in_progress = self.is_movement_in_progress()
                cooldown_active = time_since_last_target < self.movement_cooldown
                
                # Force detection if blocked for too long (prevent infinite blocking)
                force_detection = time_since_last_target > self.max_blocking_time
                
                if force_detection:
                    logger.info(f"⚡ Forcing detection: blocked for {time_since_last_target:.1f}s > {self.max_blocking_time}s")
                elif movement_in_progress and cooldown_active:
                    # Only block if BOTH conditions are true and it's a significant movement
                    buffer_distance = math.sqrt(mouse.movement_buffer_x**2 + mouse.movement_buffer_y**2)
                    if buffer_distance > 20:  # Only block for significant buffered movements
                        logger.info(f"🚫 Detection blocked: significant movement (buffer={buffer_distance:.1f}px) + cooldown")
                        return
                    else:
                        logger.info(f"✅ Allowing detection: small buffer movement ({buffer_distance:.1f}px)")
                elif movement_in_progress:
                    # Check if it's just a small buffer movement - allow detection for small movements
                    buffer_distance = math.sqrt(mouse.movement_buffer_x**2 + mouse.movement_buffer_y**2)
                    if buffer_distance > 30:  # Only block for larger movements
                        logger.info(f"🚫 Detection blocked: large movement in progress (buffer={buffer_distance:.1f}px)")
                        return
                    else:
                        logger.info(f"✅ Allowing detection: small movement ({buffer_distance:.1f}px)")
                elif cooldown_active and time_since_last_target < (self.movement_cooldown * 0.7):
                    # Only apply cooldown for 70% of the original time
                    logger.info(f"🚫 Detection blocked: strict cooldown {time_since_last_target*1000:.0f}ms < {self.movement_cooldown*700:.0f}ms")
                    return
                
                # Use precise coordinates for targeting
                precise_x, precise_y = target.get_precise_coordinates()
                
                # Log target processing
                logger.info(f"🎯 Processing target: cls={target.cls}, pos=({precise_x:.1f}, {precise_y:.1f}), size=({target.w:.1f}x{target.h:.1f})")
                
                # Process the target with optimized coordinates
                mouse.process_data((precise_x, precise_y, target.w, target.h, target.cls))
                self.last_target_time = current_time

    def _visualize_frame(self, frame):
        if cfg.show_window or cfg.show_overlay:
            if cfg.show_boxes or cfg.overlay_show_boxes:
                visuals.draw_helpers(frame.boxes)
            
            if cfg.show_window and cfg.show_detection_speed:
                visuals.draw_speed(frame.speed['preprocess'], frame.speed['inference'], frame.speed['postprocess'])
        
        # Handle no detections
        if not frame.boxes:
            # 处理无目标情况 - 清理快速瞄准状态
            mouse.handle_no_target()
            if cfg.auto_shoot or cfg.triggerbot:
                shooting.shoot(False, False)
        
        if cfg.show_window or cfg.show_overlay:
            if not frame.boxes:
                visuals.clear()

    def sort_targets(self, frame):
        if isinstance(frame, sv.Detections):
            boxes_array, classes_tensor = self._convert_sv_to_tensor(frame)
        else:
            boxes_array = frame.boxes.xywh.to(self.arch)
            classes_tensor = frame.boxes.cls.to(self.arch)
        
        if not classes_tensor.numel():
            return None

        return self._find_nearest_target(boxes_array, classes_tensor)

    def _convert_sv_to_tensor(self, frame):
        xyxy = frame.xyxy
        xywh = torch.tensor([
            (xyxy[:, 0] + xyxy[:, 2]) / 2,  
            (xyxy[:, 1] + xyxy[:, 3]) / 2,  
            xyxy[:, 2] - xyxy[:, 0],        
            xyxy[:, 3] - xyxy[:, 1]        
        ], dtype=torch.float32).to(self.arch).T
        
        classes_tensor = torch.from_numpy(np.array(frame.class_id, dtype=np.float32)).to(self.arch)
        return xywh, classes_tensor

    def _find_nearest_target(self, boxes_array, classes_tensor):
        center = torch.tensor([capture.screen_x_center, capture.screen_y_center], device=self.arch)
        distances_sq = torch.sum((boxes_array[:, :2] - center) ** 2, dim=1)
        weights = torch.ones_like(distances_sq)

        if cfg.disable_headshot:
            non_head_mask = classes_tensor != 7
            weights = torch.ones_like(classes_tensor)
            weights[classes_tensor == 7] *= 0.5
            size_factor = boxes_array[:, 2] * boxes_array[:, 3]
            distances_sq = weights * (distances_sq / size_factor)

            if not non_head_mask.any():
                return None
            nearest_idx = torch.argmin(distances_sq[non_head_mask])
            nearest_idx = torch.nonzero(non_head_mask)[nearest_idx].item()
        else:
            head_mask = classes_tensor == 7
            if head_mask.any():
                nearest_idx = torch.argmin(distances_sq[head_mask])
                nearest_idx = torch.nonzero(head_mask)[nearest_idx].item()
            else:
                nearest_idx = torch.argmin(distances_sq)
        
        target_data = boxes_array[nearest_idx, :4].cpu().numpy()
        target_class = classes_tensor[nearest_idx].item()

        return Target(*target_data, target_class)

    def get_arch(self):
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        elif 'cpu' in cfg.AI_device:
            return 'cpu'
        else:
            return f'cuda:{cfg.AI_device}'
    
    def is_movement_in_progress(self):
        """
        Check if mouse movement is currently in progress.
        This method coordinates with the mouse controller to prevent
        detection from interrupting active movements.
        """
        return mouse.is_movement_active()

frameParser = FrameParser()