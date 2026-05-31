"""
阶段18测试：一级执行模块测试
Test Stage 18: Level 1 Execute Module Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level1.execute_module import Level1ExecuteModule
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel1ExecuteModule(unittest.TestCase):
    """测试一级执行模块"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.module = Level1ExecuteModule()

    def test_module_creation(self):
        """测试模块创建"""
        self.assertIsNotNone(self.module.module_id)
        self.assertIsNotNone(self.module._logger)

    def test_init_success(self):
        """测试初始化成功"""
        request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
            task_param=TaskParam(max_steps=5000),
        )
        context = InitContext()

        result = self.module._do_init(request, context)

        self.assertTrue(result.success)

    def test_run_success(self):
        """测试执行成功"""
        # 先初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 执行
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("task_001")),
        )
        context = ExecutionContext()

        result = self.module._do_run(exec_request, context)

        self.assertTrue(result.success)

    def test_iteration_count(self):
        """测试迭代计数"""
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("task_001")),
        )
        self.module._do_run(exec_request, ExecutionContext())

        self.assertEqual(self.module.get_iteration_count(), 1)

    def test_check_passed(self):
        """测试校验通过"""
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        result = self.module._do_check(
            ValidationRequest(check_type="level1_execute_check"),
            ValidationContext()
        )

        self.assertTrue(result.passed)

    def test_snapshot_creation(self):
        """测试快照创建"""
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 创建快照（使用公共API）
        snapshot = self.module.create_snapshot(
            SnapshotRequest(),
            SnapshotContext()
        )

        self.assertEqual(snapshot.module_id, self.module.module_id)
        self.assertIn("iteration_count", snapshot.state_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
