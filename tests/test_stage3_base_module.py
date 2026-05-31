"""
第3阶段验证测试
验证模块基类的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from core.base_module import (
    ModulePrivateState,
    BaseModule,
    ControlModuleBase,
    ExecuteModuleBase,
)

from core_types.core_types import (
    ModuleID, TaskID,
    ModuleType, ModuleLevel, ModuleState,
    ModuleParam, TaskParam,
    InitResult, ModuleInput, ModuleOutput,
    CheckResult,
    SnapshotData,
)

from interfaces.module_interface import (
    InitRequest, InitContext,
    ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext,
    SnapshotRequest, SnapshotContext,
    create_default_init_request,
)


# 创建测试用的具体模块类
class TestControlModule(ControlModuleBase):
    """测试管控模块"""
    
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        return InitResult.success_result(self.module_id, "测试管控模块初始化成功")
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        return ModuleOutput.success_output(
            request.module_input.task_id,
            {"result": "control_run_success"},
            "管控模块执行成功"
        )
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        return CheckResult.passed_result("test_check", "管控模块校验通过")
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        snapshot.set_state("control_data", "test_control_value")


class TestExecuteModule(ExecuteModuleBase):
    """测试执行模块"""
    
    def _do_init(self, request: InitRequest, context: InitContext) -> InitResult:
        return InitResult.success_result(self.module_id, "测试执行模块初始化成功")
    
    def _do_run(self, request: ExecutionRequest, context: ExecutionContext) -> ModuleOutput:
        return ModuleOutput.success_output(
            request.module_input.task_id,
            {"result": "execute_run_success"},
            "执行模块执行成功"
        )
    
    def _do_check(self, request: ValidationRequest, context: ValidationContext) -> CheckResult:
        return CheckResult.passed_result("test_check", "执行模块校验通过")
    
    def _do_snapshot(self, request: SnapshotRequest, context: SnapshotContext, snapshot: SnapshotData) -> None:
        snapshot.set_state("execute_data", "test_execute_value")


def test_module_private_state():
    """测试模块私有状态容器"""
    print("测试 ModulePrivateState...")
    
    module_id = ModuleID()
    state = ModulePrivateState(module_id=module_id)
    
    # 测试基础状态
    assert state.module_id == module_id
    assert state.module_type == ModuleType.CONTROL
    assert state.module_state == ModuleState.UNINITIALIZED
    
    # 测试内部数据操作
    state.set_data("key1", "value1")
    assert state.get_data("key1") == "value1"
    assert state.get_data("nonexistent", "default") == "default"
    assert state.has_data("key1") == True
    assert state.has_data("nonexistent") == False
    
    # 测试获取所有数据
    all_data = state.get_all_data()
    assert all_data["key1"] == "value1"
    
    # 测试恢复数据
    state.clear_data()
    assert state.has_data("key1") == False
    state.restore_data({"restored": "data"})
    assert state.get_data("restored") == "data"
    
    print("✓ ModulePrivateState 测试通过")


def test_base_module_properties():
    """测试模块基类属性"""
    print("测试 BaseModule 属性...")
    
    module = TestControlModule()
    
    # 测试属性存在
    assert module.module_id is not None
    assert module.module_type == ModuleType.CONTROL
    assert module.module_level == ModuleLevel.LEVEL1
    assert module.module_state == ModuleState.UNINITIALIZED
    assert module.parent_module_id is None
    assert module.module_name == ""
    
    print("✓ BaseModule 属性测试通过")


def test_twin_structure():
    """测试双子结构管理"""
    print("测试双子结构管理...")
    
    parent = TestControlModule()
    control_child = TestControlModule()
    execute_child = TestExecuteModule()
    
    # 初始状态：没有子模块
    assert parent.has_children() == False
    assert parent.get_control_child() is None
    assert parent.get_execute_child() is None
    
    # 验证空双子结构
    report = parent.validate_twin_structure()
    assert report.overall_passed == True
    
    # 设置管控子模块
    parent.set_control_child(control_child)
    assert parent.get_control_child() == control_child
    assert parent.has_children() == True
    
    # 此时双子结构不完整（只有1个子模块）
    report = parent.validate_twin_structure()
    assert report.overall_passed == False
    
    # 设置执行子模块
    parent.set_execute_child(execute_child)
    assert parent.get_execute_child() == execute_child
    
    # 此时双子结构完整
    report = parent.validate_twin_structure()
    assert report.overall_passed == True
    
    # 验证子模块的父模块ID
    assert control_child.parent_module_id == parent.module_id
    assert execute_child.parent_module_id == parent.module_id
    
    # 测试获取所有子模块
    children = parent.get_all_children()
    assert len(children) == 2
    
    print("✓ 双子结构管理测试通过")


def test_twin_structure_validation():
    """测试双子结构验证"""
    print("测试双子结构验证...")
    
    parent = TestControlModule()
    
    # 测试错误类型
    wrong_control = TestExecuteModule()  # 用执行模块作为管控子模块
    
    try:
        parent.set_control_child(wrong_control)
        assert False, "应该抛出ValueError"
    except ValueError as e:
        assert "CONTROL" in str(e)
    
    wrong_execute = TestControlModule()  # 用管控模块作为执行子模块
    
    try:
        parent.set_execute_child(wrong_execute)
        assert False, "应该抛出ValueError"
    except ValueError as e:
        assert "EXECUTE" in str(e)
    
    print("✓ 双子结构验证测试通过")


def test_module_initialization():
    """测试模块初始化"""
    print("测试模块初始化...")
    
    module = TestControlModule()
    module_id = module.module_id
    
    # 创建初始化请求
    init_request = create_default_init_request(module_id, "TestModule")
    init_context = InitContext()
    
    # 执行初始化
    result = module.module_init(init_request, init_context)
    
    assert result.success == True
    assert module.module_state == ModuleState.READY
    assert module.module_name == "TestModule"
    
    # 重复初始化应该失败
    result2 = module.module_init(init_request, init_context)
    assert result2.success == False
    assert "状态不正确" in result2.error_detail
    
    print("✓ 模块初始化测试通过")


def test_module_execution():
    """测试模块执行"""
    print("测试模块执行...")
    
    module = TestControlModule()
    
    # 未初始化时执行应该失败
    task_id = TaskID()
    exec_request = ExecutionRequest(
        module_input=ModuleInput(task_id=task_id, data={}),
    )
    exec_context = ExecutionContext()
    
    result = module.module_run(exec_request, exec_context)
    assert result.success == False
    assert "未初始化" in result.error_detail
    
    # 初始化后执行
    init_request = create_default_init_request(module.module_id, "TestModule")
    module.module_init(init_request, InitContext())
    
    result = module.module_run(exec_request, exec_context)
    assert result.success == True
    assert result.data["result"] == "control_run_success"
    assert result.execution_time_ms >= 0
    
    print("✓ 模块执行测试通过")


def test_module_check():
    """测试模块校验"""
    print("测试模块校验...")
    
    module = TestControlModule()
    
    val_request = ValidationRequest(
        check_type="test_check",
        check_data={"value": 123},
    )
    val_context = ValidationContext()
    
    result = module.module_check(val_request, val_context)
    
    assert result.passed == True
    assert result.check_type == "test_check"
    
    print("✓ 模块校验测试通过")


def test_module_snapshot():
    """测试模块快照"""
    print("测试模块快照...")
    
    module = TestControlModule()
    
    # 初始化模块
    init_request = create_default_init_request(module.module_id, "TestModule")
    module.module_init(init_request, InitContext())
    
    # 创建快照
    snap_request = SnapshotRequest(snapshot_type="full")
    snap_context = SnapshotContext()
    
    snapshot = module.create_snapshot(snap_request, snap_context)
    
    assert snapshot.module_id == module.module_id
    assert snapshot.get_state("module_name") == "TestModule"
    assert snapshot.get_state("control_data") == "test_control_value"
    assert snapshot.get_state("module_type") == "CONTROL"
    
    print("✓ 模块快照测试通过")


def test_snapshot_restore():
    """测试快照恢复"""
    print("测试快照恢复...")
    
    from interfaces.module_interface import RestoreRequest
    
    module = TestControlModule()
    
    # 初始化并创建快照
    init_request = create_default_init_request(module.module_id, "TestModule")
    module.module_init(init_request, InitContext())
    
    snap_request = SnapshotRequest(snapshot_type="full")
    snap_context = SnapshotContext()
    snapshot = module.create_snapshot(snap_request, snap_context)
    
    # 创建新模块并从快照恢复
    new_module = TestControlModule()
    # 设置相同的module_id
    new_module._state.module_id = module.module_id
    
    restore_request = RestoreRequest(
        snapshot_data=snapshot,
        validate_before_restore=True,
    )
    
    result = new_module.restore_from_snapshot(restore_request)
    
    assert result.success == True
    assert new_module.module_name == "TestModule"
    
    print("✓ 快照恢复测试通过")


def test_control_module_base():
    """测试管控模块基类"""
    print("测试 ControlModuleBase...")
    
    # 使用TestControlModule来测试，因为它继承自ControlModuleBase
    module = TestControlModule()
    
    # 管控模块类型固定为CONTROL
    assert module.module_type == ModuleType.CONTROL
    
    print("✓ ControlModuleBase 测试通过")


def test_execute_module_base():
    """测试执行模块基类"""
    print("测试 ExecuteModuleBase...")
    
    # 使用TestExecuteModule来测试，因为它继承自ExecuteModuleBase
    module = TestExecuteModule()
    
    # 执行模块类型固定为EXECUTE
    assert module.module_type == ModuleType.EXECUTE
    
    print("✓ ExecuteModuleBase 测试通过")


def test_event_system():
    """测试事件系统"""
    print("测试事件系统...")
    
    module = TestControlModule()
    events_received = []
    
    def event_listener(event):
        events_received.append(event.event_type)
    
    # 添加监听器
    module.add_event_listener(event_listener)
    
    # 初始化会触发事件
    init_request = create_default_init_request(module.module_id, "TestModule")
    module.module_init(init_request, InitContext())
    
    # 验证事件被触发
    assert len(events_received) > 0
    
    # 移除监听器
    module.remove_event_listener(event_listener)
    
    print("✓ 事件系统测试通过")


def test_to_dict():
    """测试转换为字典"""
    print("测试 to_dict...")
    
    module = TestControlModule()
    
    # 初始化
    init_request = create_default_init_request(module.module_id, "TestModule")
    module.module_init(init_request, InitContext())
    
    # 转换为字典
    module_dict = module.to_dict()
    
    assert module_dict["module_name"] == "TestModule"
    assert module_dict["module_type"] == "CONTROL"
    assert module_dict["module_state"] == "READY"
    assert module_dict["initialized"] == True
    
    print("✓ to_dict 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第3阶段验证测试 - 模块基类实现")
    print("=" * 60)
    print()
    
    tests = [
        test_module_private_state,
        test_base_module_properties,
        test_twin_structure,
        test_twin_structure_validation,
        test_module_initialization,
        test_module_execution,
        test_module_check,
        test_module_snapshot,
        test_snapshot_restore,
        test_control_module_base,
        test_execute_module_base,
        test_event_system,
        test_to_dict,
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
        print("✓ 第3阶段验证通过！")
        return True
    else:
        print("✗ 第3阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
