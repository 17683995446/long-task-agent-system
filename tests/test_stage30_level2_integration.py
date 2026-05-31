"""
阶段30测试：二级模块集成测试
Test Stage 30: Level 2 Module Integration Tests

测试内容：
1. 二级管控模块集成（治理、异常、监控）
2. 二级执行模块独立测试（迭代、检查点、子任务）
3. 一级与二级模块协调
4. 完整的任务执行流程
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
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel2ControlIntegration(unittest.TestCase):
    """测试二级管控模块集成"""

    def setUp(self):
        """每个测试前构建模块树"""
        self.level1_control = Level1ControlModule()
        self.governance = Level2GovernanceModule()
        self.exception = Level2ExceptionModule()
        self.monitoring = Level2MonitoringModule()

        # 构建二级管控模块结构
        binder = Level2ModuleBinder()
        binder.bind_to_level1_control(
            self.level1_control,
            self.governance,
            self.exception,
            self.monitoring
        )

    def test_governance_initialization(self):
        """测试治理模块初始化"""
        init_request = InitRequest(
            module_id=self.governance.module_id,
            module_param=ModuleParam(module_id=self.governance.module_id),
        )
        result = self.governance._do_init(init_request, InitContext())
        self.assertTrue(result.success)

    def test_exception_initialization(self):
        """测试异常模块初始化"""
        init_request = InitRequest(
            module_id=self.exception.module_id,
            module_param=ModuleParam(module_id=self.exception.module_id),
        )
        result = self.exception._do_init(init_request, InitContext())
        self.assertTrue(result.success)

    def test_monitoring_initialization(self):
        """测试监控模块初始化"""
        init_request = InitRequest(
            module_id=self.monitoring.module_id,
            module_param=ModuleParam(module_id=self.monitoring.module_id),
        )
        result = self.monitoring._do_init(init_request, InitContext())
        self.assertTrue(result.success)

    def test_control_module_execution(self):
        """测试管控模块执行"""
        # 初始化所有模块
        for module in [self.governance, self.exception, self.monitoring]:
            init_request = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module._do_init(init_request, InitContext())

        # 执行治理模块
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("governance_task")),
        )
        result = self.governance._do_run(exec_request, ExecutionContext())
        self.assertTrue(result.success)

    def test_policy_management(self):
        """测试策略管理"""
        from modules.level2.governance_module import Policy, PolicyType

        # 初始化
        init_request = InitRequest(
            module_id=self.governance.module_id,
            module_param=ModuleParam(module_id=self.governance.module_id),
        )
        self.governance._do_init(init_request, InitContext())

        # 添加策略
        policy = Policy(
            policy_id="test_policy",
            policy_type=PolicyType.EXECUTION_RULE,
            name="测试策略",
            rules={"max_retries": 3},
            priority=8
        )
        self.governance.add_policy(policy)

        # 验证策略
        retrieved = self.governance.get_policy("test_policy")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "测试策略")

    def test_exception_handling(self):
        """测试异常处理"""
        from modules.level2.exception_module import ExceptionSeverity

        # 初始化
        init_request = InitRequest(
            module_id=self.exception.module_id,
            module_param=ModuleParam(module_id=self.exception.module_id),
        )
        self.exception._do_init(init_request, InitContext())

        # 注册异常
        exc_id = self.exception.register_exception(
            exception_type="TestError",
            message="测试异常",
            severity=ExceptionSeverity.MEDIUM,
            task_id=TaskID("test_task")
        )

        # 验证异常记录
        exc = self.exception.get_exception(exc_id)
        self.assertIsNotNone(exc)
        self.assertEqual(exc.message, "测试异常")

    def test_monitoring_metrics(self):
        """测试监控指标"""
        from modules.level2.monitoring_module import Metric, MetricType

        # 初始化
        init_request = InitRequest(
            module_id=self.monitoring.module_id,
            module_param=ModuleParam(module_id=self.monitoring.module_id),
        )
        self.monitoring._do_init(init_request, InitContext())

        # 注册指标
        metric = Metric("test_metric", "测试指标", MetricType.GAUGE, "count")
        self.monitoring.register_metric(metric)

        # 记录指标值
        self.monitoring.record_metric("test_metric", 42.0)

        # 验证指标
        retrieved = self.monitoring.get_metric("test_metric")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.get_latest(), 42.0)


class TestLevel2ExecuteIntegration(unittest.TestCase):
    """测试二级执行模块集成（独立测试，不绑定到一级执行模块）"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.iteration = Level2IterationModule()
        self.checkpoint = Level2CheckpointModule()
        self.subtask = Level2SubtaskModule()

    def test_iteration_initialization(self):
        """测试迭代模块初始化"""
        init_request = InitRequest(
            module_id=self.iteration.module_id,
            module_param=ModuleParam(module_id=self.iteration.module_id),
        )
        result = self.iteration._do_init(init_request, InitContext())
        self.assertTrue(result.success)

    def test_checkpoint_initialization(self):
        """测试检查点模块初始化"""
        init_request = InitRequest(
            module_id=self.checkpoint.module_id,
            module_param=ModuleParam(module_id=self.checkpoint.module_id),
        )
        result = self.checkpoint._do_init(init_request, InitContext())
        self.assertTrue(result.success)

    def test_subtask_initialization(self):
        """测试子任务模块初始化"""
        init_request = InitRequest(
            module_id=self.subtask.module_id,
            module_param=ModuleParam(module_id=self.subtask.module_id),
        )
        result = self.subtask._do_init(init_request, InitContext())
        self.assertTrue(result.success)

    def test_execute_module_execution(self):
        """测试执行模块执行"""
        # 初始化所有模块
        for module in [self.iteration, self.checkpoint, self.subtask]:
            init_request = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module._do_init(init_request, InitContext())

        # 执行迭代模块
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("iteration_task")),
        )
        result = self.iteration._do_run(exec_request, ExecutionContext())
        self.assertTrue(result.success)

    def test_execution_count_tracking(self):
        """测试执行次数跟踪"""
        # 初始化
        init_request = InitRequest(
            module_id=self.iteration.module_id,
            module_param=ModuleParam(module_id=self.iteration.module_id),
        )
        self.iteration._do_init(init_request, InitContext())

        # 执行多次
        for i in range(3):
            exec_request = ExecutionRequest(
                module_input=ModuleInput(task_id=TaskID(f"task_{i}")),
            )
            self.iteration._do_run(exec_request, ExecutionContext())

        # 验证执行次数
        self.assertEqual(self.iteration.get_execution_count(), 3)


class TestLevel1Level2Coordination(unittest.TestCase):
    """测试一级与二级模块协调"""

    def setUp(self):
        """构建完整的模块树"""
        self.level1_control = Level1ControlModule()
        self.level1_execute = Level1ExecuteModule()

        # 创建二级模块绑定
        binder = Level2ModuleBinder()
        self.level2_modules = binder.create_full_level2_binding(
            self.level1_control,
            self.level1_execute
        )

    def test_module_tree_structure(self):
        """测试模块树结构"""
        # 验证一级管控模块的子模块（只有治理模块绑定为管控子节点）
        self.assertIsInstance(
            self.level1_control.get_control_child(),
            Level2GovernanceModule
        )
        # 一级管控模块没有执行子节点（因为二级异常模块是管控类型）
        self.assertIsNone(self.level1_control.get_execute_child())

        # 验证一级执行模块（执行模块没有双子结构子模块）
        self.assertIsNone(self.level1_execute.get_control_child())
        self.assertIsNone(self.level1_execute.get_execute_child())

    def test_full_initialization_flow(self):
        """测试完整初始化流程"""
        # 初始化一级管控模块及其子模块
        init_request = InitRequest(
            module_id=self.level1_control.module_id,
            module_param=ModuleParam(module_id=self.level1_control.module_id),
        )
        self.level1_control._do_init(init_request, InitContext())

        # 初始化一级执行模块
        init_request2 = InitRequest(
            module_id=self.level1_execute.module_id,
            module_param=ModuleParam(module_id=self.level1_execute.module_id),
        )
        self.level1_execute._do_init(init_request2, InitContext())

        # 重新初始化二级管控模块（因为绑定过程可能重置了它们的状态）
        for name in ["governance", "exception", "monitoring"]:
            module = self.level2_modules[name]
            init_req = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module._do_init(init_req, InitContext())

        # 验证所有二级管控模块都已初始化（通过检查它们可以执行）
        for name in ["governance", "exception", "monitoring"]:
            module = self.level2_modules[name]
            result = module._do_check(
                ValidationRequest(check_type="init_check"),
                ValidationContext()
            )
            self.assertTrue(result.passed, f"模块 {name} 校验失败")


class TestLevel2EndToEnd(unittest.TestCase):
    """测试二级模块端到端场景"""

    def test_complete_task_execution(self):
        """测试完整的任务执行流程"""
        # 1. 构建模块树
        level1_control = Level1ControlModule()
        level1_execute = Level1ExecuteModule()

        binder = Level2ModuleBinder()
        level2_modules = binder.create_full_level2_binding(
            level1_control,
            level1_execute
        )

        # 2. 初始化所有模块
        for module in [level1_control, level1_execute]:
            init_request = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module._do_init(init_request, InitContext())

        # 重新初始化二级管控模块
        for name in ["governance", "exception", "monitoring"]:
            module = level2_modules[name]
            init_req = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module._do_init(init_req, InitContext())

        # 3. 执行治理策略
        governance = level2_modules["governance"]
        exec_request = ExecutionRequest(
            module_input=ModuleInput(task_id=TaskID("e2e_task")),
        )
        gov_result = governance._do_run(exec_request, ExecutionContext())
        self.assertTrue(gov_result.success)

        # 4. 执行迭代
        iteration = level2_modules["iteration"]
        iter_result = iteration._do_run(exec_request, ExecutionContext())
        self.assertTrue(iter_result.success)

        # 5. 收集监控数据
        monitoring = level2_modules["monitoring"]
        mon_result = monitoring._do_run(exec_request, ExecutionContext())
        self.assertTrue(mon_result.success)

        # 6. 验证结果
        self.assertIn("evaluation_results", gov_result.data)
        self.assertIn("execution_count", iter_result.data)
        self.assertIn("monitoring_report", mon_result.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
