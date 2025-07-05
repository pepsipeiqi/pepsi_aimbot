#!/usr/bin/env python3
"""
测试绝对移动鼠标控制器
验证坐标转换和绝对移动功能
"""

import sys
import time
import math

# 添加项目路径
sys.path.append('.')

from logic.mouse_absolute import mouse
from logic.config_watcher import cfg
from logic.logger import logger

def test_coordinate_conversion():
    """测试坐标转换功能"""
    logger.info("🧪 测试坐标转换功能")
    
    # 更新检测窗口偏移
    mouse.update_detection_window_offset()
    
    # 测试几个典型坐标点
    test_points = [
        (320, 320),  # 检测窗口中心
        (0, 0),      # 检测窗口左上角
        (640, 640),  # 检测窗口右下角（如果检测窗口是640x640）
        (320, 200),  # 中心上方
        (320, 440),  # 中心下方
    ]
    
    for detection_x, detection_y in test_points:
        screen_x, screen_y = mouse.detection_to_screen_coordinates(detection_x, detection_y)
        logger.info(f"检测坐标 ({detection_x}, {detection_y}) -> 屏幕坐标 ({screen_x}, {screen_y})")
    
    logger.info("✅ 坐标转换测试完成")

def test_mouse_position():
    """测试当前鼠标位置获取"""
    logger.info("🧪 测试鼠标位置获取")
    
    try:
        current_x, current_y = mouse.get_current_mouse_position()
        logger.info(f"当前鼠标位置: ({current_x}, {current_y})")
        
        # 转换为检测窗口坐标
        detection_x = current_x - mouse.detection_window_left
        detection_y = current_y - mouse.detection_window_top
        logger.info(f"对应检测窗口坐标: ({detection_x}, {detection_y})")
        
        logger.info("✅ 鼠标位置获取测试完成")
    except Exception as e:
        logger.error(f"❌ 鼠标位置获取失败: {e}")

def test_absolute_move():
    """测试绝对移动功能"""
    logger.info("🧪 测试绝对移动功能")
    
    # 获取当前鼠标位置
    try:
        start_x, start_y = mouse.get_current_mouse_position()
        logger.info(f"起始位置: ({start_x}, {start_y})")
        
        # 测试小距离移动
        logger.info("测试小距离移动...")
        test_target_x = mouse.center_x + 50  # 中心右侧50像素
        test_target_y = mouse.center_y + 30  # 中心下方30像素
        
        success = mouse.move_to_target(test_target_x, test_target_y, is_head_target=True)
        if success:
            time.sleep(0.5)  # 等待移动完成
            new_x, new_y = mouse.get_current_mouse_position()
            logger.info(f"移动后位置: ({new_x}, {new_y})")
            
            # 计算预期位置
            expected_x, expected_y = mouse.detection_to_screen_coordinates(test_target_x, test_target_y)
            error_x = abs(new_x - expected_x)
            error_y = abs(new_y - expected_y)
            logger.info(f"预期位置: ({expected_x}, {expected_y})")
            logger.info(f"移动误差: X={error_x}px, Y={error_y}px")
            
            if error_x <= 5 and error_y <= 5:
                logger.info("✅ 绝对移动精度测试通过")
            else:
                logger.warning(f"⚠️ 绝对移动精度较低: X误差{error_x}px, Y误差{error_y}px")
        else:
            logger.error("❌ 绝对移动测试失败")
        
        # 恢复原始位置
        time.sleep(1)
        mouse.execute_absolute_move(start_x, start_y)
        logger.info(f"恢复到起始位置: ({start_x}, {start_y})")
        
    except Exception as e:
        logger.error(f"❌ 绝对移动测试异常: {e}")

def main():
    """主测试函数"""
    logger.info("="*80)
    logger.info("🚀 开始测试绝对移动鼠标控制器")
    logger.info("="*80)
    
    # 显示当前配置
    logger.info(f"检测窗口尺寸: {cfg.detection_window_width}x{cfg.detection_window_height}")
    logger.info(f"捕获方式: Bettercam={cfg.Bettercam_capture}, MSS={cfg.mss_capture}, OBS={cfg.Obs_capture}")
    
    # 测试坐标转换
    test_coordinate_conversion()
    print()
    
    # 测试鼠标位置获取
    test_mouse_position()
    print()
    
    # 询问是否测试移动
    response = input("是否测试实际的鼠标移动？这会移动你的鼠标光标 (y/N): ")
    if response.lower() in ['y', 'yes']:
        test_absolute_move()
    else:
        logger.info("跳过鼠标移动测试")
    
    logger.info("="*80)
    logger.info("🎯 绝对移动鼠标控制器测试完成")
    logger.info("="*80)

if __name__ == "__main__":
    main()