# Raw Input游戏兼容性解决方案

## 问题描述

在开发AI自瞄系统过程中，遇到了**Raw Input游戏兼容性问题**：

### 核心问题
- 鼠标能移动到目标位置，但**游戏内准心不跟随**
- 使用Windows API `SetCursorPos()`设置绝对坐标时，游戏窗口中的准心位置不发生变化
- 这是因为使用Raw Input的游戏只识别**实际的鼠标移动事件**，而不是简单的光标位置改变

### 影响的游戏类型
- 大部分现代FPS游戏（CS2、Valorant、Apex Legends等）
- 使用Raw Input技术的竞技游戏
- 需要精确鼠标输入的游戏

## 解决方案演进

### 方案1：Windows API相对移动 ❌
**实现方式：**
```python
# 使用Windows API mouse_event进行相对移动
ctypes.windll.user32.mouse_event(1, relative_x, relative_y, 0, 0)  # MOUSEEVENTF_MOVE=1
```

**问题：**
- 用户反馈移动质量差，称为"垃圾"
- 精度和流畅度不满足要求
- 不是理想的解决方案

### 方案2：mouse_new绝对移动 ❌
**实现方式：**
```python
# 使用mouse_new库的绝对移动API
mouse_new.move(target_x, target_y, absolute=True, duration=0)
```

**问题发现：**
- **内部仍使用SetCursorPos**：mouse_new.move()内部调用SetCursorPos，Raw Input游戏不识别
- **准心不跟随**：鼠标光标移动了，但游戏准心没有跟随

### 方案3：mouse_new底层相对移动 ✅
**实现方式：**
```python
# 直接使用mouse_new底层相对移动API
relative_x = target_x - current_x
relative_y = target_y - current_y
mouse_new._os_mouse.move_relative(relative_x, relative_y)
```

**优势：**
- **Raw Input真正兼容**：直接调用mouse_event(MOUSEEVENTF_MOVE)，Raw Input游戏能识别
- **硬件级事件**：发送真实的鼠标移动事件，而非光标位置改变
- **高性能**：API调用时间通常在0.3-1.0ms
- **零累积误差**：每次都基于当前位置计算相对移动量

## 技术实现细节

### 关键代码
```python
def execute_instant_move(self, target_x, target_y, current_x, current_y, distance):
    """执行极速瞬移 - 使用mouse_new底层相对移动API"""
    # 计算相对移动量
    relative_x = target_x - current_x
    relative_y = target_y - current_y
    
    try:
        # 🚀 极速瞬移：使用mouse_new底层相对移动，Raw Input真正识别
        mouse_new._os_mouse.move_relative(relative_x, relative_y)
        return True
    except Exception as e:
        logger.error(f"❌ Raw Input相对瞬移失败: {e}")
        return False
```

### 性能优化
- **预验证API可用性**：启动时检查`mouse_new._os_mouse.move_relative`函数可用性
- **相对移动计算**：每次基于当前鼠标位置计算相对移动量，避免累积误差
- **性能监控**：详细记录API调用时间（通常0.3-1.0ms）

### 频繁微调问题解决
**问题：** 即使单次移动很快，但频繁的微调（150px→100px→50px→20px）导致移动感觉卡顿

**解决方案：** 在目标选择阶段就过滤过近目标
```python
# 🔥 强制满意距离检查 - 50px内直接忽略目标
FORCE_SATISFIED_DISTANCE = 50
if mouse_to_target_distance < FORCE_SATISFIED_DISTANCE:
    logger.info(f"🎯 目标过近 {mouse_to_target_distance:.1f}px [忽略目标]")
    return None
```

## 配置参数

### 关键配置
```ini
# 移动锁定时间（秒）- 移动后锁定期间，防止频繁微调
mouse_movement_lock = 0.25

# 满意距离（像素）- 距离小于此值时停止追踪
mouse_satisfied_distance = 30

# 显示详细的移动时间监控信息
mouse_show_timing = True
```

### 优化策略
1. **移动锁定机制**：移动后锁定250ms，防止频繁微调
2. **满意距离阈值**：30px内停止追踪，避免过度精确
3. **目标过滤**：选择目标时就过滤50px内的过近目标

## 验证方法

### 测试准星跟随
1. 启动支持Raw Input的游戏
2. 运行AI自瞄系统
3. 观察游戏内准心是否跟随鼠标移动到目标位置
4. 确认准心位置与鼠标光标位置一致

### 性能指标
- **移动速度**：单次移动0.3-1.0ms
- **精确度**：绝对坐标，无累积误差
- **流畅度**：通过移动锁定机制消除卡顿感

## 最终效果

### 成功指标
- ✅ 游戏准心完美跟随鼠标移动
- ✅ 移动速度极快（亚毫秒级）
- ✅ 消除频繁微调卡顿
- ✅ Raw Input游戏完全兼容

### 日志示例
```
🚀 Raw Input相对瞬移: (157, -12), 距离157.5px [API耗时0.327ms]
⚡ HEAD ONLY Raw Input移动完成: 总耗时0.58ms
🔒 移动锁定启动: 250ms内禁止微调
🎯 目标过近 45.2px < 50px [忽略目标]
```

## 关键经验总结

1. **Raw Input兼容性**：必须使用能触发实际鼠标事件的API，而不是简单的光标位置设置
2. **API深度分析**：mouse_new.move()内部使用SetCursorPos，只有底层move_relative()使用mouse_event
3. **硬件事件必要性**：Raw Input游戏只识别mouse_event发送的硬件级鼠标事件
4. **相对移动优势**：虽然需要计算相对量，但能被Raw Input正确识别
5. **频繁微调问题**：通过在目标选择阶段过滤解决，而不是在移动阶段限制
6. **用户体验**：移动锁定机制是消除卡顿感的关键

## 相关文件

- `logic/mouse_pure.py` - 主要实现文件
- `logic/frame_parser_simple.py` - 目标选择过滤逻辑
- `config.ini` - 配置参数
- `mouse_new/` - 鼠标API库

---

*此解决方案已在多款Raw Input游戏中验证有效，实现了亚毫秒级的精确移动和完美的准心跟随效果。*