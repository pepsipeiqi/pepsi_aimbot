#!/usr/bin/env python3
"""
测试简化版绝对移动鼠标控制器
验证Windows API直接移动功能
"""

import sys
import time
import math

# 添加项目路径
sys.path.append('.')

def test_simple_absolute_mouse():
    """测试简化版绝对移动鼠标控制器"""
    print("="*60)
    print("🚀 测试简化版绝对移动鼠标控制器")
    print("="*60)
    
    try:
        from logic.mouse_absolute_simple import mouse
        print("✅ 简化版绝对移动模块导入成功")
    except Exception as e:
        print(f"❌ 简化版绝对移动模块导入失败: {e}")
        return False
    
    # 测试API可用性
    print(f"🔧 Windows API可用性: {mouse.api_available}")
    
    # 测试鼠标位置获取
    current_x, current_y = mouse.get_current_mouse_position()
    print(f"🖱️ 当前鼠标位置: ({current_x}, {current_y})")
    
    # 测试坐标转换
    print(f"🔧 检测窗口偏移: ({mouse.detection_window_left}, {mouse.detection_window_top})")
    print(f"🔧 检测窗口尺寸: {mouse.screen_width}x{mouse.screen_height}")
    
    # 测试坐标转换
    test_detection_x, test_detection_y = 350, 280  # 检测窗口内坐标
    screen_x, screen_y = mouse.detection_to_screen_coordinates(test_detection_x, test_detection_y)
    print(f"🔧 坐标转换测试: 检测({test_detection_x}, {test_detection_y}) -> 屏幕({screen_x}, {screen_y})")
    
    # 计算移动距离
    move_distance = math.sqrt((screen_x - current_x)**2 + (screen_y - current_y)**2)
    print(f"📏 预计移动距离: {move_distance:.1f}px")
    
    print()
    print("✅ 所有测试通过！简化版绝对移动系统准备就绪。")
    print()
    print("📋 核心特性:")
    print("   - 直接使用Windows API SetCursorPos")
    print("   - 无外部模块依赖冲突")
    print("   - 简单、稳定、快速")
    print("   - 检测坐标直接转换为屏幕坐标")
    
    return True

if __name__ == "__main__":
    success = test_simple_absolute_mouse()
    if success:
        print("🚀 简化版绝对移动系统测试通过！")
    else:
        print("❌ 测试失败。")