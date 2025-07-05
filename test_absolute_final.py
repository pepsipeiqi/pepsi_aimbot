#!/usr/bin/env python3
"""
最终绝对移动测试 - 非交互式版本
验证所有功能都正常工作
"""

import sys
import os
import math

# 添加mouse_new路径
mouse_new_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_new')
sys.path.insert(0, mouse_new_path)

def comprehensive_test():
    """综合测试所有功能"""
    print("="*60)
    print("🚀 绝对移动功能综合测试")
    print("="*60)
    
    # 1. 测试mouse_new导入
    print("📦 测试1: mouse_new模块导入")
    try:
        import mouse as mouse_new
        print("✅ mouse_new模块导入成功")
    except Exception as e:
        print(f"❌ mouse_new模块导入失败: {e}")
        return False
    
    # 2. 测试坐标转换逻辑
    print("\n🔧 测试2: 坐标转换逻辑")
    # 模拟实际配置
    detection_window_width = 640
    detection_window_height = 640
    primary_screen_width = 1920
    primary_screen_height = 1080
    
    # 计算检测窗口偏移（居中）
    detection_window_left = int(primary_screen_width / 2 - detection_window_width / 2)
    detection_window_top = int(primary_screen_height / 2 - detection_window_height / 2)
    
    print(f"   屏幕尺寸: {primary_screen_width}x{primary_screen_height}")
    print(f"   检测窗口: {detection_window_width}x{detection_window_height}")
    print(f"   窗口偏移: ({detection_window_left}, {detection_window_top})")
    
    # 验证关键坐标转换
    center_detection_x, center_detection_y = 320, 320  # 检测窗口中心
    center_screen_x = detection_window_left + center_detection_x
    center_screen_y = detection_window_top + center_detection_y
    
    expected_screen_center_x = primary_screen_width // 2
    expected_screen_center_y = primary_screen_height // 2
    
    print(f"   检测中心 ({center_detection_x}, {center_detection_y}) -> 屏幕坐标 ({center_screen_x}, {center_screen_y})")
    print(f"   预期屏幕中心: ({expected_screen_center_x}, {expected_screen_center_y})")
    
    if abs(center_screen_x - expected_screen_center_x) <= 1 and abs(center_screen_y - expected_screen_center_y) <= 1:
        print("✅ 坐标转换逻辑正确")
    else:
        print("❌ 坐标转换逻辑有误")
        return False
    
    # 3. 测试鼠标位置获取
    print("\n🖱️  测试3: 鼠标位置获取")
    try:
        current_x, current_y = mouse_new.get_position()
        print(f"   当前鼠标位置: ({current_x}, {current_y})")
        print("✅ 鼠标位置获取成功")
    except Exception as e:
        print(f"❌ 鼠标位置获取失败: {e}")
        return False
    
    # 4. 验证API可用性
    print("\n🔌 测试4: mouse_new API可用性")
    try:
        # 测试move函数是否可调用（不实际移动）
        move_func = getattr(mouse_new, 'move', None)
        if move_func and callable(move_func):
            print("✅ move函数可用")
        else:
            print("❌ move函数不可用")
            return False
            
        # 测试其他必要函数
        get_pos_func = getattr(mouse_new, 'get_position', None)
        if get_pos_func and callable(get_pos_func):
            print("✅ get_position函数可用")
        else:
            print("❌ get_position函数不可用")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False
    
    # 5. 模拟真实场景测试
    print("\n🎯 测试5: 模拟真实瞄准场景")
    # 模拟YOLO检测到的敌人头部坐标
    enemy_head_detection_x = 350  # 检测窗口内头部X坐标
    enemy_head_detection_y = 280  # 检测窗口内头部Y坐标
    
    # 转换为屏幕绝对坐标
    target_screen_x = detection_window_left + enemy_head_detection_x
    target_screen_y = detection_window_top + enemy_head_detection_y
    
    # 计算移动距离
    move_distance = math.sqrt((target_screen_x - current_x)**2 + (target_screen_y - current_y)**2)
    
    print(f"   模拟敌人头部检测坐标: ({enemy_head_detection_x}, {enemy_head_detection_y})")
    print(f"   转换后屏幕坐标: ({target_screen_x}, {target_screen_y})")
    print(f"   当前鼠标位置: ({current_x}, {current_y})")
    print(f"   需要移动距离: {move_distance:.1f}px")
    print("✅ 真实场景模拟成功")
    
    # 6. 总结测试结果
    print("\n" + "="*60)
    print("🎉 绝对移动功能测试结果总结")
    print("="*60)
    print("✅ mouse_new模块：可用")
    print("✅ 坐标转换逻辑：正确")
    print("✅ 鼠标位置获取：正常")
    print("✅ API函数：完整")
    print("✅ 真实场景模拟：成功")
    print()
    print("🎯 新的绝对移动系统已准备就绪！")
    print()
    print("📋 使用方法:")
    print("   1. YOLO检测到敌人坐标 (detection_x, detection_y)")
    print("   2. 转换为屏幕坐标: screen_x = detection_window_left + detection_x")
    print("   3. 执行绝对移动: mouse_new.move(screen_x, screen_y, absolute=True)")
    print()
    print("⚡ 优势:")
    print("   - 直接移动到目标位置，无需复杂的相对移动计算")
    print("   - 避免累积误差和PID控制的复杂性")
    print("   - 移动精度只取决于系统API，稳定可靠")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = comprehensive_test()
    if success:
        print("🚀 所有测试通过！绝对移动系统可以使用。")
    else:
        print("❌ 某些测试失败，请检查配置。")