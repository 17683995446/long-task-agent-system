"""
超长任务Agent树形双生子模块化执行系统 - 事件总线实现
Event Bus Implementation for Long-Task Agent Twin-Module Execution System

阶段6：事件总线实现
遵循原则：图难于其易，为大于其细
核心约束：模块间仅通过事件总线通信，禁止直接调用
"""

from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading
import queue
import uuid

from core_types.core_types import (
    ModuleID, TaskID,
    ModuleState,
    ModuleEvent, ModuleEventType,
)


# =============================================================================
# 1. 事件总线异常类型 (Event Bus Exception Types)
# =============================================================================

class EventBusError(Exception):
    """事件总线基础异常"""
    pass


class EventTypeNotFoundError(EventBusError):
    """事件类型未找到异常"""
    pass


class SubscriberNotFoundError(EventBusError):
    """订阅者未找到异常"""
    pass


class EventDeliveryError(EventBusError):
    """事件投递失败异常"""
    pass


# =============================================================================
# 2. 订阅者信息 (Subscriber Info)
# =============================================================================

@dataclass
class SubscriberInfo:
    """
    订阅者信息
    记录订阅者的详细信息
    """
    subscriber_id: str
    callback: Callable[[ModuleEvent], None]
    event_types: Set[ModuleEventType]
    priority: int = 5  # 1-10, 10为最高优先级
    once: bool = False  # 是否只订阅一次
    subscribed_at: datetime = field(default_factory=datetime.now)
    
    def matches(self, event_type: ModuleEventType) -> bool:
        """检查是否匹配事件类型"""
        return event_type in self.event_types or ModuleEventType in self.event_types


# =============================================================================
# 3. 事件投递记录 (Event Delivery Record)
# =============================================================================

@dataclass
class EventDeliveryRecord:
    """
    事件投递记录
    记录事件投递的历史
    """
    event: ModuleEvent
    subscriber_id: str
    delivered_at: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str = ""


# =============================================================================
# 4. 事件总线配置 (Event Bus Config)
# =============================================================================

@dataclass
class EventBusConfig:
    """
    事件总线配置
    """
    max_queue_size: int = 1000
    delivery_timeout_seconds: float = 5.0
    enable_history: bool = True
    max_history_size: int = 1000
    async_mode: bool = False
    worker_thread_count: int = 1


# =============================================================================
# 5. 事件总线 (Event Bus)
# =============================================================================

class EventBus:
    """
    事件总线
    
    提供模块间标准化通信机制：
    1. 发布-订阅模式
    2. 支持优先级
    3. 支持一次性订阅
    4. 支持事件历史
    5. 支持同步/异步投递
    
    使用方式：
        bus = EventBus.instance()
        
        # 订阅
        def handler(event):
            print(f"收到事件: {event.event_type}")
        bus.subscribe(handler, [ModuleEventType.RUN_STARTED])
        
        # 发布
        event = ModuleEvent(event_type=ModuleEventType.RUN_STARTED, module_id=module_id)
        bus.publish(event)
    """
    
    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()
    
    def __init__(self, config: Optional[EventBusConfig] = None):
        """
        初始化事件总线
        
        Args:
            config: 配置
        """
        self._config = config or EventBusConfig()
        
        # 订阅者映射
        self._subscribers: Dict[str, SubscriberInfo] = {}
        self._event_type_to_subscribers: Dict[ModuleEventType, Set[str]] = {
            event_type: set() for event_type in ModuleEventType
        }
        
        # 事件队列（异步模式）
        self._event_queue: queue.Queue = queue.Queue(maxsize=self._config.max_queue_size)
        
        # 事件历史
        self._event_history: List[ModuleEvent] = []
        self._delivery_history: List[EventDeliveryRecord] = []
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 工作线程（异步模式）
        self._worker_threads: List[threading.Thread] = []
        self._running = False
        
        if self._config.async_mode:
            self._start_workers()
    
    # =====================================================================
    # 单例模式
    # =====================================================================
    
    @classmethod
    def instance(cls, config: Optional[EventBusConfig] = None) -> "EventBus":
        """
        获取事件总线单例
        
        Args:
            config: 配置（仅在首次创建时有效）
            
        Returns:
            EventBus: 事件总线实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """重置事件总线（仅用于测试）"""
        if cls._instance is not None:
            cls._instance.shutdown()
        cls._instance = None
    
    # =====================================================================
    # 订阅管理
    # =====================================================================
    
    def subscribe(
        self,
        callback: Callable[[ModuleEvent], None],
        event_types: List[ModuleEventType],
        priority: int = 5,
        once: bool = False,
    ) -> str:
        """
        订阅事件
        
        Args:
            callback: 回调函数
            event_types: 订阅的事件类型列表
            priority: 优先级（1-10，10最高）
            once: 是否只订阅一次
            
        Returns:
            str: 订阅者ID
        """
        subscriber_id = str(uuid.uuid4())
        
        with self._lock:
            subscriber = SubscriberInfo(
                subscriber_id=subscriber_id,
                callback=callback,
                event_types=set(event_types),
                priority=max(1, min(10, priority)),
                once=once,
            )
            
            self._subscribers[subscriber_id] = subscriber
            
            for event_type in event_types:
                if event_type not in self._event_type_to_subscribers:
                    self._event_type_to_subscribers[event_type] = set()
                self._event_type_to_subscribers[event_type].add(subscriber_id)
        
        return subscriber_id
    
    def subscribe_once(
        self,
        callback: Callable[[ModuleEvent], None],
        event_types: List[ModuleEventType],
        priority: int = 5,
    ) -> str:
        """
        一次性订阅（收到一次事件后自动取消订阅）
        
        Args:
            callback: 回调函数
            event_types: 订阅的事件类型列表
            priority: 优先级
            
        Returns:
            str: 订阅者ID
        """
        return self.subscribe(callback, event_types, priority, once=True)
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscriber_id: 订阅者ID
            
        Returns:
            bool: 是否成功取消
        """
        with self._lock:
            subscriber = self._subscribers.pop(subscriber_id, None)
            if subscriber is None:
                return False
            
            for event_type in subscriber.event_types:
                if event_type in self._event_type_to_subscribers:
                    self._event_type_to_subscribers[event_type].discard(subscriber_id)
            
            return True
    
    def unsubscribe_all(self, callback: Callable[[ModuleEvent], None]) -> int:
        """
        取消所有与该回调关联的订阅
        
        Args:
            callback: 回调函数
            
        Returns:
            int: 取消的订阅数量
        """
        count = 0
        with self._lock:
            to_remove = [
                sid for sid, sub in self._subscribers.items()
                if sub.callback == callback
            ]
            for sid in to_remove:
                if self.unsubscribe(sid):
                    count += 1
        return count
    
    # =====================================================================
    # 事件发布
    # =====================================================================
    
    def publish(self, event: ModuleEvent) -> int:
        """
        发布事件
        
        Args:
            event: 事件
            
        Returns:
            int: 投递的订阅者数量
        """
        # 记录历史
        if self._config.enable_history:
            self._add_to_history(event)
        
        if self._config.async_mode:
            # 异步模式：放入队列
            try:
                self._event_queue.put(event, timeout=1)
                return -1  # 异步模式下返回-1表示已入队
            except queue.Full:
                raise EventDeliveryError("事件队列已满")
        else:
            # 同步模式：直接投递
            return self._deliver_event(event)
    
    def publish_sync(self, event: ModuleEvent) -> int:
        """
        同步发布事件（即使总线配置为异步模式）
        
        Args:
            event: 事件
            
        Returns:
            int: 投递的订阅者数量
        """
        if self._config.enable_history:
            self._add_to_history(event)
        return self._deliver_event(event)
    
    def _deliver_event(self, event: ModuleEvent) -> int:
        """
        投递事件到所有匹配的订阅者
        
        Args:
            event: 事件
            
        Returns:
            int: 投递的订阅者数量
        """
        with self._lock:
            subscriber_ids = self._event_type_to_subscribers.get(event.event_type, set()).copy()
        
        if not subscriber_ids:
            return 0
        
        # 按优先级排序
        subscribers = []
        for sid in subscriber_ids:
            sub = self._subscribers.get(sid)
            if sub:
                subscribers.append(sub)
        subscribers.sort(key=lambda s: s.priority, reverse=True)
        
        delivered_count = 0
        once_subscribers = []
        
        for subscriber in subscribers:
            try:
                subscriber.callback(event)
                delivered_count += 1
                
                # 记录投递
                if self._config.enable_history:
                    self._delivery_history.append(EventDeliveryRecord(
                        event=event,
                        subscriber_id=subscriber.subscriber_id,
                        success=True,
                    ))
                
                # 标记一次性订阅
                if subscriber.once:
                    once_subscribers.append(subscriber.subscriber_id)
                    
            except Exception as e:
                # 记录投递失败
                if self._config.enable_history:
                    self._delivery_history.append(EventDeliveryRecord(
                        event=event,
                        subscriber_id=subscriber.subscriber_id,
                        success=False,
                        error_message=str(e),
                    ))
        
        # 移除一次性订阅
        for sid in once_subscribers:
            self.unsubscribe(sid)
        
        return delivered_count
    
    def _add_to_history(self, event: ModuleEvent) -> None:
        """添加事件到历史"""
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._config.max_history_size:
                self._event_history.pop(0)
    
    # =====================================================================
    # 异步工作线程
    # =====================================================================
    
    def _start_workers(self) -> None:
        """启动工作线程"""
        self._running = True
        for i in range(self._config.worker_thread_count):
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
            self._worker_threads.append(thread)
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1)
                self._deliver_event(event)
            except queue.Empty:
                continue
            except Exception:
                pass
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._running = False
        for thread in self._worker_threads:
            thread.join(timeout=2)
        self._worker_threads.clear()
    
    # =====================================================================
    # 查询方法
    # =====================================================================
    
    def get_subscriber_count(self, event_type: Optional[ModuleEventType] = None) -> int:
        """
        获取订阅者数量
        
        Args:
            event_type: 事件类型，如果为None则返回所有订阅者数量
            
        Returns:
            int: 订阅者数量
        """
        with self._lock:
            if event_type is None:
                return len(self._subscribers)
            return len(self._event_type_to_subscribers.get(event_type, set()))
    
    def get_subscribers(self, event_type: ModuleEventType) -> List[SubscriberInfo]:
        """
        获取指定事件类型的所有订阅者
        
        Args:
            event_type: 事件类型
            
        Returns:
            List[SubscriberInfo]: 订阅者列表
        """
        with self._lock:
            subscriber_ids = self._event_type_to_subscribers.get(event_type, set())
            return [
                self._subscribers[sid]
                for sid in subscriber_ids
                if sid in self._subscribers
            ]
    
    def get_event_history(
        self,
        event_type: Optional[ModuleEventType] = None,
        limit: int = 100,
    ) -> List[ModuleEvent]:
        """
        获取事件历史
        
        Args:
            event_type: 事件类型过滤器
            limit: 最大数量
            
        Returns:
            List[ModuleEvent]: 事件列表
        """
        with self._lock:
            history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        return history[-limit:]
    
    def clear_history(self) -> None:
        """清除事件历史"""
        with self._lock:
            self._event_history.clear()
            self._delivery_history.clear()
    
    # =====================================================================
    # 统计信息
    # =====================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self._lock:
            event_type_distribution = {
                event_type.name: len(subscribers)
                for event_type, subscribers in self._event_type_to_subscribers.items()
            }
            
            return {
                "total_subscribers": len(self._subscribers),
                "event_type_distribution": event_type_distribution,
                "history_size": len(self._event_history),
                "delivery_history_size": len(self._delivery_history),
                "async_mode": self._config.async_mode,
                "queue_size": self._event_queue.qsize() if self._config.async_mode else 0,
            }
    
    def __repr__(self) -> str:
        return f"EventBus(subscribers={len(self._subscribers)}, async={self._config.async_mode})"


# =============================================================================
# 6. 模块事件助手 (Module Event Helper)
# =============================================================================

class ModuleEventHelper:
    """
    模块事件助手
    
    提供便捷的模块事件创建和发布方法
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        初始化
        
        Args:
            event_bus: 事件总线，如果为None则使用单例
        """
        self._event_bus = event_bus or EventBus.instance()
    
    def emit_init_started(self, module_id: ModuleID, task_id: Optional[TaskID] = None) -> None:
        """发射初始化开始事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_STARTED,
            module_id=module_id,
            task_id=task_id,
        )
        self._event_bus.publish(event)
    
    def emit_init_completed(self, module_id: ModuleID, task_id: Optional[TaskID] = None) -> None:
        """发射初始化完成事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_COMPLETED,
            module_id=module_id,
            task_id=task_id,
        )
        self._event_bus.publish(event)
    
    def emit_init_failed(
        self,
        module_id: ModuleID,
        error_code: str,
        error_detail: str,
        task_id: Optional[TaskID] = None,
    ) -> None:
        """发射初始化失败事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_FAILED,
            module_id=module_id,
            task_id=task_id,
            data={"error_code": error_code, "error_detail": error_detail},
        )
        self._event_bus.publish(event)
    
    def emit_run_started(self, module_id: ModuleID, task_id: Optional[TaskID] = None) -> None:
        """发射执行开始事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.RUN_STARTED,
            module_id=module_id,
            task_id=task_id,
        )
        self._event_bus.publish(event)
    
    def emit_run_completed(
        self,
        module_id: ModuleID,
        execution_time_ms: int,
        task_id: Optional[TaskID] = None,
    ) -> None:
        """发射执行完成事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.RUN_COMPLETED,
            module_id=module_id,
            task_id=task_id,
            data={"execution_time_ms": execution_time_ms},
        )
        self._event_bus.publish(event)
    
    def emit_run_failed(
        self,
        module_id: ModuleID,
        error_code: str,
        error_detail: str,
        task_id: Optional[TaskID] = None,
    ) -> None:
        """发射执行失败事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.RUN_FAILED,
            module_id=module_id,
            task_id=task_id,
            data={"error_code": error_code, "error_detail": error_detail},
        )
        self._event_bus.publish(event)
    
    def emit_state_changed(
        self,
        module_id: ModuleID,
        old_state: ModuleState,
        new_state: ModuleState,
        task_id: Optional[TaskID] = None,
    ) -> None:
        """发射状态变更事件"""
        event = ModuleEvent(
            event_type=ModuleEventType.STATE_CHANGED,
            module_id=module_id,
            task_id=task_id,
            data={"old_state": old_state.name, "new_state": new_state.name},
        )
        self._event_bus.publish(event)


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 异常类型
    "EventBusError",
    "EventTypeNotFoundError",
    "SubscriberNotFoundError",
    "EventDeliveryError",
    
    # 数据类
    "SubscriberInfo",
    "EventDeliveryRecord",
    "EventBusConfig",
    
    # 事件总线
    "EventBus",
    
    # 助手
    "ModuleEventHelper",
]
