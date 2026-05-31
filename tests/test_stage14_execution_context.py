"""
阶段14测试：执行上下文测试
Test Stage 14: Execution Context Tests

测试范围：
1. ContextState状态枚举
2. ContextEntry上下文条目
3. StepInfo步骤信息
4. ExecutionContext核心功能
5. 步骤管理
6. 数据管理
7. 父子上下文
8. 上下文栈
9. 上下文管理器
"""

import unittest

import sys
sys.path.insert(0, '/workspace')

from core.execution_context import (
    ContextState,
    ContextEntry,
    StepInfo,
    ExecutionContext,
)
from core_types.core_types import ModuleID, TaskID


# =============================================================================
# 1. ContextEntry测试
# =============================================================================

class TestContextEntry(unittest.TestCase):
    """测试上下文条目"""

    def test_entry_creation(self):
        """测试条目创建"""
        entry = ContextEntry(key="name", value="test", source="module_001")

        self.assertEqual(entry.key, "name")
        self.assertEqual(entry.value, "test")
        self.assertEqual(entry.source, "module_001")

    def test_entry_update(self):
        """测试条目更新"""
        entry = ContextEntry(key="count", value=0)
        entry.update(5)

        self.assertEqual(entry.value, 5)


# =============================================================================
# 2. StepInfo测试
# =============================================================================

class TestStepInfo(unittest.TestCase):
    """测试步骤信息"""

    def test_step_creation(self):
        """测试步骤创建"""
        step = StepInfo(step_number=1, step_name="init")

        self.assertEqual(step.step_number, 1)
        self.assertEqual(step.status, "pending")
        self.assertIsNone(step.duration_seconds)

    def test_step_duration(self):
        """测试步骤耗时"""
        from datetime import datetime, timedelta
        step = StepInfo(
            step_number=1,
            started_at=datetime.now() - timedelta(seconds=2),
            completed_at=datetime.now(),
        )

        self.assertIsNotNone(step.duration_seconds)
        self.assertGreaterEqual(step.duration_seconds, 1.9)

    def test_step_to_dict(self):
        """测试步骤转字典"""
        step = StepInfo(step_number=1, step_name="init", status="completed")
        data = step.to_dict()

        self.assertEqual(data["step_number"], 1)
        self.assertEqual(data["step_name"], "init")
        self.assertEqual(data["status"], "completed")


# =============================================================================
# 3. ExecutionContext基础测试
# =============================================================================

class TestExecutionContextBasic(unittest.TestCase):
    """测试执行上下文基础功能"""

    def setUp(self):
        self.ctx = ExecutionContext(
            context_id="test_root",
            task_id=TaskID("task_001"),
            total_steps=5,
        )

    def test_creation(self):
        """测试创建"""
        self.assertEqual(self.ctx.context_id, "test_root")
        self.assertEqual(self.ctx.current_step, 0)
        self.assertEqual(self.ctx.total_steps, 5)
        self.assertEqual(self.ctx.state, ContextState.CREATED)

    def test_is_root(self):
        """测试根上下文"""
        self.assertTrue(self.ctx.is_root)
        self.assertEqual(self.ctx.depth, 0)

    def test_progress(self):
        """测试进度计算"""
        self.assertEqual(self.ctx.progress, 0.0)

        self.ctx.set_total_steps(10)
        self.ctx._current_step = 5
        self.assertAlmostEqual(self.ctx.progress, 0.5)

    def test_progress_zero_total(self):
        """测试零总步骤的进度"""
        ctx = ExecutionContext(context_id="no_steps", total_steps=0)
        self.assertEqual(ctx.progress, 0.0)


# =============================================================================
# 4. 状态管理测试
# =============================================================================

class TestStateManagement(unittest.TestCase):
    """测试状态管理"""

    def setUp(self):
        self.ctx = ExecutionContext(context_id="state_test")

    def test_activate(self):
        """测试激活"""
        self.ctx.activate()
        self.assertTrue(self.ctx.is_active)
        self.assertEqual(self.ctx.state, ContextState.ACTIVE)

    def test_pause_resume(self):
        """测试暂停恢复"""
        self.ctx.activate()
        self.ctx.pause()
        self.assertEqual(self.ctx.state, ContextState.PAUSED)

        self.ctx.resume()
        self.assertEqual(self.ctx.state, ContextState.ACTIVE)

    def test_complete(self):
        """测试完成"""
        self.ctx.activate()
        self.ctx.complete()
        self.assertTrue(self.ctx.is_completed)
        self.assertEqual(self.ctx.state, ContextState.COMPLETED)

    def test_fail(self):
        """测试失败"""
        self.ctx.activate()
        self.ctx.fail("发生错误")
        self.assertTrue(self.ctx.is_completed)
        self.assertEqual(self.ctx.state, ContextState.FAILED)
        self.assertEqual(self.ctx.error, "发生错误")

    def test_cancel(self):
        """测试取消"""
        self.ctx.activate()
        self.ctx.cancel()
        self.assertTrue(self.ctx.is_completed)
        self.assertEqual(self.ctx.state, ContextState.CANCELLED)


# =============================================================================
# 5. 步骤管理测试
# =============================================================================

class TestStepManagement(unittest.TestCase):
    """测试步骤管理"""

    def setUp(self):
        self.ctx = ExecutionContext(context_id="step_test", total_steps=5)

    def test_advance_step(self):
        """测试推进步骤"""
        step = self.ctx.advance_step("初始化")

        self.assertEqual(self.ctx.current_step, 1)
        self.assertEqual(step.step_name, "初始化")
        self.assertEqual(step.status, "running")

    def test_advance_multiple_steps(self):
        """测试推进多个步骤"""
        self.ctx.advance_step("步骤1")
        self.ctx.complete_current_step()
        self.ctx.advance_step("步骤2")
        self.ctx.complete_current_step()

        self.assertEqual(self.ctx.current_step, 2)

    def test_complete_current_step(self):
        """测试完成当前步骤"""
        self.ctx.advance_step("步骤1")
        step = self.ctx.complete_current_step(result="ok")

        self.assertEqual(step.status, "completed")
        self.assertEqual(step.result, "ok")
        self.assertIsNotNone(step.completed_at)

    def test_complete_step_with_error(self):
        """测试完成步骤（带错误）"""
        self.ctx.advance_step("步骤1")
        step = self.ctx.complete_current_step(error="超时")

        self.assertEqual(step.status, "failed")
        self.assertEqual(step.error, "超时")

    def test_skip_step(self):
        """测试跳过步骤"""
        step = self.ctx.skip_step("条件不满足")

        self.assertEqual(self.ctx.current_step, 1)
        self.assertEqual(step.status, "skipped")

    def test_get_step(self):
        """测试获取步骤"""
        self.ctx.advance_step("步骤1")
        self.ctx.complete_current_step()
        self.ctx.advance_step("步骤2")

        step1 = self.ctx.get_step(1)
        step2 = self.ctx.get_step(2)

        self.assertEqual(step1.step_name, "步骤1")
        self.assertEqual(step1.status, "completed")
        self.assertEqual(step2.status, "running")

    def test_get_all_steps(self):
        """测试获取所有步骤"""
        self.ctx.advance_step("步骤1")
        self.ctx.complete_current_step()
        self.ctx.advance_step("步骤2")

        steps = self.ctx.get_all_steps()
        self.assertEqual(len(steps), 2)

    def test_get_completed_steps(self):
        """测试获取已完成步骤"""
        self.ctx.advance_step("步骤1")
        self.ctx.complete_current_step()
        self.ctx.advance_step("步骤2")

        completed = self.ctx.get_completed_steps()
        self.assertEqual(len(completed), 1)

    def test_get_failed_steps(self):
        """测试获取失败步骤"""
        self.ctx.advance_step("步骤1")
        self.ctx.complete_current_step(error="失败")
        self.ctx.advance_step("步骤2")
        self.ctx.complete_current_step()

        failed = self.ctx.get_failed_steps()
        self.assertEqual(len(failed), 1)

    def test_auto_complete_previous_on_advance(self):
        """测试推进时自动完成上一步"""
        self.ctx.advance_step("步骤1")
        self.ctx.advance_step("步骤2")

        step1 = self.ctx.get_step(1)
        self.assertEqual(step1.status, "completed")

    def test_complete_without_step_raises(self):
        """测试无步骤时完成抛出异常"""
        with self.assertRaises(RuntimeError):
            self.ctx.complete_current_step()


# =============================================================================
# 6. 数据管理测试
# =============================================================================

class TestDataManagement(unittest.TestCase):
    """测试数据管理"""

    def setUp(self):
        self.ctx = ExecutionContext(context_id="data_test")

    def test_set_and_get(self):
        """测试存取数据"""
        self.ctx.set("key1", "value1")
        self.assertEqual(self.ctx.get("key1"), "value1")

    def test_get_default(self):
        """测试默认值"""
        self.assertEqual(self.ctx.get("nonexistent", "default"), "default")

    def test_update_existing(self):
        """测试更新已存在的键"""
        self.ctx.set("count", 1)
        self.ctx.set("count", 2)
        self.assertEqual(self.ctx.get("count"), 2)

    def test_has(self):
        """测试存在检查"""
        self.assertFalse(self.ctx.has("key1"))
        self.ctx.set("key1", "value1")
        self.assertTrue(self.ctx.has("key1"))

    def test_delete(self):
        """测试删除"""
        self.ctx.set("key1", "value1")
        self.assertTrue(self.ctx.delete("key1"))
        self.assertFalse(self.ctx.has("key1"))

    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        self.assertFalse(self.ctx.delete("nonexistent"))

    def test_keys(self):
        """测试获取键列表"""
        self.ctx.set("key1", "v1")
        self.ctx.set("key2", "v2")

        keys = self.ctx.keys()
        self.assertIn("key1", keys)
        self.assertIn("key2", keys)

    def test_items(self):
        """测试获取键值对"""
        self.ctx.set("key1", "v1")
        self.ctx.set("key2", "v2")

        items = self.ctx.items()
        self.assertEqual(items["key1"], "v1")
        self.assertEqual(items["key2"], "v2")

    def test_get_with_source(self):
        """测试获取带来源"""
        self.ctx.set("key1", "v1", source="module_001")
        value, source = self.ctx.get_with_source("key1")

        self.assertEqual(value, "v1")
        self.assertEqual(source, "module_001")


# =============================================================================
# 7. 父子上下文测试
# =============================================================================

class TestParentChildContext(unittest.TestCase):
    """测试父子上下文"""

    def setUp(self):
        self.root = ExecutionContext(
            context_id="root",
            task_id=TaskID("task_001"),
            total_steps=10,
        )
        self.child1 = self.root.create_child(
            context_id="child_001",
            module_id=ModuleID("module_001"),
            total_steps=3,
        )
        self.child2 = self.root.create_child(
            context_id="child_002",
            module_id=ModuleID("module_002"),
            total_steps=2,
        )

    def test_parent_reference(self):
        """测试父引用"""
        self.assertEqual(self.child1.parent, self.root)

    def test_child_depth(self):
        """测试子上下文深度"""
        self.assertEqual(self.root.depth, 0)
        self.assertEqual(self.child1.depth, 1)

    def test_root_property(self):
        """测试根属性"""
        self.assertEqual(self.child1.root, self.root)
        self.assertEqual(self.root.root, self.root)

    def test_children_list(self):
        """测试子列表"""
        children = self.root.children
        self.assertEqual(len(children), 2)

    def test_get_child(self):
        """测试获取子上下文"""
        child = self.root.get_child("child_001")
        self.assertEqual(child, self.child1)

    def test_remove_child(self):
        """测试移除子上下文"""
        self.root.remove_child("child_001")
        self.assertEqual(len(self.root.children), 1)

    def test_nested_child(self):
        """测试嵌套子上下文"""
        grandchild = self.child1.create_child(
            context_id="grandchild_001",
            total_steps=1,
        )

        self.assertEqual(grandchild.depth, 2)
        self.assertEqual(grandchild.root, self.root)

    def test_get_all_descendants(self):
        """测试获取所有后代"""
        self.child1.create_child(context_id="gc_001")
        self.child1.create_child(context_id="gc_002")

        descendants = self.root.get_all_descendants()
        self.assertEqual(len(descendants), 4)  # 2 children + 2 grandchildren

    def test_hierarchy_data_lookup(self):
        """测试层级数据查找"""
        self.root.set("global_setting", "on")
        self.child1.set("local_data", "child_value")

        # 子上下文可访问自己的数据
        self.assertEqual(self.child1.get("local_data"), "child_value")

        # 子上下文可通过层级查找访问父级数据
        self.assertEqual(
            self.child1.get_from_hierarchy("global_setting"), "on"
        )

        # 根上下文无法访问子级数据
        self.assertIsNone(
            self.root.get_from_hierarchy("local_data")
        )

    def test_independent_steps(self):
        """测试独立步骤追踪"""
        self.root.advance_step("root_step1")
        self.child1.advance_step("child_step1")

        self.assertEqual(self.root.current_step, 1)
        self.assertEqual(self.child1.current_step, 1)


# =============================================================================
# 8. 上下文栈测试
# =============================================================================

class TestContextStack(unittest.TestCase):
    """测试上下文栈"""

    def setUp(self):
        ExecutionContext.clear_stack()

    def tearDown(self):
        ExecutionContext.clear_stack()

    def test_push_and_pop(self):
        """测试推入和弹出"""
        ctx1 = ExecutionContext(context_id="ctx1")
        ctx2 = ExecutionContext(context_id="ctx2")

        ExecutionContext.push(ctx1)
        ExecutionContext.push(ctx2)

        self.assertEqual(ExecutionContext.stack_depth(), 2)
        self.assertEqual(ExecutionContext.current(), ctx2)

        popped = ExecutionContext.pop()
        self.assertEqual(popped, ctx2)
        self.assertEqual(ExecutionContext.current(), ctx1)

    def test_pop_empty(self):
        """测试弹出空栈"""
        result = ExecutionContext.pop()
        self.assertIsNone(result)

    def test_current_empty(self):
        """测试空栈的当前上下文"""
        result = ExecutionContext.current()
        self.assertIsNone(result)

    def test_clear_stack(self):
        """测试清空栈"""
        ExecutionContext.push(ExecutionContext(context_id="c1"))
        ExecutionContext.push(ExecutionContext(context_id="c2"))
        ExecutionContext.clear_stack()

        self.assertEqual(ExecutionContext.stack_depth(), 0)


# =============================================================================
# 9. 上下文管理器测试
# =============================================================================

class TestContextManager(unittest.TestCase):
    """测试上下文管理器"""

    def setUp(self):
        ExecutionContext.clear_stack()

    def tearDown(self):
        ExecutionContext.clear_stack()

    def test_enter_exit(self):
        """测试进入退出"""
        ctx = ExecutionContext(context_id="cm_test", total_steps=2)

        with ctx:
            self.assertEqual(ctx.state, ContextState.ACTIVE)
            self.assertEqual(ExecutionContext.current(), ctx)

        # 退出后应自动完成
        self.assertEqual(ctx.state, ContextState.COMPLETED)
        self.assertIsNone(ExecutionContext.current())

    def test_exit_on_error(self):
        """测试异常时退出"""
        ctx = ExecutionContext(context_id="error_test")

        with self.assertRaises(ValueError):
            with ctx:
                raise ValueError("测试错误")

        # 异常后应标记为失败
        self.assertEqual(ctx.state, ContextState.FAILED)
        self.assertIn("测试错误", ctx.error)

    def test_nested_context_manager(self):
        """测试嵌套上下文管理器"""
        parent = ExecutionContext(context_id="parent")
        child = ExecutionContext(context_id="child", parent=parent)

        with parent:
            self.assertEqual(ExecutionContext.current(), parent)
            with child:
                self.assertEqual(ExecutionContext.current(), child)
            # 子退出后，父仍为当前
            self.assertEqual(ExecutionContext.current(), parent)


# =============================================================================
# 10. 集成测试
# =============================================================================

class TestContextIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        ExecutionContext.clear_stack()

    def tearDown(self):
        ExecutionContext.clear_stack()

    def test_full_task_workflow(self):
        """测试完整任务工作流"""
        with ExecutionContext(
            context_id="task_root",
            task_id=TaskID("task_001"),
            total_steps=4,
        ) as root:
            # 设置全局配置
            root.set("config", {"timeout": 30})

            # 子模块1：初始化
            with root.create_child(
                context_id="init_module",
                module_id=ModuleID("init"),
                total_steps=2,
            ) as init_ctx:
                init_ctx.advance_step("加载配置")
                init_ctx.complete_current_step(result="ok")
                init_ctx.advance_step("验证配置")
                init_ctx.complete_current_step(result="ok")

            # 子模块2：执行
            with root.create_child(
                context_id="exec_module",
                module_id=ModuleID("exec"),
                total_steps=2,
            ) as exec_ctx:
                # 子上下文可访问父级数据
                config = exec_ctx.get_from_hierarchy("config")
                self.assertEqual(config["timeout"], 30)

                exec_ctx.advance_step("执行任务")
                exec_ctx.complete_current_step(result="done")
                exec_ctx.advance_step("清理")
                exec_ctx.complete_current_step()

        # 验证最终状态
        self.assertEqual(root.state, ContextState.COMPLETED)
        self.assertEqual(len(root.children), 2)
        self.assertEqual(root.get_child("init_module").state, ContextState.COMPLETED)


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
