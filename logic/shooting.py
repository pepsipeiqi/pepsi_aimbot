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
        
        # 简化的三连发射击系统
        self.burst_shots_per_cycle = 3  # 固定三发
        self.shot_interval = 0.020  # 固定20ms间隔
        self.burst_cooldown = 0.5  # 固定500ms冷却
        self.click_duration = 0.012  # 固定12ms点击持续
        
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
                # 简化的参数处理
                queue_data = self.queue.get()
                if len(queue_data) >= 2:
                    bScope, shooting_state = queue_data[:2]  # 只取前两个参数
                else:
                    bScope, shooting_state = queue_data
                
                self.shoot(bScope, shooting_state)
            except Exception as e:
                logger.error("[Shooting] Shooting thread crashed: %s", e)
            
    def shoot(self, bScope, shooting_state):
        with self.lock:
            # 简化的目标状态判断
            target_available = (shooting_state and bScope) or (cfg.mouse_auto_aim and bScope)
            
            # 处理目标状态变化
            if target_available and not self.is_target_active:
                # 目标出现 - 立即开始三连发
                self.start_simple_burst()
            elif not target_available and self.is_target_active:
                # 目标消失 - 停止射击
                self.stop_shooting()
            
            self.is_target_active = target_available
            
            # 如果有目标，处理简单射击逻辑
            if self.is_target_active:
                self.handle_simple_shooting()
    
    # 移除复杂的自适应参数调整
    
    def start_simple_burst(self):
        """开始简单三连发"""
        self.shooting_state = 'BURST_SHOOTING'
        self.current_burst_count = 0
        self.burst_start_time = time.time()
        self.last_shot_time = 0
        logger.info(f"🔥 开始三连发 - 20ms间隔, 500ms冷却")
    
    def stop_shooting(self):
        """简单停止射击"""
        self.shooting_state = 'IDLE'
        self.current_burst_count = 0
        # 确保释放任何按下的按钮
        if self.button_pressed:
            self.release_mouse_button()
        logger.info("⏹️ 停止三连发 - 目标丢失")
    
    def handle_simple_shooting(self):
        """处理简单三连发逻辑"""
        current_time = time.time()
        
        if self.shooting_state == 'BURST_SHOOTING':
            # 检查是否需要射击下一发
            if self.current_burst_count < self.burst_shots_per_cycle:
                if current_time - self.last_shot_time >= self.shot_interval:
                    self.fire_single_shot()
                    self.current_burst_count += 1
                    self.last_shot_time = current_time
                    logger.info(f"💥 三连发第{self.current_burst_count}枪")
            else:
                # 完成三连发，进入冷却
                self.shooting_state = 'COOLDOWN'
                self.burst_start_time = current_time
                logger.info(f"❄️ 三连发完成 - 冷却500ms")
        
        elif self.shooting_state == 'COOLDOWN':
            # 检查冷却是否结束
            if current_time - self.burst_start_time >= self.burst_cooldown:
                # 开始下一轮三连发
                self.shooting_state = 'BURST_SHOOTING'
                self.current_burst_count = 0
                self.last_shot_time = current_time - self.shot_interval  # 立即射击第一枪
                logger.info("🔄 冷却结束 - 开始新一轮三连发")
    
    def fire_single_shot(self):
        """执行简单单次射击（固定参数）"""
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
            
            # 固定点击持续时间
            time.sleep(self.click_duration)  # 固定12ms
            
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
    
    # 移除复杂的场景射击预设系统
    
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