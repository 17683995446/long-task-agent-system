"""
阶段20测试：一级模块集成测试
Test Stage 20: Level 1 Module Integration Tests

测试内容：
1. 根模块 + 一级管控 + 一级执行的完整集成
2. 模块间的通信和协调
3. 完整的任务执行流程
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level1.root_twin_binding import RootModule, RootModuleBuilder
from modules.level1.control_module import Level1ControlModule
from modules.level1.execute_module import Level1ExecuteModule
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel1Integration(unittest.TestCase):
    """测试一级模块集成"""

    def setUp(self):
        """每个测试前构建完整的模块树"""
        self.level1_control = Level1ControlModule()
        self.level1_execute = Level1ExecuteModule()
        self.root_module = (RootModuleBuilder()
            .set_level1_control(self.level1_control)
            .set_level1_execute(self.level1_execute)
            .build())

    def test_module_tree_structure(self):
        """测试模块树结构"""
        # 验证根模块
        self.assertEqual(self.root_module.module_level, ModuleLevel.ROOT)
        
        # 验证一级子模块
        self.assertEqual(self.root_module.get_control_child(), self.level1_control)
        self.assertEqual(self.root_module.get_execute_child(), self.level1_execute)
        
        # 验证父模块引用
        self.assertEqual(self.level1_control.parent_module_id, self.root_module.module_id)
        self.assertEqual(self.level1_execute.parent_module_id, self.root_module.module_id)

    def test_twin_structure_validation(self):
        """测试双子结构验证"""
        report = self.root_module.validate_twin_structure()
        self.assertTrue(report.overall_passed)

    def test_full_initialization_flow(self):
        """测试完整初始化流程"""
        request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
            task_param=TaskParam(
                max_steps=5000,
                timeout_seconds=1800,
            ),
        )
        context = InitContext()

        # 初始化根模块
        result = self.root_module.module_init(request, context)
        self.assertTrue(result.success)

    def test_full_execution_flow(self):
        """测试完整执行流程"""
        # 1. 初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
            task_param=TaskParam(max_steps=100),
        )
        self.root_module.module_init(init_request, InitContext())

        # 2. 执行
        task_id = TaskID("integration_task_001")
        exec_request = ExecutionRequest(
            module_input=ModuleInput(
                task_id=task_id,
                data={"test_data": "integration_test"}
            ),
        )
        context = ExecutionContext()

        result = self.root_module.module_run(exec_request, context)

        # 3. 验证结果
        self.assertTrue(result.success)
        self.assertEqual(result.task_id, task_id)
        self.assertIn("control_result", result.data)
        self.assertIn("execute_result", result.data)

    def test_full_validation_flow(self):
        """测试完整校验流程"""
        # 1. 初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module.module_init(init_request, InitContext())

        # 2. 执行
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("validation_task")),
        )
        self.root_module.module_run(exec_request, ExecutionContext())

        # 3. 校验
        validation_request = ValidationRequest(check_type="full_validation")
        validation_context = ValidationContext()

        # 校验根模块
        root_result = self.root_module.module_check(validation_request, validation_context)
        self.assertTrue(root_result.passed)

        # 校验一级管控模块
        control_result = self.level1_control.module_check(validation_request, validation_context)
        self.assertTrue(control_result.passed)

        # 校验一级执行模块
        execute_result = self.level1_execute.module_check(validation_request, validation_context)
        self.assertTrue(execute_result.passed)

    def test_full_snapshot_flow(self):
        """测试完整快照流程"""
        # 1. 初始化并执行
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module.module_init(init_request, InitContext())

        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("snapshot_task")),
        )
        self.root_module.module_run(exec_request, ExecutionContext())

        # 2. 创建快照
        snapshot_request = SnapshotRequest()
        snapshot_context = SnapshotContext()

        root_snapshot = self.root_module.create_snapshot(snapshot_request, snapshot_context)
        control_snapshot = self.level1_control.create_snapshot(snapshot_request, snapshot_context)
        execute_snapshot = self.level1_execute.create_snapshot(snapshot_request, snapshot_context)

        # 3. 验证快照
        self.assertEqual(root_snapshot.module_id, self.root_module.module_id)
        self.assertEqual(control_snapshot.module_id, self.level1_control.module_id)
        self.assertEqual(execute_snapshot.module_id, self.level1_execute.module_id)

    def test_multiple_task_execution(self):
        """测试多任务执行"""
        # 初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module.module_init(init_request, InitContext())

        # 执行多个任务
        task_count = 5
        for i in range(task_count):
            task_id = TaskID(f"multi_task_{i}")
            exec_request = ExecutionRequest(
                module_input=ModuleInput(task_id=task_id),
            )
            result = self.root_module.module_run(exec_request, ExecutionContext())
            self.assertTrue(result.success)

        # 验证所有任务都记录在管控模块中
        all_tasks = self.level1_control.get_all_tasks()
        self.assertEqual(len(all_tasks), task_count)

    def test_execution_metrics(self):
        """测试执行指标"""
        # 初始化
        init_request = InitRequest(
            module_id=self.root_module.module_id,
            module_param=ModuleParam(module_id=self.root_module.module_id),
        )
        self.root_module.module_init(init_request, InitContext())

        # 执行任务
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("metrics_task")),
        )
        result = self.root_module.module_run(exec_request, ExecutionContext())

        self.assertTrue(result.success)
        self.assertGreaterEqual(result.execution_time_ms, 0)

    def test_error_handling(self):
        """测试错误处理"""
        # 创建一个未初始化的根模块
        uninitialized_root = RootModule()

        # 尝试执行（应该失败）
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("error_task")),
        )

        # 未初始化时执行应该返回失败
        result = uninitialized_root.module_run(exec_request, ExecutionContext())
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "RUN_NOT_INITIALIZED")

    def test_module_hierarchy(self):
        """测试模块层级关系"""
        # 验证层级
        self.assertEqual(self.root_module.module_level, ModuleLevel.ROOT)
        self.assertEqual(self.level1_control.module_level, ModuleLevel.LEVEL1)
        self.assertEqual(self.level1_execute.module_level, ModuleLevel.LEVEL1)

        # 验证父子关系
        self.assertIsNone(self.root_module.parent_module_id)
        self.assertEqual(self.level1_control.parent_module_id, self.root_module.module_id)
        self.assertEqual(self.level1_execute.parent_module_id, self.root_module.module_id)

    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 1. 构建模块树
        builder = RootModuleBuilder()
        root = (builder
            .set_level1_control(Level1ControlModule())
            .set_level1_execute(Level1ExecuteModule())
            .build())

        # 2. 初始化
        init_request = InitRequest(
            module_id=root.module_id,
            module_param=ModuleParam(module_id=root.module_id),
            task_param=TaskParam(
                max_steps=1000,
                timeout_seconds=600,
            ),
        )
        init_result = root.module_init(init_request, InitContext())
        self.assertTrue(init_result.success)

        # 3. 校验
        validation_result = root.module_check(
            ValidationRequest(check_type="e2e_validation"),
            ValidationContext()
        )
        self.assertTrue(validation_result.passed)

        # 4. 执行
        task_id = TaskID("e2e_workflow_task")
        exec_request = ExecutionRequest(
            module_input=ModuleInput(
                task_id=task_id,
                data={"workflow": "end_to_end"}
            ),
        )
        exec_result = root.module_run(exec_request, ExecutionContext())
        self.assertTrue(exec_result.success)

        # 5. 快照
        snapshot = root.create_snapshot(SnapshotRequest(), SnapshotContext())
        self.assertIsNotNone(snapshot)

        # 6. 验证任务状态
        control_module = root.get_control_child()
        task_status = control_module.get_task_status(task_id)
        self.assertIsNotNone(task_status)
        self.assertEqual(task_status["status"], "completed")


class TestLevel1ModuleCommunication(unittest.TestCase):
    """测试一级模块间通信"""

    def test_control_execute_coordination(self):
        """测试管控与执行模块协调"""
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        root = (RootModuleBuilder()
            .set_level1_control(level1_control)
            .set_level1_execute(level1_execute)
            .build())

        # 初始化
        init_request = InitRequest(
            module_id=root.module_id,
            module_param=ModuleParam(module_id=root.module_id),
        )
        root.module_init(init_request, InitContext())

        # 执行
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("coordination_task")),
        )
        result = root.module_run(exec_request, ExecutionContext())

        self.assertTrue(result.success)
        # 验证两个子模块都参与了执行
        self.assertIn("control_result", result.data)
        self.assertIn("execute_result", result.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
