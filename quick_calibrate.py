#!/usr/bin/env python3
"""
快速校准工具
通过配置文件快速调整鼠标偏移
"""

import configparser
import os

def quick_calibrate():
    """快速校准鼠标偏移"""
    print("="*60)
    print("🚀 快速鼠标偏移校准")
    print("="*60)
    print()
    print("📋 根据游戏测试观察到的偏移，设置校正值:")
    print()
    
    # 获取用户输入的偏移值
    print("🎯 请输入观察到的偏移值：")
    print("   (如果准星偏左，输入正值；偏右输入负值)")
    print("   (如果准星偏上，输入正值；偏下输入负值)")
    print()
    
    try:
        offset_x = float(input("X轴偏移 (像素): "))
        offset_y = float(input("Y轴偏移 (像素): "))
    except ValueError:
        print("❌ 输入无效，请输入数字")
        return
    
    print()
    print(f"📝 将设置偏移校正:")
    print(f"   X轴偏移: {offset_x}")
    print(f"   Y轴偏移: {offset_y}")
    print()
    
    # 读取配置文件
    config_path = "config.ini"
    if not os.path.exists(config_path):
        print(f"❌ 找不到配置文件: {config_path}")
        return
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # 确保有默认section
        if 'DEFAULT' not in config:
            config.add_section('DEFAULT')
        
        # 添加偏移配置
        config['DEFAULT']['mouse_offset_x'] = str(int(offset_x))
        config['DEFAULT']['mouse_offset_y'] = str(int(offset_y))
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print("✅ 配置已更新到 config.ini")
        print()
        print("🔄 请重启aimbot程序以应用新的偏移设置")
        print()
        print("📋 测试步骤:")
        print("1. 重启 python run.py")
        print("2. 进入游戏测试瞄准")
        print("3. 如果还有偏移，重新运行此校准工具")
        
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")

def show_current_settings():
    """显示当前偏移设置"""
    config_path = "config.ini"
    if not os.path.exists(config_path):
        print("❌ 找不到配置文件")
        return
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        offset_x = config.get('DEFAULT', 'mouse_offset_x', fallback='0')
        offset_y = config.get('DEFAULT', 'mouse_offset_y', fallback='0')
        
        print(f"📋 当前偏移设置:")
        print(f"   X轴偏移: {offset_x}")
        print(f"   Y轴偏移: {offset_y}")
        
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")

def reset_offset():
    """重置偏移为0"""
    config_path = "config.ini"
    if not os.path.exists(config_path):
        print("❌ 找不到配置文件")
        return
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        if 'DEFAULT' not in config:
            config.add_section('DEFAULT')
        
        config['DEFAULT']['mouse_offset_x'] = '0'
        config['DEFAULT']['mouse_offset_y'] = '0'
        
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print("✅ 偏移已重置为0")
        
    except Exception as e:
        print(f"❌ 重置失败: {e}")

def main():
    """主菜单"""
    while True:
        print("\n" + "="*60)
        print("🎯 鼠标偏移校准工具")
        print("="*60)
        print()
        print("请选择操作:")
        print("1. 查看当前偏移设置")
        print("2. 设置新的偏移值")
        print("3. 重置偏移为0")
        print("4. 退出")
        print()
        
        try:
            choice = input("请输入选项 (1-4): ").strip()
            
            if choice == '1':
                show_current_settings()
            elif choice == '2':
                quick_calibrate()
            elif choice == '3':
                reset_offset()
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

if __name__ == "__main__":
    main()