"""
阶段49：四级过滤模块
Level4FilterModule

职责定义：
- 请求过滤
- 响应过滤
- 过滤规则
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

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


class FilterType(Enum):
    """过滤类型"""
    REQUEST = "request"
    RESPONSE = "response"
    BOTH = "both"


class FilterAction(Enum):
    """过滤动作"""
    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    LOG = "log"


class FilterConditionType(Enum):
    """过滤条件类型"""
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN_LIST = "in_list"
    CUSTOM = "custom"


@dataclass
class FilterCondition:
    """过滤条件"""
    condition_id: str
    field: str
    condition_type: FilterConditionType
    value: Any
    negate: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "field": self.field,
            "condition_type": self.condition_type.value,
            "value": self.value,
            "negate": self.negate,
            "metadata": self.metadata,
        }


@dataclass
class FilterRule:
    """过滤规则"""
    rule_id: str
    name: str
    filter_type: FilterType
    action: FilterAction
    conditions: List[FilterCondition] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    modification: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "filter_type": self.filter_type.value,
            "action": self.action.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "priority": self.priority,
            "enabled": self.enabled,
            "modification": self.modification,
            "metadata": self.metadata,
        }


@dataclass
class FilterResult:
    """过滤结果"""
    result_id: str
    rule_id: str
    action: FilterAction
    matched: bool
    timestamp: datetime
    original_data: Dict[str, Any] = field(default_factory=dict)
    modified_data: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "rule_id": self.rule_id,
            "action": self.action.value,
            "matched": self.matched,
            "timestamp": self.timestamp.isoformat(),
            "original_data": self.original_data,
            "modified_data": self.modified_data,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class Level4FilterModule(ExecuteModuleBase):
    """
    四级过滤模块
    
    职责：
    1. 请求过滤
    2. 响应过滤
    3. 过滤规则
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4FilterModule"
        self._logger = Logger(f"L4F_{self.module_id}")
        
        # 规则存储
        self._rules: Dict[str, FilterRule] = {}
        # 过滤结果
        self._results: List[FilterResult] = []
        # 自定义条件评估器
        self._custom_evaluators: Dict[str, Callable] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级过滤模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._rules = {}
            self._results = []
            self._custom_evaluators = {}
            
            # 3. 加载默认规则
            self._load_default_rules()
            
            self._logger.info("四级过滤模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级过滤模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级过滤模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4F_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "default_action": "allow",
            "log_filtered": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("filter_config", {})
            self._config.update(custom_config)
    
    def _load_default_rules(self) -> None:
        """加载默认规则"""
        default_rules = [
            FilterRule(
                rule_id="rule_block_empty",
                name="阻止空请求",
                filter_type=FilterType.REQUEST,
                action=FilterAction.BLOCK,
                conditions=[
                    FilterCondition(
                        condition_id="cond_empty",
                        field="body",
                        condition_type=FilterConditionType.EQUALS,
                        value="",
                    ),
                ],
                priority=100,
            ),
            FilterRule(
                rule_id="rule_log_sensitive",
                name="记录敏感词",
                filter_type=FilterType.BOTH,
                action=FilterAction.LOG,
                conditions=[
                    FilterCondition(
                        condition_id="cond_sensitive",
                        field="content",
                        condition_type=FilterConditionType.CONTAINS,
                        value="password",
                    ),
                ],
                priority=50,
            ),
        ]
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级过滤模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "filter")
            
            if operation == "filter":
                result = self._filter_operation(input_data)
            elif operation == "add_rule":
                result = self._add_rule_operation(input_data)
            elif operation == "get_rules":
                result = self._get_rules_operation()
            elif operation == "get_results":
                result = self._get_results_operation(input_data)
            elif operation == "remove_rule":
                result = self._remove_rule_operation(input_data)
            elif operation == "enable_rule":
                result = self._enable_rule_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级过滤模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4FilterModule",
                    "filter_summary": {
                        "total_rules": len(self._rules),
                        "total_results": len(self._results),
                    },
                },
                message="四级过滤模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级过滤模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4F_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _filter_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行过滤"""
        import uuid
        
        data = input_data.get("data", {})
        filter_type = FilterType(input_data.get("filter_type", "both"))
        
        # 获取适用的规则
        applicable_rules = [
            r for r in self._rules.values()
            if r.enabled and (r.filter_type == filter_type or r.filter_type == FilterType.BOTH)
        ]
        
        # 按优先级排序
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        current_data = dict(data)
        applied_results = []
        
        for rule in applicable_rules:
            matched = self._evaluate_rule(rule, current_data)
            
            if matched:
                result = FilterResult(
                    result_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    action=rule.action,
                    matched=True,
                    timestamp=datetime.now(),
                    original_data=dict(current_data),
                    reason=f"匹配规则: {rule.name}",
                )
                
                if rule.action == FilterAction.ALLOW:
                    result.modified_data = dict(current_data)
                    applied_results.append(result.to_dict())
                    self._results.append(result)
                    break
                
                elif rule.action == FilterAction.BLOCK:
                    result.modified_data = {}
                    applied_results.append(result.to_dict())
                    self._results.append(result)
                    return {
                        "operation": "filter",
                        "blocked": True,
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "results": applied_results,
                    }
                
                elif rule.action == FilterAction.MODIFY:
                    current_data = self._apply_modification(current_data, rule.modification)
                    result.modified_data = dict(current_data)
                    applied_results.append(result.to_dict())
                    self._results.append(result)
                
                elif rule.action == FilterAction.LOG:
                    result.modified_data = dict(current_data)
                    applied_results.append(result.to_dict())
                    self._results.append(result)
        
        return {
            "operation": "filter",
            "blocked": False,
            "data": current_data,
            "applied_results": applied_results,
        }
    
    def _evaluate_rule(self, rule: FilterRule, data: Dict[str, Any]) -> bool:
        """评估规则"""
        if not rule.conditions:
            return True
        
        # 所有条件都必须满足（AND逻辑）
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, data):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: FilterCondition, data: Dict[str, Any]) -> bool:
        """评估单个条件"""
        field_value = data.get(condition.field)
        expected = condition.value
        
        if condition.condition_type == FilterConditionType.EQUALS:
            result = field_value == expected
        elif condition.condition_type == FilterConditionType.CONTAINS:
            result = expected in str(field_value) if field_value is not None else False
        elif condition.condition_type == FilterConditionType.STARTS_WITH:
            result = str(field_value).startswith(str(expected)) if field_value is not None else False
        elif condition.condition_type == FilterConditionType.ENDS_WITH:
            result = str(field_value).endswith(str(expected)) if field_value is not None else False
        elif condition.condition_type == FilterConditionType.REGEX:
            try:
                pattern = re.compile(str(expected))
                result = bool(pattern.search(str(field_value))) if field_value is not None else False
            except re.error:
                result = False
        elif condition.condition_type == FilterConditionType.GREATER_THAN:
            try:
                result = float(field_value) > float(expected) if field_value is not None else False
            except (ValueError, TypeError):
                result = False
        elif condition.condition_type == FilterConditionType.LESS_THAN:
            try:
                result = float(field_value) < float(expected) if field_value is not None else False
            except (ValueError, TypeError):
                result = False
        elif condition.condition_type == FilterConditionType.IN_LIST:
            result = field_value in expected if isinstance(expected, list) else False
        elif condition.condition_type == FilterConditionType.CUSTOM:
            evaluator_name = condition.metadata.get("evaluator")
            if evaluator_name and evaluator_name in self._custom_evaluators:
                result = self._custom_evaluators[evaluator_name](field_value, expected)
            else:
                result = False
        else:
            result = False
        
        # 处理否定
        if condition.negate:
            result = not result
        
        return result
    
    def _apply_modification(self, data: Dict[str, Any], modification: Dict[str, Any]) -> Dict[str, Any]:
        """应用修改"""
        result = dict(data)
        
        for field, change in modification.items():
            if isinstance(change, dict):
                operation = change.get("operation")
                value = change.get("value")
                
                if operation == "set":
                    result[field] = value
                elif operation == "remove":
                    result.pop(field, None)
                elif operation == "append" and field in result:
                    if isinstance(result[field], list):
                        result[field].append(value)
                elif operation == "prepend" and field in result:
                    if isinstance(result[field], list):
                        result[field].insert(0, value)
                elif operation == "replace":
                    old = change.get("old")
                    if field in result and isinstance(result[field], str):
                        result[field] = result[field].replace(str(old), str(value))
            else:
                result[field] = change
        
        return result
    
    def _add_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加规则"""
        rule_id = input_data.get("rule_id")
        
        conditions = []
        for cond_data in input_data.get("conditions", []):
            condition = FilterCondition(
                condition_id=cond_data.get("condition_id", ""),
                field=cond_data.get("field", ""),
                condition_type=FilterConditionType(cond_data.get("condition_type", "equals")),
                value=cond_data.get("value"),
                negate=cond_data.get("negate", False),
                metadata=cond_data.get("metadata", {}),
            )
            conditions.append(condition)
        
        rule = FilterRule(
            rule_id=rule_id,
            name=input_data.get("name", ""),
            filter_type=FilterType(input_data.get("filter_type", "both")),
            action=FilterAction(input_data.get("action", "allow")),
            conditions=conditions,
            priority=input_data.get("priority", 0),
            enabled=input_data.get("enabled", True),
            modification=input_data.get("modification", {}),
            metadata=input_data.get("metadata", {}),
        )
        self._rules[rule_id] = rule
        
        return {"operation": "add_rule", "rule_id": rule_id, "added": True}
    
    def _get_rules_operation(self) -> Dict[str, Any]:
        """获取所有规则"""
        return {
            "operation": "get_rules",
            "rules": [r.to_dict() for r in self._rules.values()],
        }
    
    def _get_results_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取过滤结果"""
        limit = input_data.get("limit", 100)
        rule_id = input_data.get("rule_id")
        
        results = self._results
        if rule_id:
            results = [r for r in results if r.rule_id == rule_id]
        
        results = sorted(results, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_results",
            "total": len(self._results),
            "returned": len(results),
            "results": [r.to_dict() for r in results],
        }
    
    def _remove_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """移除规则"""
        rule_id = input_data.get("rule_id")
        
        if rule_id in self._rules:
            del self._rules[rule_id]
            return {"operation": "remove_rule", "rule_id": rule_id, "removed": True}
        
        return {"operation": "remove_rule", "rule_id": rule_id, "removed": False}
    
    def _enable_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """启用/禁用规则"""
        rule_id = input_data.get("rule_id")
        enabled = input_data.get("enabled", True)
        
        if rule_id not in self._rules:
            return {"operation": "enable_rule", "error": "规则不存在", "success": False}
        
        self._rules[rule_id].enabled = enabled
        
        return {
            "operation": "enable_rule",
            "rule_id": rule_id,
            "enabled": enabled,
            "success": True,
        }
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级过滤模块校验开始")
        
        checks = []
        
        if isinstance(self._rules, dict):
            checks.append("rules_valid")
        if isinstance(self._results, list):
            checks.append("results_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._custom_evaluators, dict):
            checks.append("evaluators_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="filter_validation",
                message="四级过滤模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="filter_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("rules", {rid: r.to_dict() for rid, r in self._rules.items()})
        snapshot.set_state("result_count", len(self._results))
        snapshot.metadata["module_type"] = "Level4FilterModule"
    
    # 公共接口
    def filter_data(self, data: Dict[str, Any], filter_type: FilterType = FilterType.BOTH) -> Dict[str, Any]:
        """过滤数据"""
        result = self._filter_operation({"data": data, "filter_type": filter_type.value})
        return result.get("data", data) if not result.get("blocked") else {}
    
    def add_rule(self, rule: FilterRule) -> None:
        """添加规则"""
        self._rules[rule.rule_id] = rule
    
    def register_evaluator(self, name: str, evaluator: Callable) -> None:
        """注册自定义评估器"""
        self._custom_evaluators[name] = evaluator
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4FilterModule",
    "FilterRule",
    "FilterCondition",
    "FilterResult",
    "FilterType",
    "FilterAction",
    "FilterConditionType",
]
