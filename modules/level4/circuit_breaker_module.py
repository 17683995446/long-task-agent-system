"""
阶段43：四级熔断器模块
Level4CircuitBreakerModule

职责定义：
- 熔断器管理
- 状态转换
- 故障检测
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

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


class CircuitBreakerState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerEvent(Enum):
    """熔断器事件"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    REJECTION = "rejection"


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_duration: int = 30
    half_open_max_calls: int = 3
    sliding_window_size: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "timeout_duration": self.timeout_duration,
            "half_open_max_calls": self.half_open_max_calls,
            "sliding_window_size": self.sliding_window_size,
            "metadata": self.metadata,
        }


@dataclass
class CircuitBreaker:
    """熔断器"""
    breaker_id: str
    name: str
    state: CircuitBreakerState
    config: CircuitBreakerConfig
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.now)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    half_open_calls: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "breaker_id": self.breaker_id,
            "name": self.name,
            "state": self.state.value,
            "config": self.config.to_dict(),
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat(),
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "half_open_calls": self.half_open_calls,
            "metadata": self.metadata,
        }


@dataclass
class CircuitBreakerRecord:
    """熔断器记录"""
    record_id: str
    breaker_id: str
    event: CircuitBreakerEvent
    timestamp: datetime
    state_before: CircuitBreakerState
    state_after: CircuitBreakerState
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "breaker_id": self.breaker_id,
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "state_before": self.state_before.value,
            "state_after": self.state_after.value,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class Level4CircuitBreakerModule(ExecuteModuleBase):
    """
    四级熔断器模块
    
    职责：
    1. 熔断器管理
    2. 状态转换
    3. 故障检测
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4CircuitBreakerModule"
        self._logger = Logger(f"L4CB_{self.module_id}")
        
        # 熔断器存储
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        # 熔断器记录
        self._records: List[CircuitBreakerRecord] = []
        # 滑动窗口记录
        self._window_records: Dict[str, List[CircuitBreakerEvent]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级熔断器模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._circuit_breakers = {}
            self._records = []
            self._window_records = {}
            
            self._logger.info("四级熔断器模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级熔断器模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级熔断器模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4CB_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_failure_threshold": 5,
            "default_success_threshold": 3,
            "default_timeout_duration": 30,
            "log_records": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("circuit_breaker_config", {})
            self._config.update(custom_config)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级熔断器模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "create_breaker")
            
            if operation == "create_breaker":
                result = self._create_breaker_operation(input_data)
            elif operation == "record_event":
                result = self._record_event_operation(input_data)
            elif operation == "can_execute":
                result = self._can_execute_operation(input_data)
            elif operation == "get_breaker":
                result = self._get_breaker_operation(input_data)
            elif operation == "get_records":
                result = self._get_records_operation(input_data)
            elif operation == "reset_breaker":
                result = self._reset_breaker_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "list_breakers":
                result = self._list_breakers_operation()
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级熔断器模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4CircuitBreakerModule",
                    "circuit_breaker_summary": {
                        "total_breakers": len(self._circuit_breakers),
                        "open_breakers": sum(1 for b in self._circuit_breakers.values() if b.state == CircuitBreakerState.OPEN),
                        "total_records": len(self._records),
                    },
                },
                message="四级熔断器模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级熔断器模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4CB_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _create_breaker_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建熔断器"""
        import uuid
        
        breaker_id = input_data.get("breaker_id", str(uuid.uuid4()))
        config = CircuitBreakerConfig(
            failure_threshold=input_data.get("failure_threshold", self._config.get("default_failure_threshold", 5)),
            success_threshold=input_data.get("success_threshold", self._config.get("default_success_threshold", 3)),
            timeout_duration=input_data.get("timeout_duration", self._config.get("default_timeout_duration", 30)),
            half_open_max_calls=input_data.get("half_open_max_calls", 3),
            sliding_window_size=input_data.get("sliding_window_size", 10),
            metadata=input_data.get("config_metadata", {}),
        )
        
        breaker = CircuitBreaker(
            breaker_id=breaker_id,
            name=input_data.get("name", f"breaker_{breaker_id[:8]}"),
            state=CircuitBreakerState.CLOSED,
            config=config,
            metadata=input_data.get("metadata", {}),
        )
        self._circuit_breakers[breaker_id] = breaker
        self._window_records[breaker_id] = []
        
        return {
            "operation": "create_breaker",
            "breaker_id": breaker_id,
            "state": breaker.state.value,
            "created": True,
        }
    
    def _record_event_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """记录事件"""
        breaker_id = input_data.get("breaker_id")
        event_str = input_data.get("event", "success")
        
        if not breaker_id or breaker_id not in self._circuit_breakers:
            return {"operation": "record_event", "error": "熔断器不存在", "success": False}
        
        try:
            event = CircuitBreakerEvent(event_str)
        except ValueError:
            return {"operation": "record_event", "error": f"无效事件: {event_str}", "success": False}
        
        breaker = self._circuit_breakers[breaker_id]
        state_before = breaker.state
        
        # 更新滑动窗口
        self._window_records[breaker_id].append(event)
        window_size = breaker.config.sliding_window_size
        if len(self._window_records[breaker_id]) > window_size:
            self._window_records[breaker_id] = self._window_records[breaker_id][-window_size:]
        
        # 根据当前状态和事件更新
        if breaker.state == CircuitBreakerState.CLOSED:
            self._handle_closed_state(breaker, event)
        elif breaker.state == CircuitBreakerState.OPEN:
            self._handle_open_state(breaker, event)
        elif breaker.state == CircuitBreakerState.HALF_OPEN:
            self._handle_half_open_state(breaker, event)
        
        breaker.total_calls += 1
        if event == CircuitBreakerEvent.SUCCESS:
            breaker.total_successes += 1
        else:
            breaker.total_failures += 1
        
        state_after = breaker.state
        
        # 记录状态变更
        if state_before != state_after:
            self._record_state_change(breaker_id, event, state_before, state_after)
        
        return {
            "operation": "record_event",
            "breaker_id": breaker_id,
            "event": event.value,
            "state_before": state_before.value,
            "state_after": state_after.value,
            "failure_count": breaker.failure_count,
            "success_count": breaker.success_count,
        }
    
    def _handle_closed_state(self, breaker: CircuitBreaker, event: CircuitBreakerEvent) -> None:
        """处理关闭状态"""
        if event in [CircuitBreakerEvent.FAILURE, CircuitBreakerEvent.TIMEOUT]:
            breaker.failure_count += 1
            breaker.last_failure_time = datetime.now()
            
            # 检查是否达到阈值
            if breaker.failure_count >= breaker.config.failure_threshold:
                breaker.state = CircuitBreakerState.OPEN
                breaker.last_state_change = datetime.now()
                breaker.failure_count = 0
                breaker.success_count = 0
        else:
            breaker.success_count += 1
            # 重置失败计数（可选）
            if breaker.success_count >= breaker.config.success_threshold:
                breaker.failure_count = max(0, breaker.failure_count - 1)
    
    def _handle_open_state(self, breaker: CircuitBreaker, event: CircuitBreakerEvent) -> None:
        """处理打开状态"""
        # 检查超时时间是否已过
        if breaker.last_state_change:
            elapsed = (datetime.now() - breaker.last_state_change).total_seconds()
            if elapsed >= breaker.config.timeout_duration:
                breaker.state = CircuitBreakerState.HALF_OPEN
                breaker.last_state_change = datetime.now()
                breaker.half_open_calls = 0
                breaker.failure_count = 0
                breaker.success_count = 0
    
    def _handle_half_open_state(self, breaker: CircuitBreaker, event: CircuitBreakerEvent) -> None:
        """处理半开状态"""
        breaker.half_open_calls += 1
        
        if event in [CircuitBreakerEvent.FAILURE, CircuitBreakerEvent.TIMEOUT]:
            breaker.failure_count += 1
            # 任何一个失败就回到打开状态
            breaker.state = CircuitBreakerState.OPEN
            breaker.last_state_change = datetime.now()
            breaker.failure_count = 0
            breaker.success_count = 0
            breaker.half_open_calls = 0
        else:
            breaker.success_count += 1
            # 达到成功阈值则关闭
            if breaker.success_count >= breaker.config.success_threshold:
                breaker.state = CircuitBreakerState.CLOSED
                breaker.last_state_change = datetime.now()
                breaker.failure_count = 0
                breaker.success_count = 0
                breaker.half_open_calls = 0
            elif breaker.half_open_calls >= breaker.config.half_open_max_calls:
                # 达到最大调用数但未达到成功阈值
                breaker.state = CircuitBreakerState.OPEN
                breaker.last_state_change = datetime.now()
                breaker.failure_count = 0
                breaker.success_count = 0
                breaker.half_open_calls = 0
    
    def _can_execute_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查是否可以执行"""
        breaker_id = input_data.get("breaker_id")
        if not breaker_id or breaker_id not in self._circuit_breakers:
            return {"operation": "can_execute", "error": "熔断器不存在", "can_execute": False}
        
        breaker = self._circuit_breakers[breaker_id]
        
        if breaker.state == CircuitBreakerState.CLOSED:
            can_execute = True
            reason = "circuit_closed"
        elif breaker.state == CircuitBreakerState.OPEN:
            # 检查超时
            if breaker.last_state_change:
                elapsed = (datetime.now() - breaker.last_state_change).total_seconds()
                if elapsed >= breaker.config.timeout_duration:
                    # 自动转换到半开状态
                    breaker.state = CircuitBreakerState.HALF_OPEN
                    breaker.last_state_change = datetime.now()
                    breaker.half_open_calls = 0
                    can_execute = True
                    reason = "timeout_expired_half_open"
                else:
                    can_execute = False
                    reason = "circuit_open"
            else:
                can_execute = False
                reason = "circuit_open"
        elif breaker.state == CircuitBreakerState.HALF_OPEN:
            can_execute = breaker.half_open_calls < breaker.config.half_open_max_calls
            reason = "half_open" if can_execute else "half_open_max_calls_reached"
        else:
            can_execute = False
            reason = "unknown_state"
        
        return {
            "operation": "can_execute",
            "breaker_id": breaker_id,
            "can_execute": can_execute,
            "current_state": breaker.state.value,
            "reason": reason,
        }
    
    def _get_breaker_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取熔断器信息"""
        breaker_id = input_data.get("breaker_id")
        if not breaker_id or breaker_id not in self._circuit_breakers:
            return {"operation": "get_breaker", "error": "熔断器不存在"}
        
        breaker = self._circuit_breakers[breaker_id]
        return {
            "operation": "get_breaker",
            "breaker": breaker.to_dict(),
        }
    
    def _get_records_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取记录"""
        limit = input_data.get("limit", 100)
        breaker_id = input_data.get("breaker_id")
        
        records = self._records
        if breaker_id:
            records = [r for r in records if r.breaker_id == breaker_id]
        
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_records",
            "total": len(self._records),
            "returned": len(records),
            "records": [r.to_dict() for r in records],
        }
    
    def _reset_breaker_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """重置熔断器"""
        breaker_id = input_data.get("breaker_id")
        if not breaker_id or breaker_id not in self._circuit_breakers:
            return {"operation": "reset_breaker", "error": "熔断器不存在", "success": False}
        
        breaker = self._circuit_breakers[breaker_id]
        breaker.state = CircuitBreakerState.CLOSED
        breaker.failure_count = 0
        breaker.success_count = 0
        breaker.last_failure_time = None
        breaker.last_state_change = datetime.now()
        breaker.half_open_calls = 0
        self._window_records[breaker_id] = []
        
        return {
            "operation": "reset_breaker",
            "breaker_id": breaker_id,
            "new_state": breaker.state.value,
            "success": True,
        }
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        states = {}
        for breaker in self._circuit_breakers.values():
            state = breaker.state.value
            states[state] = states.get(state, 0) + 1
        
        total_calls = sum(b.total_calls for b in self._circuit_breakers.values())
        total_failures = sum(b.total_failures for b in self._circuit_breakers.values())
        
        return {
            "operation": "get_stats",
            "total_breakers": len(self._circuit_breakers),
            "state_distribution": states,
            "total_calls": total_calls,
            "total_failures": total_failures,
            "failure_rate": total_failures / total_calls if total_calls > 0 else 0,
            "total_records": len(self._records),
        }
    
    def _list_breakers_operation(self) -> Dict[str, Any]:
        """列出所有熔断器"""
        return {
            "operation": "list_breakers",
            "breakers": [b.to_dict() for b in self._circuit_breakers.values()],
        }
    
    def _record_state_change(self, breaker_id: str, event: CircuitBreakerEvent,
                             state_before: CircuitBreakerState, state_after: CircuitBreakerState) -> None:
        """记录状态变更"""
        import uuid
        
        record = CircuitBreakerRecord(
            record_id=str(uuid.uuid4()),
            breaker_id=breaker_id,
            event=event,
            timestamp=datetime.now(),
            state_before=state_before,
            state_after=state_after,
            reason=f"Event {event.value} triggered state change",
        )
        self._records.append(record)
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级熔断器模块校验开始")
        
        checks = []
        
        if isinstance(self._circuit_breakers, dict):
            checks.append("breakers_valid")
        if isinstance(self._records, list):
            checks.append("records_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._window_records, dict):
            checks.append("window_records_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="circuit_breaker_validation",
                message="四级熔断器模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="circuit_breaker_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("breakers", {bid: b.to_dict() for bid, b in self._circuit_breakers.items()})
        snapshot.set_state("record_count", len(self._records))
        snapshot.metadata["module_type"] = "Level4CircuitBreakerModule"
    
    # 公共接口
    def create_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """创建熔断器"""
        import uuid
        breaker_id = str(uuid.uuid4())
        breaker = CircuitBreaker(
            breaker_id=breaker_id,
            name=name,
            state=CircuitBreakerState.CLOSED,
            config=config or CircuitBreakerConfig(),
        )
        self._circuit_breakers[breaker_id] = breaker
        self._window_records[breaker_id] = []
        return breaker
    
    def record_event(self, breaker_id: str, event: CircuitBreakerEvent) -> Dict[str, Any]:
        """记录事件"""
        return self._record_event_operation({"breaker_id": breaker_id, "event": event.value})
    
    def can_execute(self, breaker_id: str) -> bool:
        """检查是否可以执行"""
        result = self._can_execute_operation({"breaker_id": breaker_id})
        return result.get("can_execute", False)
    
    def get_circuit_breaker(self, breaker_id: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._circuit_breakers.get(breaker_id)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4CircuitBreakerModule",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "CircuitBreakerEvent",
    "CircuitBreakerRecord",
]
