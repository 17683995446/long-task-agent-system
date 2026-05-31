"""
第4阶段验证测试
验证双子模块容器的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from core.twin_container import (
    TwinContainerError,
    TwinStructureViolationError,
    ChildTypeError,
    DuplicateChildError,
    ChildNotFoundError,
    TwinSlot,
    ChildRecord,
    TwinContainer,
    TwinContainerBuilder,
)

from core.base_module import ControlModuleBase, ExecuteModuleBase
from core_types.core_types import (
    ModuleID, TaskID,
    ModuleType, ModuleLevel, ModuleState,
    ModuleParam,
    InitResult, ModuleInput, ModuleOutput,
    CheckResult, SnapshotData,
)

from interfaces.module_interface import (
    InitRequest, InitContext,
    ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext,
    SnapshotRequest, SnapshotContext,
)


# 创建测试用的具体模块类
class MockControlModule(ControlModuleBase):
    def _do_init(self, request, context):
        return InitResult.success_result(self.module_id, "ok")
    def _do_run(self, request, context):
        return ModuleOutput.success_output(request.module_input.task_id, {})
    def _do_check(self, request, context):
        return CheckResult.passed_result("mock", "ok")
    def _do_snapshot(self, request, context, snapshot):
        pass


class MockExecuteModule(ExecuteModuleBase):
    def _do_init(self, request, context):
        return InitResult.success_result(self.module_id, "ok")
    def _do_run(self, request, context):
        return ModuleOutput.success_output(request.module_input.task_id, {})
    def _do_check(self, request, context):
        return CheckResult.passed_result("mock", "ok")
    def _do_snapshot(self, request, context, snapshot):
        pass


def test_twin_slot_enum():
    """测试双子槽位枚举"""
    print("测试 TwinSlot...")
    
    assert TwinSlot.CONTROL is not None
    assert TwinSlot.EXECUTE is not None
    assert TwinSlot.CONTROL != TwinSlot.EXECUTE
    
    print("✓ TwinSlot 测试通过")


def test_child_record():
    """测试子模块注册记录"""
    print("测试 ChildRecord...")
    
    module = MockControlModule()
    record = ChildRecord(module=module, slot=TwinSlot.CONTROL)
    
    assert record.module_id == module.module_id
    assert record.module_type == ModuleType.CONTROL
    assert record.slot == TwinSlot.CONTROL
    
    print("✓ ChildRecord 测试通过")


def test_container_creation():
    """测试容器创建"""
    print("测试容器创建...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    
    assert container.parent_id == parent_id
    assert container.child_count == 0
    assert container.is_empty == True
    assert container.is_complete == False
    assert container.is_sealed == False
    assert container.has_control_child == False
    assert container.has_execute_child == False
    
    print("✓ 容器创建测试通过")


def test_add_control_child():
    """测试添加管控子模块"""
    print("测试添加管控子模块...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    
    container.add_control_child(control)
    
    assert container.child_count == 1
    assert container.has_control_child == True
    assert container.get_control_child() == control
    assert container.is_complete == False
    
    # 验证父引用已设置
    assert control.parent_module_id == parent_id
    
    print("✓ 添加管控子模块测试通过")


def test_add_execute_child():
    """测试添加执行子模块"""
    print("测试添加执行子模块...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    execute = MockExecuteModule()
    
    container.add_execute_child(execute)
    
    assert container.child_count == 1
    assert container.has_execute_child == True
    assert container.get_execute_child() == execute
    assert container.is_complete == False
    
    print("✓ 添加执行子模块测试通过")


def test_complete_twin_structure():
    """测试完整双子结构"""
    print("测试完整双子结构...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    assert container.child_count == 2
    assert container.is_complete == True
    assert container.is_empty == False
    assert container.get_control_child() == control
    assert container.get_execute_child() == execute
    
    print("✓ 完整双子结构测试通过")


def test_wrong_type_rejection():
    """测试错误类型拒绝"""
    print("测试错误类型拒绝...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    
    # 用执行模块作为管控子模块
    execute = MockExecuteModule()
    try:
        container.add_control_child(execute)
        assert False, "应该抛出ChildTypeError"
    except ChildTypeError as e:
        assert "CONTROL" in str(e)
    
    # 用管控模块作为执行子模块
    control = MockControlModule()
    try:
        container.add_execute_child(control)
        assert False, "应该抛出ChildTypeError"
    except ChildTypeError as e:
        assert "EXECUTE" in str(e)
    
    print("✓ 错误类型拒绝测试通过")


def test_duplicate_child_rejection():
    """测试重复子模块拒绝"""
    print("测试重复子模块拒绝...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control1 = MockControlModule()
    control2 = MockControlModule()
    
    container.add_control_child(control1)
    
    # 重复添加管控子模块
    try:
        container.add_control_child(control2)
        assert False, "应该抛出DuplicateChildError"
    except DuplicateChildError as e:
        assert "CONTROL" in str(e)
    
    print("✓ 重复子模块拒绝测试通过")


def test_seal_container():
    """测试容器封印"""
    print("测试容器封印...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    # 封印
    container.seal()
    assert container.is_sealed == True
    
    # 封印后不能添加
    try:
        container.add_control_child(MockControlModule())
        assert False, "应该抛出TwinContainerError"
    except TwinContainerError:
        pass
    
    # 封印后不能移除
    try:
        container.remove_control_child()
        assert False, "应该抛出TwinContainerError"
    except TwinContainerError:
        pass
    
    # 封印后不能清空
    try:
        container.clear_children()
        assert False, "应该抛出TwinContainerError"
    except TwinContainerError:
        pass
    
    # 解封
    container.unseal()
    assert container.is_sealed == False
    
    print("✓ 容器封印测试通过")


def test_seal_incomplete_fails():
    """测试不完整时封印失败"""
    print("测试不完整时封印失败...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    
    container.add_control_child(control)
    
    try:
        container.seal()
        assert False, "应该抛出TwinStructureViolationError"
    except TwinStructureViolationError as e:
        assert "不完整" in str(e)
    
    print("✓ 不完整时封印失败测试通过")


def test_remove_child():
    """测试移除子模块"""
    print("测试移除子模块...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    # 移除管控子模块
    removed = container.remove_control_child()
    assert removed == control
    assert container.child_count == 1
    assert container.has_control_child == False
    assert control.parent_module_id is None
    
    # 移除不存在的子模块
    try:
        container.remove_control_child()
        assert False, "应该抛出ChildNotFoundError"
    except ChildNotFoundError:
        pass
    
    print("✓ 移除子模块测试通过")


def test_clear_children():
    """测试清空子模块"""
    print("测试清空子模块...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    container.clear_children()
    
    assert container.child_count == 0
    assert container.is_empty == True
    assert control.parent_module_id is None
    assert execute.parent_module_id is None
    
    print("✓ 清空子模块测试通过")


def test_validate_structure():
    """测试结构校验"""
    print("测试结构校验...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    
    # 空容器校验
    report = container.validate_structure()
    assert report.overall_passed == False
    
    # 完整双子结构校验
    control = MockControlModule()
    execute = MockExecuteModule()
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    report = container.validate_structure()
    assert report.overall_passed == True
    
    print("✓ 结构校验测试通过")


def test_contains_and_find():
    """测试包含和查找"""
    print("测试包含和查找...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    # 测试contains
    assert container.contains(control.module_id) == True
    assert container.contains(execute.module_id) == True
    assert container.contains(ModuleID()) == False
    
    # 测试find_slot
    assert container.find_slot(control.module_id) == TwinSlot.CONTROL
    assert container.find_slot(execute.module_id) == TwinSlot.EXECUTE
    assert container.find_slot(ModuleID()) is None
    
    print("✓ 包含和查找测试通过")


def test_get_all_children():
    """测试获取所有子模块"""
    print("测试获取所有子模块...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    children = container.get_all_children()
    assert len(children) == 2
    assert children[0] == control  # CONTROL在前
    assert children[1] == execute  # EXECUTE在后
    
    print("✓ 获取所有子模块测试通过")


def test_iteration():
    """测试迭代"""
    print("测试迭代...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    # 测试__iter__
    children_list = list(container)
    assert len(children_list) == 2
    
    # 测试__len__
    assert len(container) == 2
    
    # 测试__contains__
    assert control.module_id in container
    
    print("✓ 迭代测试通过")


def test_structure_summary():
    """测试结构摘要"""
    print("测试结构摘要...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    summary = container.get_structure_summary()
    assert "TwinContainer" in summary
    assert "CONTROL" in summary
    assert "EXECUTE" in summary
    
    # 带缩进
    summary_indented = container.get_structure_summary(indent=2)
    assert "    " in summary_indented
    
    print("✓ 结构摘要测试通过")


def test_to_dict():
    """测试转换为字典"""
    print("测试 to_dict...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container.add_control_child(control)
    container.add_execute_child(execute)
    
    d = container.to_dict()
    assert d["child_count"] == 2
    assert d["is_complete"] == True
    assert d["control_child"] is not None
    assert d["execute_child"] is not None
    
    print("✓ to_dict 测试通过")


def test_builder_basic():
    """测试构建器基本用法"""
    print("测试构建器基本用法...")
    
    parent_id = ModuleID("parent")
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container = (TwinContainerBuilder(parent_id)
        .set_control_child(control)
        .set_execute_child(execute)
        .build())
    
    assert container.is_complete == True
    assert container.is_sealed == True  # 默认自动封印
    assert container.get_control_child() == control
    assert container.get_execute_child() == execute
    
    print("✓ 构建器基本用法测试通过")


def test_builder_no_auto_seal():
    """测试构建器不自动封印"""
    print("测试构建器不自动封印...")
    
    parent_id = ModuleID("parent")
    control = MockControlModule()
    execute = MockExecuteModule()
    
    container = (TwinContainerBuilder(parent_id)
        .set_control_child(control)
        .set_execute_child(execute)
        .auto_seal(False)
        .build())
    
    assert container.is_complete == True
    assert container.is_sealed == False
    
    print("✓ 构建器不自动封印测试通过")


def test_builder_incomplete_fails():
    """测试构建器不完整时失败"""
    print("测试构建器不完整时失败...")
    
    parent_id = ModuleID("parent")
    control = MockControlModule()
    
    try:
        TwinContainerBuilder(parent_id).set_control_child(control).build()
        assert False, "应该抛出TwinStructureViolationError"
    except TwinStructureViolationError as e:
        assert "不完整" in str(e)
    
    print("✓ 构建器不完整时失败测试通过")


def test_builder_wrong_type_fails():
    """测试构建器类型错误"""
    print("测试构建器类型错误...")
    
    parent_id = ModuleID("parent")
    execute = MockExecuteModule()
    
    try:
        TwinContainerBuilder(parent_id).set_control_child(execute)
        assert False, "应该抛出ChildTypeError"
    except ChildTypeError:
        pass
    
    print("✓ 构建器类型错误测试通过")


def test_repr():
    """测试字符串表示"""
    print("测试 __repr__...")
    
    parent_id = ModuleID("parent")
    container = TwinContainer(parent_id)
    
    repr_str = repr(container)
    assert "TwinContainer" in repr_str
    assert "0/2" in repr_str
    
    print("✓ __repr__ 测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第4阶段验证测试 - 双子模块容器实现")
    print("=" * 60)
    print()
    
    tests = [
        test_twin_slot_enum,
        test_child_record,
        test_container_creation,
        test_add_control_child,
        test_add_execute_child,
        test_complete_twin_structure,
        test_wrong_type_rejection,
        test_duplicate_child_rejection,
        test_seal_container,
        test_seal_incomplete_fails,
        test_remove_child,
        test_clear_children,
        test_validate_structure,
        test_contains_and_find,
        test_get_all_children,
        test_iteration,
        test_structure_summary,
        test_to_dict,
        test_builder_basic,
        test_builder_no_auto_seal,
        test_builder_incomplete_fails,
        test_builder_wrong_type_fails,
        test_repr,
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
        print("✓ 第4阶段验证通过！")
        return True
    else:
        print("✗ 第4阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
