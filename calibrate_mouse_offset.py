#!/usr/bin/env python3
"""
鼠标偏移校准工具
用于解决检测窗口与游戏窗口坐标不匹配的问题
"""

import sys
import time
import math
import ctypes
from ctypes import wintypes

# 添加项目路径
sys.path.append('.')

def get_mouse_position():
    """获取当前鼠标位置"""
    try:
        user32 = ctypes.windll.user32
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)
    except:
        return (0, 0)

def set_mouse_position(x, y):
    """设置鼠标位置"""
    try:
        user32 = ctypes.windll.user32
        return user32.SetCursorPos(x, y)
    except:
        return False

def calibrate_mouse_offset():
    """校准鼠标偏移"""
    print("="*80)
    print("🎯 鼠标偏移校准工具")
    print("="*80)
    print()
    print("📋 校准步骤:")
    print("1. 确保游戏窗口已打开并处于前台")
    print("2. 手动将鼠标移动到游戏准星的确切位置")
    print("3. 按Enter记录游戏准星位置")
    print("4. 工具会模拟AI检测到敌人并移动鼠标")
    print("5. 观察偏移差异并计算校正值")
    print()
    
    # 步骤1：记录游戏准星位置
    input("🎯 请将鼠标移动到游戏准星的确切位置，然后按Enter...")
    crosshair_x, crosshair_y = get_mouse_position()
    print(f"✅ 游戏准星位置已记录: ({crosshair_x}, {crosshair_y})")
    print()
    
    # 步骤2：模拟AI检测窗口设置
    print("🔧 当前AI检测窗口设置:")
    
    # 模拟当前配置（需要根据实际配置调整）
    detection_window_width = 640
    detection_window_height = 640
    primary_screen_width = 1920
    primary_screen_height = 1080
    
    # 计算当前的检测窗口偏移
    current_detection_left = int(primary_screen_width / 2 - detection_window_width / 2)
    current_detection_top = int(primary_screen_height / 2 - detection_window_height / 2)
    
    print(f"   检测窗口尺寸: {detection_window_width} x {detection_window_height}")
    print(f"   当前计算的偏移: ({current_detection_left}, {current_detection_top})")
    print()
    
    # 步骤3：计算检测窗口中心对应的屏幕坐标
    detection_center_x = detection_window_width / 2
    detection_center_y = detection_window_height / 2
    
    # 当前系统计算的屏幕坐标
    current_screen_x = current_detection_left + detection_center_x
    current_screen_y = current_detection_top + detection_center_y
    
    print(f"🧮 坐标计算:")
    print(f"   检测窗口中心: ({detection_center_x}, {detection_center_y})")
    print(f"   当前系统计算的屏幕坐标: ({current_screen_x}, {current_screen_y})")
    print(f"   实际游戏准星位置: ({crosshair_x}, {crosshair_y})")
    print()
    
    # 步骤4：计算偏移差异
    offset_x = crosshair_x - current_screen_x
    offset_y = crosshair_y - current_screen_y
    offset_distance = math.sqrt(offset_x**2 + offset_y**2)
    
    print(f"📏 偏移分析:")
    print(f"   X轴偏移: {offset_x:.1f}px")
    print(f"   Y轴偏移: {offset_y:.1f}px")
    print(f"   总偏移距离: {offset_distance:.1f}px")
    print()
    
    if offset_distance < 10:
        print("✅ 偏移很小，系统基本准确")
        return
    
    # 步骤5：提供校正方案
    print("🔧 校正方案:")
    print()
    
    # 方案1：调整检测窗口偏移
    corrected_detection_left = current_detection_left + offset_x
    corrected_detection_top = current_detection_top + offset_y
    
    print("📝 方案1 - 修改mouse_absolute_simple.py中的偏移计算:")
    print(f"   将detection_window_left调整为: {corrected_detection_left:.0f}")
    print(f"   将detection_window_top调整为: {corrected_detection_top:.0f}")
    print()
    print("   在update_detection_window_offset函数中添加校正:")
    print(f"   self.detection_window_left += {offset_x:.0f}  # X轴校正")
    print(f"   self.detection_window_top += {offset_y:.0f}   # Y轴校正")
    print()
    
    # 方案2：配置文件校正
    print("📝 方案2 - 在配置文件中添加偏移校正:")
    print("   在config.ini中添加:")
    print(f"   mouse_offset_x = {offset_x:.0f}")
    print(f"   mouse_offset_y = {offset_y:.0f}")
    print()
    
    # 步骤6：验证校正
    print("🧪 验证校正效果:")
    input("按Enter测试校正后的鼠标移动...")
    
    # 模拟移动到校正后的位置
    test_screen_x = current_screen_x + offset_x
    test_screen_y = current_screen_y + offset_y
    
    print(f"📍 移动鼠标到校正后的位置: ({test_screen_x:.0f}, {test_screen_y:.0f})")
    set_mouse_position(int(test_screen_x), int(test_screen_y))
    
    time.sleep(1)
    
    print()
    print("❓ 校正后鼠标是否准确对准了游戏准星？")
    print("   如果是，请应用上述校正方案")
    print("   如果否，请重新运行校准工具")
    
    # 恢复原始位置
    time.sleep(2)
    set_mouse_position(crosshair_x, crosshair_y)
    print("🔄 鼠标已恢复到原始位置")

def main():
    """主函数"""
    try:
        calibrate_mouse_offset()
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断校准")
    except Exception as e:
        print(f"\n\n❌ 校准过程中出错: {e}")
    
    print("\n" + "="*80)
    print("🎯 校准工具结束")
    print("="*80)

if __name__ == "__main__":
    main()