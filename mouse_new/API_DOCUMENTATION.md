# Mouse Library API Documentation

## 概述

这是Python Mouse库的完整API对接文档，提供跨平台的鼠标控制功能，支持Windows、Linux和macOS系统。

## 目录
1. [快速开始](#快速开始)
2. [安装](#安装)
3. [基础移动API](#基础移动api)
4. [点击操作API](#点击操作api)
5. [事件监听API](#事件监听api)
6. [高级功能API](#高级功能api)
7. [常量定义](#常量定义)
8. [错误处理](#错误处理)
9. [最佳实践](#最佳实践)
10. [完整示例](#完整示例)

---

## 快速开始

```python
import mouse

# 移动鼠标到屏幕中心
mouse.move(960, 540)

# 点击左键
mouse.click()

# 监听鼠标事件
mouse.on_click(lambda: print("鼠标被点击"))
```

---

## 安装

### 方式一：pip安装
```bash
pip install mouse
```

### 方式二：源码安装
```bash
git clone https://github.com/boppreh/mouse
cd mouse
python setup.py install
```

### 系统要求
- **Windows**: 无特殊要求
- **Linux**: 需要sudo权限访问`/dev/input/`
- **macOS**: 需要在系统偏好设置中授予辅助功能权限

---

## 基础移动API

### `mouse.move(x, y, absolute=True, duration=0, steps_per_second=120.0)`
移动鼠标光标到指定位置。

**参数:**
- `x` (int): X坐标
- `y` (int): Y坐标  
- `absolute` (bool): True=绝对坐标，False=相对移动
- `duration` (float): 移动持续时间（秒），0表示瞬间移动
- `steps_per_second` (float): 动画移动时的帧率

**返回值:** None

**示例:**
```python
# 瞬间移动到(800, 600)
mouse.move(800, 600)

# 在0.5秒内平滑移动到(1200, 800)
mouse.move(1200, 800, duration=0.5)

# 相对移动：从当前位置向右移动100像素
mouse.move(100, 0, absolute=False)
```

### `mouse.get_position()`
获取当前鼠标光标位置。

**返回值:** `(x, y)` 元组

**示例:**
```python
x, y = mouse.get_position()
print(f"当前鼠标位置: ({x}, {y})")
```

### `mouse.drag(start_x, start_y, end_x, end_y, absolute=True, duration=0)`
按住左键拖拽操作。

**参数:**
- `start_x`, `start_y` (int): 起始坐标
- `end_x`, `end_y` (int): 结束坐标
- `absolute` (bool): 坐标类型
- `duration` (float): 拖拽持续时间

**示例:**
```python
# 从(100,100)拖拽到(300,300)
mouse.drag(100, 100, 300, 300, duration=1.0)
```

---

## 点击操作API

### `mouse.click(button='left')`
单击指定按键。

**参数:**
- `button` (str): 按键类型 - 'left', 'right', 'middle', 'x', 'x2'

**示例:**
```python
mouse.click()           # 左键单击
mouse.click('right')    # 右键单击
mouse.click('middle')   # 中键单击
```

### `mouse.double_click(button='left')`
双击指定按键。

**示例:**
```python
mouse.double_click()        # 左键双击
mouse.double_click('right') # 右键双击
```

### `mouse.right_click()`
右键单击的便捷方法。

### `mouse.press(button='left')`
按下（不释放）指定按键。

**示例:**
```python
mouse.press('left')    # 按下左键
# ... 执行其他操作
mouse.release('left')  # 释放左键
```

### `mouse.release(button='left')`
释放指定按键。

### `mouse.is_pressed(button='left')`
检查指定按键是否被按下。

**返回值:** bool

**示例:**
```python
if mouse.is_pressed('left'):
    print("左键正在被按下")
```

### `mouse.wheel(delta=1)`
滚动鼠标滚轮。

**参数:**
- `delta` (int): 滚动量，正数向上，负数向下

**示例:**
```python
mouse.wheel(3)   # 向上滚动3格
mouse.wheel(-2)  # 向下滚动2格
```

---

## 事件监听API

### `mouse.on_click(callback, args=())`
监听左键点击事件。

**参数:**
- `callback` (function): 回调函数
- `args` (tuple): 传递给回调函数的参数

**返回值:** 事件处理器（用于取消监听）

**示例:**
```python
def on_left_click():
    print("检测到左键点击")

handler = mouse.on_click(on_left_click)

# 取消监听
mouse.unhook(handler)
```

### `mouse.on_double_click(callback, args=())`
监听左键双击事件。

### `mouse.on_right_click(callback, args=())`
监听右键点击事件。

### `mouse.on_middle_click(callback, args=())`
监听中键点击事件。

### `mouse.on_button(callback, args=(), buttons=('left', 'middle', 'right', 'x', 'x2'), types=('up', 'down', 'double'))`
通用按键事件监听器。

**参数:**
- `callback` (function): 回调函数
- `args` (tuple): 回调参数
- `buttons` (tuple): 要监听的按键类型
- `types` (tuple): 要监听的事件类型

**示例:**
```python
def on_any_button(event):
    print(f"按键事件: {event.button} {event.event_type}")

# 监听所有按键的所有事件
mouse.on_button(on_any_button, buttons=('left', 'right', 'middle'))
```

### `mouse.hook(callback)`
监听所有鼠标事件的底层钩子。

**参数:**
- `callback` (function): 回调函数，接收事件对象

**示例:**
```python
def event_handler(event):
    if isinstance(event, mouse.MoveEvent):
        print(f"鼠标移动到: ({event.x}, {event.y})")
    elif isinstance(event, mouse.ButtonEvent):
        print(f"按键事件: {event.button} {event.event_type}")
    elif isinstance(event, mouse.WheelEvent):
        print(f"滚轮事件: {event.delta}")

mouse.hook(event_handler)
```

### `mouse.unhook(callback)`
取消指定的事件监听器。

### `mouse.unhook_all()`
取消所有事件监听器。

### `mouse.wait(button='left', target_types=('up', 'down', 'double'))`
阻塞等待指定按键事件。

**示例:**
```python
print("请点击鼠标左键...")
mouse.wait('left', target_types=('down',))
print("检测到左键按下！")
```

---

## 高级功能API

### `mouse.record(button='right', target_types=('down',))`
录制鼠标操作序列。

**参数:**
- `button` (str): 停止录制的按键
- `target_types` (tuple): 停止录制的事件类型

**返回值:** 事件列表

**示例:**
```python
print("开始录制，右键停止...")
events = mouse.record()
print(f"录制了 {len(events)} 个事件")
```

### `mouse.play(events, speed_factor=1.0, include_clicks=True, include_moves=True, include_wheel=True)`
播放录制的鼠标操作序列。

**参数:**
- `events` (list): 事件列表
- `speed_factor` (float): 播放速度倍率
- `include_clicks` (bool): 是否包含点击事件
- `include_moves` (bool): 是否包含移动事件  
- `include_wheel` (bool): 是否包含滚轮事件

**示例:**
```python
# 录制操作
events = mouse.record()

# 原速播放
mouse.play(events)

# 2倍速播放，只包含移动
mouse.play(events, speed_factor=2.0, include_clicks=False)
```

### `mouse.replay(events, speed_factor=1.0, include_clicks=True, include_moves=True, include_wheel=True)`
`play()`的别名。

---

## 常量定义

### 按键常量
```python
mouse.LEFT = 'left'        # 左键
mouse.RIGHT = 'right'      # 右键  
mouse.MIDDLE = 'middle'    # 中键
mouse.X = 'x'             # 侧键1
mouse.X2 = 'x2'           # 侧键2
```

### 事件类型常量
```python
mouse.UP = 'up'           # 按键释放
mouse.DOWN = 'down'       # 按键按下
mouse.DOUBLE = 'double'   # 双击
```

### 事件类
```python
# 移动事件
class MoveEvent:
    x: int         # X坐标
    y: int         # Y坐标
    time: float    # 时间戳

# 按键事件  
class ButtonEvent:
    event_type: str  # 事件类型: 'up', 'down', 'double'
    button: str      # 按键: 'left', 'right', 'middle', 'x', 'x2'
    time: float      # 时间戳

# 滚轮事件
class WheelEvent:
    delta: int      # 滚动量
    time: float     # 时间戳
```

---

## 错误处理

### 常见异常

#### `OSError`
平台不支持时抛出。
```python
try:
    import mouse
except OSError as e:
    print(f"平台不支持: {e}")
```

#### 权限错误
Linux下需要sudo权限，macOS需要辅助功能权限。

### 错误处理示例
```python
import mouse

try:
    # 尝试移动鼠标
    mouse.move(1000, 1000)
except Exception as e:
    print(f"鼠标操作失败: {e}")
    
# 检查坐标范围
def safe_move(x, y):
    try:
        # 获取当前位置验证系统工作正常
        current_x, current_y = mouse.get_position()
        mouse.move(x, y)
        return True
    except Exception as e:
        print(f"移动失败: {e}")
        return False
```

---

## 最佳实践

### 1. 坐标系统适配
```python
import tkinter as tk

def get_screen_size():
    """获取屏幕分辨率"""
    root = tk.Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    return width, height

# 使用相对坐标
width, height = get_screen_size()
center_x, center_y = width // 2, height // 2
mouse.move(center_x, center_y)
```

### 2. 平滑移动
```python
def smooth_move_to(target_x, target_y, duration=1.0):
    """平滑移动到目标位置"""
    mouse.move(target_x, target_y, duration=duration)

# FPS游戏风格的快速甩枪
def flick_shot(target_x, target_y):
    """快速甩枪移动"""
    mouse.move(target_x, target_y, duration=0.1)
```

### 3. 安全的事件监听
```python
import threading
import time

class MouseMonitor:
    def __init__(self):
        self.running = False
        self.handlers = []
    
    def start_monitoring(self):
        """启动监听"""
        self.running = True
        
        def on_click():
            if self.running:
                print("鼠标点击检测")
        
        handler = mouse.on_click(on_click)
        self.handlers.append(handler)
    
    def stop_monitoring(self):
        """停止监听"""
        self.running = False
        for handler in self.handlers:
            mouse.unhook(handler)
        self.handlers.clear()

# 使用示例
monitor = MouseMonitor()
monitor.start_monitoring()

# 运行一段时间后停止
time.sleep(10)
monitor.stop_monitoring()
```

### 4. 批量操作
```python
def batch_clicks(positions, delay=0.1):
    """批量点击多个位置"""
    for x, y in positions:
        mouse.move(x, y)
        time.sleep(delay)
        mouse.click()

# 示例：点击多个按钮
button_positions = [(100, 200), (300, 400), (500, 600)]
batch_clicks(button_positions)
```

### 5. 录制回放自动化
```python
def record_and_save(filename):
    """录制操作并保存"""
    print("开始录制，右键停止...")
    events = mouse.record()
    
    # 保存到文件
    import pickle
    with open(filename, 'wb') as f:
        pickle.dump(events, f)
    
    return len(events)

def load_and_replay(filename, speed=1.0):
    """加载并回放操作"""
    import pickle
    with open(filename, 'rb') as f:
        events = pickle.load(f)
    
    mouse.play(events, speed_factor=speed)

# 使用示例
record_and_save('my_actions.pkl')
load_and_replay('my_actions.pkl', speed=2.0)
```

---

## 完整示例

### 示例1：自动化UI测试
```python
import mouse
import time

def ui_automation_test():
    """UI自动化测试示例"""
    
    # 1. 移动到登录按钮并点击
    mouse.move(500, 300)
    mouse.click()
    time.sleep(0.5)
    
    # 2. 移动到用户名输入框
    mouse.move(400, 200)
    mouse.click()
    
    # 3. 移动到密码输入框
    mouse.move(400, 250)
    mouse.click()
    
    # 4. 提交表单
    mouse.move(450, 350)
    mouse.click()
    
    print("UI测试完成")

ui_automation_test()
```

### 示例2：游戏辅助脚本
```python
import mouse
import time
import threading

class GameAssistant:
    def __init__(self):
        self.auto_click_enabled = False
        self.click_interval = 0.1
        
    def toggle_auto_click(self):
        """切换自动点击"""
        self.auto_click_enabled = not self.auto_click_enabled
        if self.auto_click_enabled:
            threading.Thread(target=self._auto_click_loop, daemon=True).start()
    
    def _auto_click_loop(self):
        """自动点击循环"""
        while self.auto_click_enabled:
            mouse.click()
            time.sleep(self.click_interval)
    
    def setup_hotkeys(self):
        """设置热键"""
        # 监听中键切换自动点击
        mouse.on_middle_click(self.toggle_auto_click)
        
        print("游戏助手已启动:")
        print("- 中键: 切换自动点击")
        print("- 右键双击: 退出")
        
        # 等待右键双击退出
        mouse.wait('right', target_types=('double',))
        self.auto_click_enabled = False
        mouse.unhook_all()

# 使用示例
assistant = GameAssistant()
assistant.setup_hotkeys()
```

### 示例3：屏幕区域监控
```python
import mouse
import time

class ScreenRegionMonitor:
    def __init__(self, regions):
        """
        regions: [(x1, y1, x2, y2, name), ...]
        """
        self.regions = regions
        self.monitoring = False
    
    def point_in_region(self, x, y, region):
        """检查点是否在区域内"""
        x1, y1, x2, y2, _ = region
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def on_mouse_move(self, event):
        """鼠标移动事件处理"""
        if not self.monitoring:
            return
            
        for region in self.regions:
            if self.point_in_region(event.x, event.y, region):
                print(f"鼠标进入区域: {region[4]} ({event.x}, {event.y})")
    
    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        mouse.hook(self.on_mouse_move)
        print("开始监控屏幕区域...")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        mouse.unhook_all()

# 使用示例
regions = [
    (0, 0, 300, 300, "左上区域"),
    (500, 500, 800, 800, "中心区域"),
    (1200, 0, 1920, 300, "右上区域")
]

monitor = ScreenRegionMonitor(regions)
monitor.start_monitoring()

# 运行10秒后停止
time.sleep(10)
monitor.stop_monitoring()
```

---

## 性能优化建议

### 1. 批量操作优化
```python
# 不推荐：频繁的单个操作
for i in range(100):
    mouse.move(i * 10, i * 10)
    time.sleep(0.01)

# 推荐：使用duration参数进行平滑移动
mouse.move(1000, 1000, duration=1.0)
```

### 2. 事件监听优化
```python
# 避免在回调中执行耗时操作
def fast_handler(event):
    # 快速处理
    event_queue.put(event)

def slow_handler():
    # 在单独线程中处理耗时操作
    while True:
        event = event_queue.get()
        # 执行复杂处理...

mouse.hook(fast_handler)
threading.Thread(target=slow_handler, daemon=True).start()
```

### 3. 内存管理
```python
# 及时清理事件监听器
try:
    handler = mouse.on_click(my_callback)
    # ... 使用代码
finally:
    mouse.unhook(handler)  # 确保清理
```

---

## 版本信息

- **当前版本**: 0.7.1
- **Python支持**: 2.7, 3.x
- **平台支持**: Windows, Linux, macOS

---

## 许可证

MIT License

---

## 联系与支持

- **GitHub**: https://github.com/boppreh/mouse
- **问题反馈**: GitHub Issues
- **文档更新**: 参考项目README.md

---

*本文档最后更新: 2025年*