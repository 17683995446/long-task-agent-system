"""
阶段51：四级任务执行模块
Level4TaskExecutorModule

职责定义：
- 任务执行
- 任务调度
- 执行监控
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

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


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Task:
    """任务定义"""
    task_id: str
    name: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_count: int = 0
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority.name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "metadata": self.metadata,
            "dependencies": self.dependencies,
        }


@dataclass
class TaskSchedule:
    """任务调度"""
    schedule_id: str
    task_id: str
    scheduled_at: datetime
    execute_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    recurring: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "task_id": self.task_id,
            "scheduled_at": self.scheduled_at.isoformat(),
            "execute_at": self.execute_at.isoformat() if self.execute_at else None,
            "cron_expression": self.cron_expression,
            "recurring": self.recurring,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionRecord:
    """执行记录"""
    record_id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata,
        }


class Level4TaskExecutorModule(ExecuteModuleBase):
    """
    四级任务执行模块
    
    职责：
    1. 任务执行
    2. 任务调度
    3. 执行监控
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4TaskExecutorModule"
        self._logger = Logger(f"L4TE_{self.module_id}")
        
        # 任务存储
        self._tasks: Dict[str, Task] = {}
        # 调度存储
        self._schedules: Dict[str, TaskSchedule] = {}
        # 执行记录
        self._execution_records: List[ExecutionRecord] = []
        # 任务处理器
        self._task_handlers: Dict[str, Callable] = {}
        # 执行队列
        self._execution_queue: List[str] = []
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级任务执行模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._tasks = {}
            self._schedules = {}
            self._execution_records = []
            self._task_handlers = {}
            self._execution_queue = []
            
            self._logger.info("四级任务执行模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级任务执行模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级任务执行模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4TE_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_timeout": 300,
            "max_concurrent": 10,
            "auto_retry": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("task_executor_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级任务执行模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_task")
            
            if operation == "create_task":
                result = self._create_task_operation(input_data)
            elif operation == "execute_task":
                result = self._execute_task_operation(input_data)
            elif operation == "schedule_task":
                result = self._schedule_task_operation(input_data)
            elif operation == "cancel_task":
                result = self._cancel_task_operation(input_data)
            elif operation == "get_task":
                result = self._get_task_operation(input_data)
            elif operation == "get_records":
                result = self._get_records_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "retry_task":
                result = self._retry_task_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级任务执行模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4TaskExecutorModule",
                    "task_summary": {
                        "total_tasks": len(self._tasks),
                        "pending_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
                        "running_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING),
                        "completed_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED),
                        "failed_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED),
                        "total_schedules": len(self._schedules),
                        "total_records": len(self._execution_records),
                    },
                },
                message="四级任务执行模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级任务执行模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4TE_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_task_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务"""
        task_id = input_data.get("task_id", str(uuid.uuid4()))
        
        task = Task(
            task_id=task_id,
            name=input_data.get("name", f"task_{task_id[:8]}"),
            status=TaskStatus.PENDING,
            priority=TaskPriority[input_data.get("priority", "NORMAL").upper()],
            created_at=datetime.now(),
            timeout_seconds=input_data.get("timeout_seconds", self._config.get("default_timeout", 300)),
            max_retries=input_data.get("max_retries", 3),
            metadata=input_data.get("metadata", {}),
            dependencies=input_data.get("dependencies", []),
        )
        self._tasks[task_id] = task
        self._execution_queue.append(task_id)
        
        # 按优先级排序队列
        self._execution_queue.sort(
            key=lambda tid: (self._tasks[tid].priority.value, self._tasks[tid].created_at)
        )
        
        return {
            "operation": "create_task",
            "task_id": task_id,
            "status": task.status.value,
            "created": True,
        }
    
    def _execute_task_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        task_id = input_data.get("task_id")
        
        if not task_id or task_id not in self._tasks:
            return {"operation": "execute_task", "error": "任务不存在", "success": False}
        
        task = self._tasks[task_id]
        
        # 检查依赖
        for dep_id in task.dependencies:
            if dep_id in self._tasks:
                dep_task = self._tasks[dep_id]
                if dep_task.status not in [TaskStatus.COMPLETED]:
                    return {
                        "operation": "execute_task",
                        "error": f"依赖任务 {dep_id} 未完成",
                        "success": False,
                    }
        
        record = ExecutionRecord(
            record_id=str(uuid.uuid4()),
            task_id=task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
        )
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.retry_count += 1
        
        try:
            # 模拟任务执行
            handler_name = task.metadata.get("handler")
            if handler_name and handler_name in self._task_handlers:
                handler = self._task_handlers[handler_name]
                task.result = handler(task.metadata.get("params", {}))
            else:
                # 默认执行逻辑
                task.result = {"executed": True, "task_id": task_id}
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            record.status = TaskStatus.COMPLETED
            record.completed_at = datetime.now()
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            record.status = TaskStatus.FAILED
            record.completed_at = datetime.now()
            record.error = str(e)
            
            # 自动重试
            if self._config.get("auto_retry", True) and task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                self._execution_queue.append(task_id)
        
        if task.completed_at and task.started_at:
            record.duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000
        
        self._execution_records.append(record)
        
        return {
            "operation": "execute_task",
            "task_id": task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count,
        }
    
    def _schedule_task_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """调度任务"""
        task_id = input_data.get("task_id")
        execute_at_str = input_data.get("execute_at")
        cron = input_data.get("cron_expression")
        
        if not task_id or task_id not in self._tasks:
            return {"operation": "schedule_task", "error": "任务不存在", "success": False}
        
        execute_at = None
        if execute_at_str:
            execute_at = datetime.fromisoformat(execute_at_str)
        
        schedule = TaskSchedule(
            schedule_id=str(uuid.uuid4()),
            task_id=task_id,
            scheduled_at=datetime.now(),
            execute_at=execute_at,
            cron_expression=cron,
            recurring=input_data.get("recurring", False),
            metadata=input_data.get("metadata", {}),
        )
        self._schedules[schedule.schedule_id] = schedule
        
        return {
            "operation": "schedule_task",
            "schedule_id": schedule.schedule_id,
            "task_id": task_id,
            "scheduled": True,
        }
    
    def _cancel_task_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """取消任务"""
        task_id = input_data.get("task_id")
        
        if not task_id or task_id not in self._tasks:
            return {"operation": "cancel_task", "error": "任务不存在", "success": False}
        
        task = self._tasks[task_id]
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return {"operation": "cancel_task", "error": "任务已完成或已取消", "success": False}
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        if task_id in self._execution_queue:
            self._execution_queue.remove(task_id)
        
        return {"operation": "cancel_task", "task_id": task_id, "cancelled": True}
    
    def _get_task_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取任务"""
        task_id = input_data.get("task_id")
        
        if not task_id or task_id not in self._tasks:
            return {"operation": "get_task", "error": "任务不存在"}
        
        task = self._tasks[task_id]
        return {"operation": "get_task", "task": task.to_dict()}
    
    def _get_records_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取执行记录"""
        limit = input_data.get("limit", 50)
        task_id = input_data.get("task_id")
        
        records = self._execution_records
        if task_id:
            records = [r for r in records if r.task_id == task_id]
        
        records = sorted(records, key=lambda r: r.started_at, reverse=True)[:limit]
        
        return {
            "operation": "get_records",
            "total": len(self._execution_records),
            "returned": len(records),
            "records": [r.to_dict() for r in records],
        }
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts = {}
        for task in self._tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_duration = sum(
            r.duration_ms for r in self._execution_records if r.duration_ms
        )
        avg_duration = total_duration / len(self._execution_records) if self._execution_records else 0
        
        return {
            "operation": "get_stats",
            "total_tasks": len(self._tasks),
            "status_counts": status_counts,
            "total_records": len(self._execution_records),
            "avg_duration_ms": avg_duration,
            "queue_length": len(self._execution_queue),
            "total_schedules": len(self._schedules),
        }
    
    def _retry_task_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """重试任务"""
        task_id = input_data.get("task_id")
        
        if not task_id or task_id not in self._tasks:
            return {"operation": "retry_task", "error": "任务不存在", "success": False}
        
        task = self._tasks[task_id]
        
        if task.retry_count >= task.max_retries:
            return {"operation": "retry_task", "error": "已达到最大重试次数", "success": False}
        
        task.status = TaskStatus.PENDING
        task.error = None
        task.completed_at = None
        task.started_at = None
        
        if task_id not in self._execution_queue:
            self._execution_queue.append(task_id)
        
        return {
            "operation": "retry_task",
            "task_id": task_id,
            "retry_count": task.retry_count,
            "queued": True,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级任务执行模块校验开始")
        
        checks = []
        
        if isinstance(self._tasks, dict):
            checks.append("tasks_valid")
        if isinstance(self._schedules, dict):
            checks.append("schedules_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._execution_records, list):
            checks.append("records_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="task_executor_validation",
                message="四级任务执行模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="task_executor_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("tasks", {tid: t.to_dict() for tid, t in self._tasks.items()})
        snapshot.set_state("schedules", {sid: s.to_dict() for sid, s in self._schedules.items()})
        snapshot.set_state("record_count", len(self._execution_records))
        snapshot.metadata["module_type"] = "Level4TaskExecutorModule"
    
    # 公共接口
    def create_task(self, name: str, priority: TaskPriority = TaskPriority.NORMAL,
                    timeout_seconds: int = 300, metadata: Dict[str, Any] = None) -> Task:
        """创建任务"""
        task = Task(
            task_id=str(uuid.uuid4()),
            name=name,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )
        self._tasks[task.task_id] = task
        self._execution_queue.append(task.task_id)
        return task
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """执行任务"""
        return self._execute_task_operation({"task_id": task_id})
    
    def register_handler(self, name: str, handler: Callable) -> None:
        """注册任务处理器"""
        self._task_handlers[name] = handler
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4TaskExecutorModule",
    "Task",
    "TaskSchedule",
    "ExecutionRecord",
    "TaskStatus",
    "TaskPriority",
]
