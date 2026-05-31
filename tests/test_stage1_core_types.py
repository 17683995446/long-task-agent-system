"""
第1阶段验证测试
验证核心类型定义的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from core_types.core_types import (
    # 基础标识类型
    ModuleID, TaskID, StepID,
    # 枚举类型
    ModuleType, ModuleLevel, ModuleState, TaskState, StepState, ModuleEventType,
    # 参数类型
    TaskParam, ModuleParam,
    # 结果类型
    InitResult, ModuleInput, ModuleOutput, CheckResult, ValidationReport,
    # 快照类型
    SnapshotData, CheckpointData,
    # 上下文类型
    ExecutionContext,
    # 事件类型
    ModuleEvent,
    # 工具调用类型
    ToolCall, ToolResult,
    # 验证函数
    validate_module_id, validate_task_id, is_valid_module_state_transition,
)


def test_module_id():
    """测试模块ID"""
    print("测试 ModuleID...")
    
    # 测试默认创建
    mid1 = ModuleID()
    assert str(mid1) is not None
    assert len(str(mid1)) == 16
    
    # 测试带前缀创建
    mid2 = ModuleID("root")
    assert str(mid2).startswith("root_")
    
    # 测试相等性
    mid3 = ModuleID()
    mid4 = ModuleID()
    assert mid3 != mid4  # UUID应不同
    
    # 测试哈希 - 相同ID的ModuleID应该有相同的哈希值
    mid_str = str(mid3)
    # 创建一个相同ID的新对象进行测试（通过直接设置_id）
    mid_copy = ModuleID()
    mid_copy._id = mid_str
    assert hash(mid3) == hash(mid_copy)
    
    print("✓ ModuleID 测试通过")


def test_task_id():
    """测试任务ID"""
    print("测试 TaskID...")
    
    tid1 = TaskID()
    assert str(tid1).startswith("task_")
    
    tid2 = TaskID("custom")
    assert str(tid2).startswith("custom_")
    
    print("✓ TaskID 测试通过")


def test_step_id():
    """测试步骤ID"""
    print("测试 StepID...")
    
    sid = StepID("task_abc123", 42)
    assert str(sid) == "task_abc123_step_000042"
    assert sid.step_number == 42
    
    print("✓ StepID 测试通过")


def test_module_type():
    """测试模块类型枚举"""
    print("测试 ModuleType...")
    
    assert ModuleType.CONTROL is not None
    assert ModuleType.EXECUTE is not None
    assert ModuleType.CONTROL != ModuleType.EXECUTE
    
    print("✓ ModuleType 测试通过")


def test_module_level():
    """测试模块层级枚举"""
    print("测试 ModuleLevel...")
    
    assert ModuleLevel.ROOT.value == 0
    assert ModuleLevel.LEVEL1.value == 1
    assert ModuleLevel.LEVEL2.value == 2
    assert ModuleLevel.LEVEL3.value == 3
    assert ModuleLevel.LEVEL4.value == 4
    
    print("✓ ModuleLevel 测试通过")


def test_module_state():
    """测试模块状态枚举"""
    print("测试 ModuleState...")
    
    states = [
        ModuleState.UNINITIALIZED,
        ModuleState.INITIALIZING,
        ModuleState.READY,
        ModuleState.RUNNING,
        ModuleState.PAUSED,
        ModuleState.COMPLETED,
        ModuleState.ERROR,
        ModuleState.RECOVERING,
    ]
    assert len(states) == 8
    
    print("✓ ModuleState 测试通过")


def test_task_param():
    """测试任务参数"""
    print("测试 TaskParam...")
    
    param = TaskParam(
        task_name="测试任务",
        task_description="这是一个测试任务",
        max_steps=5000,
        timeout_seconds=1800,
    )
    
    assert param.task_name == "测试任务"
    assert param.max_steps == 5000
    assert param.enable_checkpoint == True
    
    # 测试自定义参数
    param.set_param("custom_key", "custom_value")
    assert param.get_param("custom_key") == "custom_value"
    assert param.get_param("nonexistent", "default") == "default"
    
    print("✓ TaskParam 测试通过")


def test_init_result():
    """测试初始化结果"""
    print("测试 InitResult...")
    
    mid = ModuleID()
    
    # 测试成功结果
    success_result = InitResult.success_result(mid, "初始化成功")
    assert success_result.success == True
    assert success_result.message == "初始化成功"
    
    # 测试失败结果
    failure_result = InitResult.failure_result(mid, "ERR_001", "参数错误")
    assert failure_result.success == False
    assert failure_result.error_code == "ERR_001"
    
    print("✓ InitResult 测试通过")


def test_module_input_output():
    """测试模块输入输出"""
    print("测试 ModuleInput/ModuleOutput...")
    
    tid = TaskID()
    
    # 测试输入
    input_data = ModuleInput(
        task_id=tid,
        data={"key": "value"},
        context={"ctx": "data"},
    )
    assert input_data.get_data("key") == "value"
    input_data.set_data("new_key", "new_value")
    assert input_data.get_data("new_key") == "new_value"
    
    # 测试成功输出
    success_output = ModuleOutput.success_output(tid, {"result": "ok"}, "执行成功")
    assert success_output.success == True
    assert success_output.data["result"] == "ok"
    
    # 测试失败输出
    failure_output = ModuleOutput.failure_output(tid, "ERR_002", "执行失败")
    assert failure_output.success == False
    assert failure_output.error_code == "ERR_002"
    
    print("✓ ModuleInput/ModuleOutput 测试通过")


def test_check_result():
    """测试校验结果"""
    print("测试 CheckResult...")
    
    # 测试通过结果
    passed = CheckResult.passed_result("type_check", "类型校验通过")
    assert passed.passed == True
    assert passed.check_type == "type_check"
    
    # 测试失败结果
    failed = CheckResult.failed_result("range_check", "范围校验失败", "error")
    assert failed.passed == False
    assert failed.severity == "error"
    
    print("✓ CheckResult 测试通过")


def test_validation_report():
    """测试校验报告"""
    print("测试 ValidationReport...")
    
    tid = TaskID()
    report = ValidationReport(
        task_id=tid,
        overall_passed=True,
    )
    
    # 添加通过的结果
    report.add_result(CheckResult.passed_result("check1"))
    assert report.overall_passed == True
    
    # 添加失败的结果
    report.add_result(CheckResult.failed_result("check2", "失败", "error"))
    assert report.overall_passed == False
    
    print("✓ ValidationReport 测试通过")


def test_snapshot_data():
    """测试快照数据"""
    print("测试 SnapshotData...")
    
    mid = ModuleID()
    snapshot = SnapshotData(module_id=mid)
    
    snapshot.set_state("step", 100)
    snapshot.set_state("data", {"key": "value"})
    
    assert snapshot.get_state("step") == 100
    assert snapshot.get_state("data")["key"] == "value"
    assert snapshot.get_state("nonexistent", "default") == "default"
    assert snapshot.snapshot_version == "1.0"
    
    print("✓ SnapshotData 测试通过")


def test_checkpoint_data():
    """测试断点数据"""
    print("测试 CheckpointData...")
    
    tid = TaskID()
    checkpoint = CheckpointData(
        task_id=tid,
        current_step=500,
        total_steps=1000,
    )
    
    assert checkpoint.current_step == 500
    assert checkpoint.total_steps == 1000
    assert checkpoint.task_state == TaskState.EXECUTING
    
    print("✓ CheckpointData 测试通过")


def test_execution_context():
    """测试执行上下文"""
    print("测试 ExecutionContext...")
    
    tid = TaskID()
    ctx = ExecutionContext(task_id=tid, total_steps=100)
    
    # 测试上下文栈
    ctx.push_context({"level": 1})
    ctx.push_context({"level": 2})
    assert len(ctx.context_stack) == 2
    
    popped = ctx.pop_context()
    assert popped["level"] == 2
    assert len(ctx.context_stack) == 1
    
    # 测试步骤记录
    step_id = StepID(str(tid), 1)
    ctx.record_step(step_id)
    assert ctx.current_step == 1
    assert len(ctx.step_history) == 1
    
    print("✓ ExecutionContext 测试通过")


def test_module_event():
    """测试模块事件"""
    print("测试 ModuleEvent...")
    
    mid = ModuleID()
    tid = TaskID()
    
    event = ModuleEvent(
        event_type=ModuleEventType.INIT_STARTED,
        module_id=mid,
        task_id=tid,
        data={"info": "test"},
    )
    
    assert event.event_type == ModuleEventType.INIT_STARTED
    assert event.module_id == mid
    assert event.data["info"] == "test"
    
    print("✓ ModuleEvent 测试通过")


def test_tool_call_result():
    """测试工具调用和结果"""
    print("测试 ToolCall/ToolResult...")
    
    # 测试工具调用
    call = ToolCall(
        tool_name="test_tool",
        tool_params={"param1": "value1"},
        timeout_seconds=60,
    )
    assert call.tool_name == "test_tool"
    assert call.timeout_seconds == 60
    
    # 测试结果
    result = ToolResult(
        call_id=call.call_id,
        success=True,
        result_data={"output": "result"},
    )
    assert result.call_id == call.call_id
    assert result.success == True
    
    print("✓ ToolCall/ToolResult 测试通过")


def test_validation_functions():
    """测试验证函数"""
    print("测试验证函数...")
    
    # 测试模块ID验证
    mid = ModuleID()
    validated_mid = validate_module_id(mid)
    assert validated_mid == mid
    
    validated_mid2 = validate_module_id("test_prefix")
    assert str(validated_mid2).startswith("test_prefix_")
    
    # 测试任务ID验证
    tid = TaskID()
    validated_tid = validate_task_id(tid)
    assert validated_tid == tid
    
    # 测试状态转换验证
    assert is_valid_module_state_transition(
        ModuleState.UNINITIALIZED, ModuleState.INITIALIZING
    ) == True
    
    assert is_valid_module_state_transition(
        ModuleState.UNINITIALIZED, ModuleState.RUNNING
    ) == False
    
    assert is_valid_module_state_transition(
        ModuleState.READY, ModuleState.RUNNING
    ) == True
    
    print("✓ 验证函数测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第1阶段验证测试 - 核心类型定义")
    print("=" * 60)
    print()
    
    tests = [
        test_module_id,
        test_task_id,
        test_step_id,
        test_module_type,
        test_module_level,
        test_module_state,
        test_task_param,
        test_init_result,
        test_module_input_output,
        test_check_result,
        test_validation_report,
        test_snapshot_data,
        test_checkpoint_data,
        test_execution_context,
        test_module_event,
        test_tool_call_result,
        test_validation_functions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 测试失败: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"测试完成: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("✓ 第1阶段验证通过！")
        return True
    else:
        print("✗ 第1阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
