# -*- coding: utf-8 -*-
"""
分辨率和DPI对鼠标移动影响的测试脚本
"""
import mouse
import time
import math

def get_screen_info():
    """获取屏幕信息"""
    try:
        import tkinter as tk
        root = tk.Tk()
        
        # 获取屏幕分辨率
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # 获取DPI
        dpi = root.winfo_fpixels('1i')
        
        root.destroy()
        
        return screen_width, screen_height, dpi
    except Exception as e:
        print(f"无法获取屏幕信息: {e}")
        return 1920, 1080, 96  # 默认值

def test_resolution_boundaries():
    """测试分辨率边界"""
    width, height, dpi = get_screen_info()
    
    print(f"当前屏幕信息:")
    print(f"分辨率: {width} x {height}")
    print(f"DPI: {dpi:.1f}")
    
    # 测试边界点
    test_points = [
        (0, 0, "左上角"),
        (width-1, 0, "右上角"),
        (0, height-1, "左下角"),
        (width-1, height-1, "右下角"),
        (width//2, height//2, "中心点"),
        (width, height, "超出边界"),  # 测试边界外
    ]
    
    print("\n边界测试:")
    for x, y, desc in test_points:
        try:
            mouse.move(x, y, absolute=True, duration=0)
            actual_x, actual_y = mouse.get_position()
            
            error_x = abs(x - actual_x)
            error_y = abs(y - actual_y)
            
            print(f"{desc}: 目标({x},{y}) -> 实际({actual_x},{actual_y}) | 误差: ({error_x},{error_y})")
            time.sleep(0.1)
        except Exception as e:
            print(f"{desc}: 移动失败 - {e}")

def test_precision_at_different_scales():
    """测试不同比例下的精度"""
    width, height, dpi = get_screen_info()
    
    # 测试不同比例的移动距离
    scales = [0.1, 0.25, 0.5, 0.75, 1.0]
    center = (width//2, height//2)
    
    print(f"\n不同比例精度测试 (基于 {width}x{height}):")
    
    for scale in scales:
        distance = int(min(width, height) * scale * 0.3)  # 30%的比例距离
        target_x = center[0] + distance
        target_y = center[1] + distance
        
        # 确保不超出边界
        target_x = min(target_x, width-1)
        target_y = min(target_y, height-1)
        
        # 移动到中心
        mouse.move(center[0], center[1], absolute=True, duration=0)
        time.sleep(0.05)
        
        # 执行测试移动
        mouse.move(target_x, target_y, absolute=True, duration=0.1)
        actual_x, actual_y = mouse.get_position()
        
        error = math.sqrt((target_x - actual_x)**2 + (target_y - actual_y)**2)
        error_percentage = (error / distance) * 100 if distance > 0 else 0
        
        print(f"比例 {scale:4.1f}: 距离{distance:4d}px -> 误差{error:6.2f}px ({error_percentage:5.2f}%)")

def test_different_movement_patterns():
    """测试不同移动模式在当前分辨率下的表现"""
    width, height, dpi = get_screen_info()
    
    print(f"\n移动模式测试 (分辨率: {width}x{height}):")
    
    patterns = [
        ("水平移动", [(width//4, height//2), (3*width//4, height//2)]),
        ("垂直移动", [(width//2, height//4), (width//2, 3*height//4)]),
        ("对角移动", [(width//4, height//4), (3*width//4, 3*height//4)]),
        ("小幅移动", [(width//2, height//2), (width//2 + 50, height//2 + 50)]),
        ("大幅移动", [(100, 100), (width-100, height-100)]),
    ]
    
    for pattern_name, (start, end) in patterns:
        # 移动到起始位置
        mouse.move(start[0], start[1], absolute=True, duration=0)
        time.sleep(0.05)
        
        # 执行移动
        start_time = time.perf_counter()
        mouse.move(end[0], end[1], absolute=True, duration=0.1)
        end_time = time.perf_counter()
        
        # 检查结果
        actual_x, actual_y = mouse.get_position()
        expected_distance = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        actual_distance = math.sqrt((actual_x - start[0])**2 + (actual_y - start[1])**2)
        error = math.sqrt((end[0] - actual_x)**2 + (end[1] - actual_y)**2)
        
        print(f"{pattern_name:8s}: 预期{expected_distance:6.1f}px, 实际{actual_distance:6.1f}px, 误差{error:5.2f}px, 耗时{(end_time-start_time)*1000:5.1f}ms")

def analyze_dpi_impact():
    """分析DPI对移动的影响"""
    width, height, dpi = get_screen_info()
    
    print(f"\nDPI影响分析:")
    print(f"当前DPI: {dpi:.1f}")
    print(f"DPI类别: ", end="")
    
    if dpi <= 100:
        print("标准DPI (≤100)")
    elif dpi <= 150:
        print("高DPI (100-150)")
    elif dpi <= 200:
        print("超高DPI (150-200)")
    else:
        print(f"极高DPI (>{200})")
    
    # 计算物理尺寸（英寸）
    physical_width = width / dpi
    physical_height = height / dpi
    
    print(f"屏幕物理尺寸: {physical_width:.1f}\" x {physical_height:.1f}\"")
    
    # 测试相同物理距离在不同DPI下的像素移动
    physical_distance_inch = 1.0  # 1英寸
    pixel_distance = int(physical_distance_inch * dpi)
    
    center = (width//2, height//2)
    target = (center[0] + pixel_distance, center[1])
    
    mouse.move(center[0], center[1], absolute=True, duration=0)
    time.sleep(0.05)
    mouse.move(target[0], target[1], absolute=True, duration=0.1)
    actual_x, actual_y = mouse.get_position()
    
    error = abs(target[0] - actual_x)
    print(f"1英寸移动测试: {pixel_distance}px -> 误差{error}px")

def comprehensive_resolution_test():
    """综合分辨率测试"""
    print("=" * 60)
    print("鼠标移动分辨率适应性测试")
    print("=" * 60)
    
    # 1. 获取和显示屏幕信息
    get_screen_info()
    
    # 2. 边界测试
    test_resolution_boundaries()
    
    # 3. 不同比例精度测试
    test_precision_at_different_scales()
    
    # 4. 移动模式测试
    test_different_movement_patterns()
    
    # 5. DPI影响分析
    analyze_dpi_impact()
    
    print("\n" + "=" * 60)
    print("测试完成")

if __name__ == "__main__":
    comprehensive_resolution_test()