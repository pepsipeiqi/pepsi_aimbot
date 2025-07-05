"""
简化版 mouse_new 控制器 - 最小依赖版本

这个版本去除了对Windows特定库和supervision的依赖，
专注于核心的鼠标移动逻辑测试。
"""

import sys
import os
import time
import math

# 添加 mouse_new 到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'mouse_new'))

try:
    import mouse
    MOUSE_NEW_AVAILABLE = True
    print("✅ mouse_new library loaded successfully")
except Exception as e:
    print(f"❌ Failed to load mouse_new library: {e}")
    MOUSE_NEW_AVAILABLE = False

class SimpleMouseController:
    """简化的鼠标控制器 - 最小依赖版本"""
    
    def __init__(self):
        # 默认配置（避免依赖config.ini）
        self.screen_width = 380
        self.screen_height = 380
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        
        self.dpi = 1100
        self.sensitivity = 3.0
        self.fov_x = 40
        self.fov_y = 40
        
        self.body_y_offset = 0.1
        self.aim_threshold = 10
        self.max_single_move = 200
        
        # 状态
        self.target_locked = False
        self.lock_start_time = 0
        self.lock_timeout = 2.0
        
        print(f"🎯 SimpleMouseController initialized")
        print(f"   Screen: {self.screen_width}x{self.screen_height}")
        print(f"   Center: ({self.center_x}, {self.center_y})")
        print(f"   DPI: {self.dpi}, Sensitivity: {self.sensitivity}")
    
    def process_target(self, target_x, target_y, target_w=0, target_h=0, target_cls=0):
        """处理目标（简化版）"""
        if not MOUSE_NEW_AVAILABLE:
            print("❌ mouse_new not available, skipping movement")
            return False
        
        # 应用身体偏移
        if target_cls != 7:  # 不是头部
            target_y += target_h * self.body_y_offset
        
        # 计算偏移
        offset_x = target_x - self.center_x
        offset_y = target_y - self.center_y
        distance = math.sqrt(offset_x**2 + offset_y**2)
        
        target_type = "HEAD" if target_cls == 7 else "BODY"
        print(f"🎯 Processing {target_type} target: ({target_x:.1f}, {target_y:.1f}), distance={distance:.1f}px")
        
        # 检查是否已经锁定
        if distance <= self.aim_threshold:
            if not self.target_locked:
                self.target_locked = True
                self.lock_start_time = time.time()
                print(f"🔒 Target locked! Distance: {distance:.1f}px")
            return True
        
        # 需要移动
        print(f"📐 Need to move: offset=({offset_x:.1f}, {offset_y:.1f})")
        return self.move_to_target(offset_x, offset_y, target_cls)
    
    def move_to_target(self, offset_x, offset_y, target_cls):
        """移动到目标位置"""
        if not MOUSE_NEW_AVAILABLE:
            print("❌ mouse_new not available, cannot move")
            return False
        
        try:
            # 限制单次移动距离
            distance = math.sqrt(offset_x**2 + offset_y**2)
            if distance > self.max_single_move:
                scale = self.max_single_move / distance
                offset_x *= scale
                offset_y *= scale
                print(f"🔧 Movement scaled: {distance:.1f}px → {self.max_single_move}px")
            
            # 转换为鼠标移动
            mouse_x, mouse_y = self.convert_pixel_to_mouse(offset_x, offset_y)
            
            print(f"🎯 Moving: pixel_offset=({offset_x:.1f}, {offset_y:.1f}) → mouse_move=({mouse_x:.1f}, {mouse_y:.1f})")
            
            # 执行移动（使用mouse_new）
            mouse.move(mouse_x, mouse_y, absolute=False)
            
            # 重置锁定状态
            self.target_locked = False
            
            return True
            
        except Exception as e:
            print(f"❌ Mouse movement failed: {e}")
            return False
    
    def convert_pixel_to_mouse(self, pixel_x, pixel_y):
        """像素到鼠标移动转换"""
        degrees_per_pixel_x = self.fov_x / self.screen_width
        degrees_per_pixel_y = self.fov_y / self.screen_height
        
        degrees_x = pixel_x * degrees_per_pixel_x
        degrees_y = pixel_y * degrees_per_pixel_y
        
        mouse_x = (degrees_x / 360) * (self.dpi * (1 / self.sensitivity))
        mouse_y = (degrees_y / 360) * (self.dpi * (1 / self.sensitivity))
        
        return mouse_x, mouse_y
    
    def handle_no_target(self):
        """处理无目标情况"""
        if self.target_locked:
            if time.time() - self.lock_start_time > self.lock_timeout:
                self.target_locked = False
                print("🔄 Target lock timeout - resetting")
    
    def test_movement(self, test_safe=True):
        """测试鼠标移动功能"""
        if not MOUSE_NEW_AVAILABLE:
            print("❌ Cannot test movement - mouse_new not available")
            return False
        
        if test_safe:
            print("🔍 Testing safe movement (no actual mouse movement)")
            # 只测试转换逻辑
            test_cases = [
                (10, 10, "Small movement"),
                (50, 30, "Medium movement"),
                (100, 100, "Large movement"),
            ]
            
            for pixel_x, pixel_y, description in test_cases:
                mouse_x, mouse_y = self.convert_pixel_to_mouse(pixel_x, pixel_y)
                print(f"  {description}: pixel({pixel_x}, {pixel_y}) → mouse({mouse_x:.2f}, {mouse_y:.2f})")
            
            print("✅ Safe movement test completed")
            return True
        else:
            print("⚠️  Real movement test - this will move your mouse!")
            try:
                # 获取当前位置
                start_pos = mouse.get_position()
                print(f"📍 Start position: {start_pos}")
                
                # 小幅移动
                print("🔄 Moving 5px right...")
                mouse.move(5, 0, absolute=False)
                time.sleep(0.5)
                
                # 移回
                print("🔄 Moving back...")
                mouse.move(-5, 0, absolute=False)
                time.sleep(0.5)
                
                end_pos = mouse.get_position()
                print(f"📍 End position: {end_pos}")
                
                error = ((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)**0.5
                print(f"✅ Movement precision: {error:.2f}px error")
                
                return True
                
            except Exception as e:
                print(f"❌ Real movement test failed: {e}")
                return False

# 创建全局实例
simple_mouse_controller = SimpleMouseController()

if __name__ == "__main__":
    print("🚀 Testing SimpleMouseController")
    print("="*40)
    
    # 测试基础功能
    controller = SimpleMouseController()
    
    # 测试安全移动（只计算，不移动鼠标）
    controller.test_movement(test_safe=True)
    
    # 测试目标处理
    print("\n🎯 Testing target processing...")
    test_targets = [
        (200, 170, 50, 80, 0, "Body target slightly right"),
        (190, 190, 30, 40, 7, "Head target at center"),
        (150, 150, 40, 60, 0, "Body target left-up"),
    ]
    
    for target_x, target_y, target_w, target_h, target_cls, description in test_targets:
        print(f"\nTesting: {description}")
        controller.process_target(target_x, target_y, target_w, target_h, target_cls)
    
    print("\n✅ All tests completed!")
    
    # 询问是否进行真实移动测试
    real_test = input("\n🔴 Perform real mouse movement test? (y/N): ")
    if real_test.lower() == 'y':
        controller.test_movement(test_safe=False)
    
    print("\n🏁 Testing finished!")