#!/usr/bin/env python3
"""
丝滑移动设置工具
调整mouse_new的移动参数以获得最佳体验
"""

import configparser
import os

def show_current_settings():
    """显示当前丝滑移动设置"""
    config_path = "config.ini"
    if not os.path.exists(config_path):
        print("❌ 找不到配置文件")
        return
    
    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # 读取丝滑移动相关设置
        move_duration = config.get('DEFAULT', 'mouse_move_duration', fallback='0.08')
        head_duration = config.get('DEFAULT', 'mouse_head_duration', fallback='0.06')
        steps_per_second = config.get('DEFAULT', 'mouse_steps_per_second', fallback='240.0')
        move_threshold = config.get('DEFAULT', 'mouse_move_threshold', fallback='8')
        debounce_time = config.get('DEFAULT', 'mouse_debounce_time', fallback='0.05')
        min_move_distance = config.get('DEFAULT', 'min_move_distance', fallback='3')
        
        print("📋 当前丝滑移动设置:")
        print(f"   身体目标移动时长: {move_duration}s ({float(move_duration)*1000:.0f}ms)")
        print(f"   头部目标移动时长: {head_duration}s ({float(head_duration)*1000:.0f}ms)")
        print(f"   移动帧率: {steps_per_second} FPS")
        print(f"   移动阈值: {move_threshold}px")
        print(f"   防抖时间: {debounce_time}s ({float(debounce_time)*1000:.0f}ms)")
        print(f"   最小移动距离: {min_move_distance}px")
        
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")

def update_smooth_settings():
    """更新丝滑移动设置"""
    print("🎯 丝滑移动参数调整")
    print("="*50)
    print()
    print("📋 参数说明:")
    print("1. 移动时长：控制移动的丝滑程度")
    print("   - 更长 = 更丝滑但稍慢")
    print("   - 更短 = 更快但可能不够平滑")
    print()
    print("2. 移动阈值：防止微小抖动")
    print("   - 更高 = 减少抖动但可能错过小调整")
    print("   - 更低 = 更敏感但可能抖动")
    print()
    print("3. 防抖时间：避免频繁移动")
    print("   - 更长 = 更稳定但响应慢")
    print("   - 更短 = 更敏感但可能抖动")
    print()
    
    try:
        # 获取用户输入
        print("请输入新的参数值（直接按Enter保持当前值）:")
        print()
        
        body_duration = input("身体目标移动时长 (秒，推荐0.06-0.12): ").strip()
        head_duration = input("头部目标移动时长 (秒，推荐0.04-0.08): ").strip()
        steps_fps = input("移动帧率 (FPS，推荐120-300): ").strip()
        move_threshold = input("移动阈值 (像素，推荐5-15): ").strip()
        debounce_time = input("防抖时间 (秒，推荐0.02-0.08): ").strip()
        min_distance = input("最小移动距离 (像素，推荐2-5): ").strip()
        
        # 读取配置文件
        config_path = "config.ini"
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path, encoding='utf-8')
        
        if 'DEFAULT' not in config:
            config.add_section('DEFAULT')
        
        # 更新配置
        if body_duration:
            config['DEFAULT']['mouse_move_duration'] = str(float(body_duration))
        if head_duration:
            config['DEFAULT']['mouse_head_duration'] = str(float(head_duration))
        if steps_fps:
            config['DEFAULT']['mouse_steps_per_second'] = str(float(steps_fps))
        if move_threshold:
            config['DEFAULT']['mouse_move_threshold'] = str(int(float(move_threshold)))
        if debounce_time:
            config['DEFAULT']['mouse_debounce_time'] = str(float(debounce_time))
        if min_distance:
            config['DEFAULT']['min_move_distance'] = str(int(float(min_distance)))
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print()
        print("✅ 配置已更新")
        print("🔄 请重启aimbot以应用新设置")
        
    except ValueError:
        print("❌ 输入格式错误，请输入数字")
    except Exception as e:
        print(f"❌ 更新失败: {e}")

def preset_configs():
    """预设配置"""
    print("🎯 丝滑移动预设配置")
    print("="*50)
    print()
    print("请选择预设:")
    print("1. 极速模式 - 最快响应，轻微抖动")
    print("2. 平衡模式 - 速度与平滑的平衡（推荐）")
    print("3. 丝滑模式 - 最平滑移动，稍慢响应")
    print("4. 精准模式 - 高精度，适合远距离")
    print("5. 自定义模式 - 手动调整参数")
    print()
    
    try:
        choice = input("请选择 (1-5): ").strip()
        
        presets = {
            '1': {  # 极速模式
                'mouse_move_duration': '0.04',
                'mouse_head_duration': '0.03',
                'mouse_steps_per_second': '300.0',
                'mouse_move_threshold': '5',
                'mouse_debounce_time': '0.02',
                'min_move_distance': '2'
            },
            '2': {  # 平衡模式（推荐）
                'mouse_move_duration': '0.08',
                'mouse_head_duration': '0.06',
                'mouse_steps_per_second': '240.0',
                'mouse_move_threshold': '8',
                'mouse_debounce_time': '0.05',
                'min_move_distance': '3'
            },
            '3': {  # 丝滑模式
                'mouse_move_duration': '0.12',
                'mouse_head_duration': '0.09',
                'mouse_steps_per_second': '180.0',
                'mouse_move_threshold': '12',
                'mouse_debounce_time': '0.08',
                'min_move_distance': '4'
            },
            '4': {  # 精准模式
                'mouse_move_duration': '0.10',
                'mouse_head_duration': '0.08',
                'mouse_steps_per_second': '200.0',
                'mouse_move_threshold': '6',
                'mouse_debounce_time': '0.06',
                'min_move_distance': '2'
            }
        }
        
        if choice == '5':
            update_smooth_settings()
            return
        elif choice in presets:
            preset = presets[choice]
            
            # 应用预设
            config_path = "config.ini"
            config = configparser.ConfigParser()
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
            
            if 'DEFAULT' not in config:
                config.add_section('DEFAULT')
            
            for key, value in preset.items():
                config['DEFAULT'][key] = value
            
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            mode_names = {
                '1': '极速模式',
                '2': '平衡模式',
                '3': '丝滑模式',
                '4': '精准模式'
            }
            
            print(f"✅ 已应用 {mode_names[choice]}")
            print("🔄 请重启aimbot以应用新设置")
        else:
            print("❌ 无效选择")
            
    except Exception as e:
        print(f"❌ 应用预设失败: {e}")

def main():
    """主菜单"""
    while True:
        print("\n" + "="*60)
        print("🎯 丝滑移动设置工具")
        print("="*60)
        print()
        print("🎮 针对'一卡一卡'移动问题的解决方案")
        print("💡 使用mouse_new的duration参数实现丝滑移动")
        print()
        print("请选择操作:")
        print("1. 查看当前设置")
        print("2. 使用预设配置（推荐）")
        print("3. 自定义参数调整")
        print("4. 退出")
        print()
        
        try:
            choice = input("请输入选项 (1-4): ").strip()
            
            if choice == '1':
                show_current_settings()
            elif choice == '2':
                preset_configs()
            elif choice == '3':
                update_smooth_settings()
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