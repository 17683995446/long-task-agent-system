"""
阶段25测试：二级检查点模块测试
Test Stage 25: Level2CheckpointModule Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level2.checkpoint_module import Level2CheckpointModule
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel2CheckpointModule(unittest.TestCase):
    """测试Level2CheckpointModule"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.module = Level2CheckpointModule()

    def test_module_creation(self):
        """测试模块创建"""
        self.assertIsNotNone(self.module.module_id)
        self.assertEqual(self.module.module_level, ModuleLevel.LEVEL2)

    def test_init_success(self):
        """测试初始化成功"""
        request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        context = InitContext()

        result = self.module._do_init(request, context)

        self.assertTrue(result.success)
        self.assertEqual(result.module_id, self.module.module_id)

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

    def test_check_passed(self):
        """测试校验通过"""
        # 先初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        result = self.module._do_check(
            ValidationRequest(check_type="checkpoint_check"),
            ValidationContext()
        )

        self.assertTrue(result.passed)

    def test_snapshot_creation(self):
        """测试快照创建"""
        # 先初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 创建快照
        snapshot = self.module.create_snapshot(
            SnapshotRequest(),
            SnapshotContext()
        )

        self.assertEqual(snapshot.module_id, self.module.module_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
