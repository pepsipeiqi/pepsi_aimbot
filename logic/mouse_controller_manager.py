"""
🎯 鼠标控制器管理器 - 传统vs预测式控制系统的切换管理

This manager provides seamless switching between:
1. Traditional mouse controller (current zone-based system)
2. Predictive mouse controller (new prediction + feedback system)

Features:
- Runtime switching between control modes
- Performance comparison and monitoring
- Automatic fallback if prediction system fails
- Configuration-driven controller selection
- Unified interface for both systems
"""

import time
from enum import Enum
from typing import Optional, Dict, Any

class ControllerType(Enum):
    TRADITIONAL = "traditional"
    PREDICTIVE = "predictive"
    AUTO = "auto"  # Automatically choose best performing

class MouseControllerManager:
    """鼠标控制器管理器 - 统一接口"""
    
    def __init__(self):
        self.current_controller_type = ControllerType.TRADITIONAL
        self.traditional_controller = None
        self.predictive_controller = None
        self.fallback_controller = None
        
        # 性能监控
        self.performance_stats = {
            ControllerType.TRADITIONAL: {'success_count': 0, 'total_count': 0, 'avg_time': 0.0},
            ControllerType.PREDICTIVE: {'success_count': 0, 'total_count': 0, 'avg_time': 0.0}
        }
        
        # 加载配置
        self._load_configuration()
        
        # 初始化控制器
        self._initialize_controllers()
        
        print(f"🎯 MouseControllerManager initialized")
        print(f"   Current mode: {self.current_controller_type.value}")
        print(f"   Auto-switching: {'✅' if self.current_controller_type == ControllerType.AUTO else '❌'}")
    
    def _load_configuration(self):
        """加载配置"""
        try:
            from logic.config_watcher import cfg
            
            # 从配置读取控制器类型
            controller_mode = getattr(cfg, 'mouse_controller_mode', 'traditional')
            
            if controller_mode == 'predictive':
                self.current_controller_type = ControllerType.PREDICTIVE
            elif controller_mode == 'auto':
                self.current_controller_type = ControllerType.AUTO
            else:
                self.current_controller_type = ControllerType.TRADITIONAL
            
            # 预测式控制器配置
            self.predictive_enabled = getattr(cfg, 'enable_predictive_control', True)
            self.auto_fallback_enabled = getattr(cfg, 'enable_auto_fallback', True)
            self.performance_comparison_enabled = getattr(cfg, 'enable_performance_comparison', True)
            
            print(f"✅ Configuration loaded: mode={controller_mode}")
            
        except Exception as e:
            print(f"⚠️ Config loading failed, using defaults: {e}")
            self.current_controller_type = ControllerType.TRADITIONAL
            self.predictive_enabled = True
            self.auto_fallback_enabled = True
            self.performance_comparison_enabled = True
    
    def _initialize_controllers(self):
        """初始化控制器"""
        # 传统控制器（现有系统）
        try:
            from logic.mouse_new_raw_input_fixed import RawInputCompatibleController
            self.traditional_controller = RawInputCompatibleController()
            print("✅ Traditional controller initialized")
        except Exception as e:
            print(f"❌ Traditional controller initialization failed: {e}")
        
        # 预测式控制器（新系统）
        if self.predictive_enabled:
            try:
                from logic.mouse_predictive_controller import PredictiveMouseController
                self.predictive_controller = PredictiveMouseController()
                print("✅ Predictive controller initialized")
            except Exception as e:
                print(f"❌ Predictive controller initialization failed: {e}")
                if self.current_controller_type == ControllerType.PREDICTIVE:
                    print("⚠️ Falling back to traditional controller")
                    self.current_controller_type = ControllerType.TRADITIONAL
        
        # 设置后备控制器 - 智能选择
        if self.predictive_controller:
            self.fallback_controller = self.predictive_controller
        elif self.traditional_controller:
            self.fallback_controller = self.traditional_controller
        else:
            self.fallback_controller = None
            
        # 如果传统控制器不可用但设置为传统模式，自动切换到预测式
        if self.current_controller_type == ControllerType.TRADITIONAL and not self.traditional_controller and self.predictive_controller:
            print("⚠️ Traditional controller unavailable, auto-switching to predictive")
            self.current_controller_type = ControllerType.PREDICTIVE
    
    def process_target(self, target_x: float, target_y: float, target_w: float = 0, 
                      target_h: float = 0, target_cls: int = 0) -> bool:
        """
        处理目标 - 统一接口
        
        Args:
            target_x, target_y: 目标中心坐标
            target_w, target_h: 目标尺寸
            target_cls: 目标类别 (0=BODY, 7=HEAD)
        
        Returns:
            bool: 处理是否成功
        """
        start_time = time.time()
        
        # 选择控制器
        active_controller = self._get_active_controller()
        controller_type = self._get_controller_type(active_controller)
        
        if active_controller is None:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ No available controller")
            return False
        
        # 记录处理前的信息
        distance = self._calculate_distance_to_center(target_x, target_y)
        target_type = "HEAD" if target_cls == 7 else "BODY"
        
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🎯 CONTROLLER: {controller_type.value.upper()} | "
              f"{target_type} | distance={distance:.1f}px")
        
        # 执行处理
        try:
            if controller_type == ControllerType.PREDICTIVE:
                success = active_controller.process_target(target_x, target_y, target_w, target_h, target_cls)
            else:
                # 传统控制器使用现有接口
                success = active_controller.process_target(target_x, target_y, target_w, target_h, target_cls)
            
            execution_time = time.time() - start_time
            
            # 更新性能统计
            self._update_performance_stats(controller_type, success, execution_time)
            
            # 自动切换逻辑
            if self.current_controller_type == ControllerType.AUTO:
                self._evaluate_auto_switching()
            
            # 性能对比日志
            if self.performance_comparison_enabled and success:
                self._log_performance_comparison(controller_type, execution_time, distance)
            
            return success
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Controller {controller_type.value} failed: {e}")
            
            # 自动回退
            if self.auto_fallback_enabled and controller_type != ControllerType.TRADITIONAL and self.fallback_controller:
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 🔄 Falling back to traditional controller")
                try:
                    success = self.fallback_controller.process_target(target_x, target_y, target_w, target_h, target_cls)
                    execution_time = time.time() - start_time
                    self._update_performance_stats(ControllerType.TRADITIONAL, success, execution_time)
                    return success
                except Exception as fallback_error:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ❌ Fallback also failed: {fallback_error}")
            
            self._update_performance_stats(controller_type, False, execution_time)
            return False
    
    def _get_active_controller(self):
        """获取当前活跃的控制器"""
        if self.current_controller_type == ControllerType.PREDICTIVE:
            return self.predictive_controller or self.fallback_controller
        elif self.current_controller_type == ControllerType.AUTO:
            # 基于性能选择最佳控制器
            return self._get_best_performing_controller()
        else:
            return self.traditional_controller or self.fallback_controller
    
    def _get_controller_type(self, controller) -> ControllerType:
        """获取控制器类型"""
        if controller == self.predictive_controller:
            return ControllerType.PREDICTIVE
        else:
            return ControllerType.TRADITIONAL
    
    def _get_best_performing_controller(self):
        """基于性能选择最佳控制器"""
        traditional_score = self._calculate_performance_score(ControllerType.TRADITIONAL)
        predictive_score = self._calculate_performance_score(ControllerType.PREDICTIVE)
        
        if predictive_score > traditional_score and self.predictive_controller:
            return self.predictive_controller
        else:
            return self.traditional_controller or self.fallback_controller
    
    def _calculate_performance_score(self, controller_type: ControllerType) -> float:
        """计算控制器性能分数"""
        stats = self.performance_stats[controller_type]
        
        if stats['total_count'] == 0:
            return 0.5  # 未测试的控制器给中等分数
        
        success_rate = stats['success_count'] / stats['total_count']
        speed_factor = max(0.1, min(1.0, 1.0 / (stats['avg_time'] + 0.001)))  # 速度因子
        
        # 综合分数：成功率 * 0.7 + 速度因子 * 0.3
        score = success_rate * 0.7 + speed_factor * 0.3
        return score
    
    def _update_performance_stats(self, controller_type: ControllerType, success: bool, execution_time: float):
        """更新性能统计"""
        stats = self.performance_stats[controller_type]
        
        # 更新计数
        stats['total_count'] += 1
        if success:
            stats['success_count'] += 1
        
        # 更新平均时间（移动平均）
        alpha = 0.1  # 平滑因子
        if stats['avg_time'] == 0:
            stats['avg_time'] = execution_time
        else:
            stats['avg_time'] = (1 - alpha) * stats['avg_time'] + alpha * execution_time
    
    def _evaluate_auto_switching(self):
        """评估是否需要自动切换控制器"""
        # 至少需要10次测试才开始评估
        traditional_total = self.performance_stats[ControllerType.TRADITIONAL]['total_count']
        predictive_total = self.performance_stats[ControllerType.PREDICTIVE]['total_count']
        
        if traditional_total < 10 or predictive_total < 10:
            return
        
        traditional_score = self._calculate_performance_score(ControllerType.TRADITIONAL)
        predictive_score = self._calculate_performance_score(ControllerType.PREDICTIVE)
        
        # 如果性能差异超过20%，考虑切换建议
        if abs(traditional_score - predictive_score) > 0.2:
            better_controller = "predictive" if predictive_score > traditional_score else "traditional"
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 📊 AUTO EVALUATION: "
                  f"{better_controller} performing better (traditional={traditional_score:.2f}, "
                  f"predictive={predictive_score:.2f})")
    
    def _log_performance_comparison(self, controller_type: ControllerType, execution_time: float, distance: float):
        """记录性能对比日志"""
        traditional_stats = self.performance_stats[ControllerType.TRADITIONAL]
        predictive_stats = self.performance_stats[ControllerType.PREDICTIVE]
        
        # 每50次处理输出一次统计
        total_processed = traditional_stats['total_count'] + predictive_stats['total_count']
        if total_processed % 50 == 0 and total_processed > 0:
            print(f"\n📊 PERFORMANCE COMPARISON (last 50 operations):")
            print(f"Traditional: {traditional_stats['success_count']}/{traditional_stats['total_count']} "
                  f"({traditional_stats['success_count']/max(1,traditional_stats['total_count'])*100:.1f}% success, "
                  f"{traditional_stats['avg_time']*1000:.1f}ms avg)")
            print(f"Predictive:  {predictive_stats['success_count']}/{predictive_stats['total_count']} "
                  f"({predictive_stats['success_count']/max(1,predictive_stats['total_count'])*100:.1f}% success, "
                  f"{predictive_stats['avg_time']*1000:.1f}ms avg)")
    
    def _calculate_distance_to_center(self, target_x: float, target_y: float) -> float:
        """计算到屏幕中心的距离"""
        try:
            from logic.capture import capture
            center_x = capture.screen_x_center
            center_y = capture.screen_y_center
        except:
            center_x, center_y = 250, 250  # 默认值
        
        return ((target_x - center_x)**2 + (target_y - center_y)**2)**0.5
    
    def switch_controller(self, controller_type: ControllerType):
        """手动切换控制器"""
        if controller_type == ControllerType.PREDICTIVE and not self.predictive_controller:
            print(f"❌ Cannot switch to predictive controller - not available")
            return False
        
        self.current_controller_type = controller_type
        print(f"🔄 Switched to {controller_type.value} controller")
        return True
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {}
        
        for controller_type in [ControllerType.TRADITIONAL, ControllerType.PREDICTIVE]:
            stats = self.performance_stats[controller_type]
            summary[controller_type.value] = {
                'success_rate': stats['success_count'] / max(1, stats['total_count']),
                'avg_execution_time_ms': stats['avg_time'] * 1000,
                'total_operations': stats['total_count'],
                'performance_score': self._calculate_performance_score(controller_type)
            }
        
        # 添加当前控制器信息
        summary['current_controller'] = self.current_controller_type.value
        summary['predictive_available'] = self.predictive_controller is not None
        
        return summary
    
    def process_data(self, data):
        """
        处理YOLO检测数据 - 兼容性接口
        
        Args:
            data: supervision.Detections 对象或传统的元组格式
        
        Returns:
            bool: 处理是否成功
        """
        try:
            import supervision as sv
            
            # 解析检测数据
            if isinstance(data, sv.Detections):
                if len(data.xyxy) == 0:
                    return self.handle_no_target()
                
                # 获取第一个检测目标
                bbox = data.xyxy[0]  # [x1, y1, x2, y2]
                target_x = (bbox[0] + bbox[2]) / 2  # Center X
                target_y = (bbox[1] + bbox[3]) / 2  # Center Y
                target_w = bbox[2] - bbox[0]        # Width
                target_h = bbox[3] - bbox[1]        # Height
                target_cls = data.class_id[0] if len(data.class_id) > 0 else 0
            else:
                # 传统元组格式
                if len(data) >= 5:
                    target_x, target_y, target_w, target_h, target_cls = data[:5]
                else:
                    return self.handle_no_target()
            
            # 处理目标
            return self.process_target(target_x, target_y, target_w, target_h, target_cls)
            
        except Exception as e:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} - ❌ Error processing detection data: {e}")
            return self.handle_no_target()
    
    def handle_no_target(self):
        """处理无目标情况"""
        active_controller = self._get_active_controller()
        if active_controller and hasattr(active_controller, 'handle_no_target'):
            active_controller.handle_no_target()
    
    def print_performance_stats(self):
        """打印性能统计"""
        summary = self.get_performance_summary()
        
        print("\n📊 Mouse Controller Performance Summary:")
        print("=" * 60)
        
        for controller_name, stats in summary.items():
            if controller_name in ['traditional', 'predictive']:
                print(f"{controller_name.capitalize():12s}: "
                      f"Success={stats['success_rate']*100:5.1f}% | "
                      f"Time={stats['avg_execution_time_ms']:5.1f}ms | "
                      f"Operations={stats['total_operations']:4d} | "
                      f"Score={stats['performance_score']:4.2f}")
        
        print(f"Current mode: {summary['current_controller'].upper()}")
        print(f"Predictive available: {'✅' if summary['predictive_available'] else '❌'}")
        print("=" * 60)

# 创建全局控制器管理器实例
mouse_controller_manager = MouseControllerManager()