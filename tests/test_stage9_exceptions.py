"""
第9阶段验证测试
验证异常处理体系的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from core.exceptions import (
    ExceptionSeverity,
    ExceptionContext,
    ModuleException,
    InitException,
    ParamValidationException,
    ResourceInitException,
    RunException,
    PreconditionException,
    TimeoutException,
    InvalidResultException,
    SubmoduleException,
    CheckException,
    TypeCheckException,
    RangeCheckException,
    RuleCheckException,
    ValidationException,
    MissingFieldException,
    FormatException,
    RecoveryException,
    SnapshotRecoveryException,
    RollbackException,
    RetryExhaustedException,
    StateException,
    InvalidStateTransitionException,
    StateInconsistencyException,
    ConfigurationException,
    ConfigMissingException,
    TwinStructureException,
    ChildCountException,
    ChildTypeException,
    is_recoverable,
    get_exception_severity,
    exception_to_dict,
    wrap_exception,
)

from core_types.core_types import ModuleID, TaskID


def test_exception_severity():
    """测试异常严重级别"""
    print("测试异常严重级别...")
    
    assert ExceptionSeverity.DEBUG is not None
    assert ExceptionSeverity.INFO is not None
    assert ExceptionSeverity.WARNING is not None
    assert ExceptionSeverity.ERROR is not None
    assert ExceptionSeverity.CRITICAL is not None
    assert ExceptionSeverity.FATAL is not None
    
    print("✓ 异常严重级别测试通过")


def test_exception_context():
    """测试异常上下文"""
    print("测试异常上下文...")
    
    module_id = ModuleID()
    task_id = TaskID()
    
    context = ExceptionContext(
        module_id=module_id,
        module_name="TestModule",
        task_id=task_id,
        step_number=5,
        extra={"key": "value"},
    )
    
    assert context.module_id == module_id
    assert context.module_name == "TestModule"
    assert context.task_id == task_id
    assert context.step_number == 5
    assert context.extra["key"] == "value"
    
    # 测试转换为字典
    context_dict = context.to_dict()
    assert context_dict["module_name"] == "TestModule"
    assert context_dict["step_number"] == 5
    
    print("✓ 异常上下文测试通过")


def test_module_exception():
    """测试基础模块异常"""
    print("测试基础模块异常...")
    
    exc = ModuleException(
        code="TEST_001",
        message="测试异常",
        severity=ExceptionSeverity.ERROR,
        recoverable=True,
    )
    
    assert exc.code == "TEST_001"
    assert exc.message == "测试异常"
    assert exc.severity == ExceptionSeverity.ERROR
    assert exc.recoverable == True
    assert exc.cause is None
    
    # 测试字符串表示
    assert str(exc) == "[TEST_001] 测试异常"
    
    # 测试转换为字典
    exc_dict = exc.to_dict()
    assert exc_dict["code"] == "TEST_001"
    assert exc_dict["message"] == "测试异常"
    assert exc_dict["recoverable"] == True
    
    print("✓ 基础模块异常测试通过")


def test_exception_chain_methods():
    """测试异常链式方法"""
    print("测试异常链式方法...")
    
    module_id = ModuleID()
    task_id = TaskID()
    
    exc = ModuleException(
        code="TEST_001",
        message="测试异常",
    ).with_module(module_id, "TestModule").with_task(task_id).with_step(10).with_extra("custom", "value")
    
    assert exc.context.module_id == module_id
    assert exc.context.module_name == "TestModule"
    assert exc.context.task_id == task_id
    assert exc.context.step_number == 10
    assert exc.context.extra["custom"] == "value"
    
    print("✓ 异常链式方法测试通过")


def test_init_exception():
    """测试初始化异常"""
    print("测试初始化异常...")
    
    exc = InitException(
        code="INIT_001",
        message="初始化失败",
    )
    
    assert exc.code == "INIT_001"
    assert isinstance(exc, ModuleException)
    
    print("✓ 初始化异常测试通过")


def test_param_validation_exception():
    """测试参数验证异常"""
    print("测试参数验证异常...")
    
    exc = ParamValidationException(
        message="参数验证失败",
        param_name="timeout",
        param_value=-1,
    )
    
    assert exc.code == "INIT_001"
    assert exc.context.extra["param_name"] == "timeout"
    assert exc.context.extra["param_value"] == "-1"
    
    print("✓ 参数验证异常测试通过")


def test_run_exception():
    """测试执行异常"""
    print("测试执行异常...")
    
    exc = RunException(
        code="RUN_001",
        message="执行失败",
    )
    
    assert exc.code == "RUN_001"
    assert exc.recoverable == True  # 执行异常默认可恢复
    
    print("✓ 执行异常测试通过")


def test_timeout_exception():
    """测试超时异常"""
    print("测试超时异常...")
    
    exc = TimeoutException(
        message="执行超时",
        timeout_seconds=30.0,
    )
    
    assert exc.code == "RUN_002"
    assert exc.context.extra["timeout_seconds"] == 30.0
    
    print("✓ 超时异常测试通过")


def test_check_exception():
    """测试校验异常"""
    print("测试校验异常...")
    
    exc = CheckException(
        code="CHECK_001",
        message="校验失败",
    )
    
    assert exc.severity == ExceptionSeverity.WARNING  # 校验异常默认警告级别
    assert exc.recoverable == True
    
    print("✓ 校验异常测试通过")


def test_type_check_exception():
    """测试类型校验异常"""
    print("测试类型校验异常...")
    
    exc = TypeCheckException(
        message="类型校验失败",
        expected_type="int",
        actual_type="str",
    )
    
    assert exc.code == "CHECK_001"
    assert exc.context.extra["expected_type"] == "int"
    assert exc.context.extra["actual_type"] == "str"
    
    print("✓ 类型校验异常测试通过")


def test_range_check_exception():
    """测试范围校验异常"""
    print("测试范围校验异常...")
    
    exc = RangeCheckException(
        message="范围校验失败",
        value=100,
        min_value=0,
        max_value=50,
    )
    
    assert exc.code == "CHECK_002"
    assert exc.context.extra["value"] == "100"
    
    print("✓ 范围校验异常测试通过")


def test_recovery_exception():
    """测试恢复异常"""
    print("测试恢复异常...")
    
    exc = RecoveryException(
        code="REC_001",
        message="恢复失败",
    )
    
    assert exc.recoverable == False  # 恢复异常默认不可恢复
    
    print("✓ 恢复异常测试通过")


def test_snapshot_recovery_exception():
    """测试快照恢复异常"""
    print("测试快照恢复异常...")
    
    exc = SnapshotRecoveryException(
        message="快照恢复失败",
        snapshot_id="snap_123",
    )
    
    assert exc.code == "REC_001"
    assert exc.context.extra["snapshot_id"] == "snap_123"
    
    print("✓ 快照恢复异常测试通过")


def test_retry_exhausted_exception():
    """测试重试次数耗尽异常"""
    print("测试重试次数耗尽异常...")
    
    exc = RetryExhaustedException(
        message="重试次数耗尽",
        max_retries=5,
    )
    
    assert exc.code == "REC_003"
    assert exc.context.extra["max_retries"] == 5
    
    print("✓ 重试次数耗尽异常测试通过")


def test_state_exception():
    """测试状态异常"""
    print("测试状态异常...")
    
    exc = InvalidStateTransitionException(
        message="非法状态转换",
        from_state="UNINITIALIZED",
        to_state="RUNNING",
    )
    
    assert exc.code == "STATE_001"
    assert exc.context.extra["from_state"] == "UNINITIALIZED"
    assert exc.context.extra["to_state"] == "RUNNING"
    
    print("✓ 状态异常测试通过")


def test_twin_structure_exception():
    """测试双子结构异常"""
    print("测试双子结构异常...")
    
    exc = TwinStructureException(
        code="TWIN_001",
        message="双子结构异常",
    )
    
    assert exc.severity == ExceptionSeverity.CRITICAL  # 双子结构异常默认严重级别
    assert exc.recoverable == False
    
    print("✓ 双子结构异常测试通过")


def test_child_count_exception():
    """测试子模块数量异常"""
    print("测试子模块数量异常...")
    
    exc = ChildCountException(
        message="子模块数量不正确",
        expected=2,
        actual=1,
    )
    
    assert exc.code == "TWIN_001"
    assert exc.context.extra["expected"] == 2
    assert exc.context.extra["actual"] == 1
    
    print("✓ 子模块数量异常测试通过")


def test_child_type_exception():
    """测试子模块类型异常"""
    print("测试子模块类型异常...")
    
    exc = ChildTypeException(
        message="子模块类型不匹配",
        expected_type="CONTROL",
        actual_type="EXECUTE",
    )
    
    assert exc.code == "TWIN_002"
    assert exc.context.extra["expected_type"] == "CONTROL"
    assert exc.context.extra["actual_type"] == "EXECUTE"
    
    print("✓ 子模块类型异常测试通过")


def test_is_recoverable():
    """测试is_recoverable函数"""
    print("测试is_recoverable函数...")
    
    exc1 = RunException(code="RUN_001", message="可恢复异常")
    assert is_recoverable(exc1) == True
    
    exc2 = RecoveryException(code="REC_001", message="不可恢复异常")
    assert is_recoverable(exc2) == False
    
    # 普通异常
    exc3 = ValueError("普通异常")
    assert is_recoverable(exc3) == False
    
    print("✓ is_recoverable函数测试通过")


def test_get_exception_severity():
    """测试get_exception_severity函数"""
    print("测试get_exception_severity函数...")
    
    exc1 = ModuleException(
        code="TEST_001",
        message="测试",
        severity=ExceptionSeverity.CRITICAL,
    )
    assert get_exception_severity(exc1) == ExceptionSeverity.CRITICAL
    
    # 普通异常
    exc2 = ValueError("普通异常")
    assert get_exception_severity(exc2) == ExceptionSeverity.ERROR
    
    print("✓ get_exception_severity函数测试通过")


def test_exception_to_dict():
    """测试exception_to_dict函数"""
    print("测试exception_to_dict函数...")
    
    exc = ModuleException(
        code="TEST_001",
        message="测试异常",
    )
    
    exc_dict = exception_to_dict(exc)
    assert exc_dict["code"] == "TEST_001"
    assert exc_dict["message"] == "测试异常"
    
    # 普通异常
    exc2 = ValueError("普通异常")
    exc_dict2 = exception_to_dict(exc2)
    assert exc_dict2["type"] == "ValueError"
    assert exc_dict2["message"] == "普通异常"
    
    print("✓ exception_to_dict函数测试通过")


def test_wrap_exception():
    """测试wrap_exception函数"""
    print("测试wrap_exception函数...")
    
    # 包装普通异常
    original = ValueError("原始异常")
    wrapped = wrap_exception(original, code="WRAPPED_001", message="包装后的异常")
    
    assert wrapped.code == "WRAPPED_001"
    assert wrapped.message == "包装后的异常"
    assert wrapped.cause == original
    
    # ModuleException不应该被重复包装
    module_exc = ModuleException(code="TEST_001", message="模块异常")
    result = wrap_exception(module_exc)
    assert result == module_exc
    
    print("✓ wrap_exception函数测试通过")


def test_exception_with_cause():
    """测试带原始异常的异常"""
    print("测试带原始异常的异常...")
    
    original = ValueError("原始异常")
    
    exc = ModuleException(
        code="TEST_001",
        message="包装异常",
        cause=original,
    )
    
    assert exc.cause == original
    assert exc.to_dict()["cause"] == "原始异常"
    
    print("✓ 带原始异常的异常测试通过")


def test_exception_inheritance():
    """测试异常继承关系"""
    print("测试异常继承关系...")
    
    exc = ParamValidationException(message="测试")
    
    assert isinstance(exc, InitException)
    assert isinstance(exc, ModuleException)
    assert isinstance(exc, Exception)
    
    exc2 = TimeoutException(message="测试")
    assert isinstance(exc2, RunException)
    assert isinstance(exc2, ModuleException)
    
    print("✓ 异常继承关系测试通过")


def test_exception_repr():
    """测试异常repr"""
    print("测试异常repr...")
    
    exc = ModuleException(
        code="TEST_001",
        message="测试异常",
        severity=ExceptionSeverity.ERROR,
    )
    
    repr_str = repr(exc)
    assert "ModuleException" in repr_str
    assert "TEST_001" in repr_str
    assert "ERROR" in repr_str
    
    print("✓ 异常repr测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第9阶段验证测试 - 异常处理体系实现")
    print("=" * 60)
    print()
    
    tests = [
        test_exception_severity,
        test_exception_context,
        test_module_exception,
        test_exception_chain_methods,
        test_init_exception,
        test_param_validation_exception,
        test_run_exception,
        test_timeout_exception,
        test_check_exception,
        test_type_check_exception,
        test_range_check_exception,
        test_recovery_exception,
        test_snapshot_recovery_exception,
        test_retry_exhausted_exception,
        test_state_exception,
        test_twin_structure_exception,
        test_child_count_exception,
        test_child_type_exception,
        test_is_recoverable,
        test_get_exception_severity,
        test_exception_to_dict,
        test_wrap_exception,
        test_exception_with_cause,
        test_exception_inheritance,
        test_exception_repr,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 60)
    print(f"测试完成: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("✓ 第9阶段验证通过！")
        return True
    else:
        print("✗ 第9阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
