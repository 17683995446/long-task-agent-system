"""
阶段23测试：二级监控模块测试
Test Stage 23: Level2MonitoringModule Tests
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from modules.level2.monitoring_module import Level2MonitoringModule, Metric, MetricType, Alert, AlertLevel
from core_types.core_types import (
    ModuleID, TaskID, TaskParam, ModuleInput, ModuleParam, ModuleLevel,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
)


class TestLevel2MonitoringModule(unittest.TestCase):
    """测试Level2MonitoringModule"""

    def setUp(self):
        """每个测试前创建模块实例"""
        self.module = Level2MonitoringModule()

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
            ValidationRequest(check_type="monitoring_check"),
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

    def test_register_metric(self):
        """测试注册指标"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 注册指标
        metric = Metric("test_metric", "测试指标", MetricType.GAUGE, "count")
        self.module.register_metric(metric)

        # 验证指标
        retrieved = self.module.get_metric("test_metric")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "测试指标")

    def test_record_metric(self):
        """测试记录指标值"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 注册指标
        metric = Metric("test_metric", "测试指标", MetricType.GAUGE, "count")
        self.module.register_metric(metric)

        # 记录指标值
        self.module.record_metric("test_metric", 42.0)

        # 验证指标值
        retrieved = self.module.get_metric("test_metric")
        self.assertEqual(retrieved.get_latest(), 42.0)

    def test_create_alert(self):
        """测试创建告警"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 创建告警
        alert_id = self.module.create_alert(
            name="测试告警",
            level=AlertLevel.WARNING,
            message="这是一个测试告警",
            metric_id="test_metric"
        )

        # 验证告警
        self.assertIsNotNone(alert_id)

    def test_acknowledge_and_resolve_alert(self):
        """测试确认和解决告警"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 创建告警
        alert_id = self.module.create_alert(
            name="测试告警",
            level=AlertLevel.WARNING,
            message="这是一个测试告警"
        )

        # 确认告警
        result = self.module.acknowledge_alert(alert_id)
        self.assertTrue(result)

        # 解决告警
        result = self.module.resolve_alert(alert_id)
        self.assertTrue(result)

        # 验证告警已解决
        active_alerts = self.module.get_active_alerts()
        self.assertEqual(len(active_alerts), 0)

    def test_get_monitoring_summary(self):
        """测试获取监控摘要"""
        # 初始化
        init_request = InitRequest(
            module_id=self.module.module_id,
            module_param=ModuleParam(module_id=self.module.module_id),
        )
        self.module._do_init(init_request, InitContext())

        # 获取监控摘要
        summary = self.module.get_monitoring_summary()
        self.assertIn("total_metrics", summary)
        self.assertIn("active_alerts", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
