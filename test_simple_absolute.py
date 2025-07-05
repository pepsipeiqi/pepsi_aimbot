#!/usr/bin/env python3
"""
简化的绝对移动测试
测试基本的坐标转换逻辑和mouse_new模块功能
"""

import sys
import os
import math

# 添加mouse_new路径
mouse_new_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_new')
sys.path.insert(0, mouse_new_path)

def test_mouse_new_import():
    """测试mouse_new模块导入"""
    print("🧪 测试mouse_new模块导入...")
    try:
        import mouse as mouse_new
        print("✅ mouse_new模块导入成功")
        return mouse_new
    except Exception as e:
        print(f"❌ mouse_new模块导入失败: {e}")
        return None

def test_coordinate_conversion():
    """测试坐标转换逻辑"""
    print("🧪 测试坐标转换逻辑...")
    
    # 模拟配置
    detection_window_width = 640
    detection_window_height = 640
    primary_screen_width = 1920
    primary_screen_height = 1080
    
    # 计算检测窗口在屏幕上的偏移（居中）
    detection_window_left = int(primary_screen_width / 2 - detection_window_width / 2)
    detection_window_top = int(primary_screen_height / 2 - detection_window_height / 2)
    
    print(f"屏幕尺寸: {primary_screen_width}x{primary_screen_height}")
    print(f"检测窗口尺寸: {detection_window_width}x{detection_window_height}")
    print(f"检测窗口偏移: ({detection_window_left}, {detection_window_top})")
    
    # 测试坐标转换
    test_points = [
        (320, 320),  # 检测窗口中心
        (0, 0),      # 检测窗口左上角
        (640, 640),  # 检测窗口右下角
        (320, 200),  # 中心上方
        (320, 440),  # 中心下方
    ]
    
    for detection_x, detection_y in test_points:
        screen_x = detection_window_left + detection_x
        screen_y = detection_window_top + detection_y
        print(f"检测坐标 ({detection_x}, {detection_y}) -> 屏幕坐标 ({screen_x}, {screen_y})")
    
    print("✅ 坐标转换测试完成")
    return detection_window_left, detection_window_top

def test_mouse_position(mouse_new):
    """测试鼠标位置获取"""
    print("🧪 测试鼠标位置获取...")
    try:
        current_x, current_y = mouse_new.get_position()
        print(f"当前鼠标位置: ({current_x}, {current_y})")
        print("✅ 鼠标位置获取成功")
        return current_x, current_y
    except Exception as e:
        print(f"❌ 鼠标位置获取失败: {e}")
        return None, None

def test_absolute_move(mouse_new, detection_window_left, detection_window_top):
    """测试绝对移动"""
    print("🧪 测试绝对移动...")
    
    # 获取当前位置
    start_x, start_y = mouse_new.get_position()
    print(f"起始位置: ({start_x}, {start_y})")
    
    # 计算一个安全的测试目标（检测窗口中心右侧50像素）
    detection_center_x = 320
    detection_center_y = 320
    test_detection_x = detection_center_x + 50
    test_detection_y = detection_center_y + 30
    
    # 转换为屏幕坐标
    target_screen_x = detection_window_left + test_detection_x
    target_screen_y = detection_window_top + test_detection_y
    
    print(f"测试目标检测坐标: ({test_detection_x}, {test_detection_y})")
    print(f"测试目标屏幕坐标: ({target_screen_x}, {target_screen_y})")
    
    # 询问是否执行移动
    response = input("是否执行测试移动？这会移动你的鼠标光标 (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("跳过移动测试")
        return
    
    try:
        # 执行绝对移动
        print(f"移动到: ({target_screen_x}, {target_screen_y})")
        mouse_new.move(target_screen_x, target_screen_y, absolute=True, duration=0)
        
        import time
        time.sleep(0.5)  # 等待移动完成
        
        # 检查移动结果
        new_x, new_y = mouse_new.get_position()
        error_x = abs(new_x - target_screen_x)
        error_y = abs(new_y - target_screen_y)
        
        print(f"移动后位置: ({new_x}, {new_y})")
        print(f"移动误差: X={error_x}px, Y={error_y}px")
        
        if error_x <= 5 and error_y <= 5:
            print("✅ 绝对移动精度测试通过")
        else:
            print(f"⚠️ 绝对移动精度较低: X误差{error_x}px, Y误差{error_y}px")
        
        # 恢复原始位置
        time.sleep(1)
        print(f"恢复到起始位置: ({start_x}, {start_y})")
        mouse_new.move(start_x, start_y, absolute=True, duration=0)
        
    except Exception as e:
        print(f"❌ 绝对移动测试失败: {e}")

def main():
    """主测试函数"""
    print("="*60)
    print("🚀 简化绝对移动测试")
    print("="*60)
    
    # 测试mouse_new导入
    mouse_new = test_mouse_new_import()
    if not mouse_new:
        print("❌ 无法导入mouse_new模块，测试终止")
        return
    print()
    
    # 测试坐标转换
    detection_window_left, detection_window_top = test_coordinate_conversion()
    print()
    
    # 测试鼠标位置
    current_x, current_y = test_mouse_position(mouse_new)
    if current_x is None:
        print("❌ 无法获取鼠标位置，跳过移动测试")
    else:
        print()
        # 测试绝对移动
        test_absolute_move(mouse_new, detection_window_left, detection_window_top)
    
    print()
    print("="*60)
    print("🎯 简化绝对移动测试完成")
    print("="*60)

if __name__ == "__main__":
    main()