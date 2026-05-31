"""
阶段66-85测试：系统集成测试
Test Stage 66-85: System Integration Tests

测试内容：
1. 模块树组装
2. 任务执行引擎
3. 系统监控面板
4. 完整系统集成
"""

import unittest
import sys
sys.path.insert(0, '/workspace')

from system.module_tree import ModuleTree, ModuleTreeBuilder, ModuleNode
from system.execution_engine import ExecutionEngine, ExecutionRecord, ExecutionStatus
from system.monitoring_dashboard import MonitoringDashboard, SystemHealth
from core_types.core_types import (
    ModuleID, TaskID, ModuleParam, ModuleInput, ModuleLevel,
)
from interfaces.module_interface import InitRequest, InitContext


class TestModuleTree(unittest.TestCase):
    """测试模块树"""

    def test_build_standard_tree(self):
        """测试构建标准模块树"""
        builder = ModuleTreeBuilder()
        tree = builder.build_standard_tree()

        # 验证模块数量
        self.assertGreaterEqual(tree.get_module_count(), 4)  # 根 + 一级*2 + 二级*2

        # 验证根模块
        root = tree.get_root()
        self.assertIsNotNone(root)
        self.assertEqual(root.level, ModuleLevel.ROOT)

    def test_build_minimal_tree(self):
        """测试构建最小模块树"""
        builder = ModuleTreeBuilder()
        tree = builder.build_minimal_tree()

        # 验证模块数量
        self.assertEqual(tree.get_module_count(), 3)  # 根 + 一级*2

    def test_get_module(self):
        """测试获取模块"""
        builder = ModuleTreeBuilder()
        tree = builder.build_minimal_tree()

        root = tree.get_root()
        module = tree.get_module(root.module.module_id)
        self.assertIsNotNone(module)
        self.assertEqual(module.module_id, root.module.module_id)

    def test_get_modules_by_level(self):
        """测试按层级获取模块"""
        builder = ModuleTreeBuilder()
        tree = builder.build_minimal_tree()

        root_modules = tree.get_modules_by_level(ModuleLevel.ROOT)
        self.assertEqual(len(root_modules), 1)

        level1_modules = tree.get_modules_by_level(ModuleLevel.LEVEL1)
        self.assertEqual(len(level1_modules), 2)

    def test_traverse(self):
        """测试遍历模块树"""
        builder = ModuleTreeBuilder()
        tree = builder.build_minimal_tree()

        # 前序遍历
        modules = list(tree.traverse("pre"))
        self.assertEqual(len(modules), 3)

        # 后序遍历
        modules = list(tree.traverse("post"))
        self.assertEqual(len(modules), 3)

        # 层序遍历
        modules = list(tree.traverse("level"))
        self.assertEqual(len(modules), 3)

    def test_get_tree_depth(self):
        """测试获取树深度"""
        builder = ModuleTreeBuilder()
        tree = builder.build_minimal_tree()

        depth = tree.get_tree_depth()
        self.assertGreaterEqual(depth, 2)


class TestExecutionEngine(unittest.TestCase):
    """测试任务执行引擎"""

    def setUp(self):
        """每个测试前构建引擎"""
        builder = ModuleTreeBuilder()
        self.tree = builder.build_minimal_tree()
        self.engine = ExecutionEngine(self.tree)

        # 初始化模块
        for module in self.tree.get_all_modules():
            init_request = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module.module_init(init_request, InitContext())

    def test_execute_task(self):
        """测试执行任务"""
        task_id = TaskID("test_task")
        module_input = ModuleInput(task_id=task_id, data={"test": "data"})

        record = self.engine.execute_task(task_id, module_input)

        self.assertIsNotNone(record)
        self.assertEqual(record.task_id, task_id)
        self.assertIn(record.status, [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED])

    def test_get_execution_status(self):
        """测试获取执行状态"""
        task_id = TaskID("test_task_status")
        module_input = ModuleInput(task_id=task_id)

        self.engine.execute_task(task_id, module_input)
        status = self.engine.get_execution_status(task_id)

        self.assertIsNotNone(status)

    def test_get_execution_record(self):
        """测试获取执行记录"""
        task_id = TaskID("test_task_record")
        module_input = ModuleInput(task_id=task_id)

        self.engine.execute_task(task_id, module_input)
        record = self.engine.get_execution_record(task_id)

        self.assertIsNotNone(record)
        self.assertEqual(record.task_id, task_id)

    def test_get_execution_history(self):
        """测试获取执行历史"""
        # 执行多个任务
        for i in range(3):
            task_id = TaskID(f"test_task_{i}")
            module_input = ModuleInput(task_id=task_id)
            self.engine.execute_task(task_id, module_input)

        history = self.engine.get_execution_history()
        self.assertGreaterEqual(len(history), 3)

    def test_get_statistics(self):
        """测试获取执行统计"""
        # 执行一些任务
        for i in range(3):
            task_id = TaskID(f"test_task_{i}")
            module_input = ModuleInput(task_id=task_id)
            self.engine.execute_task(task_id, module_input)

        stats = self.engine.get_statistics()
        self.assertIn("total_executions", stats)
        self.assertIn("completed", stats)
        self.assertIn("failed", stats)
        self.assertIn("success_rate", stats)


class TestMonitoringDashboard(unittest.TestCase):
    """测试系统监控面板"""

    def setUp(self):
        """每个测试前构建面板"""
        builder = ModuleTreeBuilder()
        self.tree = builder.build_minimal_tree()
        self.engine = ExecutionEngine(self.tree)
        self.dashboard = MonitoringDashboard(self.tree, self.engine)

    def test_collect_system_metrics(self):
        """测试收集系统指标"""
        metrics = self.dashboard.collect_system_metrics()

        self.assertIn("timestamp", metrics)
        self.assertIn("module_count", metrics)
        self.assertIn("tree_depth", metrics)
        self.assertIn("execution_stats", metrics)

    def test_get_module_status(self):
        """测试获取模块状态"""
        status = self.dashboard.get_module_status()

        self.assertIn("modules", status)
        self.assertGreaterEqual(len(status["modules"]), 3)

    def test_get_execution_overview(self):
        """测试获取执行概览"""
        overview = self.dashboard.get_execution_overview()

        self.assertIn("time_range_minutes", overview)
        self.assertIn("total_executions", overview)
        self.assertIn("success_rate", overview)

    def test_check_health(self):
        """测试健康检查"""
        health = self.dashboard.check_health()

        self.assertIsNotNone(health)
        self.assertIn(health.status, ["healthy", "warning", "critical"])
        self.assertGreaterEqual(health.score, 0)
        self.assertLessEqual(health.score, 100)

    def test_create_and_get_alerts(self):
        """测试创建和获取告警"""
        # 创建告警
        alert_id = self.dashboard.create_alert(
            level="warning",
            message="测试告警",
            source="test"
        )

        self.assertIsNotNone(alert_id)

        # 获取告警
        alerts = self.dashboard.get_alerts()
        self.assertGreaterEqual(len(alerts), 1)

    def test_acknowledge_alert(self):
        """测试确认告警"""
        # 创建告警
        alert_id = self.dashboard.create_alert(
            level="warning",
            message="测试告警",
            source="test"
        )

        # 确认告警
        result = self.dashboard.acknowledge_alert(alert_id)
        self.assertTrue(result)

    def test_get_dashboard_summary(self):
        """测试获取面板摘要"""
        summary = self.dashboard.get_dashboard_summary()

        self.assertIn("timestamp", summary)
        self.assertIn("system_metrics", summary)
        self.assertIn("health", summary)
        self.assertIn("execution_overview", summary)

    def test_export_report(self):
        """测试导出报告"""
        report = self.dashboard.export_report()

        self.assertIn("generated_at", report)
        self.assertIn("summary", report)
        self.assertIn("module_status", report)


class TestSystemIntegration(unittest.TestCase):
    """测试完整系统集成"""

    def test_full_system_workflow(self):
        """测试完整系统工作流"""
        # 1. 构建模块树
        builder = ModuleTreeBuilder()
        tree = builder.build_standard_tree()

        # 2. 初始化所有模块
        for module in tree.get_all_modules():
            init_request = InitRequest(
                module_id=module.module_id,
                module_param=ModuleParam(module_id=module.module_id),
            )
            module.module_init(init_request, InitContext())

        # 3. 创建执行引擎
        engine = ExecutionEngine(tree)

        # 4. 创建监控面板
        dashboard = MonitoringDashboard(tree, engine)

        # 5. 执行任务
        task_id = TaskID("integration_task")
        module_input = ModuleInput(task_id=task_id, data={"test": "integration"})
        record = engine.execute_task(task_id, module_input)

        # 6. 验证执行结果
        self.assertIsNotNone(record)

        # 7. 检查系统健康
        health = dashboard.check_health()
        self.assertIsNotNone(health)

        # 8. 获取系统指标
        metrics = dashboard.collect_system_metrics()
        self.assertGreater(metrics["module_count"], 0)

    def test_system_statistics(self):
        """测试系统统计"""
        builder = ModuleTreeBuilder()
        tree = builder.build_standard_tree()
        engine = ExecutionEngine(tree)
        dashboard = MonitoringDashboard(tree, engine)

        # 执行多个任务
        for i in range(5):
            task_id = TaskID(f"stats_task_{i}")
            module_input = ModuleInput(task_id=task_id)
            engine.execute_task(task_id, module_input)

        # 获取统计
        stats = engine.get_statistics()
        self.assertGreaterEqual(stats["total_executions"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
