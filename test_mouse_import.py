#!/usr/bin/env python3
"""
测试鼠标模块导入和功能
验证mouse_new导入是否正常
"""

import sys
import os

def test_mouse_import():
    """测试鼠标模块导入"""
    print("="*60)
    print("🔧 测试鼠标模块导入")
    print("="*60)
    
    # 方法1：测试安全导入
    print("📦 方法1: 使用importlib安全导入")
    try:
        import importlib.util
        
        # 构建路径
        mouse_new_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_new')
        mouse_init_path = os.path.join(mouse_new_path, "mouse", "__init__.py")
        
        print(f"   mouse_new路径: {mouse_new_path}")
        print(f"   __init__.py路径: {mouse_init_path}")
        print(f"   路径存在: {os.path.exists(mouse_init_path)}")
        
        if os.path.exists(mouse_init_path):
            # 使用importlib导入
            mouse_spec = importlib.util.spec_from_file_location(
                "mouse_new_module", 
                mouse_init_path
            )
            mouse_new = importlib.util.module_from_spec(mouse_spec)
            mouse_spec.loader.exec_module(mouse_new)
            
            # 检查函数
            has_get_position = hasattr(mouse_new, 'get_position')
            has_move = hasattr(mouse_new, 'move')
            
            print(f"   ✅ 导入成功")
            print(f"   get_position函数: {has_get_position}")
            print(f"   move函数: {has_move}")
            
            if has_get_position and has_move:
                print("   ✅ 所有必要函数都存在")
                
                # 测试函数调用
                try:
                    pos = mouse_new.get_position()
                    print(f"   🖱️ 当前鼠标位置: {pos}")
                    print("   ✅ get_position函数工作正常")
                except Exception as e:
                    print(f"   ❌ get_position函数调用失败: {e}")
                
                return True
            else:
                print("   ❌ 缺少必要函数")
                return False
        else:
            print("   ❌ mouse_new模块文件不存在")
            return False
            
    except Exception as e:
        print(f"   ❌ 安全导入失败: {e}")
    
    # 方法2：测试传统导入
    print("\n📦 方法2: 传统导入方式")
    try:
        # 添加路径
        mouse_new_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mouse_new')
        if mouse_new_path not in sys.path:
            sys.path.insert(0, mouse_new_path)
        
        # 清除缓存
        if 'mouse' in sys.modules:
            del sys.modules['mouse']
        
        import mouse as mouse_new
        
        # 检查函数
        has_get_position = hasattr(mouse_new, 'get_position')
        has_move = hasattr(mouse_new, 'move')
        
        print(f"   ✅ 传统导入成功")
        print(f"   get_position函数: {has_get_position}")
        print(f"   move函数: {has_move}")
        
        if has_get_position:
            pos = mouse_new.get_position()
            print(f"   🖱️ 当前鼠标位置: {pos}")
            return True
        else:
            print("   ❌ 缺少get_position函数")
            return False
            
    except Exception as e:
        print(f"   ❌ 传统导入失败: {e}")
    
    return False

def test_windows_api_backup():
    """测试Windows API备用方案"""
    print("\n🔧 测试Windows API备用方案")
    print("-"*60)
    
    try:
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        
        # 测试获取位置
        point = wintypes.POINT()
        result = user32.GetCursorPos(ctypes.byref(point))
        
        if result:
            print(f"   ✅ GetCursorPos成功: ({point.x}, {point.y})")
        else:
            print("   ❌ GetCursorPos失败")
            return False
        
        # 测试设置位置（移动1像素然后恢复）
        original_x, original_y = point.x, point.y
        test_x, test_y = original_x + 1, original_y + 1
        
        result = user32.SetCursorPos(test_x, test_y)
        if result:
            print(f"   ✅ SetCursorPos测试成功")
            
            # 恢复原位置
            user32.SetCursorPos(original_x, original_y)
            print(f"   ✅ 位置已恢复")
            return True
        else:
            print("   ❌ SetCursorPos失败")
            return False
            
    except Exception as e:
        print(f"   ❌ Windows API测试失败: {e}")
        return False

def test_mouse_pure_module():
    """测试mouse_pure模块"""
    print("\n🔧 测试mouse_pure模块")
    print("-"*60)
    
    try:
        # 添加项目路径
        sys.path.append('.')
        
        from logic.mouse_pure import mouse
        
        print("   ✅ mouse_pure模块导入成功")
        
        # 测试获取位置
        pos = mouse.get_current_mouse_position()
        print(f"   🖱️ 获取位置: {pos}")
        
        if pos != (0, 0):
            print("   ✅ 位置获取正常")
            return True
        else:
            print("   ⚠️ 位置为(0,0)，可能有问题")
            return False
            
    except Exception as e:
        print(f"   ❌ mouse_pure模块测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 鼠标模块导入诊断工具")
    print("解决 'module mouse has no attribute get_position' 问题")
    print()
    
    # 测试mouse_new导入
    mouse_new_ok = test_mouse_import()
    
    # 测试Windows API备用
    windows_api_ok = test_windows_api_backup()
    
    # 测试完整模块
    mouse_pure_ok = test_mouse_pure_module()
    
    print("\n" + "="*60)
    print("📋 测试结果总结")
    print("="*60)
    print(f"mouse_new模块: {'✅ 正常' if mouse_new_ok else '❌ 有问题'}")
    print(f"Windows API备用: {'✅ 正常' if windows_api_ok else '❌ 有问题'}")
    print(f"mouse_pure模块: {'✅ 正常' if mouse_pure_ok else '❌ 有问题'}")
    print()
    
    if mouse_new_ok:
        print("🎉 mouse_new模块工作正常，应该能使用丝滑移动")
    elif windows_api_ok:
        print("⚠️ mouse_new有问题，但Windows API备用方案可用")
        print("   系统会使用瞬间移动而不是丝滑移动")
    else:
        print("❌ 所有方案都有问题，需要进一步诊断")
    
    print()
    print("🔧 如果mouse_new有问题，建议:")
    print("1. 检查mouse_new目录是否完整")
    print("2. 重启aimbot程序")
    print("3. 系统会自动使用Windows API备用方案")

if __name__ == "__main__":
    main()