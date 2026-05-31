"""
阶段21：二级治理模块
Level 2 Governance Module

职责定义：
- 任务策略管理
- 规则引擎执行
- 权限控制
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum, auto

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


class PolicyType(Enum):
    """策略类型"""
    ACCESS_CONTROL = auto()   # 访问控制
    RESOURCE_LIMIT = auto()   # 资源限制
    EXECUTION_RULE = auto()   # 执行规则
    DATA_VALIDATION = auto()  # 数据验证


class Policy:
    """策略定义"""
    
    def __init__(
        self,
        policy_id: str,
        policy_type: PolicyType,
        name: str,
        rules: Dict[str, Any],
        priority: int = 5
    ):
        self.policy_id = policy_id
        self.policy_type = policy_type
        self.name = name
        self.rules = rules
        self.priority = priority
        self.created_at = datetime.now()
        self.enabled = True
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估策略"""
        if not self.enabled:
            return True
        
        # 简单规则评估
        for key, expected_value in self.rules.items():
            actual_value = context.get(key)
            if actual_value != expected_value:
                return False
        return True


class Level2GovernanceModule(ControlModuleBase):
    """
    二级治理模块
    
    职责：
    1. 管理任务执行策略
    2. 执行规则引擎
    3. 权限控制决策
    4. 策略冲突检测
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL2
        self._state.module_name = "Level2GovernanceModule"
        self._logger = Logger(f"L2Governance_{self.module_id}")
        
        # 策略管理
        self._policies: Dict[str, Policy] = {}
        self._policy_history: List[Dict[str, Any]] = []
        
        # 规则引擎
        self._rule_evaluators: Dict[PolicyType, Callable] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化治理模块"""
        try:
            self._logger.info("二级治理模块初始化开始")
            
            # 1. 初始化策略存储
            self._policies = {}
            self._policy_history = []
            
            # 2. 注册默认规则评估器
            self._register_default_evaluators()
            
            # 3. 加载默认策略
            self._load_default_policies()
            
            self._logger.info("二级治理模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="二级治理模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"二级治理模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L2G_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _register_default_evaluators(self) -> None:
        """注册默认规则评估器"""
        self._rule_evaluators = {
            PolicyType.ACCESS_CONTROL: self._evaluate_access_control,
            PolicyType.RESOURCE_LIMIT: self._evaluate_resource_limit,
            PolicyType.EXECUTION_RULE: self._evaluate_execution_rule,
            PolicyType.DATA_VALIDATION: self._evaluate_data_validation,
        }
    
    def _load_default_policies(self) -> None:
        """加载默认策略"""
        default_policies = [
            Policy(
                policy_id="default_access",
                policy_type=PolicyType.ACCESS_CONTROL,
                name="默认访问控制",
                rules={"allowed": True},
                priority=10
            ),
            Policy(
                policy_id="default_resource",
                policy_type=PolicyType.RESOURCE_LIMIT,
                name="默认资源限制",
                rules={"max_memory_mb": 1024, "max_cpu_percent": 80},
                priority=5
            ),
        ]
        for policy in default_policies:
            self._policies[policy.policy_id] = policy
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行治理逻辑"""
        self._logger.info("二级治理模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 1. 收集执行上下文
            eval_context = self._build_evaluation_context(request, context)
            
            # 2. 评估所有策略
            evaluation_results = self._evaluate_all_policies(eval_context)
            
            # 3. 检查策略冲突
            conflicts = self._detect_conflicts(evaluation_results)
            
            # 4. 记录策略执行历史
            self._record_policy_execution(task_id, evaluation_results, conflicts)
            
            self._logger.info("二级治理模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "evaluation_results": evaluation_results,
                    "conflicts": conflicts,
                    "policies_applied": len(evaluation_results),
                },
                message="治理策略执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"二级治理模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L2G_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _build_evaluation_context(
        self,
        request: ExecutionRequest,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """构建评估上下文"""
        return {
            "task_id": str(request.module_input.task_id) if request.module_input else None,
            "execution_depth": context.execution_depth,
            "priority": request.priority,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _evaluate_all_policies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估所有策略"""
        results = []
        
        # 按优先级排序
        sorted_policies = sorted(
            self._policies.values(),
            key=lambda p: p.priority,
            reverse=True
        )
        
        for policy in sorted_policies:
            evaluator = self._rule_evaluators.get(policy.policy_type)
            if evaluator:
                passed = evaluator(policy.rules, context)
                results.append({
                    "policy_id": policy.policy_id,
                    "policy_name": policy.name,
                    "policy_type": policy.policy_type.name,
                    "passed": passed,
                    "priority": policy.priority,
                })
        
        return results
    
    def _evaluate_access_control(self, rules: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估访问控制策略"""
        return rules.get("allowed", True)
    
    def _evaluate_resource_limit(self, rules: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估资源限制策略"""
        # 简化实现，总是通过
        return True
    
    def _evaluate_execution_rule(self, rules: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估执行规则策略"""
        return True
    
    def _evaluate_data_validation(self, rules: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估数据验证策略"""
        return True
    
    def _detect_conflicts(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测策略冲突"""
        conflicts = []
        # 简化实现，检测同名策略的不同结果
        policy_results = {}
        for result in results:
            pid = result["policy_id"]
            if pid in policy_results:
                if policy_results[pid] != result["passed"]:
                    conflicts.append({
                        "policy_id": pid,
                        "conflict_type": "result_mismatch",
                    })
            else:
                policy_results[pid] = result["passed"]
        return conflicts
    
    def _record_policy_execution(
        self,
        task_id: TaskID,
        results: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> None:
        """记录策略执行历史"""
        self._policy_history.append({
            "task_id": str(task_id),
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "conflicts": conflicts,
        })
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验治理模块"""
        self._logger.info("二级治理模块校验开始")
        
        checks = []
        
        # 1. 校验策略存储
        if isinstance(self._policies, dict):
            checks.append("policy_storage_valid")
        
        # 2. 校验规则评估器
        if len(self._rule_evaluators) > 0:
            checks.append("evaluators_valid")
        
        # 3. 校验默认策略
        if len(self._policies) > 0:
            checks.append("default_policies_loaded")
        
        all_passed = len(checks) == 3
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="level2_governance_validation",
                message="二级治理模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="level2_governance_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("policies_count", len(self._policies))
        snapshot.set_state("policy_ids", list(self._policies.keys()))
        snapshot.set_state("history_count", len(self._policy_history))
        snapshot.metadata["module_type"] = "Level2GovernanceModule"
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    def add_policy(self, policy: Policy) -> None:
        """添加策略"""
        self._policies[policy.policy_id] = policy
        self._logger.info(f"策略已添加: {policy.policy_id}")
    
    def remove_policy(self, policy_id: str) -> bool:
        """移除策略"""
        if policy_id in self._policies:
            del self._policies[policy_id]
            self._logger.info(f"策略已移除: {policy_id}")
            return True
        return False
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """获取策略"""
        return self._policies.get(policy_id)
    
    def get_all_policies(self) -> Dict[str, Policy]:
        """获取所有策略"""
        return self._policies.copy()
    
    def enable_policy(self, policy_id: str) -> bool:
        """启用策略"""
        policy = self._policies.get(policy_id)
        if policy:
            policy.enabled = True
            return True
        return False
    
    def disable_policy(self, policy_id: str) -> bool:
        """禁用策略"""
        policy = self._policies.get(policy_id)
        if policy:
            policy.enabled = False
            return True
        return False


__all__ = [
    "Level2GovernanceModule",
    "Policy",
    "PolicyType",
]
