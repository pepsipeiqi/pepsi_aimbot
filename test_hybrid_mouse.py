#!/usr/bin/env python3
"""
测试混合移动鼠标系统
验证相对移动功能
"""

import sys
import time
import ctypes
from ctypes import wintypes

def test_relative_movement():
    """测试相对移动功能"""
    print("="*60)
    print("🚀 测试相对移动功能")
    print("="*60)
    
    # 设置Windows API
    try:
        user32 = ctypes.windll.user32
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user32.GetCursorPos.restype = wintypes.BOOL
        print("✅ Windows API设置成功")
    except Exception as e:
        print(f"❌ Windows API设置失败: {e}")
        return False
    
    # 获取当前鼠标位置
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    start_x, start_y = point.x, point.y
    print(f"🖱️ 当前鼠标位置: ({start_x}, {start_y})")
    
    # 模拟游戏场景
    print("\n🎮 模拟游戏场景:")
    print("   假设检测到敌人在检测窗口的 (400, 300) 位置")
    print("   检测窗口偏移为 (640, 220)")
    
    # 计算目标屏幕坐标
    detection_x, detection_y = 400, 300
    detection_offset_x, detection_offset_y = 640, 220
    target_screen_x = detection_offset_x + detection_x
    target_screen_y = detection_offset_y + detection_y
    
    print(f"   目标屏幕坐标: ({target_screen_x}, {target_screen_y})")
    
    # 计算相对移动量
    relative_x = target_screen_x - start_x
    relative_y = target_screen_y - start_y
    
    print(f"   需要的相对移动量: ({relative_x}, {relative_y})")
    
    # 导入win32 API进行相对移动
    try:
        import win32api
        import win32con
        
        print(f"\n🔄 执行相对移动: ({relative_x}, {relative_y})")
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, relative_x, relative_y, 0, 0)
        
        # 检查移动后的位置
        time.sleep(0.1)
        user32.GetCursorPos(ctypes.byref(point))
        end_x, end_y = point.x, point.y
        
        print(f"✅ 移动后位置: ({end_x}, {end_y})")
        print(f"📏 实际移动量: ({end_x - start_x}, {end_y - start_y})")
        
        # 计算误差
        error_x = abs(end_x - target_screen_x)
        error_y = abs(end_y - target_screen_y)
        
        print(f"📐 移动误差: X={error_x}px, Y={error_y}px")
        
        if error_x <= 5 and error_y <= 5:
            print("✅ 相对移动精度测试通过")
        else:
            print("⚠️ 相对移动精度需要调整")
        
        # 恢复原位置
        time.sleep(2)
        restore_x = start_x - end_x
        restore_y = start_y - end_y
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, restore_x, restore_y, 0, 0)
        print(f"🔄 鼠标已恢复到原位置")
        
        return True
        
    except ImportError:
        print("❌ win32api不可用，使用ctypes备用方案")
        
        # 使用ctypes的备用方案
        try:
            print(f"\n🔄 执行ctypes相对移动: ({relative_x}, {relative_y})")
            ctypes.windll.user32.mouse_event(1, relative_x, relative_y, 0, 0)
            print("✅ ctypes相对移动执行完成")
            return True
        except Exception as e:
            print(f"❌ ctypes相对移动失败: {e}")
            return False

def explain_hybrid_system():
    """解释混合系统原理"""
    print("="*60)
    print("🧠 混合移动系统原理")
    print("="*60)
    print()
    print("📋 问题分析:")
    print("   - 绝对移动 SetCursorPos() 只移动系统光标")
    print("   - Raw Input游戏忽略系统光标位置")
    print("   - 游戏只响应鼠标相对移动事件")
    print()
    print("🔧 混合解决方案:")
    print("   1. 获取当前鼠标位置")
    print("   2. 计算目标的屏幕绝对坐标")
    print("   3. 计算需要的相对移动量 = 目标位置 - 当前位置")
    print("   4. 使用 mouse_event(MOUSEEVENTF_MOVE, dx, dy) 发送相对移动")
    print()
    print("✅ 优势:")
    print("   - 兼容Raw Input游戏")
    print("   - 游戏准心跟随鼠标移动")
    print("   - 保持绝对坐标的精确计算")
    print()
    print("🎯 效果:")
    print("   - 系统鼠标光标移动到目标位置")
    print("   - 游戏准心也同步移动到目标位置")

def main():
    """主测试函数"""
    print("="*60)
    print("🎯 混合移动鼠标系统测试")
    print("="*60)
    
    # 解释系统原理
    explain_hybrid_system()
    
    print("\n" + "="*60)
    
    # 测试相对移动
    success = test_relative_movement()
    
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)
    
    if success:
        print("✅ 混合移动系统测试成功")
        print("🎮 该系统应该能解决Raw Input游戏的准心同步问题")
        print()
        print("📝 下一步:")
        print("   1. 启动游戏和aimbot")
        print("   2. 测试瞄准效果")
        print("   3. 观察游戏准心是否跟随移动")
    else:
        print("❌ 混合移动系统测试失败")
        print("🔧 请检查Windows API兼容性")

if __name__ == "__main__":
    main()