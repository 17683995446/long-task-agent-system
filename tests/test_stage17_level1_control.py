"""
阶段17测试：一级管控模块测试
Test Stage 17: Level 1 Control Module Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level1.control_module import Level1ControlModule
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel1ControlModule(unittest.TestCase):
    """测试一级管控模块"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.module = Level1ControlModule()

    def test_module_creation(self):
        """测试模块创建"""
        self.assertIsNotNone(self.module.module_id)
        self.assertIsNotNone(self.module._logger)

    def test_init_success(self):
        """测试初始化成功"""
        request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
            task_param=TaskParam(
                max_steps=5000,
                timeout_seconds=1800,
            ),
        )
        context = InitContext()

        result = self.module._do_init(request, context)

        self.assertTrue(result.success)
        self.assertEqual(result.module_id, self.module.module_id)

    def test_init_default_config(self):
        """测试默认配置初始化"""
        request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        context = InitContext()

        self.module._do_init(request, context)

        config = self.module.get_global_config()
        self.assertEqual(config["max_iterations"], 10000)
        self.assertEqual(config["timeout_seconds"], 3600)

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

    def test_task_registration(self):
        """测试任务注册"""
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        task_id = TaskID("task_001")
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=task_id),
        )
        context = ExecutionContext()

        self.module._do_run(exec_request, context)

        # 验证任务已注册
        task_status = self.module.get_task_status(task_id)
        self.assertIsNotNone(task_status)
        self.assertEqual(task_status["status"], "completed")

    def test_check_passed(self):
        """测试校验通过"""
        # 先初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        result = self.module._do_check(
            ValidationRequest(check_type="level1_control_check"),
            ValidationContext()
        )

        self.assertTrue(result.passed)

    def test_snapshot_creation(self):
        """测试快照创建"""
        # 先初始化并执行
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        task_id = TaskID("task_001")
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=task_id),
        )
        self.module._do_run(exec_request, ExecutionContext())

        # 创建快照（使用公共API）
        snapshot = self.module.create_snapshot(
            SnapshotRequest(),
            SnapshotContext()
        )

        self.assertEqual(snapshot.module_id, self.module.module_id)
        self.assertIn("global_config", snapshot.state_data)
        self.assertIn("task_count", snapshot.state_data)

    def test_global_config_update(self):
        """测试全局配置更新"""
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        self.module.update_global_config({"custom_key": "custom_value"})

        config = self.module.get_global_config()
        self.assertEqual(config["custom_key"], "custom_value")

    def test_get_all_tasks(self):
        """测试获取所有任务"""
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 执行多个任务
        for i in range(3):
            task_id = TaskID(f"task_{i}")
            exec_request = ExecutionRequest(
                module_input=ModuleInput(task_id=task_id),
            )
            self.module._do_run(exec_request, ExecutionContext())

        all_tasks = self.module.get_all_tasks()
        self.assertEqual(len(all_tasks), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
