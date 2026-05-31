"""
第5阶段验证测试
验证模块注册中心的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from core.module_registry import (
    RegistryError,
    ModuleAlreadyRegisteredError,
    ModuleNotRegisteredError,
    DuplicateModuleIDError,
    ModuleRegistryRecord,
    ModuleRegistry,
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


def setup_registry():
    """创建并初始化一个测试用的注册中心"""
    ModuleRegistry.reset()
    return ModuleRegistry.instance()


def test_singleton():
    """测试单例模式"""
    print("测试单例模式...")
    
    ModuleRegistry.reset()
    r1 = ModuleRegistry.instance()
    r2 = ModuleRegistry.instance()
    
    assert r1 is r2
    
    ModuleRegistry.reset()
    r3 = ModuleRegistry.instance()
    assert r1 is not r3  # 重置后应该是新实例
    
    print("✓ 单例模式测试通过")


def test_register_module():
    """测试注册模块"""
    print("测试注册模块...")
    
    registry = setup_registry()
    module = MockControlModule()
    
    registry.register(module)
    
    assert registry.is_registered(module.module_id) == True
    assert registry.total_count == 1
    
    print("✓ 注册模块测试通过")


def test_register_duplicate_fails():
    """测试重复注册失败"""
    print("测试重复注册失败...")
    
    registry = setup_registry()
    module = MockControlModule()
    
    registry.register(module)
    
    try:
        registry.register(module)
        assert False, "应该抛出ModuleAlreadyRegisteredError"
    except ModuleAlreadyRegisteredError:
        pass
    
    print("✓ 重复注册失败测试通过")


def test_unregister_module():
    """测试注销模块"""
    print("测试注销模块...")
    
    registry = setup_registry()
    module = MockControlModule()
    
    registry.register(module)
    assert registry.total_count == 1
    
    registry.unregister(module.module_id)
    assert registry.total_count == 0
    assert registry.is_registered(module.module_id) == False
    
    print("✓ 注销模块测试通过")


def test_unregister_not_registered_fails():
    """测试注销未注册模块失败"""
    print("测试注销未注册模块失败...")
    
    registry = setup_registry()
    
    try:
        registry.unregister(ModuleID())
        assert False, "应该抛出ModuleNotRegisteredError"
    except ModuleNotRegisteredError:
        pass
    
    print("✓ 注销未注册模块失败测试通过")


def test_get_by_id():
    """测试根据ID获取模块"""
    print("测试根据ID获取模块...")
    
    registry = setup_registry()
    module = MockControlModule()
    
    registry.register(module)
    
    found = registry.get_by_id(module.module_id)
    assert found is module
    
    not_found = registry.get_by_id(ModuleID())
    assert not_found is None
    
    print("✓ 根据ID获取模块测试通过")


def test_get_by_name():
    """测试根据名称获取模块"""
    print("测试根据名称获取模块...")
    
    registry = setup_registry()
    module1 = MockControlModule()
    module2 = MockControlModule()
    
    # 初始化模块以设置名称
    init_request = InitRequest(
        module_id=module1.module_id,
        module_param=ModuleParam(module_id=module1.module_id, module_name="TestModule"),
    )
    module1._state.module_name = "TestModule"
    module2._state.module_name = "TestModule"
    
    registry.register(module1)
    registry.register(module2)
    
    found = registry.get_by_name("TestModule")
    assert len(found) == 2
    
    not_found = registry.get_by_name("NonExistent")
    assert len(not_found) == 0
    
    print("✓ 根据名称获取模块测试通过")


def test_get_by_type():
    """测试根据类型获取模块"""
    print("测试根据类型获取模块...")
    
    registry = setup_registry()
    control = MockControlModule()
    execute = MockExecuteModule()
    
    registry.register(control)
    registry.register(execute)
    
    control_modules = registry.get_by_type(ModuleType.CONTROL)
    assert len(control_modules) == 1
    assert control_modules[0] is control
    
    execute_modules = registry.get_by_type(ModuleType.EXECUTE)
    assert len(execute_modules) == 1
    assert execute_modules[0] is execute
    
    print("✓ 根据类型获取模块测试通过")


def test_get_by_level():
    """测试根据层级获取模块"""
    print("测试根据层级获取模块...")
    
    registry = setup_registry()
    module1 = MockControlModule()
    module1._state.module_level = ModuleLevel.LEVEL1
    module2 = MockControlModule()
    module2._state.module_level = ModuleLevel.LEVEL2
    
    registry.register(module1)
    registry.register(module2)
    
    level1 = registry.get_by_level(ModuleLevel.LEVEL1)
    assert len(level1) == 1
    
    level2 = registry.get_by_level(ModuleLevel.LEVEL2)
    assert len(level2) == 1
    
    print("✓ 根据层级获取模块测试通过")


def test_get_by_tag():
    """测试根据标签获取模块"""
    print("测试根据标签获取模块...")
    
    registry = setup_registry()
    module1 = MockControlModule()
    module2 = MockControlModule()
    
    registry.register(module1, tags=["important"])
    registry.register(module2, tags=["important", "test"])
    
    important = registry.get_by_tag("important")
    assert len(important) == 2
    
    test_only = registry.get_by_tag("test")
    assert len(test_only) == 1
    
    not_found = registry.get_by_tag("nonexistent")
    assert len(not_found) == 0
    
    print("✓ 根据标签获取模块测试通过")


def test_get_by_type_and_level():
    """测试根据类型和层级获取模块"""
    print("测试根据类型和层级获取模块...")
    
    registry = setup_registry()
    control_l1 = MockControlModule()
    control_l1._state.module_level = ModuleLevel.LEVEL1
    control_l2 = MockControlModule()
    control_l2._state.module_level = ModuleLevel.LEVEL2
    execute_l1 = MockExecuteModule()
    execute_l1._state.module_level = ModuleLevel.LEVEL1
    
    registry.register(control_l1)
    registry.register(control_l2)
    registry.register(execute_l1)
    
    result = registry.get_by_type_and_level(ModuleType.CONTROL, ModuleLevel.LEVEL1)
    assert len(result) == 1
    assert result[0] is control_l1
    
    print("✓ 根据类型和层级获取模块测试通过")


def test_parent_child_relationship():
    """测试父子关系"""
    print("测试父子关系...")
    
    registry = setup_registry()
    parent = MockControlModule()
    control_child = MockControlModule()
    execute_child = MockExecuteModule()
    
    # 设置父子关系
    control_child._state.parent_module_id = parent.module_id
    execute_child._state.parent_module_id = parent.module_id
    
    registry.register(parent)
    registry.register(control_child)
    registry.register(execute_child)
    
    # 测试获取父模块
    found_parent = registry.get_parent(control_child.module_id)
    assert found_parent is parent
    
    # 测试获取子模块
    children = registry.get_children(parent.module_id)
    assert len(children) == 2
    
    # 根模块没有父模块
    root_parent = registry.get_parent(parent.module_id)
    assert root_parent is None
    
    print("✓ 父子关系测试通过")


def test_get_ancestors():
    """测试获取祖先模块"""
    print("测试获取祖先模块...")
    
    registry = setup_registry()
    
    # 构建三级树：root -> level1_control -> level2_control
    root = MockControlModule()
    level1 = MockControlModule()
    level2 = MockControlModule()
    
    level1._state.parent_module_id = root.module_id
    level2._state.parent_module_id = level1.module_id
    
    registry.register(root)
    registry.register(level1)
    registry.register(level2)
    
    ancestors = registry.get_ancestors(level2.module_id)
    assert len(ancestors) == 2
    assert ancestors[0] is level1  # 最近的祖先在前
    assert ancestors[1] is root
    
    # 根模块没有祖先
    root_ancestors = registry.get_ancestors(root.module_id)
    assert len(root_ancestors) == 0
    
    print("✓ 获取祖先模块测试通过")


def test_get_descendants():
    """测试获取后代模块"""
    print("测试获取后代模块...")
    
    registry = setup_registry()
    
    root = MockControlModule()
    level1_c = MockControlModule()
    level1_e = MockExecuteModule()
    level2_c = MockControlModule()
    
    level1_c._state.parent_module_id = root.module_id
    level1_e._state.parent_module_id = root.module_id
    level2_c._state.parent_module_id = level1_c.module_id
    
    registry.register(root)
    registry.register(level1_c)
    registry.register(level1_e)
    registry.register(level2_c)
    
    descendants = registry.get_descendants(root.module_id)
    assert len(descendants) == 3
    
    level1_descendants = registry.get_descendants(level1_c.module_id)
    assert len(level1_descendants) == 1
    assert level1_descendants[0] is level2_c
    
    print("✓ 获取后代模块测试通过")


def test_get_root_modules():
    """测试获取根模块"""
    print("测试获取根模块...")
    
    registry = setup_registry()
    
    root = MockControlModule()
    child = MockControlModule()
    child._state.parent_module_id = root.module_id
    
    registry.register(root)
    registry.register(child)
    
    roots = registry.get_root_modules()
    assert len(roots) == 1
    assert roots[0] is root
    
    print("✓ 获取根模块测试通过")


def test_get_depth():
    """测试获取模块深度"""
    print("测试获取模块深度...")
    
    registry = setup_registry()
    
    root = MockControlModule()
    level1 = MockControlModule()
    level2 = MockControlModule()
    
    level1._state.parent_module_id = root.module_id
    level2._state.parent_module_id = level1.module_id
    
    registry.register(root)
    registry.register(level1)
    registry.register(level2)
    
    assert registry.get_depth(root.module_id) == 0
    assert registry.get_depth(level1.module_id) == 1
    assert registry.get_depth(level2.module_id) == 2
    
    print("✓ 获取模块深度测试通过")


def test_tree_structure():
    """测试树形结构输出"""
    print("测试树形结构输出...")
    
    registry = setup_registry()
    
    root = MockControlModule()
    root._state.module_name = "RootModule"
    control_child = MockControlModule()
    control_child._state.module_name = "ControlChild"
    control_child._state.parent_module_id = root.module_id
    execute_child = MockExecuteModule()
    execute_child._state.module_name = "ExecuteChild"
    execute_child._state.parent_module_id = root.module_id
    
    registry.register(root)
    registry.register(control_child)
    registry.register(execute_child)
    
    tree = registry.get_tree_structure(root.module_id)
    assert "RootModule" in tree
    assert "ControlChild" in tree
    assert "ExecuteChild" in tree
    assert "[控]" in tree
    assert "[执]" in tree
    
    print("✓ 树形结构输出测试通过")


def test_statistics():
    """测试注册统计"""
    print("测试注册统计...")
    
    registry = setup_registry()
    
    c1 = MockControlModule()
    c2 = MockControlModule()
    e1 = MockExecuteModule()
    
    registry.register(c1, tags=["important"])
    registry.register(c2)
    registry.register(e1, tags=["test"])
    
    stats = registry.get_statistics()
    assert stats["total_count"] == 3
    assert stats["control_count"] == 2
    assert stats["execute_count"] == 1
    assert stats["root_count"] == 3
    assert "important" in stats["all_tags"]
    assert "test" in stats["all_tags"]
    
    print("✓ 注册统计测试通过")


def test_tag_management():
    """测试标签管理"""
    print("测试标签管理...")
    
    registry = setup_registry()
    module = MockControlModule()
    
    registry.register(module, tags=["initial"])
    
    # 添加标签
    registry.add_tag(module.module_id, "new_tag")
    
    found = registry.get_by_tag("new_tag")
    assert len(found) == 1
    
    # 移除标签
    registry.remove_tag(module.module_id, "new_tag")
    
    found = registry.get_by_tag("new_tag")
    assert len(found) == 0
    
    # 原始标签还在
    found = registry.get_by_tag("initial")
    assert len(found) == 1
    
    print("✓ 标签管理测试通过")


def test_batch_register():
    """测试批量注册"""
    print("测试批量注册...")
    
    registry = setup_registry()
    
    modules = [MockControlModule() for _ in range(5)]
    registered_ids = registry.register_batch(modules, tags=["batch"])
    
    assert len(registered_ids) == 5
    assert registry.total_count == 5
    
    batch_modules = registry.get_by_tag("batch")
    assert len(batch_modules) == 5
    
    print("✓ 批量注册测试通过")


def test_unregister_all():
    """测试注销所有模块"""
    print("测试注销所有模块...")
    
    registry = setup_registry()
    
    for _ in range(3):
        registry.register(MockControlModule())
    
    assert registry.total_count == 3
    
    count = registry.unregister_all()
    assert count == 3
    assert registry.total_count == 0
    
    print("✓ 注销所有模块测试通过")


def test_get_all_modules():
    """测试获取所有模块"""
    print("测试获取所有模块...")
    
    registry = setup_registry()
    
    m1 = MockControlModule()
    m2 = MockExecuteModule()
    m3 = MockControlModule()
    
    registry.register(m1)
    registry.register(m2)
    registry.register(m3)
    
    all_modules = registry.get_all_modules()
    assert len(all_modules) == 3
    assert all_modules[0] is m1  # 按注册顺序
    assert all_modules[1] is m2
    assert all_modules[2] is m3
    
    print("✓ 获取所有模块测试通过")


def test_validate_registry():
    """测试注册中心验证"""
    print("测试注册中心验证...")
    
    registry = setup_registry()
    
    parent = MockControlModule()
    child = MockControlModule()
    child._state.parent_module_id = parent.module_id
    
    registry.register(parent)
    registry.register(child)
    
    report = registry.validate_registry()
    assert report.overall_passed == True
    
    print("✓ 注册中心验证测试通过")


def test_registry_record():
    """测试注册记录"""
    print("测试注册记录...")
    
    registry = setup_registry()
    module = MockControlModule()
    
    registry.register(module, tags=["tag1", "tag2"])
    
    record = registry.get_record(module.module_id)
    assert record is not None
    assert record.module_id == module.module_id
    assert record.has_tag("tag1") == True
    assert record.has_tag("tag2") == True
    assert record.has_tag("nonexistent") == False
    
    print("✓ 注册记录测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第5阶段验证测试 - 模块注册中心实现")
    print("=" * 60)
    print()
    
    tests = [
        test_singleton,
        test_register_module,
        test_register_duplicate_fails,
        test_unregister_module,
        test_unregister_not_registered_fails,
        test_get_by_id,
        test_get_by_name,
        test_get_by_type,
        test_get_by_level,
        test_get_by_tag,
        test_get_by_type_and_level,
        test_parent_child_relationship,
        test_get_ancestors,
        test_get_descendants,
        test_get_root_modules,
        test_get_depth,
        test_tree_structure,
        test_statistics,
        test_tag_management,
        test_batch_register,
        test_unregister_all,
        test_get_all_modules,
        test_validate_registry,
        test_registry_record,
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
        print("✓ 第5阶段验证通过！")
        return True
    else:
        print("✗ 第5阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
