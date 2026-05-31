"""
阶段21测试：二级治理模块测试
Test Stage 21: Level2GovernanceModule Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level2.governance_module import Level2GovernanceModule, Policy, PolicyType
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel2GovernanceModule(unittest.TestCase):
    """测试Level2GovernanceModule"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.module = Level2GovernanceModule()

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
            ValidationRequest(check_type="governance_check"),
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

    def test_add_policy(self):
        """测试添加策略"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 添加策略
        policy = Policy(
            policy_id="test_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            name="测试策略",
            rules={"allowed": True},
            priority=5
        )
        self.module.add_policy(policy)

        # 验证策略
        retrieved = self.module.get_policy("test_policy")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "测试策略")

    def test_remove_policy(self):
        """测试移除策略"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 添加策略
        policy = Policy(
            policy_id="test_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            name="测试策略",
            rules={"allowed": True},
            priority=5
        )
        self.module.add_policy(policy)

        # 移除策略
        result = self.module.remove_policy("test_policy")
        self.assertTrue(result)

        # 验证策略已移除
        retrieved = self.module.get_policy("test_policy")
        self.assertIsNone(retrieved)

    def test_policy_evaluation(self):
        """测试策略评估"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 添加策略
        policy = Policy(
            policy_id="test_policy",
            policy_type=PolicyType.ACCESS_CONTROL,
            name="测试策略",
            rules={"allowed": True},
            priority=5
        )
        self.module.add_policy(policy)

        # 评估策略
        result = policy.evaluate({"allowed": True})
        self.assertTrue(result)

        result = policy.evaluate({"allowed": False})
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
