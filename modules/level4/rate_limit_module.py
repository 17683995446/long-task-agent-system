"""
阶段42：四级速率限制模块
Level4RateLimitModule

职责定义：
- 速率限制
- 令牌桶管理
- 限流策略
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
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


class RateLimitStrategy(Enum):
    """限流策略"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitDecision(Enum):
    """限流决策"""
    ALLOW = "allow"
    DENY = "deny"
    THROTTLE = "throttle"


@dataclass
class TokenBucket:
    """令牌桶"""
    bucket_id: str
    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bucket_id": self.bucket_id,
            "capacity": self.capacity,
            "tokens": self.tokens,
            "refill_rate": self.refill_rate,
            "last_refill": self.last_refill.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RateLimitRule:
    """限流规则"""
    rule_id: str
    name: str
    resource: str
    strategy: RateLimitStrategy
    limit: int
    window_seconds: int
    burst: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "resource": self.resource,
            "strategy": self.strategy.value,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "burst": self.burst,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class RateLimitRecord:
    """限流记录"""
    record_id: str
    resource: str
    client_id: str
    timestamp: datetime
    decision: RateLimitDecision
    tokens_remaining: int
    retry_after: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "resource": self.resource,
            "client_id": self.client_id,
            "timestamp": self.timestamp.isoformat(),
            "decision": self.decision.value,
            "tokens_remaining": self.tokens_remaining,
            "retry_after": self.retry_after,
            "metadata": self.metadata,
        }


class Level4RateLimitModule(ExecuteModuleBase):
    """
    四级速率限制模块
    
    职责：
    1. 速率限制
    2. 令牌桶管理
    3. 限流策略
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4RateLimitModule"
        self._logger = Logger(f"L4RL_{self.module_id}")
        
        # 令牌桶存储
        self._token_buckets: Dict[str, TokenBucket] = {}
        # 限流规则
        self._rules: List[RateLimitRule] = []
        # 限流记录
        self._records: List[RateLimitRecord] = []
        # 滑动窗口计数器
        self._window_counters: Dict[str, List[datetime]] = {}
        # 固定窗口计数器
        self._fixed_window_counters: Dict[str, Dict[str, int]] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级速率限制模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._token_buckets = {}
            self._rules = []
            self._records = []
            self._window_counters = {}
            self._fixed_window_counters = {}
            
            # 3. 加载默认规则
            self._load_default_rules()
            
            self._logger.info("四级速率限制模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级速率限制模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级速率限制模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4RL_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_strategy": "token_bucket",
            "default_limit": 100,
            "default_window": 60,
            "log_records": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("rate_limit_config", {})
            self._config.update(custom_config)
    
    def _load_default_rules(self) -> None:
        """加载默认规则"""
        default_rules = [
            RateLimitRule(
                rule_id="rule_default",
                name="默认限流",
                resource="*",
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                limit=100,
                window_seconds=60,
                burst=10,
            ),
            RateLimitRule(
                rule_id="rule_api",
                name="API限流",
                resource="/api/*",
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                limit=1000,
                window_seconds=60,
            ),
            RateLimitRule(
                rule_id="rule_login",
                name="登录限流",
                resource="/login",
                strategy=RateLimitStrategy.FIXED_WINDOW,
                limit=5,
                window_seconds=60,
            ),
        ]
        self._rules.extend(default_rules)
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级速率限制模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "check_rate")
            
            if operation == "check_rate":
                result = self._check_rate_operation(input_data)
            elif operation == "add_rule":
                result = self._add_rule_operation(input_data)
            elif operation == "get_bucket":
                result = self._get_bucket_operation(input_data)
            elif operation == "get_records":
                result = self._get_records_operation(input_data)
            elif operation == "create_bucket":
                result = self._create_bucket_operation(input_data)
            elif operation == "get_stats":
                result = self._get_stats_operation()
            elif operation == "reset_bucket":
                result = self._reset_bucket_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级速率限制模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4RateLimitModule",
                    "rate_limit_summary": {
                        "total_rules": len(self._rules),
                        "total_buckets": len(self._token_buckets),
                        "total_records": len(self._records),
                    },
                },
                message="四级速率限制模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级速率限制模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4RL_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _check_rate_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查速率"""
        import uuid
        
        resource = input_data.get("resource", "*")
        client_id = input_data.get("client_id", "default")
        requested_tokens = input_data.get("requested_tokens", 1)
        
        # 查找匹配的规则
        matching_rules = self._find_matching_rules(resource)
        
        if not matching_rules:
            # 没有匹配规则，使用默认策略
            return {
                "operation": "check_rate",
                "resource": resource,
                "client_id": client_id,
                "decision": RateLimitDecision.ALLOW.value,
                "reason": "no_matching_rules",
                "tokens_remaining": -1,
            }
        
        # 使用第一个匹配规则
        rule = matching_rules[0]
        
        if rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            decision, tokens_remaining, retry_after = self._check_token_bucket(
                resource, client_id, requested_tokens, rule
            )
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            decision, tokens_remaining, retry_after = self._check_sliding_window(
                resource, client_id, rule
            )
        elif rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            decision, tokens_remaining, retry_after = self._check_fixed_window(
                resource, client_id, rule
            )
        elif rule.strategy == RateLimitStrategy.LEAKY_BUCKET:
            decision, tokens_remaining, retry_after = self._check_leaky_bucket(
                resource, client_id, rule
            )
        else:
            decision, tokens_remaining, retry_after = RateLimitDecision.ALLOW, -1, None
        
        # 记录
        record = RateLimitRecord(
            record_id=str(uuid.uuid4()),
            resource=resource,
            client_id=client_id,
            timestamp=datetime.now(),
            decision=decision,
            tokens_remaining=tokens_remaining,
            retry_after=retry_after,
        )
        self._records.append(record)
        
        return {
            "operation": "check_rate",
            "resource": resource,
            "client_id": client_id,
            "decision": decision.value,
            "tokens_remaining": tokens_remaining,
            "retry_after": retry_after,
            "rule_id": rule.rule_id,
            "strategy": rule.strategy.value,
        }
    
    def _find_matching_rules(self, resource: str) -> List[RateLimitRule]:
        """查找匹配的规则"""
        matching = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self._match_resource(rule.resource, resource):
                matching.append(rule)
        
        # 按优先级排序（更具体的规则优先）
        matching.sort(key=lambda r: len(r.resource), reverse=True)
        return matching
    
    def _match_resource(self, pattern: str, resource: str) -> bool:
        """匹配资源"""
        if pattern == "*":
            return True
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            return resource.startswith(prefix)
        return pattern == resource
    
    def _check_token_bucket(self, resource: str, client_id: str,
                            requested_tokens: int, rule: RateLimitRule) -> tuple:
        """检查令牌桶"""
        bucket_id = f"{resource}:{client_id}"
        
        if bucket_id not in self._token_buckets:
            self._token_buckets[bucket_id] = TokenBucket(
                bucket_id=bucket_id,
                capacity=rule.limit + rule.burst,
                tokens=float(rule.limit + rule.burst),
                refill_rate=rule.limit / rule.window_seconds,
                last_refill=datetime.now(),
            )
        
        bucket = self._token_buckets[bucket_id]
        
        # 补充令牌
        now = datetime.now()
        elapsed = (now - bucket.last_refill).total_seconds()
        tokens_to_add = elapsed * bucket.refill_rate
        bucket.tokens = min(bucket.capacity, bucket.tokens + tokens_to_add)
        bucket.last_refill = now
        
        # 检查是否有足够令牌
        if bucket.tokens >= requested_tokens:
            bucket.tokens -= requested_tokens
            return RateLimitDecision.ALLOW, int(bucket.tokens), None
        else:
            retry_after = int((requested_tokens - bucket.tokens) / bucket.refill_rate) + 1
            return RateLimitDecision.DENY, int(bucket.tokens), retry_after
    
    def _check_sliding_window(self, resource: str, client_id: str,
                              rule: RateLimitRule) -> tuple:
        """检查滑动窗口"""
        counter_key = f"{resource}:{client_id}"
        now = datetime.now()
        window_start = now - timedelta(seconds=rule.window_seconds)
        
        if counter_key not in self._window_counters:
            self._window_counters[counter_key] = []
        
        # 清理过期记录
        self._window_counters[counter_key] = [
            ts for ts in self._window_counters[counter_key] if ts > window_start
        ]
        
        current_count = len(self._window_counters[counter_key])
        
        if current_count < rule.limit:
            self._window_counters[counter_key].append(now)
            return RateLimitDecision.ALLOW, rule.limit - current_count - 1, None
        else:
            oldest = min(self._window_counters[counter_key])
            retry_after = int((oldest + timedelta(seconds=rule.window_seconds) - now).total_seconds()) + 1
            return RateLimitDecision.DENY, 0, max(1, retry_after)
    
    def _check_fixed_window(self, resource: str, client_id: str,
                            rule: RateLimitRule) -> tuple:
        """检查固定窗口"""
        counter_key = f"{resource}:{client_id}"
        now = datetime.now()
        window_key = now.strftime("%Y-%m-%d %H:%M")
        
        if counter_key not in self._fixed_window_counters:
            self._fixed_window_counters[counter_key] = {}
        
        # 清理旧窗口
        current_window = now.strftime("%Y-%m-%d %H:%M")
        self._fixed_window_counters[counter_key] = {
            k: v for k, v in self._fixed_window_counters[counter_key].items()
            if k == current_window
        }
        
        current_count = self._fixed_window_counters[counter_key].get(window_key, 0)
        
        if current_count < rule.limit:
            self._fixed_window_counters[counter_key][window_key] = current_count + 1
            return RateLimitDecision.ALLOW, rule.limit - current_count - 1, None
        else:
            # 计算到下一窗口的时间
            next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
            retry_after = int((next_minute - now).total_seconds()) + 1
            return RateLimitDecision.DENY, 0, retry_after
    
    def _check_leaky_bucket(self, resource: str, client_id: str,
                            rule: RateLimitRule) -> tuple:
        """检查漏桶"""
        # 漏桶实现：与令牌桶类似，但容量固定，流出速率固定
        bucket_id = f"leaky:{resource}:{client_id}"
        
        if bucket_id not in self._token_buckets:
            self._token_buckets[bucket_id] = TokenBucket(
                bucket_id=bucket_id,
                capacity=rule.burst or rule.limit,
                tokens=0,
                refill_rate=rule.limit / rule.window_seconds,
                last_refill=datetime.now(),
            )
        
        bucket = self._token_buckets[bucket_id]
        now = datetime.now()
        elapsed = (now - bucket.last_refill).total_seconds()
        
        # 漏水（减少令牌）
        bucket.tokens = max(0, bucket.tokens - elapsed * bucket.refill_rate)
        bucket.last_refill = now
        
        # 检查是否有空间
        if bucket.tokens + 1 <= bucket.capacity:
            bucket.tokens += 1
            return RateLimitDecision.ALLOW, int(bucket.capacity - bucket.tokens), None
        else:
            return RateLimitDecision.DENY, 0, int(1 / bucket.refill_rate) + 1
    
    def _add_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加规则"""
        import uuid
        
        rule = RateLimitRule(
            rule_id=str(uuid.uuid4()),
            name=input_data.get("name", ""),
            resource=input_data.get("resource", "*"),
            strategy=RateLimitStrategy(input_data.get("strategy", "token_bucket")),
            limit=input_data.get("limit", 100),
            window_seconds=input_data.get("window_seconds", 60),
            burst=input_data.get("burst", 0),
            enabled=input_data.get("enabled", True),
            metadata=input_data.get("metadata", {}),
        )
        self._rules.append(rule)
        
        return {
            "operation": "add_rule",
            "rule_id": rule.rule_id,
            "added": True,
        }
    
    def _get_bucket_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取令牌桶信息"""
        bucket_id = input_data.get("bucket_id")
        if not bucket_id or bucket_id not in self._token_buckets:
            return {"operation": "get_bucket", "error": "令牌桶不存在"}
        
        bucket = self._token_buckets[bucket_id]
        return {
            "operation": "get_bucket",
            "bucket": bucket.to_dict(),
        }
    
    def _get_records_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取限流记录"""
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
    
    def _create_bucket_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建令牌桶"""
        bucket_id = input_data.get("bucket_id")
        capacity = input_data.get("capacity", 100)
        refill_rate = input_data.get("refill_rate", 1.0)
        
        bucket = TokenBucket(
            bucket_id=bucket_id,
            capacity=capacity,
            tokens=float(capacity),
            refill_rate=refill_rate,
            last_refill=datetime.now(),
            metadata=input_data.get("metadata", {}),
        )
        self._token_buckets[bucket_id] = bucket
        
        return {
            "operation": "create_bucket",
            "bucket_id": bucket_id,
            "created": True,
        }
    
    def _get_stats_operation(self) -> Dict[str, Any]:
        """获取统计信息"""
        deny_count = sum(1 for r in self._records if r.decision == RateLimitDecision.DENY)
        allow_count = sum(1 for r in self._records if r.decision == RateLimitDecision.ALLOW)
        
        return {
            "operation": "get_stats",
            "total_records": len(self._records),
            "allow_count": allow_count,
            "deny_count": deny_count,
            "allow_rate": allow_count / len(self._records) if self._records else 0,
            "active_buckets": len(self._token_buckets),
            "active_rules": len([r for r in self._rules if r.enabled]),
        }
    
    def _reset_bucket_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """重置令牌桶"""
        bucket_id = input_data.get("bucket_id")
        if not bucket_id or bucket_id not in self._token_buckets:
            return {"operation": "reset_bucket", "error": "令牌桶不存在", "success": False}
        
        bucket = self._token_buckets[bucket_id]
        bucket.tokens = float(bucket.capacity)
        bucket.last_refill = datetime.now()
        
        return {
            "operation": "reset_bucket",
            "bucket_id": bucket_id,
            "tokens": bucket.tokens,
            "success": True,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级速率限制模块校验开始")
        
        checks = []
        
        if isinstance(self._token_buckets, dict):
            checks.append("buckets_valid")
        if isinstance(self._rules, list):
            checks.append("rules_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._records, list):
            checks.append("records_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="rate_limit_validation",
                message="四级速率限制模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="rate_limit_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("buckets", {bid: b.to_dict() for bid, b in self._token_buckets.items()})
        snapshot.set_state("rules", [r.to_dict() for r in self._rules])
        snapshot.set_state("record_count", len(self._records))
        snapshot.metadata["module_type"] = "Level4RateLimitModule"
    
    # 公共接口
    def check_rate(self, resource: str, client_id: str = "default",
                   requested_tokens: int = 1) -> Dict[str, Any]:
        """检查速率"""
        return self._check_rate_operation({
            "resource": resource,
            "client_id": client_id,
            "requested_tokens": requested_tokens,
        })
    
    def add_rule(self, rule: RateLimitRule) -> None:
        """添加规则"""
        self._rules.append(rule)
    
    def get_bucket(self, bucket_id: str) -> Optional[TokenBucket]:
        """获取令牌桶"""
        return self._token_buckets.get(bucket_id)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4RateLimitModule",
    "TokenBucket",
    "RateLimitRule",
    "RateLimitRecord",
    "RateLimitStrategy",
    "RateLimitDecision",
]
