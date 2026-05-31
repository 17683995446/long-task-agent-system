"""
阶段27-29测试：二级模块双子结构绑定测试
Test Stage 27-29: Level 2 Module Twin Structure Binding Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level1.control_module import Level1ControlModule
from modules.level1.execute_module import Level1ExecuteModule
from modules.level2 import (
    Level2GovernanceModule,
    Level2ExceptionModule,
    Level2MonitoringModule,
    Level2IterationModule,
    Level2CheckpointModule,
    Level2SubtaskModule,
    Level2ModuleBinder,
    Level2ModuleFactory,
)
from core_types.core_types import ModuleLevel


class TestLevel2ModuleBinder(unittest.TestCase):
    """测试二级模块绑定器"""

    def setUp(self):
        """每个测试前创建实例"""
        self.binder = Level2ModuleBinder()
        self.level1_control = Level1ControlModule()
        self.level1_execute = Level1ExecuteModule()

    def test_bind_to_level1_control(self):
        """测试绑定二级管控模块到一级管控模块"""
        governance = Level2GovernanceModule()
        exception = Level2ExceptionModule()
        monitoring = Level2MonitoringModule()

        self.binder.bind_to_level1_control(
            self.level1_control,
            governance,
            exception,
            monitoring
        )

        # 验证绑定：只绑定治理模块作为管控子节点
        self.assertEqual(self.level1_control.get_control_child(), governance)
        # 治理模块的子节点是监控模块
        self.assertEqual(governance.get_control_child(), monitoring)

    def test_bind_to_level1_execute(self):
        """测试绑定二级执行模块到一级执行模块（简化绑定）"""
        iteration = Level2IterationModule()
        checkpoint = Level2CheckpointModule()
        subtask = Level2SubtaskModule()

        # 执行绑定（简化版，不实际绑定到双子结构）
        self.binder.bind_to_level1_execute(
            self.level1_execute,
            iteration,
            checkpoint,
            subtask
        )

        # 验证：执行模块不绑定子模块（因为执行模块只能绑定管控子模块）
        self.assertIsNone(self.level1_execute.get_control_child())
        self.assertIsNone(self.level1_execute.get_execute_child())

    def test_create_full_level2_binding(self):
        """测试创建完整的二级模块绑定"""
        modules = self.binder.create_full_level2_binding(
            self.level1_control,
            self.level1_execute
        )

        # 验证返回的模块
        self.assertIn("governance", modules)
        self.assertIn("exception", modules)
        self.assertIn("monitoring", modules)
        self.assertIn("iteration", modules)
        self.assertIn("checkpoint", modules)
        self.assertIn("subtask", modules)

        # 验证模块层级
        for module in modules.values():
            self.assertEqual(module.module_level, ModuleLevel.LEVEL2)

    def test_validate_level2_binding_success(self):
        """测试验证二级模块绑定成功"""
        # 先创建绑定
        self.binder.create_full_level2_binding(
            self.level1_control,
            self.level1_execute
        )

        # 验证
        result = self.binder.validate_level2_binding(
            self.level1_control,
            self.level1_execute
        )

        self.assertTrue(result.passed)

    def test_validate_level2_binding_failure(self):
        """测试验证二级模块绑定失败"""
        # 不创建绑定，直接验证
        result = self.binder.validate_level2_binding(
            self.level1_control,
            self.level1_execute
        )

        self.assertFalse(result.passed)


class TestLevel2ModuleFactory(unittest.TestCase):
    """测试二级模块工厂"""

    def test_create_control_modules(self):
        """测试创建二级管控模块"""
        modules = Level2ModuleFactory.create_control_modules()

        self.assertIn("governance", modules)
        self.assertIn("exception", modules)
        self.assertIn("monitoring", modules)

        # 验证类型
        self.assertIsInstance(modules["governance"], Level2GovernanceModule)
        self.assertIsInstance(modules["exception"], Level2ExceptionModule)
        self.assertIsInstance(modules["monitoring"], Level2MonitoringModule)

    def test_create_execute_modules(self):
        """测试创建二级执行模块"""
        modules = Level2ModuleFactory.create_execute_modules()

        self.assertIn("iteration", modules)
        self.assertIn("checkpoint", modules)
        self.assertIn("subtask", modules)

        # 验证类型
        self.assertIsInstance(modules["iteration"], Level2IterationModule)
        self.assertIsInstance(modules["checkpoint"], Level2CheckpointModule)
        self.assertIsInstance(modules["subtask"], Level2SubtaskModule)

    def test_create_all_modules(self):
        """测试创建所有二级模块"""
        modules = Level2ModuleFactory.create_all_modules()

        self.assertEqual(len(modules), 6)
        self.assertIn("governance", modules)
        self.assertIn("iteration", modules)


class TestLevel2ModuleHierarchy(unittest.TestCase):
    """测试二级模块层级结构"""

    def test_module_hierarchy(self):
        """测试模块层级关系"""
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        binder = Level2ModuleBinder()
        binder.create_full_level2_binding(level1_control, level1_execute)

        # 验证一级管控模块的子模块
        self.assertEqual(level1_control.get_control_child().module_level, ModuleLevel.LEVEL2)

        # 验证一级执行模块没有双子结构子模块
        self.assertIsNone(level1_execute.get_control_child())
        self.assertIsNone(level1_execute.get_execute_child())

    def test_parent_child_relationship(self):
        """测试父子关系"""
        level1_control = Level1ControlModule()
        governance = Level2GovernanceModule()

        governance.set_control_child(Level2MonitoringModule())
        level1_control.set_control_child(governance)

        # 验证父模块引用
        self.assertEqual(governance.parent_module_id, level1_control.module_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
