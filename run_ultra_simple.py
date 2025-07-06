"""
Ultra Simple Aimbot Runner - 强制使用mouse_new API的Raw Input兼容版本

核心流程：
1. YOLO模型检测敌人
2. 计算目标坐标
3. 使用增强的mouse_new Raw Input兼容系统移动
4. 锁定目标并开枪

特点：
- 强制使用mouse_new API，不使用硬件驱动
- 多重Raw Input绕过技术（SendInput, SetPhysicalCursorPos等）
- 自动检测和切换最有效的鼠标注入方法
- 保持超激进的速度优化算法
- 详细的兼容性日志用于故障排除
"""

from ultralytics import YOLO
import torch
import time
import sys
import os

from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.hotkeys_watcher import hotkeys_watcher
from logic.checks import run_checks
from logic.logger import logger
import supervision as sv

# 导入控制器管理器 - 支持传统和预测式控制
from logic.mouse_controller_manager import mouse_controller_manager as ultra_simple_mouse

# 简化的tracker配置
tracker = sv.ByteTrack() if not cfg.disable_tracker else None

@torch.inference_mode()
def perform_detection(model, image, tracker: sv.ByteTrack | None = None):
    """执行YOLO检测 - 超简化配置"""
    kwargs = dict(
        source=image,
        imgsz=cfg.ai_model_image_size,
        conf=cfg.AI_conf,
        iou=0.50,
        device=cfg.AI_device,
        half=not "cpu" in cfg.AI_device,
        max_det=10,  # 减少最大检测数量，提高速度
        agnostic_nms=False,
        augment=False,
        vid_stride=False,
        visualize=False,
        verbose=False,
        show_boxes=False,
        show_labels=False,
        show_conf=False,
        save=False,
        show=False,
        stream=True
    )

    kwargs["cfg"] = "logic/tracker.yaml" if tracker else "logic/game.yaml"
    results = model.predict(**kwargs)

    if tracker:
        for res in results:
            det = sv.Detections.from_ultralytics(res)
            return tracker.update_with_detections(det)
    else:
        return next(results)

class SimpleFrameParser:
    """超简化的帧解析器"""
    
    def __init__(self):
        self.frame_count = 0
        logger.info("🎯 SimpleFrameParser initialized")
    
    def parse(self, result):
        """解析检测结果并控制鼠标"""
        self.frame_count += 1
        import time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            if isinstance(result, sv.Detections):
                # supervision格式
                if len(result.xyxy) > 0:
                    # 详细YOLO检测日志
                    print(f"{current_time} - 🔍 YOLO: {len(result.xyxy)} targets detected")
                    for i, (bbox, cls_id) in enumerate(zip(result.xyxy, result.class_id)):
                        x1, y1, x2, y2 = bbox
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        width = x2 - x1
                        height = y2 - y1
                        target_type = "HEAD" if cls_id == 7 else "BODY"
                        print(f"  Target {i+1}: {target_type}({cls_id}) bbox=({x1:.1f},{y1:.1f},{x2:.1f},{y2:.1f}) center=({center_x:.1f},{center_y:.1f}) size={width:.1f}x{height:.1f}")
                    
                    ultra_simple_mouse.process_data(result)
                    
                    # 添加视觉调试 - 显示检测框
                    from logic.visual import visuals
                    visuals.draw_helpers(result)
                else:
                    # 减少日志噪音 - 只在有目标时打印
                    ultra_simple_mouse.handle_no_target()
            else:
                # YOLO原始结果格式
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes
                    if len(boxes) > 0:
                        # 详细YOLO检测日志
                        print(f"{current_time} - 🔍 YOLO: {len(boxes)} targets detected")
                        
                        for i, box in enumerate(boxes):
                            xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                            cls = int(box.cls[0].cpu().numpy()) if box.cls is not None else 0
                            conf = float(box.conf[0].cpu().numpy()) if box.conf is not None else 1.0
                            
                            # 计算中心点和尺寸
                            center_x = (xyxy[0] + xyxy[2]) / 2
                            center_y = (xyxy[1] + xyxy[3]) / 2
                            width = xyxy[2] - xyxy[0]
                            height = xyxy[3] - xyxy[1]
                            
                            target_type = "HEAD" if cls == 7 else "BODY"
                            print(f"  Target {i+1}: {target_type}({cls}) conf={conf:.2f} bbox=({xyxy[0]:.1f},{xyxy[1]:.1f},{xyxy[2]:.1f},{xyxy[3]:.1f}) center=({center_x:.1f},{center_y:.1f}) size={width:.1f}x{height:.1f}")
                        
                        # 获取第一个检测框
                        box = boxes[0]
                        xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                        cls = int(box.cls[0].cpu().numpy()) if box.cls is not None else 0
                        conf = float(box.conf[0].cpu().numpy()) if box.conf is not None else 1.0
                        
                        # 计算中心点和尺寸
                        center_x = (xyxy[0] + xyxy[2]) / 2
                        center_y = (xyxy[1] + xyxy[3]) / 2
                        width = xyxy[2] - xyxy[0]
                        height = xyxy[3] - xyxy[1]
                        
                        print(f"{current_time} - 🎯 SELECTED: Target 1 for processing")
                        
                        # 传递给鼠标控制器
                        ultra_simple_mouse.process_target(center_x, center_y, width, height, cls)
                        
                        # 添加视觉调试 - 显示检测框
                        from logic.visual import visuals
                        visuals.draw_helpers(boxes)
                    else:
                        # 减少日志噪音 - 只在有目标时打印
                        ultra_simple_mouse.handle_no_target()
                else:
                    print(f"{current_time} - 🔍 YOLO: No detection results")
                    ultra_simple_mouse.handle_no_target()
        
        except Exception as e:
            logger.error(f"❌ Frame parsing error: {e}")
            ultra_simple_mouse.handle_no_target()

def init():
    """超简化的初始化和主循环"""
    print("🚀 Starting Ultra Simple Aimbot System with Enhanced mouse_new Raw Input Compatibility")
    logger.info("🚀 Ultra Simple Aimbot - Enhanced mouse_new Raw Input Compatible edition")
    
    # 运行基础检查
    try:
        run_checks()
    except Exception as e:
        logger.warning(f"⚠️ Some checks failed: {e}")
        print(f"⚠️ Some checks failed (continuing anyway): {e}")
    
    # 加载AI模型
    try:
        model = YOLO(f"models/{cfg.AI_model_name}", task="detect")
        logger.info(f"✅ AI Model loaded: {cfg.AI_model_name}")
        print(f"✅ AI Model loaded: {cfg.AI_model_name}")
    except Exception as e:
        logger.error(f"❌ AI model loading failed: {e}")
        print(f"❌ AI model loading failed: {e}")
        print("❌ Cannot continue without AI model")
        input("Press Enter to exit...")
        return
    
    # 创建帧解析器
    frame_parser = SimpleFrameParser()
    
    frame_count = 0
    last_log_time = time.time()
    
    print("🎯 Enhanced mouse_new aimbot started - YOLO → Raw Input Compatible Movement → Lock → Shoot")
    logger.info("🎯 Enhanced mouse_new aimbot started - YOLO → Raw Input Compatible Movement → Lock → Shoot")
    
    # 主循环 - 极简版本
    while True:
        try:
            # 获取新帧
            image = capture.get_new_frame()
            
            if image is not None:
                frame_count += 1
                
                # 圆形捕获（如果启用）
                if cfg.circle_capture:
                    image = capture.convert_to_circle(image)
                
                # 更新可视化
                if cfg.show_window or cfg.show_overlay:
                    visuals.queue.put(image)
                
                # 执行检测
                result = perform_detection(model, image, tracker)
                
                # 如果未暂停则处理结果
                if hotkeys_watcher.app_pause == 0:
                    frame_parser.parse(result)
                
                # 每5秒打印一次状态
                current_time = time.time()
                if current_time - last_log_time >= 5.0:
                    logger.info(f"📊 Processed {frame_count} frames in {current_time - last_log_time:.1f}s")
                    last_log_time = current_time
                    
        except KeyboardInterrupt:
            print("\n⚡ Stopping ultra simple aimbot...")
            logger.info("⚡ Stopping ultra simple aimbot...")
            break
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            print(f"❌ Error in main loop: {e}")
            # 继续运行而不是崩溃
            continue
    
    print("👋 Ultra simple aimbot stopped")
    logger.info("👋 Ultra simple aimbot stopped")

if __name__ == "__main__":
    try:
        init()
    except KeyboardInterrupt:
        print("\n⚡ User interrupted, stopping...")
        logger.info("⚡ User interrupted, stopping...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")