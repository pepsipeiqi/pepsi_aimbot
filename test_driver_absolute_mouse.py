#!/usr/bin/env python3
"""
测试Raw Input兼容的驱动绝对移动鼠标控制器
验证新的mouse_driver_absolute.py实现
"""

import time
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """测试模块导入"""
    print("🔧 测试模块导入...")
    try:
        from logic.mouse_driver_absolute import mouse
        print("✅ 成功导入 mouse_driver_absolute")
        return mouse
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return None

def test_initialization(mouse):
    """测试初始化"""
    print("\n🔧 测试初始化...")
    try:
        # 检查是否已初始化
        if hasattr(mouse, '_initialized') and mouse._initialized:
            print("✅ 鼠标控制器已初始化")
            print(f"📊 屏幕分辨率: {mouse.screen_width_pixels}x{mouse.screen_height_pixels}")
            print(f"📊 检测窗口: {mouse.screen_width}x{mouse.screen_height}")
            return True
        else:
            print("❌ 鼠标控制器未初始化")
            return False
    except Exception as e:
        print(f"❌ 初始化检查失败: {e}")
        return False

def test_coordinate_conversion(mouse):
    """测试坐标转换"""
    print("\n🔧 测试坐标转换...")
    try:
        # 测试几个检测坐标点
        test_points = [
            (190, 190),  # 检测窗口中心
            (100, 100),  # 左上区域
            (280, 280),  # 右下区域
        ]
        
        for detection_x, detection_y in test_points:
            screen_x, screen_y = mouse.detection_to_screen_coordinates(detection_x, detection_y)
            print(f"📍 检测坐标({detection_x}, {detection_y}) -> 屏幕坐标({screen_x}, {screen_y})")
        
        print("✅ 坐标转换测试通过")
        return True
    except Exception as e:
        print(f"❌ 坐标转换测试失败: {e}")
        return False

def test_movement(mouse):
    """测试鼠标移动"""
    print("\n🔧 测试鼠标移动...")
    try:
        # 获取当前鼠标位置
        if hasattr(mouse, 'abs_controller') and mouse.abs_controller:
            # 测试移动到检测窗口中心
            center_x = mouse.screen_width // 2
            center_y = mouse.screen_height // 2
            
            print(f"🎯 测试移动到检测窗口中心: ({center_x}, {center_y})")
            
            # 测试身体目标移动
            success = mouse.move_to_target(center_x, center_y, 0, False)
            if success:
                print("✅ 身体目标移动测试成功")
            else:
                print("❌ 身体目标移动测试失败")
            
            time.sleep(1)
            
            # 测试头部目标移动
            head_x = center_x + 50
            head_y = center_y - 50
            print(f"🎯 测试移动到头部位置: ({head_x}, {head_y})")
            
            success = mouse.move_to_target(head_x, head_y, 0, True)
            if success:
                print("✅ 头部目标移动测试成功")
            else:
                print("❌ 头部目标移动测试失败")
            
            return True
        else:
            print("❌ 绝对移动控制器不可用")
            return False
    except Exception as e:
        print(f"❌ 移动测试失败: {e}")
        return False

def test_configuration():
    """测试配置参数"""
    print("\n🔧 测试配置参数...")
    try:
        from logic.config_watcher import cfg
        
        # 检查新增的配置参数
        mouse_driver_absolute = getattr(cfg, 'mouse_driver_absolute', None)
        mouse_hardware_type = getattr(cfg, 'mouse_hardware_type', None)
        mouse_precision_level = getattr(cfg, 'mouse_precision_level', None)
        
        print(f"📋 mouse_driver_absolute: {mouse_driver_absolute}")
        print(f"📋 mouse_hardware_type: {mouse_hardware_type}")
        print(f"📋 mouse_precision_level: {mouse_precision_level}")
        
        # 检查基础配置参数
        mouse_dpi = getattr(cfg, 'mouse_dpi', None)
        mouse_sensitivity = getattr(cfg, 'mouse_sensitivity', None)
        
        print(f"📋 mouse_dpi: {mouse_dpi}")
        print(f"📋 mouse_sensitivity: {mouse_sensitivity}")
        
        print("✅ 配置参数检查完成")
        return True
    except Exception as e:
        print(f"❌ 配置参数检查失败: {e}")
        return False

def performance_test(mouse):
    """性能测试"""
    print("\n🔧 性能测试...")
    try:
        if not (hasattr(mouse, '_initialized') and mouse._initialized):
            print("❌ 鼠标控制器未初始化，跳过性能测试")
            return False
        
        # 测试移动性能
        test_count = 5
        total_time = 0
        success_count = 0
        
        center_x = mouse.screen_width // 2
        center_y = mouse.screen_height // 2
        
        print(f"📊 执行 {test_count} 次移动性能测试...")
        
        for i in range(test_count):
            # 生成测试目标点
            offset_x = 50 * (1 if i % 2 == 0 else -1)
            offset_y = 30 * (1 if i % 2 == 0 else -1)
            target_x = center_x + offset_x
            target_y = center_y + offset_y
            
            start_time = time.perf_counter()
            success = mouse.move_to_target(target_x, target_y, 0, False)
            end_time = time.perf_counter()
            
            move_time = (end_time - start_time) * 1000
            total_time += move_time
            
            if success:
                success_count += 1
                print(f"  测试 {i+1}: ✅ 成功 ({move_time:.2f}ms)")
            else:
                print(f"  测试 {i+1}: ❌ 失败 ({move_time:.2f}ms)")
            
            time.sleep(0.2)  # 短暂间隔
        
        # 计算统计结果
        avg_time = total_time / test_count
        success_rate = (success_count / test_count) * 100
        
        print(f"\n📊 性能测试结果:")
        print(f"   成功率: {success_rate:.1f}% ({success_count}/{test_count})")
        print(f"   平均响应时间: {avg_time:.2f}ms")
        
        if avg_time <= 10 and success_rate >= 80:
            print("🎉 性能测试通过")
            return True
        else:
            print("⚠️ 性能需要优化")
            return False
            
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Raw Input兼容驱动绝对移动鼠标控制器测试")
    print("=" * 60)
    
    # 1. 导入测试
    mouse = test_import()
    if not mouse:
        print("\n❌ 测试终止：模块导入失败")
        return
    
    # 2. 配置测试
    if not test_configuration():
        print("\n⚠️ 配置参数检查失败，但继续测试")
    
    # 3. 初始化测试
    if not test_initialization(mouse):
        print("\n❌ 测试终止：初始化失败")
        return
    
    # 4. 坐标转换测试
    if not test_coordinate_conversion(mouse):
        print("\n❌ 测试终止：坐标转换失败")
        return
    
    # 5. 移动测试（需要用户确认）
    print("\n⚠️ 即将进行鼠标移动测试，请确保：")
    print("   1. 鼠标可以自由移动")
    print("   2. 没有其他程序干扰")
    print("   3. 准备观察鼠标移动效果")
    
    user_input = input("继续移动测试? (y/N): ").strip().lower()
    if user_input == 'y':
        if not test_movement(mouse):
            print("\n⚠️ 移动测试失败")
        
        # 6. 性能测试
        user_input = input("继续性能测试? (y/N): ").strip().lower()
        if user_input == 'y':
            performance_test(mouse)
    else:
        print("⏭️ 跳过移动测试")
    
    # 清理
    try:
        mouse.cleanup()
        print("\n🔄 清理完成")
    except:
        pass
    
    print("\n🎉 测试完成")

if __name__ == "__main__":
    main()