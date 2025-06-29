from ultralytics import YOLO
import torch

from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.frame_parser_simple import simpleFrameParser
from logic.hotkeys_watcher import hotkeys_watcher
from logic.checks import run_checks
import supervision as sv

# 简化的tracker配置
tracker = sv.ByteTrack() if not cfg.disable_tracker else None

@torch.inference_mode()
def perform_detection(model, image, tracker: sv.ByteTrack | None = None):
    """执行YOLO检测 - 简化配置"""
    kwargs = dict(
        source=image,
        imgsz=cfg.ai_model_image_size,
        conf=cfg.AI_conf,
        iou=0.50,
        device=cfg.AI_device,
        half=not "cpu" in cfg.AI_device,
        max_det=20,
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

def init():
    """简化的初始化和主循环"""
    print("🚀 Starting Simple Aimbot System")
    
    # 运行基础检查
    run_checks()
    
    # 加载AI模型
    try:
        model = YOLO(f"models/{cfg.AI_model_name}", task="detect")
        print(f"✅ AI Model loaded: {cfg.AI_model_name}")
    except Exception as e:
        print("❌ AI model loading failed:", e)
        quit(0)
    
    frame_count = 0
    
    print("🎯 Simple aimbot started - YOLO → Aim → Shoot")
    
    # 主循环 - 简单直接
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
                    simpleFrameParser.parse(result)
                
                # 每1000帧打印一次状态
                if frame_count % 1000 == 0:
                    print(f"📊 Processed {frame_count} frames")
                    
        except KeyboardInterrupt:
            print("\n⚡ Stopping simple aimbot...")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            # 继续运行而不是崩溃
            continue
    
    print("👋 Simple aimbot stopped")

if __name__ == "__main__":
    init()