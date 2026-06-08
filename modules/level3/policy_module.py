"""
阶段31：三级策略模块
Level3PolicyModule

职责定义：
- 细粒度策略管理
- 策略组合与优先级排序
- 策略冲突检测
- 策略执行评估
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.base_module import ControlModuleBase
from core_types.core_types import (
    ModuleID, TaskID, ModuleLevel,
    InitResult, ModuleOutput, CheckResult, SnapshotData,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)
from utils.logger import Logger


class PolicyPriority(Enum):
    """策略优先级"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    MINIMAL = 5


@dataclass
class Policy:
    """策略定义"""
    policy_id: str
    name: str
    description: str
    priority: PolicyPriority
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PolicyEvaluationResult:
    """策略评估结果"""
    policy_id: str
    matched: bool
    actions_triggered: List[str]
    evaluation_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class Level3PolicyModule(ControlModuleBase):
    """
    三级策略模块
    
    职责：
    1. 细粒度策略管理（CRUD）
    2. 策略组合与优先级排序
    3. 策略冲突检测与解决
    4. 策略执行评估
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL3
        self._state.module_name = "Level3PolicyModule"
        self._logger = Logger(f"L3P_{self.module_id}")
        
        # 策略存储
        self._policies: Dict[str, Policy] = {}
        self._policy_history: List[Dict[str, Any]] = []
        self._evaluation_count: int = 0
        self._conflict_count: int = 0
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化策略模块"""
        try:
            self._logger.info("策略模块初始化开始")
            
            # 1. 加载默认策略
            self._load_default_policies()
            
            # 2. 从请求加载自定义策略
            if request.task_param:
                custom_policies = request.task_param.get_param("policies", [])
                for p in custom_policies:
                    self.add_policy(**p)
            
            self._logger.info(f"策略模块初始化完成，加载了 {len(self._policies)} 个策略")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message=f"策略模块初始化成功，策略数量: {len(self._policies)}"
            )
            
        except Exception as e:
            self._logger.error(f"策略模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L3P_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_default_policies(self) -> None:
        """加载默认策略"""
        defaults = [
            Policy(
                policy_id="default_timeout",
                name="默认超时策略",
                description="任务执行超过设定时间自动终止",
                priority=PolicyPriority.HIGH,
                conditions={"max_duration_seconds": 3600},
                actions=["log_warning", "trigger_timeout"],
            ),
            Policy(
                policy_id="default_retry",
                name="默认重试策略",
                description="失败任务自动重试",
                priority=PolicyPriority.MEDIUM,
                conditions={"max_retries": 3, "retry_interval_seconds": 5},
                actions=["retry_task", "log_retry"],
            ),
            Policy(
                policy_id="default_rate_limit",
                name="默认限流策略",
                description="限制单位时间内的任务执行次数",
                priority=PolicyPriority.HIGH,
                conditions={"max_requests_per_minute": 100},
                actions=["throttle", "log_throttle"],
            ),
        ]
        for p in defaults:
            self._policies[p.policy_id] = p
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行策略评估"""
        self._logger.info("策略模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 构建评估上下文
            eval_context = self._build_evaluation_context(request, context)
            
            # 2. 评估所有策略
            results = self._evaluate_all_policies(eval_context)
            
            # 3. 检测策略冲突
            conflicts = self._detect_conflicts(results)
            
            # 4. 解决冲突（按优先级）
            resolved = self._resolve_conflicts(results, conflicts)
            
            # 5. 生成治理报告
            report = self._generate_governance_report(results, conflicts, resolved)
            
            self._evaluation_count += 1
            self._conflict_count += len(conflicts)
            
            self._logger.info(f"策略评估完成: {len(results)}个策略, {len(conflicts)}个冲突")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "governance_report": report,
                    "policies_evaluated": len(results),
                    "conflicts_detected": len(conflicts),
                    "conflicts_resolved": len(resolved),
                    "module": "Level3PolicyModule",
                },
                message="策略模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"策略模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L3P_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _build_evaluation_context(
        self,
        request: ExecutionRequest,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """构建策略评估上下文"""
        return {
            "task_id": str(request.module_input.task_id) if request.module_input else None,
            "execution_context": {
                "step_count": getattr(context, 'step_count', 0),
                "current_step": getattr(context, 'current_step', None),
            },
            "timestamp": datetime.now().isoformat(),
            "module_level": self._state.module_level.name,
        }
    
    def _evaluate_all_policies(
        self,
        eval_context: Dict[str, Any]
    ) -> List[PolicyEvaluationResult]:
        """评估所有策略"""
        results = []
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            
            start = datetime.now()
            matched = self._evaluate_policy(policy, eval_context)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            result = PolicyEvaluationResult(
                policy_id=policy.policy_id,
                matched=matched,
                actions_triggered=policy.actions if matched else [],
                evaluation_time_ms=elapsed,
                metadata={"priority": policy.priority.name},
            )
            results.append(result)
        
        # 按优先级排序
        results.sort(key=lambda r: r.metadata.get("priority", "MINIMAL"))
        return results
    
    def _evaluate_policy(
        self,
        policy: Policy,
        eval_context: Dict[str, Any]
    ) -> bool:
        """评估单个策略"""
        # 简化的策略匹配逻辑
        conditions = policy.conditions
        
        # 检查执行步骤数条件
        if "max_steps" in conditions:
            step_count = eval_context.get("execution_context", {}).get("step_count", 0)
            if step_count > conditions["max_steps"]:
                return True
        
        # 默认匹配
        return True
    
    def _detect_conflicts(
        self,
        results: List[PolicyEvaluationResult]
    ) -> List[Tuple[str, str, str]]:
        """检测策略冲突"""
        conflicts = []
        matched = [r for r in results if r.matched]
        
        # 检测互斥动作冲突
        for i, r1 in enumerate(matched):
            for r2 in matched[i+1:]:
                # 检查是否有互斥动作
                mutex_pairs = [
                    ("allow", "deny"),
                    ("retry", "abort"),
                    ("throttle", "bypass"),
                ]
                for a1 in r1.actions_triggered:
                    for a2 in r2.actions_triggered:
                        for m1, m2 in mutex_pairs:
                            if (m1 in a1 and m2 in a2) or (m2 in a1 and m1 in a2):
                                conflicts.append((r1.policy_id, r2.policy_id, f"{a1} vs {a2}"))
        
        return conflicts
    
    def _resolve_conflicts(
        self,
        results: List[PolicyEvaluationResult],
        conflicts: List[Tuple[str, str, str]]
    ) -> List[Dict[str, Any]]:
        """解决策略冲突（按优先级）"""
        resolved = []
        
        for p1_id, p2_id, reason in conflicts:
            p1 = self._policies.get(p1_id)
            p2 = self._policies.get(p2_id)
            
            if p1 and p2:
                # 优先级高的策略胜出
                winner = p1 if p1.priority.value <= p2.priority.value else p2
                loser = p2 if winner == p1 else p1
                
                resolved.append({
                    "conflict": f"{p1_id} vs {p2_id}",
                    "reason": reason,
                    "winner": winner.policy_id,
                    "winner_priority": winner.priority.name,
                    "loser": loser.policy_id,
                    "resolution": "priority_based",
                })
        
        return resolved
    
    def _generate_governance_report(
        self,
        results: List[PolicyEvaluationResult],
        conflicts: List[Tuple[str, str, str]],
        resolved: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成治理报告"""
        matched_policies = [r for r in results if r.matched]
        
        return {
            "total_policies": len(results),
            "matched_policies": len(matched_policies),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len(resolved),
            "avg_evaluation_time_ms": sum(r.evaluation_time_ms for r in results) / max(len(results), 1),
            "triggered_actions": list(set(
                action for r in matched_policies for action in r.actions_triggered
            )),
            "resolution_details": resolved,
            "generated_at": datetime.now().isoformat(),
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验策略模块"""
        self._logger.info("策略模块校验开始")
        
        checks = []
        
        # 1. 校验策略存储
        if isinstance(self._policies, dict):
            checks.append("policy_store_valid")
        
        # 2. 校验策略完整性
        invalid_policies = []
        for pid, p in self._policies.items():
            if not p.policy_id or not p.name:
                invalid_policies.append(pid)
        if not invalid_policies:
            checks.append("policies_integrity_valid")
        
        # 3. 校验优先级定义
        priorities = set(p.priority for p in self._policies.values())
        if len(priorities) > 0:
            checks.append("priorities_valid")
        
        # 4. 校验模块层级
        if self._state.module_level == ModuleLevel.LEVEL3:
            checks.append("level_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="policy_validation",
                message=f"策略模块校验通过，策略数量: {len(self._policies)}"
            )
        else:
            return CheckResult.failed_result(
                check_type="policy_validation",
                message=f"校验失败: {checks}, 无效策略: {invalid_policies}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建策略模块快照"""
        snapshot.set_state("policies", {
            pid: {
                "name": p.name,
                "priority": p.priority.name,
                "enabled": p.enabled,
                "conditions": p.conditions,
                "actions": p.actions,
            }
            for pid, p in self._policies.items()
        })
        snapshot.set_state("evaluation_count", self._evaluation_count)
        snapshot.set_state("conflict_count", self._conflict_count)
        snapshot.set_state("policy_history_count", len(self._policy_history))
        snapshot.metadata["module_type"] = "Level3PolicyModule"
        snapshot.metadata["policy_count"] = len(self._policies)
    
    # =====================================================================
    # 策略管理公共接口
    # =====================================================================
    
    def add_policy(
        self,
        policy_id: str,
        name: str,
        description: str = "",
        priority: str = "MEDIUM",
        conditions: Dict[str, Any] = None,
        actions: List[str] = None,
        enabled: bool = True,
    ) -> bool:
        """
        添加策略
        
        Args:
            policy_id: 策略唯一标识
            name: 策略名称
            description: 策略描述
            priority: 优先级 (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL)
            conditions: 触发条件
            actions: 触发动作列表
            enabled: 是否启用
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if policy_id in self._policies:
                self._logger.warning(f"策略已存在，将覆盖: {policy_id}")
            
            priority_enum = PolicyPriority[priority.upper()]
            policy = Policy(
                policy_id=policy_id,
                name=name,
                description=description,
                priority=priority_enum,
                conditions=conditions or {},
                actions=actions or [],
                enabled=enabled,
            )
            self._policies[policy_id] = policy
            
            self._policy_history.append({
                "action": "add",
                "policy_id": policy_id,
                "timestamp": datetime.now().isoformat(),
            })
            
            self._logger.info(f"策略添加成功: {policy_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"策略添加失败: {e}")
            return False
    
    def remove_policy(self, policy_id: str) -> bool:
        """移除策略"""
        if policy_id in self._policies:
            del self._policies[policy_id]
            self._policy_history.append({
                "action": "remove",
                "policy_id": policy_id,
                "timestamp": datetime.now().isoformat(),
            })
            self._logger.info(f"策略移除成功: {policy_id}")
            return True
        return False
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """获取策略"""
        return self._policies.get(policy_id)
    
    def get_all_policies(self) -> Dict[str, Policy]:
        """获取所有策略"""
        return self._policies.copy()
    
    def get_enabled_policies(self) -> List[Policy]:
        """获取启用的策略"""
        return [p for p in self._policies.values() if p.enabled]
    
    def enable_policy(self, policy_id: str) -> bool:
        """启用策略"""
        if policy_id in self._policies:
            self._policies[policy_id].enabled = True
            return True
        return False
    
    def disable_policy(self, policy_id: str) -> bool:
        """禁用策略"""
        if policy_id in self._policies:
            self._policies[policy_id].enabled = False
            return True
        return False
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        return {
            "total": len(self._policies),
            "enabled": sum(1 for p in self._policies.values() if p.enabled),
            "disabled": sum(1 for p in self._policies.values() if not p.enabled),
            "by_priority": {
                p.name: sum(1 for pol in self._policies.values() if pol.priority == p)
                for p in PolicyPriority
            },
            "evaluation_count": self._evaluation_count,
            "conflict_count": self._conflict_count,
        }


__all__ = [
    "Level3PolicyModule",
    "Policy",
    "PolicyPriority",
    "PolicyEvaluationResult",
]
