import queue
import threading
import os
import time
import win32con, win32api

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
        self.lock = threading.Lock()
        
        # 爆发射击节奏控制 - 极致优化
        self.burst_shots_per_cycle = 3  # 每次爆发3枪
        self.shot_interval = 0.02  # 每枪间隔20ms（极速三连点）
        self.burst_cooldown = 0.5  # 爆发后冷却500ms
        self.click_duration = 0.015  # 单次点击持续15ms（确保游戏识别）
        
        # 射击状态管理
        self.shooting_state = 'IDLE'  # IDLE, BURST_SHOOTING, COOLDOWN
        self.current_burst_count = 0
        self.last_shot_time = 0
        self.burst_start_time = 0
        self.is_target_active = False
        
        self.start()
        if cfg.mouse_rzr:
            dll_name = "rzctl.dll" 
            script_directory = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(script_directory, dll_name)
            self.rzr = RZCONTROL(dll_path)
            
            if not self.rzr.init():
                logger.error("[Shooting] Failed to initialize rzctl")
            
    def run(self):
        while True:
            try:
                bScope, shooting_state = self.queue.get()
                self.shoot(bScope, shooting_state)
            except Exception as e:
                logger.error("[Shooting] Shooting thread crashed: %s", e)
            
    def shoot(self, bScope, shooting_state):
        with self.lock:
            # 更新目标状态
            target_available = (shooting_state and bScope) or (cfg.mouse_auto_aim and bScope)
            
            # 处理目标状态变化
            if target_available and not self.is_target_active:
                # 目标出现 - 开始射击循环
                self.start_shooting_cycle()
            elif not target_available and self.is_target_active:
                # 目标消失 - 停止射击
                self.stop_shooting_cycle()
            
            self.is_target_active = target_available
            
            # 如果有目标，处理爆发射击逻辑
            if self.is_target_active:
                self.handle_burst_shooting()
    
    def start_shooting_cycle(self):
        """开始射击循环"""
        self.shooting_state = 'BURST_SHOOTING'
        self.current_burst_count = 0
        self.burst_start_time = time.time()
        self.last_shot_time = 0
        logger.info("🔥 开始爆发射击模式 - 3枪+500ms节奏")
    
    def stop_shooting_cycle(self):
        """停止射击循环"""
        self.shooting_state = 'IDLE'
        self.current_burst_count = 0
        # 确保释放任何按下的按钮
        if self.button_pressed:
            self.release_mouse_button()
        logger.info("⏹️ 停止射击 - 目标丢失")
    
    def handle_burst_shooting(self):
        """处理爆发射击逻辑"""
        current_time = time.time()
        
        if self.shooting_state == 'BURST_SHOOTING':
            # 检查是否需要射击下一发
            if self.current_burst_count < self.burst_shots_per_cycle:
                if current_time - self.last_shot_time >= self.shot_interval:
                    self.fire_single_shot()
                    self.current_burst_count += 1
                    self.last_shot_time = current_time
                    logger.info(f"💥 射击第{self.current_burst_count}枪")
            else:
                # 完成一轮爆发，进入冷却
                self.shooting_state = 'COOLDOWN'
                self.burst_start_time = current_time
                logger.info("❄️ 进入冷却期 - 500ms")
        
        elif self.shooting_state == 'COOLDOWN':
            # 检查冷却是否结束
            if current_time - self.burst_start_time >= self.burst_cooldown:
                # 开始下一轮爆发
                self.shooting_state = 'BURST_SHOOTING'
                self.current_burst_count = 0
                self.last_shot_time = current_time - self.shot_interval  # 立即射击第一枪
                logger.info("🔄 冷却结束 - 开始新一轮射击")
    
    def fire_single_shot(self):
        """执行单次射击（完整的点击：按下->释放）- 优化版本"""
        try:
            # 按下
            if cfg.mouse_rzr:  # Razer
                self.rzr.mouse_click(MOUSE_CLICK.LEFT_DOWN)
            elif cfg.mouse_ghub:  # ghub
                self.ghub.mouse_down()
            elif cfg.arduino_shoot:  # arduino
                arduino.press()
            else:  # native
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            
            # 优化的点击持续时间
            time.sleep(self.click_duration)  # 15ms确保游戏稳定识别
            
            if cfg.mouse_rzr:  # Razer
                self.rzr.mouse_click(MOUSE_CLICK.LEFT_UP)
            elif cfg.mouse_ghub:  # ghub
                self.ghub.mouse_up()
            elif cfg.arduino_shoot:  # arduino
                arduino.release()
            else:  # native
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
        except Exception as e:
            logger.error(f"射击失败: {e}")
    
    def release_mouse_button(self):
        """释放鼠标按钮"""
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
    
shooting = Shooting()