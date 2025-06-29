import queue
import threading
import os
import time
import win32con, win32api
from concurrent.futures import ThreadPoolExecutor

from logic.ghub import gHub
from logic.config_watcher import cfg
from logic.logger import logger

if cfg.mouse_rzr:
    from logic.rzctl import RZCONTROL 
    from logic.rzctl import MOUSE_CLICK

if cfg.arduino_move or cfg.arduino_shoot:
    from logic.arduino import arduino
    
class Shooting(threading.Thread):
    def __init__(self):
        super(Shooting, self).__init__()
        self.queue = queue.Queue(maxsize=1)
        self.daemon = True
        self.name = 'Shooting'
        self.button_pressed = False
        self.ghub = gHub
        # Phase 2: 移除旧锁，使用新的RLock
        
        # 游戏适配三连发射击系统 - 适配游戏射速限制
        self.burst_shots_per_cycle = 3  # 固定三发
        self.shot_interval = 0.095  # 95ms间隔（适配游戏射速限制）
        self.burst_cooldown = 0.7  # 700ms冷却（稳定间隔）
        self.click_duration = 0.018  # 18ms点击持续（确保识别）
        
        # 射击状态管理
        self.shooting_state = 'IDLE'  # IDLE, BURST_SHOOTING, COOLDOWN
        self.current_burst_count = 0
        self.last_shot_time = 0
        self.burst_start_time = 0
        self.is_target_active = False
        
        # Phase 1: 独立射击计时器系统
        self.burst_timer = None
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="BurstShoot")
        self.shooting_lock = threading.RLock()  # 使用可重入锁
        
        # Phase 1: 高精度时间统计
        self.shot_times = []  # 记录实际射击时间
        self.target_intervals = []  # 记录目标间隔
        self.performance_stats = {'shots_fired': 0, 'avg_interval': 0, 'max_deviation': 0}
        
        self.start()
        if cfg.mouse_rzr:
            dll_name = "rzctl.dll" 
            script_directory = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(script_directory, dll_name)
            self.rzr = RZCONTROL(dll_path)
            
            if not self.rzr.init():
                logger.error("[Shooting] Failed to initialize rzctl")
            
    def run(self):
        # Phase 2: 优化主循环 - 减少异常处理开销
        while True:
            try:
                # 简化的参数处理
                queue_data = self.queue.get(timeout=1.0)  # 添加超时避免永久阻塞
                if not queue_data:
                    continue
                    
                if len(queue_data) >= 2:
                    bScope, shooting_state = queue_data[:2]  # 只取前两个参数
                else:
                    bScope, shooting_state = queue_data
                
                self.shoot(bScope, shooting_state)
                
            except queue.Empty:
                # 超时情况下检查是否应该停止射击
                if self.is_target_active and self.shooting_state != 'IDLE':
                    with self.shooting_lock:
                        if time.perf_counter() - self.burst_start_time > 1.5:  # 1.5秒无新目标则停止
                            self.is_target_active = False
                            self.stop_shooting()
                            logger.info("🔄 长时间无目标更新，自动停止射击")
                continue
            except Exception as e:
                logger.error("[Shooting] Shooting thread crashed: %s", e)
            
    def shoot(self, bScope, shooting_state):
        # Phase 2: 优化状态机 - 减少锁开销和重复检查
        target_available = (shooting_state and bScope) or (cfg.mouse_auto_aim and bScope)
        
        # 快速状态变化检查，避免不必要的锁争用
        if target_available == self.is_target_active:
            return  # 状态未变化，直接返回
        
        with self.shooting_lock:  # 使用新的RLock
            # 二次检查，防止并发状态变化
            if target_available == self.is_target_active:
                return
            
            # 处理目标状态变化
            if target_available and not self.is_target_active:
                # 目标出现 - 立即开始三连发
                self.is_target_active = True
                self.start_simple_burst()
            elif not target_available and self.is_target_active:
                # 目标消失 - 停止射击
                self.is_target_active = False
                self.stop_shooting()
    
    def get_performance_stats(self):
        """Phase 3: 获取射击性能统计"""
        with self.shooting_lock:
            return self.performance_stats.copy()
    
    def reset_performance_stats(self):
        """Phase 3: 重置性能统计"""
        with self.shooting_lock:
            self.performance_stats = {'shots_fired': 0, 'avg_interval': 0, 'max_deviation': 0}
            logger.info("📊 射击性能统计已重置")
    
    def is_shooting_active(self):
        """Phase 2: 快速检查射击状态 - 避免锁争用"""
        return self.shooting_state != 'IDLE' and self.is_target_active
    
    def start_simple_burst(self):
        """Phase 1: 开始高精度三连发"""
        with self.shooting_lock:
            if self.shooting_state == 'BURST_SHOOTING':
                return  # 已在射击中，避免重复启动
            
            self.shooting_state = 'BURST_SHOOTING'
            self.current_burst_count = 0
            self.burst_start_time = time.perf_counter()  # 高精度计时
            self.last_shot_time = 0
            self.shot_times.clear()  # 清空统计
            
            # 立即射击第一发，然后启动计时器
            self.schedule_next_shot(immediate=True)
            logger.info(f"🔥 开始游戏适配三连发 - 95ms间隔, 700ms冷却")
    
    def stop_shooting(self):
        """Phase 1: 停止射击 - 取消所有计时器"""
        with self.shooting_lock:
            self.shooting_state = 'IDLE'
            self.current_burst_count = 0
            self.is_target_active = False
            
            # 取消所有计时器
            if self.burst_timer:
                self.burst_timer.cancel()
                self.burst_timer = None
            
            # 确保释放任何按下的按钮
            if self.button_pressed:
                self.release_mouse_button()
            
            logger.info("⏹️ 停止游戏适配三连发 - 目标丢失")
    
    def schedule_next_shot(self, immediate=False):
        """Phase 1: 调度下一发射击 - 独立计时器"""
        if self.shooting_state != 'BURST_SHOOTING':
            return
            
        if self.current_burst_count >= self.burst_shots_per_cycle:
            # 完成三连发，进入冷却
            self.shooting_state = 'COOLDOWN'
            self.burst_start_time = time.perf_counter()
            self.schedule_cooldown_end()
            self.log_burst_performance()
            logger.info(f"❄️ 三连发完成 - 冷却700ms (总时间{(time.perf_counter() - self.burst_start_time)*1000:.0f}ms)")
            return
        
        # 计算下一发射击时间
        if immediate:
            delay = 0.0
        else:
            delay = self.shot_interval
        
        # 使用独立计时器调度
        self.burst_timer = threading.Timer(delay, self.execute_timed_shot)
        self.burst_timer.start()
    
    def execute_timed_shot(self):
        """Phase 1: 执行定时射击"""
        with self.shooting_lock:
            if self.shooting_state != 'BURST_SHOOTING':
                return
                
            shot_time = time.perf_counter()
            self.shot_times.append(shot_time)
            
            # 非阻塞射击执行
            self.executor.submit(self.fire_single_shot_async)
            
            self.current_burst_count += 1
            self.last_shot_time = shot_time
            
            # 计算实际间隔
            if len(self.shot_times) > 1:
                actual_interval = (shot_time - self.shot_times[-2]) * 1000  # ms
                self.target_intervals.append(actual_interval)
                logger.info(f"💥 三连发第{self.current_burst_count}枪 - 实际间隔{actual_interval:.1f}ms (目桰95ms)")
            else:
                logger.info(f"💥 三连发第{self.current_burst_count}枪 - 首发")
            
            # 调度下一发
            self.schedule_next_shot()
    
    def schedule_cooldown_end(self):
        """Phase 1: 调度冷却结束"""
        def cooldown_finished():
            with self.shooting_lock:
                if self.is_target_active and self.shooting_state == 'COOLDOWN':
                    self.shooting_state = 'BURST_SHOOTING'
                    self.current_burst_count = 0
                    self.shot_times.clear()
                    self.schedule_next_shot(immediate=True)
                    logger.info("🔄 冷却结束 - 开始新一轮三连发")
                else:
                    self.shooting_state = 'IDLE'
        
        self.burst_timer = threading.Timer(self.burst_cooldown, cooldown_finished)
        self.burst_timer.start()
    
    def handle_simple_shooting(self):
        """Phase 1: 简化的射击处理 - 不再需要轮询"""
        # 新系统不需要轮询，由计时器独立处理
        pass
    
    def fire_single_shot_async(self):
        """Phase 1: 非阻塞射击执行 - 避免阻塞主线程"""
        try:
            # 记录射击开始时间
            shoot_start = time.perf_counter()
            
            # 按下
            if cfg.mouse_rzr:  # Razer
                self.rzr.mouse_click(MOUSE_CLICK.LEFT_DOWN)
            elif cfg.mouse_ghub:  # ghub
                self.ghub.mouse_down()
            elif cfg.arduino_shoot:  # arduino
                arduino.press()
            else:  # native
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            
            # 非阻塞等待点击持续时间
            def release_click():
                try:
                    if cfg.mouse_rzr:  # Razer
                        self.rzr.mouse_click(MOUSE_CLICK.LEFT_UP)
                    elif cfg.mouse_ghub:  # ghub
                        self.ghub.mouse_up()
                    elif cfg.arduino_shoot:  # arduino
                        arduino.release()
                    else:  # native
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    
                    # 统计射击执行时间
                    shoot_end = time.perf_counter()
                    execution_time = (shoot_end - shoot_start) * 1000
                    self.performance_stats['shots_fired'] += 1
                    
                except Exception as e:
                    logger.error(f"释放射击失败: {e}")
            
            # 使用计时器非阻塞释放
            release_timer = threading.Timer(self.click_duration, release_click)
            release_timer.start()
            
        except Exception as e:
            logger.error(f"射击失败: {e}")
    
    def fire_single_shot(self):
        """Phase 1: 兼容性射击接口 - 转发到非阻塞版本"""
        self.fire_single_shot_async()
    
    def log_burst_performance(self):
        """Phase 1: 记录三连发性能统计"""
        if len(self.target_intervals) > 0:
            avg_interval = sum(self.target_intervals) / len(self.target_intervals)
            max_deviation = max(abs(interval - 95.0) for interval in self.target_intervals)
            total_burst_time = sum(self.target_intervals)
            self.performance_stats['avg_interval'] = avg_interval
            self.performance_stats['max_deviation'] = max_deviation
            
            logger.info(f"📊 三连发性能: 平均间隔{avg_interval:.1f}ms (目桰95ms), 最大偏差{max_deviation:.1f}ms")
            logger.info(f"🎯 三连发总时间: {total_burst_time:.0f}ms (游戏适配190-200ms)")
            self.target_intervals.clear()
    
    # 移除复杂的场景射击预设系统
    
    def release_mouse_button(self):
        """Phase 1: 释放鼠标按钮 - 并发执行"""
        def release_async():
            try:
                if cfg.mouse_rzr:  # Razer
                    self.rzr.mouse_click(MOUSE_CLICK.LEFT_UP)
                elif cfg.mouse_ghub:  # ghub
                    self.ghub.mouse_up()
                elif cfg.arduino_shoot:  # arduino
                    arduino.release()
                else:  # native
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
                self.button_pressed = False
            except Exception as e:
                logger.error(f"释放按钮失败: {e}")
        
        self.executor.submit(release_async)
    
    def cleanup(self):
        """Phase 1: 清理资源"""
        with self.shooting_lock:
            self.shooting_state = 'IDLE'
            if self.burst_timer:
                self.burst_timer.cancel()
            self.executor.shutdown(wait=False)
            logger.info("🗑️ 射击系统清理完成")
    
shooting = Shooting()

# Phase 1: 添加退出清理
import atexit
atexit.register(shooting.cleanup)