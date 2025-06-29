from ultralytics import YOLO
import torch
import time

from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.frame_parser import frameParser
from logic.hotkeys_watcher import hotkeys_watcher
from logic.checks import run_checks
import supervision as sv
    
tracker = sv.ByteTrack() if not cfg.disable_tracker else None

@torch.inference_mode()
def perform_detection(model, image, tracker: sv.ByteTrack | None = None):
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
    run_checks()
    
    try:
        model = YOLO(f"models/{cfg.AI_model_name}", task="detect")
    except Exception as e:
        print("An error occurred when loading the AI model:\n", e)
        quit(0)
    
    # Detection frequency control variables
    last_detection_time = 0
    detection_interval = 1.0 / getattr(cfg, 'detection_fps_limit', 60)  # Default 60 FPS limit
    frame_skip_counter = 0
    
    while True:
        current_time = time.time()
        image = capture.get_new_frame()
        
        if image is not None:
            if cfg.circle_capture:
                image = capture.convert_to_circle(image)
                
            if cfg.show_window or cfg.show_overlay:
                visuals.queue.put(image)
            
            # Check if enough time has passed since last detection
            time_since_last_detection = current_time - last_detection_time
            
            # Skip detection if:
            # 1. Not enough time has passed (frame rate limiting)
            # 2. Mouse is actively moving (movement coordination)
            fps_limited = time_since_last_detection < detection_interval
            movement_blocking = frameParser.is_movement_in_progress()
            
            should_skip_detection = fps_limited or movement_blocking
            
            if should_skip_detection:
                frame_skip_counter += 1
                
                # Log skip reason periodically (every 30 frames to avoid spam)
                if frame_skip_counter % 30 == 1:
                    if fps_limited and movement_blocking:
                        print(f"🔄 Detection skip #{frame_skip_counter}: FPS limit + movement active")
                    elif fps_limited:
                        print(f"⏱️ Detection skip #{frame_skip_counter}: FPS limit ({time_since_last_detection*1000:.0f}ms < {detection_interval*1000:.0f}ms)")
                    elif movement_blocking:
                        print(f"🚫 Detection skip #{frame_skip_counter}: movement active")
                
                # Still update visuals even when skipping detection
                continue
            
            # Perform detection
            result = perform_detection(model, image, tracker)
            last_detection_time = current_time
            frame_skip_counter = 0

            if hotkeys_watcher.app_pause == 0:
                frameParser.parse(result)

if __name__ == "__main__":
    init()