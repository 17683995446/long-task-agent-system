"""
超长任务Agent树形双生子模块化执行系统 - 校验器基类实现
Validator Base Implementation for Long-Task Agent Twin-Module Execution System

阶段13：校验器基类实现
遵循原则：图难于其易，为大于其细
核心约束：抽象基类，可继承扩展，支持校验并修正
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

from core_types.core_types import ModuleID


# =============================================================================
# 1. 校验结果枚举 (Validation Result Enumeration)
# =============================================================================

class ValidationLevel(Enum):
    """校验结果级别"""
    VALID = auto()        # 有效
    WARNING = auto()      # 警告（可继续）
    ERROR = auto()        # 错误（需修正）
    CRITICAL = auto()     # 严重错误（不可恢复）


# =============================================================================
# 2. 校验结果 (Validation Result)
# =============================================================================

@dataclass
class ValidationResult:
    """
    校验结果
    记录单次校验的完整信息
    """
    is_valid: bool = True
    level: ValidationLevel = ValidationLevel.VALID
    message: str = ""
    field: str = ""              # 校验的字段名
    expected: Any = None         # 期望值
    actual: Any = None           # 实际值
    fixed: bool = False          # 是否已修正
    fixed_value: Any = None      # 修正后的值

    @classmethod
    def valid(cls, message: str = "校验通过") -> "ValidationResult":
        """创建有效结果"""
        return cls(
            is_valid=True,
            level=ValidationLevel.VALID,
            message=message,
        )

    @classmethod
    def warning(cls, message: str, field: str = "") -> "ValidationResult":
        """创建警告结果"""
        return cls(
            is_valid=True,
            level=ValidationLevel.WARNING,
            message=message,
            field=field,
        )

    @classmethod
    def error(
        cls,
        message: str,
        field: str = "",
        expected: Any = None,
        actual: Any = None,
    ) -> "ValidationResult":
        """创建错误结果"""
        return cls(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message=message,
            field=field,
            expected=expected,
            actual=actual,
        )

    @classmethod
    def critical(cls, message: str, field: str = "") -> "ValidationResult":
        """创建严重错误结果"""
        return cls(
            is_valid=False,
            level=ValidationLevel.CRITICAL,
            message=message,
            field=field,
        )

    def with_fix(self, fixed_value: Any) -> "ValidationResult":
        """标记已修正"""
        self.fixed = True
        self.fixed_value = fixed_value
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "level": self.level.name,
            "message": self.message,
            "field": self.field,
            "expected": str(self.expected) if self.expected is not None else None,
            "actual": str(self.actual) if self.actual is not None else None,
            "fixed": self.fixed,
            "fixed_value": str(self.fixed_value) if self.fixed_value is not None else None,
        }


# =============================================================================
# 3. 校验报告 (Validation Report)
# =============================================================================

@dataclass
class ValidationReport:
    """
    校验报告
    汇总多次校验结果
    """
    validator_name: str = ""
    total_checks: int = 0
    passed: int = 0
    warnings: int = 0
    errors: int = 0
    critical: int = 0
    results: List[ValidationResult] = field(default_factory=list)
    all_fixed: bool = True

    def add_result(self, result: ValidationResult) -> None:
        """添加校验结果"""
        self.results.append(result)
        self.total_checks += 1

        if result.is_valid:
            if result.level == ValidationLevel.WARNING:
                self.warnings += 1
            else:
                self.passed += 1
        else:
            if result.level == ValidationLevel.CRITICAL:
                self.critical += 1
            else:
                self.errors += 1

        if not result.fixed and not result.is_valid:
            self.all_fixed = False

    @property
    def is_valid(self) -> bool:
        """是否全部有效（忽略警告）"""
        return self.errors == 0 and self.critical == 0

    @property
    def has_issues(self) -> bool:
        """是否有任何问题（包括警告）"""
        return self.warnings > 0 or self.errors > 0 or self.critical > 0

    def get_errors(self) -> List[ValidationResult]:
        """获取所有错误"""
        return [r for r in self.results if not r.is_valid]

    def get_warnings(self) -> List[ValidationResult]:
        """获取所有警告"""
        return [r for r in self.results if r.level == ValidationLevel.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "validator_name": self.validator_name,
            "total_checks": self.total_checks,
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
            "critical": self.critical,
            "is_valid": self.is_valid,
            "all_fixed": self.all_fixed,
            "results": [r.to_dict() for r in self.results],
        }


# =============================================================================
# 4. 校验规则 (Validation Rule)
# =============================================================================

@dataclass
class ValidationRule:
    """
    校验规则
    定义单个校验规则
    """
    name: str                           # 规则名称
    field: str                          # 校验字段
    rule_type: str                      # 规则类型（required/type/range/regex/custom）
    params: Dict[str, Any] = field(default_factory=dict)  # 规则参数
    message: str = ""                   # 错误消息模板
    auto_fix: bool = False              # 是否自动修正
    fix_value: Any = None               # 修正值（固定值）
    fix_strategy: str = "default"       # 修正策略（default/previous/computed）

    def get_param(self, key: str, default: Any = None) -> Any:
        """获取规则参数"""
        return self.params.get(key, default)


# =============================================================================
# 5. 校验器基类 (Validator Base)
# =============================================================================

class ValidatorBase(ABC):
    """
    校验器抽象基类

    所有校验器的基类，提供：
    1. 校验规则管理
    2. 校验执行框架
    3. 校验并修正功能
    4. 校验报告生成

    使用方式：
        class MyValidator(ValidatorBase):
            def validate(self, data, context=None):
                # 实现具体校验逻辑
                pass

        validator = MyValidator()
        report = validator.validate_and_fix(data)
    """

    def __init__(self, name: str = "BaseValidator"):
        """
        初始化校验器

        Args:
            name: 校验器名称
        """
        self._name = name
        self._rules: List[ValidationRule] = []

    # =====================================================================
    # 属性
    # =====================================================================

    @property
    def name(self) -> str:
        """校验器名称"""
        return self._name

    @property
    def rules(self) -> List[ValidationRule]:
        """校验规则列表"""
        return self._rules

    # =====================================================================
    # 规则管理
    # =====================================================================

    def add_rule(self, rule: ValidationRule) -> None:
        """添加校验规则"""
        self._rules.append(rule)

    def add_rules(self, rules: List[ValidationRule]) -> None:
        """批量添加校验规则"""
        self._rules.extend(rules)

    def clear_rules(self) -> None:
        """清除所有规则"""
        self._rules.clear()

    def get_rule(self, name: str) -> Optional[ValidationRule]:
        """根据名称获取规则"""
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None

    # =====================================================================
    # 抽象方法（子类必须实现）
    # =====================================================================

    @abstractmethod
    def validate(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """
        执行校验（抽象方法）

        Args:
            data: 待校验数据
            context: 校验上下文

        Returns:
            ValidationReport: 校验报告
        """
        pass

    # =====================================================================
    # 校验并修正
    # =====================================================================

    def validate_and_fix(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        auto_fix: bool = True,
    ) -> Tuple[Any, ValidationReport]:
        """
        校验并修正数据

        Args:
            data: 待校验数据
            context: 校验上下文
            auto_fix: 是否自动修正

        Returns:
            Tuple[Any, ValidationReport]: (修正后数据, 校验报告)
        """
        # 1. 执行校验
        report = self.validate(data, context)

        # 2. 如果不需要修正或没有错误，直接返回
        if not auto_fix or report.is_valid:
            return data, report

        # 3. 执行修正
        fixed_data = self._apply_fixes(data, report, context)

        # 4. 重新校验
        final_report = self.validate(fixed_data, context)

        return fixed_data, final_report

    def _apply_fixes(
        self,
        data: Any,
        report: ValidationReport,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        应用修正（内部方法）

        Args:
            data: 原始数据
            report: 校验报告
            context: 上下文

        Returns:
            Any: 修正后数据
        """
        # 基类提供默认实现，子类可重写
        if not isinstance(data, dict):
            return data

        fixed_data = dict(data)

        for result in report.get_errors():
            if result.field and result.fixed_value is not None:
                fixed_data[result.field] = result.fixed_value
            else:
                # 尝试从规则获取修正值
                rule = self._find_rule_for_field(result.field)
                if rule and rule.auto_fix:
                    fix_value = self._compute_fix_value(rule, fixed_data, context)
                    if fix_value is not None:
                        fixed_data[result.field] = fix_value
                        result.with_fix(fix_value)

        return fixed_data

    def _find_rule_for_field(self, field: str) -> Optional[ValidationRule]:
        """查找字段的校验规则"""
        for rule in self._rules:
            if rule.field == field:
                return rule
        return None

    def _compute_fix_value(
        self,
        rule: ValidationRule,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """计算修正值"""
        if rule.fix_strategy == "default":
            return rule.fix_value
        elif rule.fix_strategy == "previous":
            # 从上下文获取之前的值
            if context and "previous" in context:
                prev = context["previous"]
                if isinstance(prev, dict) and rule.field in prev:
                    return prev[rule.field]
        return rule.fix_value

    # =====================================================================
    # 辅助方法
    # =====================================================================

    def _create_report(self) -> ValidationReport:
        """创建校验报告"""
        return ValidationReport(validator_name=self._name)

    def _check_required(
        self,
        data: Dict[str, Any],
        field: str,
        report: ValidationReport,
    ) -> bool:
        """检查必填字段"""
        if field not in data or data[field] is None:
            result = ValidationResult.error(
                message=f"字段 '{field}' 是必填项",
                field=field,
                expected="非空值",
                actual=None,
            )
            report.add_result(result)
            return False
        return True

    def _check_type(
        self,
        data: Dict[str, Any],
        field: str,
        expected_type: type,
        report: ValidationReport,
    ) -> bool:
        """检查字段类型"""
        if field not in data:
            return True  # 字段不存在，跳过类型检查

        actual = data[field]
        if not isinstance(actual, expected_type):
            result = ValidationResult.error(
                message=f"字段 '{field}' 类型错误",
                field=field,
                expected=expected_type.__name__,
                actual=type(actual).__name__,
            )
            report.add_result(result)
            return False
        return True

    def _check_range(
        self,
        data: Dict[str, Any],
        field: str,
        min_val: Any,
        max_val: Any,
        report: ValidationReport,
    ) -> bool:
        """检查值范围"""
        if field not in data:
            return True

        value = data[field]
        
        # 跳过不可比较的类型
        try:
            if min_val is not None and value < min_val:
                result = ValidationResult.error(
                    message=f"字段 '{field}' 值小于最小值",
                    field=field,
                    expected=f">= {min_val}",
                    actual=value,
                )
                report.add_result(result)
                return False

            if max_val is not None and value > max_val:
                result = ValidationResult.error(
                    message=f"字段 '{field}' 值大于最大值",
                    field=field,
                    expected=f"<= {max_val}",
                    actual=value,
                )
                report.add_result(result)
                return False
        except TypeError:
            # 类型不可比较，跳过范围检查
            pass

        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name}, rules={len(self._rules)})"


# =============================================================================
# 6. 组合校验器 (Composite Validator)
# =============================================================================

class CompositeValidator(ValidatorBase):
    """
    组合校验器
    支持组合多个校验器
    """

    def __init__(self, name: str = "CompositeValidator"):
        super().__init__(name)
        self._validators: List[ValidatorBase] = []

    def add_validator(self, validator: ValidatorBase) -> None:
        """添加子校验器"""
        self._validators.append(validator)

    def remove_validator(self, name: str) -> bool:
        """移除子校验器"""
        for i, v in enumerate(self._validators):
            if v.name == name:
                self._validators.pop(i)
                return True
        return False

    def validate(
        self,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationReport:
        """执行所有子校验器"""
        report = self._create_report()

        for validator in self._validators:
            sub_report = validator.validate(data, context)
            for result in sub_report.results:
                report.add_result(result)

        return report


# =============================================================================
# 模块导出列表
# =============================================================================

__all__ = [
    # 枚举
    "ValidationLevel",
    # 数据类
    "ValidationResult",
    "ValidationReport",
    "ValidationRule",
    # 基类
    "ValidatorBase",
    # 组合校验器
    "CompositeValidator",
]
