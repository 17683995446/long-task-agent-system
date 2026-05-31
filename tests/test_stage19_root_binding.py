"""
阶段19测试：根模块双子结构绑定测试
Test Stage 19: Root Module Twin Structure Binding Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level1.root_twin_binding import RootModule, RootModuleBuilder, TwinStructureBinder
from modules.level1.control_module import Level1ControlModule
from modules.level1.execute_module import Level1ExecuteModule
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestRootModule(unittest.TestCase):
    """测试根模块"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.root_module = RootModule()

    def test_module_creation(self):
        """测试模块创建"""
        self.assertIsNotNone(self.root_module.module_id)
        self.assertEqual(self.root_module.module_level, ModuleLevel.ROOT)
        self.assertEqual(self.root_module.module_name, "RootModule")

    def test_init_success(self):
        """测试初始化成功"""
        request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        context = InitContext()

        result = self.root_module._do_init(request, context)

        self.assertTrue(result.success)
        self.assertEqual(result.module_id, self.root_module.module_id)

    def test_run_without_children(self):
        """测试无子模块时执行失败"""
        # 先初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module._do_init(init_request, InitContext())

        # 执行（应该失败，因为没有子模块）
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("task_001")),
        )
        context = ExecutionContext()

        result = self.root_module._do_run(exec_request, context)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "ROOT_MISSING_CHILDREN")

    def test_run_with_children(self):
        """测试有子模块时执行成功"""
        # 创建一级子模块
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        # 绑定到根模块
        self.root_module.set_control_child(level1_control)
        self.root_module.set_execute_child(level1_execute)

        # 初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module._do_init(init_request, InitContext())

        # 执行
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("task_001")),
        )
        context = ExecutionContext()

        result = self.root_module._do_run(exec_request, context)

        self.assertTrue(result.success)
        self.assertIn("control_result", result.data)
        self.assertIn("execute_result", result.data)

    def test_check_passed(self):
        """测试校验通过"""
        # 创建一级子模块
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        self.root_module.set_control_child(level1_control)
        self.root_module.set_execute_child(level1_execute)

        # 初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module._do_init(init_request, InitContext())

        result = self.root_module._do_check(
            ValidationRequest(check_type="root_validation"),
            ValidationContext()
        )

        self.assertTrue(result.passed)

    def test_snapshot_creation(self):
        """测试快照创建"""
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module._do_init(init_request, InitContext())

        # 使用公共API create_snapshot 而不是 _do_snapshot
        snapshot = self.root_module.create_snapshot(
            SnapshotRequest(),
            SnapshotContext()
        )

        self.assertEqual(snapshot.module_id, self.root_module.module_id)
        self.assertIn("system_config", snapshot.state_data)

    def test_get_system_config(self):
        """测试获取系统配置"""
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module._do_init(init_request, InitContext())

        config = self.root_module.get_system_config()
        self.assertIn("system_name", config)
        self.assertIn("version", config)


class TestRootModuleBuilder(unittest.TestCase):
    """测试根模块构建器"""

    def test_build_with_children(self):
        """测试构建带子模块的根模块"""
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        root = (RootModuleBuilder()
            .set_level1_control(level1_control)
            .set_level1_execute(level1_execute)
            .build())

        self.assertIsNotNone(root)
        self.assertEqual(root.get_control_child(), level1_control)
        self.assertEqual(root.get_execute_child(), level1_execute)

    def test_build_without_control_raises(self):
        """测试缺少管控模块时抛出异常"""
        level1_execute = Level1ExecuteModule()

        with self.assertRaises(ValueError) as context:
            (RootModuleBuilder()
                .set_level1_execute(level1_execute)
                .build())

        self.assertIn("缺少一级管控模块", str(context.exception))

    def test_build_without_execute_raises(self):
        """测试缺少执行模块时抛出异常"""
        level1_control = Level1ControlModule()

        with self.assertRaises(ValueError) as context:
            (RootModuleBuilder()
                .set_level1_control(level1_control)
                .build())

        self.assertIn("缺少一级执行模块", str(context.exception))

    def test_build_with_custom_root(self):
        """测试使用自定义根模块构建"""
        custom_root = RootModule()
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        root = (RootModuleBuilder()
            .set_root_module(custom_root)
            .set_level1_control(level1_control)
            .set_level1_execute(level1_execute)
            .build())

        self.assertEqual(root, custom_root)


class TestTwinStructureBinder(unittest.TestCase):
    """测试双子结构绑定器"""

    def test_bind_level1_to_root(self):
        """测试绑定一级模块到根模块"""
        root_module = RootModule()
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        TwinStructureBinder.bind_level1_to_root(
            root_module, level1_control, level1_execute
        )

        self.assertEqual(root_module.get_control_child(), level1_control)
        self.assertEqual(root_module.get_execute_child(), level1_execute)

    def test_validate_binding_success(self):
        """测试验证绑定成功"""
        root_module = RootModule()
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        TwinStructureBinder.bind_level1_to_root(
            root_module, level1_control, level1_execute
        )

        result = TwinStructureBinder.validate_binding(root_module)
        self.assertTrue(result.passed)

    def test_validate_binding_failure(self):
        """测试验证绑定失败（只有一个子模块）"""
        root_module = RootModule()
        level1_control = Level1ControlModule()
        # 只绑定一个子模块（违反双子结构）
        root_module.set_control_child(level1_control)

        result = TwinStructureBinder.validate_binding(root_module)
        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
