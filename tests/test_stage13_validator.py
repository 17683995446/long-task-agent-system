"""
阶段13测试：校验器基类测试
Test Stage 13: Validator Base Tests

测试范围：
1. ValidationResult校验结果
2. ValidationReport校验报告
3. ValidationRule校验规则
4. ValidatorBase校验器基类
5. CompositeValidator组合校验器
6. 具体校验器实现示例
"""

import unittest

import sys
sys.path.insert(0, '/workspace')

from validators.validator_base import (
    ValidationLevel,
    ValidationResult,
    ValidationReport,
    ValidationRule,
    ValidatorBase,
    CompositeValidator,
)


# =============================================================================
# 1. ValidationResult测试
# =============================================================================

class TestValidationResult(unittest.TestCase):
    """测试校验结果"""

    def test_valid_result(self):
        """测试有效结果"""
        result = ValidationResult.valid("校验通过")

        self.assertTrue(result.is_valid)
        self.assertEqual(result.level, ValidationLevel.VALID)
        self.assertEqual(result.message, "校验通过")

    def test_warning_result(self):
        """测试警告结果"""
        result = ValidationResult.warning("字段可能有问题", field="name")

        self.assertTrue(result.is_valid)
        self.assertEqual(result.level, ValidationLevel.WARNING)
        self.assertEqual(result.field, "name")

    def test_error_result(self):
        """测试错误结果"""
        result = ValidationResult.error(
            "类型错误",
            field="age",
            expected="int",
            actual="str",
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.level, ValidationLevel.ERROR)
        self.assertEqual(result.expected, "int")
        self.assertEqual(result.actual, "str")

    def test_critical_result(self):
        """测试严重错误结果"""
        result = ValidationResult.critical("数据损坏", field="data")

        self.assertFalse(result.is_valid)
        self.assertEqual(result.level, ValidationLevel.CRITICAL)

    def test_with_fix(self):
        """测试修正标记"""
        result = ValidationResult.error("值无效", field="count")
        result.with_fix(0)

        self.assertTrue(result.fixed)
        self.assertEqual(result.fixed_value, 0)

    def test_to_dict(self):
        """测试转换为字典"""
        result = ValidationResult.error("错误", field="x", expected=10, actual=5)
        data = result.to_dict()

        self.assertEqual(data["level"], "ERROR")
        self.assertEqual(data["field"], "x")
        self.assertFalse(data["is_valid"])


# =============================================================================
# 2. ValidationReport测试
# =============================================================================

class TestValidationReport(unittest.TestCase):
    """测试校验报告"""

    def test_empty_report(self):
        """测试空报告"""
        report = ValidationReport(validator_name="TestValidator")

        self.assertEqual(report.total_checks, 0)
        self.assertTrue(report.is_valid)
        self.assertFalse(report.has_issues)

    def test_add_valid_result(self):
        """测试添加有效结果"""
        report = ValidationReport()
        report.add_result(ValidationResult.valid())

        self.assertEqual(report.passed, 1)
        self.assertEqual(report.total_checks, 1)
        self.assertTrue(report.is_valid)

    def test_add_warning_result(self):
        """测试添加警告结果"""
        report = ValidationReport()
        report.add_result(ValidationResult.warning("警告"))

        self.assertEqual(report.warnings, 1)
        self.assertTrue(report.is_valid)  # 警告不影响有效性
        self.assertTrue(report.has_issues)

    def test_add_error_result(self):
        """测试添加错误结果"""
        report = ValidationReport()
        report.add_result(ValidationResult.error("错误"))

        self.assertEqual(report.errors, 1)
        self.assertFalse(report.is_valid)
        self.assertTrue(report.has_issues)

    def test_add_critical_result(self):
        """测试添加严重错误结果"""
        report = ValidationReport()
        report.add_result(ValidationResult.critical("严重错误"))

        self.assertEqual(report.critical, 1)
        self.assertFalse(report.is_valid)

    def test_mixed_results(self):
        """测试混合结果"""
        report = ValidationReport()
        report.add_result(ValidationResult.valid())
        report.add_result(ValidationResult.warning("警告"))
        report.add_result(ValidationResult.error("错误"))

        self.assertEqual(report.passed, 1)
        self.assertEqual(report.warnings, 1)
        self.assertEqual(report.errors, 1)
        self.assertEqual(report.total_checks, 3)

    def test_get_errors(self):
        """测试获取错误列表"""
        report = ValidationReport()
        report.add_result(ValidationResult.valid())
        report.add_result(ValidationResult.error("错误1", field="a"))
        report.add_result(ValidationResult.error("错误2", field="b"))

        errors = report.get_errors()
        self.assertEqual(len(errors), 2)

    def test_get_warnings(self):
        """测试获取警告列表"""
        report = ValidationReport()
        report.add_result(ValidationResult.warning("警告1"))
        report.add_result(ValidationResult.warning("警告2"))
        report.add_result(ValidationResult.error("错误"))

        warnings = report.get_warnings()
        self.assertEqual(len(warnings), 2)

    def test_to_dict(self):
        """测试转换为字典"""
        report = ValidationReport(validator_name="Test")
        report.add_result(ValidationResult.valid())
        data = report.to_dict()

        self.assertEqual(data["validator_name"], "Test")
        self.assertEqual(data["passed"], 1)


# =============================================================================
# 3. ValidationRule测试
# =============================================================================

class TestValidationRule(unittest.TestCase):
    """测试校验规则"""

    def test_rule_creation(self):
        """测试规则创建"""
        rule = ValidationRule(
            name="required_name",
            field="name",
            rule_type="required",
            message="名称是必填项",
        )

        self.assertEqual(rule.name, "required_name")
        self.assertEqual(rule.field, "name")
        self.assertEqual(rule.rule_type, "required")
        self.assertFalse(rule.auto_fix)

    def test_rule_with_params(self):
        """测试带参数的规则"""
        rule = ValidationRule(
            name="range_age",
            field="age",
            rule_type="range",
            params={"min": 0, "max": 150},
        )

        self.assertEqual(rule.get_param("min"), 0)
        self.assertEqual(rule.get_param("max"), 150)
        self.assertIsNone(rule.get_param("missing"))

    def test_rule_with_auto_fix(self):
        """测试自动修正规则"""
        rule = ValidationRule(
            name="default_status",
            field="status",
            rule_type="required",
            auto_fix=True,
            fix_value="pending",
        )

        self.assertTrue(rule.auto_fix)
        self.assertEqual(rule.fix_value, "pending")


# =============================================================================
# 4. 具体校验器实现（用于测试）
# =============================================================================

class SimpleDictValidator(ValidatorBase):
    """简单字典校验器（用于测试）"""

    def __init__(self):
        super().__init__(name="SimpleDictValidator")

    def validate(self, data, context=None):
        report = self._create_report()

        if not isinstance(data, dict):
            report.add_result(ValidationResult.critical("数据必须是字典"))
            return report

        # 检查必填字段
        for rule in self._rules:
            if rule.rule_type == "required":
                self._check_required(data, rule.field, report)
            elif rule.rule_type == "type":
                expected_type = rule.get_param("type")
                if expected_type:
                    self._check_type(data, rule.field, expected_type, report)
            elif rule.rule_type == "range":
                min_val = rule.get_param("min")
                max_val = rule.get_param("max")
                self._check_range(data, rule.field, min_val, max_val, report)

        return report


# =============================================================================
# 5. ValidatorBase测试
# =============================================================================

class TestValidatorBase(unittest.TestCase):
    """测试校验器基类"""

    def setUp(self):
        self.validator = SimpleDictValidator()

    def test_validator_creation(self):
        """测试校验器创建"""
        self.assertEqual(self.validator.name, "SimpleDictValidator")
        self.assertEqual(len(self.validator.rules), 0)

    def test_add_rule(self):
        """测试添加规则"""
        rule = ValidationRule("r1", "name", "required")
        self.validator.add_rule(rule)

        self.assertEqual(len(self.validator.rules), 1)
        self.assertEqual(self.validator.get_rule("r1"), rule)

    def test_add_rules(self):
        """测试批量添加规则"""
        rules = [
            ValidationRule("r1", "name", "required"),
            ValidationRule("r2", "age", "required"),
        ]
        self.validator.add_rules(rules)

        self.assertEqual(len(self.validator.rules), 2)

    def test_clear_rules(self):
        """测试清除规则"""
        self.validator.add_rule(ValidationRule("r1", "name", "required"))
        self.validator.clear_rules()

        self.assertEqual(len(self.validator.rules), 0)

    def test_validate_dict_type(self):
        """测试校验字典类型"""
        report = self.validator.validate({})

        self.assertTrue(report.is_valid)

    def test_validate_non_dict(self):
        """测试校验非字典类型"""
        report = self.validator.validate("not a dict")

        self.assertFalse(report.is_valid)
        self.assertEqual(report.critical, 1)

    def test_validate_required_field(self):
        """测试校验必填字段"""
        self.validator.add_rule(ValidationRule("r1", "name", "required"))

        # 缺少字段
        report = self.validator.validate({})
        self.assertFalse(report.is_valid)

        # 有字段
        report = self.validator.validate({"name": "test"})
        self.assertTrue(report.is_valid)

    def test_validate_type_field(self):
        """测试校验字段类型"""
        self.validator.add_rule(
            ValidationRule("r1", "age", "type", params={"type": int})
        )

        # 类型正确
        report = self.validator.validate({"age": 25})
        self.assertTrue(report.is_valid)

        # 类型错误
        report = self.validator.validate({"age": "25"})
        self.assertFalse(report.is_valid)

    def test_validate_range(self):
        """测试校验范围"""
        self.validator.add_rule(
            ValidationRule("r1", "age", "range", params={"min": 0, "max": 150})
        )

        # 在范围内
        report = self.validator.validate({"age": 25})
        self.assertTrue(report.is_valid)

        # 超出范围
        report = self.validator.validate({"age": 200})
        self.assertFalse(report.is_valid)

    def test_validate_and_fix_no_fix(self):
        """测试校验但不修正"""
        self.validator.add_rule(ValidationRule("r1", "name", "required"))

        data = {}
        fixed, report = self.validator.validate_and_fix(data, auto_fix=False)

        self.assertEqual(fixed, {})
        self.assertFalse(report.is_valid)

    def test_validate_and_fix_with_fix(self):
        """测试校验并修正"""
        self.validator.add_rule(
            ValidationRule(
                "r1", "status", "required",
                auto_fix=True,
                fix_value="pending",
            )
        )

        data = {}
        fixed, report = self.validator.validate_and_fix(data, auto_fix=True)

        self.assertEqual(fixed.get("status"), "pending")


# =============================================================================
# 6. CompositeValidator测试
# =============================================================================

class TestCompositeValidator(unittest.TestCase):
    """测试组合校验器"""

    def setUp(self):
        self.composite = CompositeValidator(name="TestComposite")

    def test_add_validator(self):
        """测试添加子校验器"""
        v1 = SimpleDictValidator()
        self.composite.add_validator(v1)

        self.assertEqual(len(self.composite._validators), 1)

    def test_remove_validator(self):
        """测试移除子校验器"""
        v1 = SimpleDictValidator()
        self.composite.add_validator(v1)

        result = self.composite.remove_validator("SimpleDictValidator")
        self.assertTrue(result)
        self.assertEqual(len(self.composite._validators), 0)

    def test_composite_validate(self):
        """测试组合校验"""
        v1 = SimpleDictValidator()
        v1.add_rule(ValidationRule("r1", "name", "required"))

        v2 = SimpleDictValidator()
        v2.add_rule(ValidationRule("r2", "age", "required"))

        self.composite.add_validator(v1)
        self.composite.add_validator(v2)

        # 缺少两个字段
        report = self.composite.validate({})
        self.assertEqual(report.errors, 2)

        # 缺少一个字段
        report = self.composite.validate({"name": "test"})
        self.assertEqual(report.errors, 1)

        # 全部满足
        report = self.composite.validate({"name": "test", "age": 25})
        self.assertTrue(report.is_valid)


# =============================================================================
# 7. 集成测试
# =============================================================================

class TestValidatorIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_validation_workflow(self):
        """测试完整校验流程"""
        # 创建校验器
        validator = SimpleDictValidator()

        # 添加规则
        validator.add_rules([
            ValidationRule("r1", "name", "required"),
            ValidationRule("r2", "age", "required"),
            ValidationRule("r3", "age", "type", params={"type": int}),
            ValidationRule("r4", "age", "range", params={"min": 0, "max": 150}),
        ])

        # 测试数据
        test_cases = [
            # (数据, 是否应该有效)
            ({}, False),  # 缺少所有必填字段
            ({"name": "Alice"}, False),  # 缺少age
            ({"name": "Alice", "age": 25}, True),  # 有效
            ({"name": "Bob", "age": -5}, False),  # age超出范围
            ({"name": "Charlie", "age": "30"}, False),  # age类型错误
        ]

        for data, expected_valid in test_cases:
            report = validator.validate(data)
            self.assertEqual(
                report.is_valid, expected_valid,
                f"数据 {data} 校验结果应为 {expected_valid}"
            )

    def test_auto_fix_workflow(self):
        """测试自动修正流程"""
        validator = SimpleDictValidator()

        # 添加带自动修正的规则
        validator.add_rules([
            ValidationRule("r1", "status", "required", auto_fix=True, fix_value="pending"),
            ValidationRule("r2", "count", "required", auto_fix=True, fix_value=0),
        ])

        # 原始数据缺少字段
        original = {"name": "test"}

        # 校验并修正
        fixed, report = validator.validate_and_fix(original, auto_fix=True)

        # 检查修正结果
        self.assertEqual(fixed["status"], "pending")
        self.assertEqual(fixed["count"], 0)


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
