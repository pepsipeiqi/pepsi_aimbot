#!/usr/bin/env python3
"""
测试丝滑移动效果
验证mouse_new的duration参数是否能解决"一卡一卡"的问题
"""

import sys
import time
import os

# 添加mouse_new路径
mouse_new_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_new')
sys.path.insert(0, mouse_new_path)

def test_smooth_movement():
    """测试丝滑移动效果"""
    print("="*60)
    print("🎯 测试丝滑移动效果")
    print("="*60)
    
    try:
        import mouse as mouse_new
        print("✅ mouse_new模块导入成功")
    except Exception as e:
        print(f"❌ mouse_new模块导入失败: {e}")
        return False
    
    # 获取当前鼠标位置
    try:
        start_x, start_y = mouse_new.get_position()
        print(f"🖱️ 当前鼠标位置: ({start_x}, {start_y})")
    except Exception as e:
        print(f"❌ 获取鼠标位置失败: {e}")
        return False
    
    print("\n🎮 丝滑移动测试:")
    print("   将测试不同duration参数的移动效果")
    print("   观察移动是否丝滑，没有'一卡一卡'的感觉")
    print()
    
    # 测试不同的移动方式
    test_cases = [
        {
            'name': '瞬间移动（旧方式）',
            'duration': 0,
            'offset': (100, 50),
            'description': '类似之前的移动方式，瞬间到达'
        },
        {
            'name': '快速丝滑移动',
            'duration': 0.05,
            'offset': (150, 80),
            'description': '50ms丝滑移动，适合头部目标'
        },
        {
            'name': '标准丝滑移动',
            'duration': 0.08,
            'offset': (200, 120),
            'description': '80ms丝滑移动，适合身体目标'
        },
        {
            'name': '超丝滑移动',
            'duration': 0.15,
            'offset': (250, 150),
            'description': '150ms超丝滑移动，演示效果'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"📋 测试 {i}: {test['name']}")
        print(f"   描述: {test['description']}")
        print(f"   参数: duration={test['duration']}s")
        
        response = input("   按Enter执行测试，或输入's'跳过: ").strip().lower()
        if response == 's':
            print("   ⏭️ 跳过此测试")
            continue
        
        # 计算目标位置
        target_x = start_x + test['offset'][0]
        target_y = start_y + test['offset'][1]
        
        print(f"   🎯 移动到: ({target_x}, {target_y})")
        
        try:
            # 执行移动
            start_time = time.time()
            mouse_new.move(
                target_x, 
                target_y, 
                absolute=True, 
                duration=test['duration'],
                steps_per_second=240.0
            )
            end_time = time.time()
            
            actual_duration = end_time - start_time
            print(f"   ✅ 移动完成，实际耗时: {actual_duration*1000:.0f}ms")
            
            # 验证位置
            final_x, final_y = mouse_new.get_position()
            error_x = abs(final_x - target_x)
            error_y = abs(final_y - target_y)
            print(f"   📍 最终位置: ({final_x}, {final_y})")
            print(f"   📏 位置误差: X={error_x}px, Y={error_y}px")
            
            if error_x <= 5 and error_y <= 5:
                print("   ✅ 位置精度良好")
            else:
                print("   ⚠️ 位置精度较低")
            
        except Exception as e:
            print(f"   ❌ 移动失败: {e}")
        
        print()
        time.sleep(1)  # 等待1秒再进行下一个测试
    
    # 恢复到原始位置
    print("🔄 恢复到原始位置...")
    try:
        mouse_new.move(start_x, start_y, absolute=True, duration=0.1)
        print("✅ 位置已恢复")
    except Exception as e:
        print(f"❌ 恢复位置失败: {e}")
    
    return True

def test_gaming_scenario():
    """测试游戏场景移动"""
    print("="*60)
    print("🎮 游戏场景移动测试")
    print("="*60)
    
    try:
        import mouse as mouse_new
    except Exception as e:
        print(f"❌ mouse_new模块不可用: {e}")
        return False
    
    print("🎯 模拟游戏中的瞄准场景:")
    print("   1. 检测到敌人头部")
    print("   2. 快速丝滑移动到目标")
    print("   3. 模拟连续跟踪移动")
    print()
    
    response = input("是否进行游戏场景测试？这会移动你的鼠标 (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("跳过游戏场景测试")
        return True
    
    # 获取起始位置
    start_x, start_y = mouse_new.get_position()
    
    # 模拟敌人头部位置序列（模拟移动的敌人）
    enemy_positions = [
        (start_x + 80, start_y - 30),   # 右上
        (start_x + 60, start_y - 20),   # 移动中
        (start_x + 40, start_y - 10),   # 继续移动
        (start_x + 20, start_y),        # 接近中心
        (start_x, start_y + 10),        # 穿过中心
        (start_x - 20, start_y + 20),   # 左下方向
        (start_x - 40, start_y + 30),   # 继续左下
    ]
    
    print("🚀 开始模拟瞄准序列...")
    
    for i, (target_x, target_y) in enumerate(enemy_positions, 1):
        print(f"🎯 目标 {i}: ({target_x}, {target_y})")
        
        try:
            # 使用快速丝滑移动（模拟头部瞄准）
            mouse_new.move(
                target_x, 
                target_y, 
                absolute=True, 
                duration=0.06,  # 60ms头部瞄准时长
                steps_per_second=240.0
            )
            
            # 短暂停顿（模拟瞄准确认）
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ 移动失败: {e}")
            break
    
    print("✅ 瞄准序列完成")
    
    # 恢复原始位置
    time.sleep(0.5)
    mouse_new.move(start_x, start_y, absolute=True, duration=0.1)
    print("🔄 已恢复到原始位置")
    
    return True

def explain_smooth_movement():
    """解释丝滑移动原理"""
    print("="*60)
    print("🧠 丝滑移动原理解释")
    print("="*60)
    print()
    print("📋 问题分析:")
    print("   - 之前的移动：每次AI检测都触发一次瞬间移动")
    print("   - 结果：鼠标'一卡一卡'地移动到目标")
    print("   - 原因：没有使用移动动画，每次都是瞬移")
    print()
    print("🔧 丝滑移动解决方案:")
    print("   - 使用mouse_new.move()的duration参数")
    print("   - duration>0时，鼠标会平滑移动到目标")
    print("   - steps_per_second控制移动帧率")
    print()
    print("⚙️ 关键参数:")
    print("   - duration: 移动持续时间")
    print("     * 0.06s = 头部目标（快速精准）")
    print("     * 0.08s = 身体目标（平衡）")
    print("     * 0.10s+ = 远距离移动（超丝滑）")
    print()
    print("   - steps_per_second: 移动帧率")
    print("     * 120 FPS = 标准流畅")
    print("     * 240 FPS = 高流畅度")
    print("     * 300+ FPS = 极致流畅")
    print()
    print("🎯 效果对比:")
    print("   - 旧方式：目标(100,200) -> 瞬移 -> 到达")
    print("   - 新方式：目标(100,200) -> 80ms平滑移动 -> 到达")
    print()
    print("✅ 优势:")
    print("   - 移动看起来自然丝滑")
    print("   - 兼容Raw Input游戏")
    print("   - 可调节移动速度")
    print("   - 减少移动抖动")

def main():
    """主测试函数"""
    print("="*60)
    print("🎯 丝滑移动测试工具")
    print("="*60)
    print()
    print("🎮 针对'一卡一卡'移动问题的测试")
    print("💡 验证mouse_new的duration参数效果")
    print()
    
    while True:
        print("请选择测试:")
        print("1. 解释丝滑移动原理")
        print("2. 测试不同移动方式")
        print("3. 模拟游戏瞄准场景")
        print("4. 退出")
        print()
        
        try:
            choice = input("请输入选项 (1-4): ").strip()
            
            if choice == '1':
                explain_smooth_movement()
            elif choice == '2':
                test_smooth_movement()
            elif choice == '3':
                test_gaming_scenario()
            elif choice == '4':
                print("👋 再见！")
                break
            else:
                print("❌ 无效选项，请输入1-4")
                
        except KeyboardInterrupt:
            print("\n👋 用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")
        
        print("\n" + "-"*60 + "\n")

if __name__ == "__main__":
    main()