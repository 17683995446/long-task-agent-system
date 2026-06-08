"""
阶段60：四级队列工作模块
Level4QueueWorkerModule

职责定义：
- 队列消费
- 消息处理
- 死信处理
- 任务调度
- 并发控制
- 消息重试
"""

from typing import Optional, Dict, Any, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import time

from core.base_module import ExecuteModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class QueueType(Enum):
    """队列类型"""
    FIFO = "fifo"
    PRIORITY = "priority"
    DELAYED = "delayed"
    DEAD_LETTER = "dead_letter"


@dataclass
class Message:
    """消息"""
    message_id: str
    queue_name: str
    payload: Any
    priority: int = 0
    delay_seconds: int = 0
    max_retries: int = 3
    retry_count: int = 0
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "queue_name": self.queue_name,
            "payload": str(self.payload)[:200] if self.payload else None,
            "priority": self.priority,
            "delay_seconds": self.delay_seconds,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Queue:
    """队列"""
    queue_name: str
    queue_type: QueueType
    max_size: int = 1000
    messages: List[Message] = field(default_factory=list)
    processed_count: int = 0
    failed_count: int = 0
    dead_letter_count: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_name": self.queue_name,
            "queue_type": self.queue_type.value,
            "max_size": self.max_size,
            "message_count": len(self.messages),
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "dead_letter_count": self.dead_letter_count,
            "enabled": self.enabled,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    def size(self) -> int:
        """获取队列大小"""
        return len(self.messages)

    def is_full(self) -> bool:
        """队列是否已满"""
        return len(self.messages) >= self.max_size

    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self.messages) == 0


@dataclass
class Worker:
    """工作器"""
    worker_id: str
    queue_name: str
    handler: Optional[str] = None
    concurrency: int = 1
    max_messages: int = 100
    enabled: bool = True
    processed_count: int = 0
    failed_count: int = 0
    running: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "queue_name": self.queue_name,
            "handler": self.handler,
            "concurrency": self.concurrency,
            "max_messages": self.max_messages,
            "enabled": self.enabled,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "running": self.running,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }


@dataclass
class ProcessingRecord:
    """处理记录"""
    record_id: str
    message_id: str
    worker_id: str
    queue_name: str
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "message_id": self.message_id,
            "worker_id": self.worker_id,
            "queue_name": self.queue_name,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


class Level4QueueWorkerModule(ExecuteModuleBase):
    """
    四级队列工作模块

    职责：
    1. 队列管理（创建、删除、监控）
    2. 消息生产与消费
    3. 工作器管理
    4. 死信处理
    5. 消息重试机制
    6. 并发控制
    7. 处理记录与统计
    """

    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4QueueWorkerModule"
        self._logger = Logger(f"L4QW_{self.module_id}")

        # 队列存储
        self._queues: Dict[str, Queue] = {}
        # 工作器存储
        self._workers: Dict[str, Worker] = {}
        # 消息存储（全局）
        self._messages: Dict[str, Message] = {}
        # 处理记录
        self._records: List[ProcessingRecord] = []
        # 消息处理器注册表
        self._handlers: Dict[str, Callable] = {}
        # 死信队列
        self._dead_letter_queue: List[Message] = []
        # 锁
        self._lock = threading.Lock()

    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级队列工作模块初始化开始")

            # 1. 加载配置
            self._load_config(request)

            # 2. 初始化存储
            self._queues = {}
            self._workers = {}
            self._messages = {}
            self._records = []
            self._handlers = {}
            self._dead_letter_queue = []

            # 3. 创建默认队列
            self._create_default_queues()

            self._logger.info("四级队列工作模块初始化完成")

            return InitResult.success_result(
                module_id=self.module_id,
                message="四级队列工作模块初始化成功"
            )

        except Exception as e:
            self._logger.error(f"四级队列工作模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4QW_INIT_FAILED",
                error_detail=str(e)
            )

    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_max_size": 1000,
            "default_max_retries": 3,
            "default_retry_delay": 5,
            "max_records": 10000,
            "dead_letter_max_size": 1000,
            "auto_process": False,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("queue_worker_config", {})
            self._config.update(custom_config)

    def _create_default_queues(self) -> None:
        """创建默认队列"""
        default_queues = [
            Queue(
                queue_name="default",
                queue_type=QueueType.FIFO,
                max_size=self._config.get("default_max_size", 1000),
            ),
            Queue(
                queue_name="priority",
                queue_type=QueueType.PRIORITY,
                max_size=self._config.get("default_max_size", 1000),
            ),
            Queue(
                queue_name="delayed",
                queue_type=QueueType.DELAYED,
                max_size=self._config.get("default_max_size", 1000),
            ),
            Queue(
                queue_name="dead_letter",
                queue_type=QueueType.DEAD_LETTER,
                max_size=self._config.get("dead_letter_max_size", 1000),
            ),
        ]
        for queue in default_queues:
            self._queues[queue.queue_name] = queue

    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级队列工作模块执行开始")

        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()

            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_queue")

            if operation == "create_queue":
                result = self._create_queue_operation(input_data)
            elif operation == "publish_message":
                result = self._publish_message_operation(input_data)
            elif operation == "consume_message":
                result = self._consume_message_operation(input_data)
            elif operation == "create_worker":
                result = self._create_worker_operation(input_data)
            elif operation == "start_worker":
                result = self._start_worker_operation(input_data)
            elif operation == "stop_worker":
                result = self._stop_worker_operation(input_data)
            elif operation == "get_queue":
                result = self._get_queue_operation(input_data)
            elif operation == "get_message":
                result = self._get_message_operation(input_data)
            elif operation == "retry_message":
                result = self._retry_message_operation(input_data)
            elif operation == "get_dead_letters":
                result = self._get_dead_letters_operation(input_data)
            elif operation == "get_records":
                result = self._get_records_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "register_handler":
                result = self._register_handler_operation(input_data)
            elif operation == "list_queues":
                result = self._list_queues_operation()
            else:
                result = {"error": f"未知操作: {operation}"}

            self._logger.info("四级队列工作模块执行完成")

            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4QueueWorkerModule",
                    "queue_worker_summary": {
                        "total_queues": len(self._queues),
                        "total_workers": len(self._workers),
                        "total_messages": len(self._messages),
                        "total_records": len(self._records),
                        "dead_letter_count": len(self._dead_letter_queue),
                    },
                },
                message="四级队列工作模块执行成功"
            )

        except Exception as e:
            self._logger.error(f"四级队列工作模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4QW_EXECUTION_FAILED",
                error_detail=str(e)
            )

    def _create_queue_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建队列"""
        queue_name = input_data.get("queue_name")
        queue_type = QueueType(input_data.get("queue_type", "fifo"))
        max_size = input_data.get("max_size", self._config.get("default_max_size", 1000))

        if not queue_name:
            return {"operation": "create_queue", "error": "队列名称不能为空", "success": False}

        if queue_name in self._queues:
            return {"operation": "create_queue", "error": "队列已存在", "success": False}

        queue = Queue(
            queue_name=queue_name,
            queue_type=queue_type,
            max_size=max_size,
            metadata=input_data.get("metadata", {}),
        )
        self._queues[queue_name] = queue

        return {
            "operation": "create_queue",
            "queue_name": queue_name,
            "queue_type": queue_type.value,
            "max_size": max_size,
            "created": True,
        }

    def _publish_message_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """发布消息"""
        import uuid

        queue_name = input_data.get("queue_name", "default")
        payload = input_data.get("payload")

        if queue_name not in self._queues:
            return {"operation": "publish_message", "error": f"队列 {queue_name} 不存在", "success": False}

        queue = self._queues[queue_name]
        if queue.is_full():
            return {"operation": "publish_message", "error": "队列已满", "success": False}

        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            queue_name=queue_name,
            payload=payload,
            priority=input_data.get("priority", 0),
            delay_seconds=input_data.get("delay_seconds", 0),
            max_retries=input_data.get("max_retries", self._config.get("default_max_retries", 3)),
            metadata=input_data.get("metadata", {}),
        )

        # 计算调度时间
        if message.delay_seconds > 0:
            message.scheduled_at = datetime.now() + timedelta(seconds=message.delay_seconds)

        self._messages[message_id] = message
        queue.messages.append(message)

        # 优先级队列按优先级排序
        if queue.queue_type == QueueType.PRIORITY:
            queue.messages.sort(key=lambda m: m.priority, reverse=True)

        return {
            "operation": "publish_message",
            "message_id": message_id,
            "queue_name": queue_name,
            "queue_size": queue.size(),
            "published": True,
        }

    def _consume_message_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """消费消息"""
        import uuid
        import time

        queue_name = input_data.get("queue_name", "default")
        worker_id = input_data.get("worker_id")
        auto_ack = input_data.get("auto_ack", True)

        if queue_name not in self._queues:
            return {"operation": "consume_message", "error": f"队列 {queue_name} 不存在", "success": False}

        queue = self._queues[queue_name]
        if queue.is_empty():
            return {"operation": "consume_message", "queue_name": queue_name, "message": None, "empty": True}

        # 查找可消费的消息
        now = datetime.now()
        eligible_messages = [
            m for m in queue.messages
            if m.status == MessageStatus.PENDING
            and (m.scheduled_at is None or m.scheduled_at <= now)
        ]

        if not eligible_messages:
            return {"operation": "consume_message", "queue_name": queue_name, "message": None, "no_eligible": True}

        # 按优先级和创建时间排序
        eligible_messages.sort(key=lambda m: (-m.priority, m.created_at))
        message = eligible_messages[0]

        # 更新消息状态
        message.status = MessageStatus.PROCESSING
        message.processed_at = now

        # 记录处理
        record_id = str(uuid.uuid4())
        record = ProcessingRecord(
            record_id=record_id,
            message_id=message.message_id,
            worker_id=worker_id or "manual",
            queue_name=queue_name,
            success=False,
            started_at=now,
        )
        self._records.append(record)

        # 尝试处理消息
        start_time = time.time()
        try:
            handler = self._handlers.get(queue_name)
            if handler:
                handler(message.payload)
                message.status = MessageStatus.COMPLETED
                record.success = True
                queue.processed_count += 1
            else:
                # 无处理器，标记为完成
                message.status = MessageStatus.COMPLETED
                record.success = True
                queue.processed_count += 1

            record.completed_at = datetime.now()
            record.processing_time_ms = (time.time() - start_time) * 1000

            # 从队列中移除
            if auto_ack and message in queue.messages:
                queue.messages.remove(message)

            return {
                "operation": "consume_message",
                "message_id": message.message_id,
                "queue_name": queue_name,
                "status": message.status.value,
                "success": True,
                "processing_time_ms": record.processing_time_ms,
            }

        except Exception as e:
            message.status = MessageStatus.FAILED
            message.error = str(e)
            message.retry_count += 1
            record.error = str(e)
            record.completed_at = datetime.now()
            record.processing_time_ms = (time.time() - start_time) * 1000
            queue.failed_count += 1

            # 检查是否需要重试
            if message.retry_count < message.max_retries:
                message.status = MessageStatus.RETRYING
                retry_delay = self._config.get("default_retry_delay", 5)
                message.scheduled_at = datetime.now() + timedelta(seconds=retry_delay * message.retry_count)
            else:
                # 移入死信队列
                message.status = MessageStatus.DEAD_LETTER
                self._dead_letter_queue.append(message)
                queue.dead_letter_count += 1
                if message in queue.messages:
                    queue.messages.remove(message)

                # 限制死信队列大小
                dlq_max = self._config.get("dead_letter_max_size", 1000)
                if len(self._dead_letter_queue) > dlq_max:
                    self._dead_letter_queue = self._dead_letter_queue[-dlq_max:]

            return {
                "operation": "consume_message",
                "message_id": message.message_id,
                "queue_name": queue_name,
                "status": message.status.value,
                "success": False,
                "error": str(e),
                "retry_count": message.retry_count,
            }

    def _create_worker_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建工作器"""
        import uuid

        worker_id = str(uuid.uuid4())
        queue_name = input_data.get("queue_name", "default")

        if queue_name not in self._queues:
            return {"operation": "create_worker", "error": f"队列 {queue_name} 不存在", "success": False}

        worker = Worker(
            worker_id=worker_id,
            queue_name=queue_name,
            handler=input_data.get("handler"),
            concurrency=input_data.get("concurrency", 1),
            max_messages=input_data.get("max_messages", 100),
            metadata=input_data.get("metadata", {}),
        )
        self._workers[worker_id] = worker

        return {
            "operation": "create_worker",
            "worker_id": worker_id,
            "queue_name": queue_name,
            "created": True,
        }

    def _start_worker_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """启动工作器"""
        worker_id = input_data.get("worker_id")

        if not worker_id or worker_id not in self._workers:
            return {"operation": "start_worker", "error": "工作器不存在", "success": False}

        worker = self._workers[worker_id]
        if not worker.enabled:
            return {"operation": "start_worker", "error": "工作器已禁用", "success": False}

        worker.running = True
        worker.last_activity = datetime.now()

        # 模拟处理消息
        processed = 0
        for _ in range(worker.max_messages):
            result = self._consume_message_operation({
                "queue_name": worker.queue_name,
                "worker_id": worker_id,
                "auto_ack": True,
            })
            if result.get("empty") or result.get("no_eligible"):
                break
            if result.get("success"):
                processed += 1
                worker.processed_count += 1
            else:
                worker.failed_count += 1

        worker.running = False
        worker.last_activity = datetime.now()

        return {
            "operation": "start_worker",
            "worker_id": worker_id,
            "processed": processed,
            "running": False,
        }

    def _stop_worker_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """停止工作器"""
        worker_id = input_data.get("worker_id")

        if not worker_id or worker_id not in self._workers:
            return {"operation": "stop_worker", "error": "工作器不存在", "success": False}

        worker = self._workers[worker_id]
        worker.running = False
        worker.last_activity = datetime.now()

        return {
            "operation": "stop_worker",
            "worker_id": worker_id,
            "stopped": True,
        }

    def _get_queue_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取队列信息"""
        queue_name = input_data.get("queue_name")

        if not queue_name:
            return {
                "operation": "get_queue",
                "queues": [q.to_dict() for q in self._queues.values()],
            }

        if queue_name not in self._queues:
            return {"operation": "get_queue", "error": f"队列 {queue_name} 不存在"}

        queue = self._queues[queue_name]
        return {
            "operation": "get_queue",
            "queue": queue.to_dict(),
            "messages": [m.to_dict() for m in queue.messages[:50]],
        }

    def _get_message_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取消息信息"""
        message_id = input_data.get("message_id")

        if not message_id or message_id not in self._messages:
            return {"operation": "get_message", "error": "消息不存在"}

        message = self._messages[message_id]
        return {
            "operation": "get_message",
            "message": message.to_dict(),
        }

    def _retry_message_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """重试消息"""
        message_id = input_data.get("message_id")
        queue_name = input_data.get("queue_name", "default")

        if not message_id or message_id not in self._messages:
            return {"operation": "retry_message", "error": "消息不存在", "success": False}

        message = self._messages[message_id]
        message.status = MessageStatus.PENDING
        message.retry_count = 0
        message.error = None
        message.scheduled_at = None

        # 重新放入队列
        if queue_name in self._queues:
            queue = self._queues[queue_name]
            if not queue.is_full() and message not in queue.messages:
                queue.messages.append(message)
                message.queue_name = queue_name

        return {
            "operation": "retry_message",
            "message_id": message_id,
            "new_status": message.status.value,
            "retried": True,
        }

    def _get_dead_letters_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取死信消息"""
        limit = input_data.get("limit", 100)

        messages = sorted(
            self._dead_letter_queue,
            key=lambda m: m.created_at,
            reverse=True
        )[:limit]

        return {
            "operation": "get_dead_letters",
            "total": len(self._dead_letter_queue),
            "returned": len(messages),
            "messages": [m.to_dict() for m in messages],
        }

    def _get_records_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取处理记录"""
        limit = input_data.get("limit", 100)
        queue_name = input_data.get("queue_name")
        success_only = input_data.get("success_only", False)

        records = self._records
        if queue_name:
            records = [r for r in records if r.queue_name == queue_name]
        if success_only:
            records = [r for r in records if r.success]

        records = sorted(records, key=lambda r: r.started_at, reverse=True)[:limit]

        return {
            "operation": "get_records",
            "total": len(self._records),
            "returned": len(records),
            "records": [r.to_dict() for r in records],
        }

    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_messages = sum(q.size() for q in self._queues.values())
        total_processed = sum(q.processed_count for q in self._queues.values())
        total_failed = sum(q.failed_count for q in self._queues.values())

        queue_stats = {}
        for name, queue in self._queues.items():
            queue_stats[name] = {
                "size": queue.size(),
                "processed": queue.processed_count,
                "failed": queue.failed_count,
                "dead_letters": queue.dead_letter_count,
            }

        active_workers = sum(1 for w in self._workers.values() if w.running)

        return {
            "operation": "get_stats",
            "total_queues": len(self._queues),
            "total_workers": len(self._workers),
            "active_workers": active_workers,
            "total_messages": total_messages,
            "total_processed": total_processed,
            "total_failed": total_failed,
            "success_rate": total_processed / (total_processed + total_failed) if (total_processed + total_failed) > 0 else 0,
            "dead_letter_count": len(self._dead_letter_queue),
            "queue_stats": queue_stats,
            "total_records": len(self._records),
        }

    def _register_handler_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册消息处理器"""
        queue_name = input_data.get("queue_name")
        handler_name = input_data.get("handler_name")

        if not queue_name or not handler_name:
            return {"operation": "register_handler", "error": "队列名称和处理器名称不能为空", "success": False}

        # 注意：实际处理器函数需要在代码中注册，这里仅记录
        return {
            "operation": "register_handler",
            "queue_name": queue_name,
            "handler_name": handler_name,
            "registered": True,
        }

    def _list_queues_operation(self) -> Dict[str, Any]:
        """列出所有队列"""
        return {
            "operation": "list_queues",
            "queues": [q.to_dict() for q in self._queues.values()],
        }

    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级队列工作模块校验开始")

        checks = []

        if isinstance(self._queues, dict) and len(self._queues) > 0:
            checks.append("queues_valid")
        if isinstance(self._workers, dict):
            checks.append("workers_valid")
        if isinstance(self._messages, dict):
            checks.append("messages_valid")
        if isinstance(self._records, list):
            checks.append("records_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._dead_letter_queue, list):
            checks.append("dead_letter_valid")

        all_passed = len(checks) == 6

        if all_passed:
            return CheckResult.passed_result(
                check_type="queue_worker_validation",
                message="四级队列工作模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="queue_worker_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )

    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("queue_count", len(self._queues))
        snapshot.set_state("worker_count", len(self._workers))
        snapshot.set_state("message_count", len(self._messages))
        snapshot.set_state("record_count", len(self._records))
        snapshot.set_state("dead_letter_count", len(self._dead_letter_queue))
        snapshot.metadata["module_type"] = "Level4QueueWorkerModule"

    # 公共接口
    def create_queue(self, name: str, queue_type: str = "fifo", max_size: int = 1000) -> str:
        """创建队列"""
        queue = Queue(
            queue_name=name,
            queue_type=QueueType(queue_type),
            max_size=max_size,
        )
        self._queues[name] = queue
        return name

    def publish(self, queue_name: str, payload: Any, priority: int = 0,
                delay_seconds: int = 0, max_retries: int = 3) -> str:
        """发布消息"""
        import uuid
        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            queue_name=queue_name,
            payload=payload,
            priority=priority,
            delay_seconds=delay_seconds,
            max_retries=max_retries,
        )
        if delay_seconds > 0:
            message.scheduled_at = datetime.now() + timedelta(seconds=delay_seconds)
        self._messages[message_id] = message
        if queue_name in self._queues:
            self._queues[queue_name].messages.append(message)
            if self._queues[queue_name].queue_type == QueueType.PRIORITY:
                self._queues[queue_name].messages.sort(key=lambda m: m.priority, reverse=True)
        return message_id

    def consume(self, queue_name: str, handler: Callable = None) -> Optional[Message]:
        """消费消息"""
        if queue_name not in self._queues:
            return None
        queue = self._queues[queue_name]
        now = datetime.now()
        eligible = [
            m for m in queue.messages
            if m.status == MessageStatus.PENDING
            and (m.scheduled_at is None or m.scheduled_at <= now)
        ]
        if not eligible:
            return None
        eligible.sort(key=lambda m: (-m.priority, m.created_at))
        message = eligible[0]
        message.status = MessageStatus.PROCESSING
        message.processed_at = now
        return message

    def register_handler(self, queue_name: str, handler: Callable) -> None:
        """注册消息处理器"""
        self._handlers[queue_name] = handler

    def get_queue_stats(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """获取队列统计"""
        if queue_name not in self._queues:
            return None
        queue = self._queues[queue_name]
        return {
            "name": queue.queue_name,
            "type": queue.queue_type.value,
            "size": queue.size(),
            "processed": queue.processed_count,
            "failed": queue.failed_count,
            "dead_letters": queue.dead_letter_count,
        }

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4QueueWorkerModule",
    "MessageStatus",
    "QueueType",
    "Message",
    "Queue",
    "Worker",
    "ProcessingRecord",
]
