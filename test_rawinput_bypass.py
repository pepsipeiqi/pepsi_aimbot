#!/usr/bin/env python3
"""
测试Raw Input绕过鼠标控制器
验证相对移动绕过方案是否有效
"""

import time
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_relative_move():
    """测试相对移动"""
    print("🔧 测试Raw Input绕过鼠标控制器")
    print("=" * 50)
    
    try:
        from logic.mouse_rawinput_bypass import mouse
        print("✅ 成功导入 mouse_rawinput_bypass")
        
        # 显示配置信息
        print(f"📋 DPI: {mouse.dpi}")
        print(f"📋 灵敏度: {mouse.sensitivity}")
        print(f"📋 移动比例: {mouse.move_ratio:.3f}")
        
        # 获取当前鼠标位置
        current_x, current_y = mouse.get_current_mouse_position()
        print(f"📍 当前鼠标位置: ({current_x}, {current_y})")
        
        # 测试小幅度相对移动
        print("\n🔧 测试小幅度相对移动...")
        test_moves = [
            (50, 0, "向右50px"),
            (0, 50, "向下50px"),
            (-50, 0, "向左50px"),
            (0, -50, "向上50px")
        ]
        
        for delta_x, delta_y, description in test_moves:
            print(f"🎯 {description}: 相对移动({delta_x}, {delta_y})")
            
            # 获取移动前位置
            before_x, before_y = mouse.get_current_mouse_position()
            
            # 执行相对移动
            success = mouse.mouse_event_relative_move(delta_x, delta_y)
            
            # 验证结果
            time.sleep(0.1)
            after_x, after_y = mouse.get_current_mouse_position()
            
            actual_delta_x = after_x - before_x
            actual_delta_y = after_y - before_y
            
            if success:
                print(f"   ✅ 成功: 实际移动({actual_delta_x}, {actual_delta_y})")
            else:
                print(f"   ❌ 失败")
            
            time.sleep(0.5)
        
        # 测试move_to_target接口
        print(f"\n🔧 测试move_to_target接口...")
        
        # 计算一个检测坐标位置
        detection_x = 100
        detection_y = 100
        screen_x, screen_y = mouse.detection_to_screen_coordinates(detection_x, detection_y)
        
        print(f"🎯 移动到检测坐标({detection_x}, {detection_y}) -> 屏幕({screen_x}, {screen_y})")
        
        success = mouse.move_to_target(detection_x, detection_y, 0, False)
        if success:
            print("✅ move_to_target测试成功")
            
            # 验证最终位置
            time.sleep(0.2)
            final_x, final_y = mouse.get_current_mouse_position()
            print(f"📍 最终鼠标位置: ({final_x}, {final_y})")
            
            error_x = abs(final_x - screen_x)
            error_y = abs(final_y - screen_y)
            print(f"📏 位置误差: X={error_x}px, Y={error_y}px")
            
            if error_x <= 10 and error_y <= 10:
                print("🎉 精度测试通过")
            else:
                print("⚠️ 精度需要调整配置参数")
                print("💡 提示: 可以通过修改config.ini中的mouse_rawinput_move_ratio来调整")
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
    print("⚠️ Raw Input绕过测试")
    print("这个测试将使用相对移动来模拟绝对移动")
    print("关键是观察游戏内准心是否跟随移动")
    print("\n请确保：")
    print("1. 游戏正在运行且有焦点")
    print("2. 鼠标可以自由移动")
    print("3. 观察游戏内准心是否跟随鼠标移动")
    
    user_input = input("继续测试? (y/N): ").strip().lower()
    if user_input != 'y':
        print("测试取消")
        return
    
    success = test_relative_move()
    
    if success:
        print("\n🎉 Raw Input绕过测试完成")
        print("💡 重点观察：")
        print("   - 鼠标是否移动了")
        print("   - 游戏内准心是否也跟随移动")
        print("   - 如果准心跟随，说明绕过成功")
        print("   - 如果准心不动，需要尝试其他方案")
    else:
        print("\n❌ 测试失败")

if __name__ == "__main__":
    main()