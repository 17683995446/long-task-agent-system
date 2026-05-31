"""
阶段22测试：二级异常处理模块测试
Test Stage 22: Level2ExceptionModule Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level2.exception_module import Level2ExceptionModule, ExceptionSeverity, ExceptionRecord, RecoveryStrategy
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel2ExceptionModule(unittest.TestCase):
    """测试Level2ExceptionModule"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.module = Level2ExceptionModule()

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
            ValidationRequest(check_type="exception_check"),
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

    def test_register_exception(self):
        """测试注册异常"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 注册异常
        exc_id = self.module.register_exception(
            exception_type="TestError",
            message="测试异常",
            severity=ExceptionSeverity.MEDIUM,
            task_id=TaskID("test_task")
        )

        # 验证异常记录
        exc = self.module.get_exception(exc_id)
        self.assertIsNotNone(exc)
        self.assertEqual(exc.message, "测试异常")

    def test_resolve_exception(self):
        """测试解决异常"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 注册异常
        exc_id = self.module.register_exception(
            exception_type="TestError",
            message="测试异常",
            severity=ExceptionSeverity.MEDIUM,
            task_id=TaskID("test_task")
        )

        # 解决异常
        result = self.module.resolve_exception(exc_id, "已修复")
        self.assertTrue(result)

        # 验证异常已解决
        exc = self.module.get_exception(exc_id)
        self.assertTrue(exc.resolved)
        self.assertEqual(exc.resolution, "已修复")

    def test_get_exception_statistics(self):
        """测试获取异常统计"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 注册多个异常
        self.module.register_exception(
            exception_type="TestError",
            message="测试异常1",
            severity=ExceptionSeverity.LOW,
            task_id=TaskID("task_1")
        )
        self.module.register_exception(
            exception_type="TestError",
            message="测试异常2",
            severity=ExceptionSeverity.HIGH,
            task_id=TaskID("task_2")
        )

        # 获取统计
        stats = self.module.get_exception_statistics()
        self.assertEqual(stats["total_exceptions"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
