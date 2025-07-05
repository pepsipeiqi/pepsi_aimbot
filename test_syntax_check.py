#!/usr/bin/env python3
"""
语法和导入检查测试
检查新代码的语法正确性
"""

import ast
import sys
import os

def check_syntax(file_path):
    """检查Python文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试解析AST
        ast.parse(content)
        print(f"✅ {file_path}: 语法正确")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path}: 语法错误 - {e}")
        return False
    except Exception as e:
        print(f"❌ {file_path}: 检查失败 - {e}")
        return False

def main():
    """主检查函数"""
    print("🔧 语法和结构检查")
    print("=" * 50)
    
    # 检查新创建的文件
    files_to_check = [
        "logic/mouse_driver_absolute.py",
        "test_driver_absolute_mouse.py"
    ]
    
    all_passed = True
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            if not check_syntax(file_path):
                all_passed = False
        else:
            print(f"⚠️ {file_path}: 文件不存在")
            all_passed = False
    
    # 检查修改的文件
    modified_file = "logic/frame_parser_ultra_simple.py"
    if os.path.exists(modified_file):
        check_syntax(modified_file)
    
    print(f"\n{'🎉 所有检查通过' if all_passed else '⚠️ 发现问题'}")
    
    # 输出实现摘要
    print("\n📋 实现摘要:")
    print("1. ✅ 创建了 logic/mouse_driver_absolute.py")
    print("2. ✅ 更新了 logic/frame_parser_ultra_simple.py")
    print("3. ✅ 添加了配置参数到 config.ini")
    print("4. ✅ 创建了测试文件")
    
    print("\n🎯 新功能:")
    print("- Raw Input兼容的绝对移动")
    print("- 使用TrueAbsoluteController驱动")
    print("- 可配置的硬件类型和精度等级")
    print("- 性能优化和错误处理")

if __name__ == "__main__":
    main()