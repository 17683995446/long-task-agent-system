"""
阶段50：四级节流模块
Level4ThrottleModule

职责定义：
- 请求节流
- 并发控制
- 资源限制
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading

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


class ThrottleStrategy(Enum):
    """节流策略"""
    FIXED_RATE = "fixed_rate"
    ADAPTIVE = "adaptive"
    BURST = "burst"
    PRIORITY = "priority"


class ThrottleDecision(Enum):
    """节流决策"""
    ALLOW = "allow"
    DELAY = "delay"
    REJECT = "reject"
    QUEUE = "queue"


@dataclass
class ThrottleSlot:
    """节流槽位"""
    slot_id: str
    resource: str
    max_concurrent: int
    current_concurrent: int = 0
    total_processed: int = 0
    total_rejected: int = 0
    avg_processing_time_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "resource": self.resource,
            "max_concurrent": self.max_concurrent,
            "current_concurrent": self.current_concurrent,
            "total_processed": self.total_processed,
            "total_rejected": self.total_rejected,
            "avg_processing_time_ms": self.avg_processing_time_ms,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ThrottleRule:
    """节流规则"""
    rule_id: str
    name: str
    resource: str
    strategy: ThrottleStrategy
    max_requests_per_second: float
    max_concurrent: int
    burst_size: int = 0
    queue_size: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "resource": self.resource,
            "strategy": self.strategy.value,
            "max_requests_per_second": self.max_requests_per_second,
            "max_concurrent": self.max_concurrent,
            "burst_size": self.burst_size,
            "queue_size": self.queue_size,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class ThrottleRecord:
    """节流记录"""
    record_id: str
    resource: str
    client_id: str
    timestamp: datetime
    decision: ThrottleDecision
    delay_ms: int = 0
    queue_position: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "resource": self.resource,
            "client_id": self.client_id,
            "timestamp": self.timestamp.isoformat(),
            "decision": self.decision.value,
            "delay_ms": self.delay_ms,
            "queue_position": self.queue_position,
            "metadata": self.metadata,
        }


class Level4ThrottleModule(ExecuteModuleBase):
    """
    四级节流模块
    
    职责：
    1. 请求节流
    2. 并发控制
    3. 资源限制
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4ThrottleModule"
        self._logger = Logger(f"L4TH_{self.module_id}")
        
        # 节流槽位
        self._slots: Dict[str, ThrottleSlot] = {}
        # 节流规则
        self._rules: List[ThrottleRule] = []
        # 节流记录
        self._records: List[ThrottleRecord] = []
        # 请求历史（用于速率计算）
        self._request_history: Dict[str, List[datetime]] = {}
        # 队列
        self._queues: Dict[str, List[str]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级节流模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._slots = {}
            self._rules = []
            self._records = []
            self._request_history = {}
            self._queues = {}
            
            # 3. 加载默认规则
            self._load_default_rules()
            
            self._logger.info("四级节流模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级节流模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级节流模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4TH_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_max_rps": 10.0,
            "default_max_concurrent": 5,
            "default_burst_size": 2,
            "log_records": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("throttle_config", {})
            self._config.update(custom_config)
    
    def _load_default_rules(self) -> None:
        """加载默认规则"""
        default_rules = [
            ThrottleRule(
                rule_id="rule_default",
                name="默认节流",
                resource="*",
                strategy=ThrottleStrategy.FIXED_RATE,
                max_requests_per_second=10.0,
                max_concurrent=5,
                burst_size=2,
            ),
            ThrottleRule(
                rule_id="rule_api",
                name="API节流",
                resource="/api/*",
                strategy=ThrottleStrategy.BURST,
                max_requests_per_second=100.0,
                max_concurrent=20,
                burst_size=10,
            ),
        ]
        self._rules.extend(default_rules)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级节流模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "check_throttle")
            
            if operation == "check_throttle":
                result = self._check_throttle_operation(input_data)
            elif operation == "add_rule":
                result = self._add_rule_operation(input_data)
            elif operation == "release_slot":
                result = self._release_slot_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "get_records":
                result = self._get_records_operation(input_data)
            elif operation == "create_slot":
                result = self._create_slot_operation(input_data)
            elif operation == "get_queue":
                result = self._get_queue_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级节流模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4ThrottleModule",
                    "throttle_summary": {
                        "total_rules": len(self._rules),
                        "total_slots": len(self._slots),
                        "total_records": len(self._records),
                    },
                },
                message="四级节流模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级节流模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4TH_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _check_throttle_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查节流"""
        import uuid
        
        resource = input_data.get("resource", "*")
        client_id = input_data.get("client_id", "default")
        priority = input_data.get("priority", 0)
        
        # 查找匹配的规则
        matching_rules = self._find_matching_rules(resource)
        
        if not matching_rules:
            return {
                "operation": "check_throttle",
                "resource": resource,
                "decision": ThrottleDecision.ALLOW.value,
                "reason": "no_matching_rules",
            }
        
        rule = matching_rules[0]
        
        # 获取或创建槽位
        slot_id = f"{resource}:{client_id}"
        if slot_id not in self._slots:
            self._slots[slot_id] = ThrottleSlot(
                slot_id=slot_id,
                resource=resource,
                max_concurrent=rule.max_concurrent,
            )
        
        slot = self._slots[slot_id]
        
        # 检查并发数
        if slot.current_concurrent >= rule.max_concurrent:
            # 检查队列
            if rule.queue_size > 0:
                queue_key = f"{resource}"
                if queue_key not in self._queues:
                    self._queues[queue_key] = []
                
                if len(self._queues[queue_key]) < rule.queue_size:
                    self._queues[queue_key].append(client_id)
                    decision = ThrottleDecision.QUEUE
                    queue_position = len(self._queues[queue_key])
                    delay_ms = queue_position * 100
                else:
                    decision = ThrottleDecision.REJECT
                    queue_position = 0
                    delay_ms = 0
            else:
                decision = ThrottleDecision.REJECT
                queue_position = 0
                delay_ms = 0
        else:
            # 检查速率
            current_rps = self._calculate_rps(resource)
            
            if current_rps >= rule.max_requests_per_second:
                # 检查突发
                if rule.burst_size > 0:
                    recent_requests = self._get_recent_requests(resource, 1)
                    if len(recent_requests) < rule.burst_size:
                        decision = ThrottleDecision.ALLOW
                    else:
                        decision = ThrottleDecision.DELAY
                        delay_ms = int(1000 / rule.max_requests_per_second)
                else:
                    decision = ThrottleDecision.DELAY
                    delay_ms = int(1000 / rule.max_requests_per_second)
            else:
                decision = ThrottleDecision.ALLOW
                queue_position = 0
                delay_ms = 0
        
        # 记录请求
        if decision == ThrottleDecision.ALLOW:
            slot.current_concurrent += 1
            self._record_request(resource)
        
        # 记录
        record = ThrottleRecord(
            record_id=str(uuid.uuid4()),
            resource=resource,
            client_id=client_id,
            timestamp=datetime.now(),
            decision=decision,
            delay_ms=delay_ms,
            queue_position=queue_position,
        )
        self._records.append(record)
        
        if decision == ThrottleDecision.REJECT:
            slot.total_rejected += 1
        else:
            slot.total_processed += 1
        
        slot.last_updated = datetime.now()
        
        return {
            "operation": "check_throttle",
            "resource": resource,
            "client_id": client_id,
            "decision": decision.value,
            "delay_ms": delay_ms,
            "queue_position": queue_position,
            "current_concurrent": slot.current_concurrent,
            "current_rps": self._calculate_rps(resource),
            "rule_id": rule.rule_id,
        }
    
    def _find_matching_rules(self, resource: str) -> List[ThrottleRule]:
        """查找匹配的规则"""
        matching = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._match_resource(rule.resource, resource):
                matching.append(rule)
        
        matching.sort(key=lambda r: len(r.resource), reverse=True)
        return matching
    
    def _match_resource(self, pattern: str, resource: str) -> bool:
        """匹配资源"""
        if pattern == "*":
            return True
        if pattern.endswith("/*"):
            return resource.startswith(pattern[:-2])
        return pattern == resource
    
    def _calculate_rps(self, resource: str) -> float:
        """计算当前RPS"""
        recent = self._get_recent_requests(resource, 1)
        return len(recent)
    
    def _get_recent_requests(self, resource: str, seconds: int) -> List[datetime]:
        """获取最近请求"""
        if resource not in self._request_history:
            self._request_history[resource] = []
        
        cutoff = datetime.now() - timedelta(seconds=seconds)
        self._request_history[resource] = [
            ts for ts in self._request_history[resource] if ts > cutoff
        ]
        
        return self._request_history[resource]
    
    def _record_request(self, resource: str) -> None:
        """记录请求"""
        if resource not in self._request_history:
            self._request_history[resource] = []
        self._request_history[resource].append(datetime.now())
    
    def _release_slot_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """释放槽位"""
        resource = input_data.get("resource", "*")
        client_id = input_data.get("client_id", "default")
        processing_time_ms = input_data.get("processing_time_ms", 0)
        
        slot_id = f"{resource}:{client_id}"
        if slot_id in self._slots:
            slot = self._slots[slot_id]
            slot.current_concurrent = max(0, slot.current_concurrent - 1)
            
            # 更新平均处理时间
            if slot.total_processed > 0:
                slot.avg_processing_time_ms = (
                    (slot.avg_processing_time_ms * (slot.total_processed - 1) + processing_time_ms)
                    / slot.total_processed
                )
            
            slot.last_updated = datetime.now()
        
        # 处理队列
        queue_key = f"{resource}"
        if queue_key in self._queues and self._queues[queue_key]:
            self._queues[queue_key].pop(0)
        
        return {
            "operation": "release_slot",
            "resource": resource,
            "client_id": client_id,
            "released": True,
        }
    
    def _add_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加规则"""
        import uuid
        
        rule = ThrottleRule(
            rule_id=str(uuid.uuid4()),
            name=input_data.get("name", ""),
            resource=input_data.get("resource", "*"),
            strategy=ThrottleStrategy(input_data.get("strategy", "fixed_rate")),
            max_requests_per_second=input_data.get("max_requests_per_second", 10.0),
            max_concurrent=input_data.get("max_concurrent", 5),
            burst_size=input_data.get("burst_size", 0),
            queue_size=input_data.get("queue_size", 0),
            enabled=input_data.get("enabled", True),
            metadata=input_data.get("metadata", {}),
        )
        self._rules.append(rule)
        
        return {"operation": "add_rule", "rule_id": rule.rule_id, "added": True}
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_concurrent = sum(s.current_concurrent for s in self._slots.values())
        total_processed = sum(s.total_processed for s in self._slots.values())
        total_rejected = sum(s.total_rejected for s in self._slots.values())
        
        return {
            "operation": "get_stats",
            "total_rules": len(self._rules),
            "total_slots": len(self._slots),
            "total_concurrent": total_concurrent,
            "total_processed": total_processed,
            "total_rejected": total_rejected,
            "reject_rate": total_rejected / (total_processed + total_rejected) if (total_processed + total_rejected) > 0 else 0,
            "total_records": len(self._records),
        }
    
    def _get_records_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取记录"""
        limit = input_data.get("limit", 100)
        resource = input_data.get("resource")
        
        records = self._records
        if resource:
            records = [r for r in records if r.resource == resource]
        
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_records",
            "total": len(self._records),
            "returned": len(records),
            "records": [r.to_dict() for r in records],
        }
    
    def _create_slot_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建槽位"""
        slot_id = input_data.get("slot_id")
        resource = input_data.get("resource", "*")
        max_concurrent = input_data.get("max_concurrent", 5)
        
        slot = ThrottleSlot(
            slot_id=slot_id,
            resource=resource,
            max_concurrent=max_concurrent,
            metadata=input_data.get("metadata", {}),
        )
        self._slots[slot_id] = slot
        
        return {"operation": "create_slot", "slot_id": slot_id, "created": True}
    
    def _get_queue_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取队列"""
        resource = input_data.get("resource", "*")
        queue_key = f"{resource}"
        
        queue = self._queues.get(queue_key, [])
        
        return {
            "operation": "get_queue",
            "resource": resource,
            "queue_length": len(queue),
            "queue": queue,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级节流模块校验开始")
        
        checks = []
        
        if isinstance(self._slots, dict):
            checks.append("slots_valid")
        if isinstance(self._rules, list):
            checks.append("rules_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._records, list):
            checks.append("records_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="throttle_validation",
                message="四级节流模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="throttle_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("slots", {sid: s.to_dict() for sid, s in self._slots.items()})
        snapshot.set_state("rules", [r.to_dict() for r in self._rules])
        snapshot.set_state("record_count", len(self._records))
        snapshot.metadata["module_type"] = "Level4ThrottleModule"
    
    # 公共接口
    def check_throttle(self, resource: str, client_id: str = "default") -> Dict[str, Any]:
        """检查节流"""
        return self._check_throttle_operation({"resource": resource, "client_id": client_id})
    
    def release_slot(self, resource: str, client_id: str = "default") -> None:
        """释放槽位"""
        self._release_slot_operation({"resource": resource, "client_id": client_id})
    
    def add_rule(self, rule: ThrottleRule) -> None:
        """添加规则"""
        self._rules.append(rule)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4ThrottleModule",
    "ThrottleSlot",
    "ThrottleRule",
    "ThrottleRecord",
    "ThrottleStrategy",
    "ThrottleDecision",
]
