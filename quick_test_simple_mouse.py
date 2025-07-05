#!/usr/bin/env python3
"""
快速测试简化版绝对移动鼠标控制器
验证Windows API直接移动是否有效
"""

import time
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple_absolute():
    """测试简化版绝对移动"""
    print("🔧 测试简化版绝对移动鼠标控制器")
    print("=" * 50)
    
    try:
        from logic.mouse_simple_absolute import mouse
        print("✅ 成功导入 mouse_simple_absolute")
        
        # 获取当前鼠标位置
        current_x, current_y = mouse.get_current_mouse_position()
        print(f"📍 当前鼠标位置: ({current_x}, {current_y})")
        
        # 测试移动到屏幕中心
        center_x = mouse.screen_width_pixels // 2
        center_y = mouse.screen_height_pixels // 2
        print(f"🎯 测试移动到屏幕中心: ({center_x}, {center_y})")
        
        # 执行移动
        success = mouse.simple_absolute_move(center_x, center_y)
        if success:
            print("✅ 移动到屏幕中心成功")
            
            # 验证移动结果
            time.sleep(0.1)
            new_x, new_y = mouse.get_current_mouse_position()
            print(f"📍 移动后鼠标位置: ({new_x}, {new_y})")
            
            # 计算误差
            error_x = abs(new_x - center_x)
            error_y = abs(new_y - center_y)
            print(f"📏 移动误差: X={error_x}px, Y={error_y}px")
            
            if error_x <= 5 and error_y <= 5:
                print("🎉 精度测试通过")
            else:
                print("⚠️ 精度需要改进")
        else:
            print("❌ 移动失败")
            return False
        
        # 测试检测坐标转换和移动
        print("\n🔧 测试检测坐标转换...")
        detection_x = 200  # 检测窗口内的坐标
        detection_y = 150
        
        screen_x, screen_y = mouse.detection_to_screen_coordinates(detection_x, detection_y)
        print(f"📍 检测坐标({detection_x}, {detection_y}) -> 屏幕坐标({screen_x}, {screen_y})")
        
        # 测试move_to_target接口
        print(f"🎯 测试move_to_target接口...")
        success = mouse.move_to_target(detection_x, detection_y, 0, False)
        if success:
            print("✅ move_to_target测试成功")
            
            # 验证结果
            time.sleep(0.1)
            final_x, final_y = mouse.get_current_mouse_position()
            print(f"📍 最终鼠标位置: ({final_x}, {final_y})")
            
            error_x = abs(final_x - screen_x)
            error_y = abs(final_y - screen_y)
            print(f"📏 目标误差: X={error_x}px, Y={error_y}px")
        else:
            print("❌ move_to_target测试失败")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("⚠️ 即将进行鼠标移动测试")
    print("请确保：")
    print("1. 鼠标可以自由移动")
    print("2. 没有其他程序干扰鼠标")
    print("3. 准备观察鼠标移动到屏幕中心")
    
    user_input = input("继续测试? (y/N): ").strip().lower()
    if user_input != 'y':
        print("测试取消")
        return
    
    success = test_simple_absolute()
    
    if success:
        print("\n🎉 简化版绝对移动测试完成")
        print("💡 如果鼠标成功移动，说明简化版本可以解决Raw Input问题")
    else:
        print("\n❌ 测试失败")

if __name__ == "__main__":
    main()