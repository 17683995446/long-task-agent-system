"""
阶段46：四级数据校验模块
Level4ValidationModule

职责定义：
- 数据校验
- 规则引擎
- 校验报告
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


class ValidationSeverity(Enum):
    """校验严重级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationRuleType(Enum):
    """校验规则类型"""
    REQUIRED = "required"
    TYPE = "type"
    RANGE = "range"
    PATTERN = "pattern"
    LENGTH = "length"
    CUSTOM = "custom"
    ENUM = "enum"


@dataclass
class ValidationRule:
    """校验规则"""
    rule_id: str
    name: str
    rule_type: ValidationRuleType
    field: str
    params: Dict[str, Any] = field(default_factory=dict)
    severity: ValidationSeverity = ValidationSeverity.ERROR
    message: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "rule_type": self.rule_type.value,
            "field": self.field,
            "params": self.params,
            "severity": self.severity.value,
            "message": self.message,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class ValidationError:
    """校验错误"""
    error_id: str
    rule_id: str
    field: str
    message: str
    severity: ValidationSeverity
    value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "rule_id": self.rule_id,
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "value": str(self.value) if self.value is not None else None,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationReport:
    """校验报告"""
    report_id: str
    timestamp: datetime
    total_rules: int
    passed_rules: int
    failed_rules: int
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "valid": len(self.errors) == 0,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


class Level4ValidationModule(ExecuteModuleBase):
    """
    四级数据校验模块
    
    职责：
    1. 数据校验
    2. 规则引擎
    3. 校验报告
    """
    
    def __init__(self, module_id: ModuleID = None):
        super().__init__(module_id=module_id)
        self._state.module_level = ModuleLevel.LEVEL4
        self._state.module_name = "Level4ValidationModule"
        self._logger = Logger(f"L4V_{self.module_id}")
        
        # 规则存储
        self._rules: Dict[str, ValidationRule] = {}
        # 校验报告
        self._reports: List[ValidationReport] = []
        # 自定义校验器
        self._custom_validators: Dict[str, Callable] = {}
        
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        """初始化模块"""
        try:
            self._logger.info("四级数据校验模块初始化开始")
            
            # 1. 加载配置
            self._load_config(request)
            
            # 2. 初始化存储
            self._rules = {}
            self._reports = []
            self._custom_validators = {}
            
            # 3. 加载默认规则
            self._load_default_rules()
            
            self._logger.info("四级数据校验模块初始化完成")
            
            return InitResult.success_result(
                module_id=self.module_id,
                message="四级数据校验模块初始化成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级数据校验模块初始化失败: {e}")
            return InitResult.failure_result(
                module_id=self.module_id,
                error_code="L4V_INIT_FAILED",
                error_detail=str(e)
            )
    
    def _load_config(self, request: InitRequest) -> None:
        """加载配置"""
        self._config = {
            "enabled": True,
            "priority": 5,
            "stop_on_first_error": False,
            "include_warnings": True,
        }
        if request.task_param:
            custom_config = request.task_param.get_param("validation_config", {})
            self._config.update(custom_config)
    
    def _load_default_rules(self) -> None:
        """加载默认规则"""
        default_rules = [
            ValidationRule(
                rule_id="rule_required",
                name="必填校验",
                rule_type=ValidationRuleType.REQUIRED,
                field="*",
                message="字段 {field} 为必填项",
            ),
            ValidationRule(
                rule_id="rule_email",
                name="邮箱格式校验",
                rule_type=ValidationRuleType.PATTERN,
                field="email",
                params={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
                message="邮箱格式不正确",
            ),
            ValidationRule(
                rule_id="rule_min_length",
                name="最小长度校验",
                rule_type=ValidationRuleType.LENGTH,
                field="password",
                params={"min": 8},
                message="密码长度至少为8位",
            ),
        ]
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        """执行模块逻辑"""
        self._logger.info("四级数据校验模块执行开始")
        
        try:
            task_id = request.module_input.task_id if request.module_input else TaskID()
            
            # 安全获取输入数据
            input_data = {}
            if request.module_input and hasattr(request.module_input, 'data') and request.module_input.data:
                input_data = request.module_input.data
            elif request.module_input and hasattr(request.module_input, 'input_data') and request.module_input.input_data:
                input_data = request.module_input.input_data
            operation = input_data.get("operation", "validate")
            
            if operation == "validate":
                result = self._validate_operation(input_data)
            elif operation == "add_rule":
                result = self._add_rule_operation(input_data)
            elif operation == "get_rules":
                result = self._get_rules_operation()
            elif operation == "get_reports":
                result = self._get_reports_operation(input_data)
            elif operation == "register_validator":
                result = self._register_validator_operation(input_data)
            elif operation == "remove_rule":
                result = self._remove_rule_operation(input_data)
            else:
                result = {"error": f"未知操作: {operation}"}
            
            self._logger.info("四级数据校验模块执行完成")
            
            return ModuleOutput.success_output(
                task_id=task_id,
                data={
                    "result": result,
                    "module": "Level4ValidationModule",
                    "validation_summary": {
                        "total_rules": len(self._rules),
                        "total_reports": len(self._reports),
                    },
                },
                message="四级数据校验模块执行成功"
            )
            
        except Exception as e:
            self._logger.error(f"四级数据校验模块执行失败: {e}")
            return ModuleOutput.failure_output(
                task_id=request.module_input.task_id if request.module_input else TaskID(),
                error_code="L4V_EXECUTION_FAILED",
                error_detail=str(e)
            )
    
    def _validate_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行校验"""
        import uuid
        
        data = input_data.get("data", {})
        rule_ids = input_data.get("rule_ids")
        
        report = ValidationReport(
            report_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            total_rules=0,
            passed_rules=0,
            failed_rules=0,
        )
        
        # 确定要使用的规则
        rules_to_check = []
        if rule_ids:
            rules_to_check = [self._rules[r] for r in rule_ids if r in self._rules and self._rules[r].enabled]
        else:
            rules_to_check = [r for r in self._rules.values() if r.enabled]
        
        report.total_rules = len(rules_to_check)
        
        for rule in rules_to_check:
            passed, error = self._execute_rule(rule, data)
            if passed:
                report.passed_rules += 1
            else:
                report.failed_rules += 1
                if error:
                    if error.severity == ValidationSeverity.ERROR:
                        report.errors.append(error)
                    elif error.severity == ValidationSeverity.WARNING:
                        report.warnings.append(error)
                
                if self._config.get("stop_on_first_error", False) and report.errors:
                    break
        
        self._reports.append(report)
        
        return {
            "operation": "validate",
            "report_id": report.report_id,
            "valid": len(report.errors) == 0,
            "report": report.to_dict(),
        }
    
    def _execute_rule(self, rule: ValidationRule, data: Dict[str, Any]) -> tuple:
        """执行单个规则"""
        import uuid
        
        field = rule.field
        value = data.get(field) if field != "*" else data
        
        if rule.rule_type == ValidationRuleType.REQUIRED:
            if value is None or (isinstance(value, str) and not value.strip()):
                error = ValidationError(
                    error_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    field=field,
                    message=rule.message or f"字段 {field} 为必填项",
                    severity=rule.severity,
                    value=value,
                )
                return False, error
        
        elif rule.rule_type == ValidationRuleType.TYPE:
            expected_type = rule.params.get("type")
            if expected_type and value is not None:
                type_map = {
                    "string": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                }
                if expected_type in type_map and not isinstance(value, type_map[expected_type]):
                    error = ValidationError(
                        error_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        field=field,
                        message=rule.message or f"字段 {field} 类型应为 {expected_type}",
                        severity=rule.severity,
                        value=value,
                    )
                    return False, error
        
        elif rule.rule_type == ValidationRuleType.RANGE:
            if value is not None:
                min_val = rule.params.get("min")
                max_val = rule.params.get("max")
                try:
                    num_value = float(value)
                    if min_val is not None and num_value < min_val:
                        error = ValidationError(
                            error_id=str(uuid.uuid4()),
                            rule_id=rule.rule_id,
                            field=field,
                            message=rule.message or f"字段 {field} 应大于等于 {min_val}",
                            severity=rule.severity,
                            value=value,
                        )
                        return False, error
                    if max_val is not None and num_value > max_val:
                        error = ValidationError(
                            error_id=str(uuid.uuid4()),
                            rule_id=rule.rule_id,
                            field=field,
                            message=rule.message or f"字段 {field} 应小于等于 {max_val}",
                            severity=rule.severity,
                            value=value,
                        )
                        return False, error
                except (ValueError, TypeError):
                    pass
        
        elif rule.rule_type == ValidationRuleType.PATTERN:
            if value is not None:
                pattern = rule.params.get("pattern", "")
                if pattern and not re.match(pattern, str(value)):
                    error = ValidationError(
                        error_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        field=field,
                        message=rule.message or f"字段 {field} 格式不正确",
                        severity=rule.severity,
                        value=value,
                    )
                    return False, error
        
        elif rule.rule_type == ValidationRuleType.LENGTH:
            if value is not None:
                min_len = rule.params.get("min")
                max_len = rule.params.get("max")
                try:
                    length = len(value)
                    if min_len is not None and length < min_len:
                        error = ValidationError(
                            error_id=str(uuid.uuid4()),
                            rule_id=rule.rule_id,
                            field=field,
                            message=rule.message or f"字段 {field} 长度应大于等于 {min_len}",
                            severity=rule.severity,
                            value=value,
                        )
                        return False, error
                    if max_len is not None and length > max_len:
                        error = ValidationError(
                            error_id=str(uuid.uuid4()),
                            rule_id=rule.rule_id,
                            field=field,
                            message=rule.message or f"字段 {field} 长度应小于等于 {max_len}",
                            severity=rule.severity,
                            value=value,
                        )
                        return False, error
                except TypeError:
                    pass
        
        elif rule.rule_type == ValidationRuleType.ENUM:
            if value is not None:
                allowed = rule.params.get("values", [])
                if allowed and value not in allowed:
                    error = ValidationError(
                        error_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        field=field,
                        message=rule.message or f"字段 {field} 的值不在允许列表中",
                        severity=rule.severity,
                        value=value,
                    )
                    return False, error
        
        elif rule.rule_type == ValidationRuleType.CUSTOM:
            validator_name = rule.params.get("validator")
            if validator_name and validator_name in self._custom_validators:
                validator = self._custom_validators[validator_name]
                try:
                    result = validator(value, rule.params)
                    if not result:
                        error = ValidationError(
                            error_id=str(uuid.uuid4()),
                            rule_id=rule.rule_id,
                            field=field,
                            message=rule.message or f"字段 {field} 自定义校验失败",
                            severity=rule.severity,
                            value=value,
                        )
                        return False, error
                except Exception as e:
                    error = ValidationError(
                        error_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        field=field,
                        message=rule.message or f"字段 {field} 自定义校验异常: {e}",
                        severity=rule.severity,
                        value=value,
                    )
                    return False, error
        
        return True, None
    
    def _add_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加规则"""
        rule_id = input_data.get("rule_id")
        
        rule = ValidationRule(
            rule_id=rule_id,
            name=input_data.get("name", ""),
            rule_type=ValidationRuleType(input_data.get("rule_type", "required")),
            field=input_data.get("field", ""),
            params=input_data.get("params", {}),
            severity=ValidationSeverity(input_data.get("severity", "error")),
            message=input_data.get("message", ""),
            enabled=input_data.get("enabled", True),
            metadata=input_data.get("metadata", {}),
        )
        self._rules[rule_id] = rule
        
        return {
            "operation": "add_rule",
            "rule_id": rule_id,
            "added": True,
        }
    
    def _get_rules_operation(self) -> Dict[str, Any]:
        """获取所有规则"""
        return {
            "operation": "get_rules",
            "rules": [r.to_dict() for r in self._rules.values()],
        }
    
    def _get_reports_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取校验报告"""
        limit = input_data.get("limit", 10)
        reports = sorted(self._reports, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return {
            "operation": "get_reports",
            "total": len(self._reports),
            "returned": len(reports),
            "reports": [r.to_dict() for r in reports],
        }
    
    def _register_validator_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册自定义校验器"""
        # 注意：实际使用时需要通过代码注册，这里仅记录
        validator_name = input_data.get("validator_name")
        
        return {
            "operation": "register_validator",
            "validator_name": validator_name,
            "registered": True,
            "note": "自定义校验器需要通过代码注册",
        }
    
    def _remove_rule_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """移除规则"""
        rule_id = input_data.get("rule_id")
        
        if rule_id in self._rules:
            del self._rules[rule_id]
            return {"operation": "remove_rule", "rule_id": rule_id, "removed": True}
        
        return {"operation": "remove_rule", "rule_id": rule_id, "removed": False}
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        """校验模块"""
        self._logger.info("四级数据校验模块校验开始")
        
        checks = []
        
        if isinstance(self._rules, dict):
            checks.append("rules_valid")
        if isinstance(self._reports, list):
            checks.append("reports_valid")
        if self._state.module_level == ModuleLevel.LEVEL4:
            checks.append("level_valid")
        if isinstance(self._custom_validators, dict):
            checks.append("validators_valid")
        
        all_passed = len(checks) == 4
        
        if all_passed:
            return CheckResult.passed_result(
                check_type="validation_validation",
                message="四级数据校验模块校验通过"
            )
        else:
            return CheckResult.failed_result(
                check_type="validation_validation",
                message=f"校验失败: {checks}",
                severity="error"
            )
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        """创建快照"""
        snapshot.set_state("config", self._config)
        snapshot.set_state("rules", {rid: r.to_dict() for rid, r in self._rules.items()})
        snapshot.set_state("report_count", len(self._reports))
        snapshot.set_state("validator_names", list(self._custom_validators.keys()))
        snapshot.metadata["module_type"] = "Level4ValidationModule"
    
    # 公共接口
    def validate(self, data: Dict[str, Any], rule_ids: List[str] = None) -> ValidationReport:
        """校验数据"""
        result = self._validate_operation({"data": data, "rule_ids": rule_ids})
        report_id = result.get("report_id")
        return next((r for r in self._reports if r.report_id == report_id), None)
    
    def add_rule(self, rule: ValidationRule) -> None:
        """添加规则"""
        self._rules[rule.rule_id] = rule
    
    def register_custom_validator(self, name: str, validator: Callable) -> None:
        """注册自定义校验器"""
        self._custom_validators[name] = validator
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._logger.info(f"配置已更新: {config}")


__all__ = [
    "Level4ValidationModule",
    "ValidationRule",
    "ValidationError",
    "ValidationReport",
    "ValidationSeverity",
    "ValidationRuleType",
]
