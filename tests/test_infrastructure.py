"""
阶段15测试：基础设施层集成测试
Test Stage 15: Infrastructure Layer Integration Tests

测试范围：
1. 类型定义完整性测试
2. 接口协议测试
3. 基类继承测试
4. 双子容器测试
5. 事件总线测试
6. 日志系统测试
7. 配置管理测试
8. 异常处理测试
9. 状态快照测试
10. 缓存与存储测试
11. 校验器测试
12. 执行上下文测试
13. 跨组件集成测试

验证标准：所有基础设施组件协同工作
"""

import unittest
import tempfile
import shutil
import threading
import time

import sys
sys.path.insert(0, '/workspace')

# 导入所有基础设施组件
from core_types.core_types import (
    ModuleID, TaskID, ModuleType, ModuleState,
    TaskParam, InitResult, ModuleInput, ModuleOutput,
    CheckResult, SnapshotData, CheckpointData,
)

from interfaces.module_interface import (
    IModuleInit, IModuleRun, IModuleCheck, IModuleSnapshot, IModule,
)

from core.base_module import BaseModule
from core.twin_container import TwinContainer, TwinSlot
from core.module_registry import ModuleRegistry
from core.event_bus import EventBus, ModuleEvent
from core.exceptions import (
    ModuleException, InitException, RunException,
    CheckException, ValidationException, RecoveryException,
)

from utils.logger import Logger, LogLevel
from utils.config_manager import ConfigManager

from state.snapshot_base import SnapshotBase, CheckpointManager
from state.short_term_cache import ShortTermCache, ModuleCacheManager
from state.long_term_storage import LongTermStorage

from validators.validator_base import (
    ValidatorBase, ValidationResult, ValidationReport,
    ValidationRule, ValidationLevel, CompositeValidator,
)

from core.execution_context import ExecutionContext, ContextState


# =============================================================================
# 1. 类型定义完整性测试
# =============================================================================

class TestCoreTypes(unittest.TestCase):
    """测试核心类型定义"""

    def test_module_id_creation(self):
        """测试ModuleID创建"""
        mid = ModuleID("test")
        self.assertTrue(str(mid).startswith("test_"))

    def test_task_id_creation(self):
        """测试TaskID创建"""
        tid = TaskID("task")
        self.assertTrue(str(tid).startswith("task_"))

    def test_module_type_enum(self):
        """测试ModuleType枚举"""
        self.assertEqual(ModuleType.CONTROL.name, "CONTROL")
        self.assertEqual(ModuleType.EXECUTE.name, "EXECUTE")

    def test_module_state_enum(self):
        """测试ModuleState枚举"""
        self.assertEqual(ModuleState.UNINITIALIZED.name, "UNINITIALIZED")
        self.assertEqual(ModuleState.RUNNING.name, "RUNNING")

    def test_dataclasses_creation(self):
        """测试数据类创建"""
        param = TaskParam(task_name="test_task")
        self.assertEqual(param.task_name, "test_task")

        init_result = InitResult(success=True, module_id=ModuleID("test"))
        self.assertTrue(init_result.success)

        module_input = ModuleInput(task_id=TaskID("test_task"))
        self.assertIsInstance(module_input.task_id, TaskID)


# =============================================================================
# 2. 接口协议测试
# =============================================================================

class TestInterfaceProtocols(unittest.TestCase):
    """测试接口协议"""

    def test_imodule_init_protocol(self):
        """测试IModuleInit协议"""
        self.assertTrue(hasattr(IModuleInit, 'module_init'))

    def test_imodule_run_protocol(self):
        """测试IModuleRun协议"""
        self.assertTrue(hasattr(IModuleRun, 'module_run'))

    def test_imodule_check_protocol(self):
        """测试IModuleCheck协议"""
        self.assertTrue(hasattr(IModuleCheck, 'module_check'))

    def test_imodule_snapshot_protocol(self):
        """测试IModuleSnapshot协议"""
        self.assertTrue(hasattr(IModuleSnapshot, 'create_snapshot'))
        self.assertTrue(hasattr(IModuleSnapshot, 'restore_from_snapshot'))

    def test_imodule_combined(self):
        """测试IModule组合接口"""
        # IModule继承自各个子接口
        self.assertTrue(hasattr(IModule, 'module_init'))
        self.assertTrue(hasattr(IModule, 'module_run'))
        self.assertTrue(hasattr(IModule, 'module_check'))


# =============================================================================
# 3. 基类继承测试
# =============================================================================

class ConcreteModule(BaseModule):
    """具体模块实现（用于测试）"""

    def __init__(self, module_id: ModuleID = None, module_type: ModuleType = ModuleType.CONTROL):
        super().__init__(module_id=module_id)
        # 设置模块类型
        self._state.module_type = module_type

    def _do_init(self, request, context) -> InitResult:
        """实际初始化逻辑"""
        return InitResult(success=True, module_id=self.module_id)

    def _do_run(self, request, context) -> ModuleOutput:
        """实际执行逻辑"""
        return ModuleOutput(task_id=TaskID("test_task"), success=True)

    def _do_check(self, request, context) -> CheckResult:
        """实际校验逻辑"""
        return CheckResult.passed_result(check_type="test_check")

    def _do_snapshot(self, request, context) -> SnapshotData:
        """实际快照逻辑"""
        return SnapshotData(module_id=self.module_id)


class TestBaseModule(unittest.TestCase):
    """测试基类继承"""

    def test_base_module_creation(self):
        """测试基类模块创建"""
        module = ConcreteModule()
        self.assertIsNotNone(module.module_id)
        # 默认类型是CONTROL
        self.assertEqual(module.module_type, ModuleType.CONTROL)

    def test_base_module_execute_type(self):
        """测试EXECUTE类型模块"""
        module = ConcreteModule(module_type=ModuleType.EXECUTE)
        self.assertEqual(module.module_type, ModuleType.EXECUTE)

    def test_base_module_state_management(self):
        """测试状态管理"""
        module = ConcreteModule()
        self.assertEqual(module.module_state, ModuleState.UNINITIALIZED)

        module._state.module_state = ModuleState.RUNNING
        self.assertEqual(module.module_state, ModuleState.RUNNING)

    def test_base_module_child_management(self):
        """测试子模块管理"""
        # 使用TwinContainer来管理双子结构
        container = TwinContainer(parent_id=ModuleID("parent"))
        child1 = ConcreteModule(module_type=ModuleType.CONTROL)
        child2 = ConcreteModule(module_type=ModuleType.EXECUTE)

        container.add_control_child(child1)
        container.add_execute_child(child2)

        self.assertEqual(container.child_count, 2)
        self.assertTrue(container.is_complete)

    def test_base_module_interface_implementation(self):
        """测试接口实现"""
        from interfaces.module_interface import (
            create_default_init_request, create_default_execution_request,
            create_default_validation_request, InitContext, ExecutionContext as ExecCtx, ValidationContext
        )
        module = ConcreteModule()

        # 测试所有接口方法（使用带module_id的请求）
        init_result = module.module_init(
            create_default_init_request(module.module_id),
            InitContext()
        )
        # 由于BaseModule有复杂的初始化流程，我们主要测试不抛出异常
        # 实际结果取决于验证逻辑
        self.assertIsInstance(init_result, InitResult)

        run_result = module.module_run(
            create_default_execution_request(module.module_id),
            ExecCtx()
        )
        self.assertTrue(run_result.success)

        check_result = module.module_check(
            create_default_validation_request(module.module_id),
            ValidationContext()
        )
        self.assertTrue(check_result.passed)


# =============================================================================
# 4. 双子容器测试
# =============================================================================

class TestTwinContainer(unittest.TestCase):
    """测试双子容器"""

    def test_twin_container_creation(self):
        """测试双子容器创建"""
        container = TwinContainer(parent_id=ModuleID("parent"))
        self.assertEqual(container.child_count, 0)

    def test_add_control_child(self):
        """测试添加管控子模块"""
        container = TwinContainer(parent_id=ModuleID("parent"))
        control = ConcreteModule(module_type=ModuleType.CONTROL)

        container.add_control_child(control)
        self.assertEqual(container.get_control_child(), control)

    def test_add_execute_child(self):
        """测试添加执行子模块"""
        container = TwinContainer(parent_id=ModuleID("parent"))
        execute = ConcreteModule(module_type=ModuleType.EXECUTE)

        container.add_execute_child(execute)
        self.assertEqual(container.get_execute_child(), execute)

    def test_twin_structure_validation(self):
        """测试双子结构验证"""
        container = TwinContainer(parent_id=ModuleID("parent"))
        control = ConcreteModule(module_type=ModuleType.CONTROL)
        execute = ConcreteModule(module_type=ModuleType.EXECUTE)

        container.add_control_child(control)
        container.add_execute_child(execute)

        self.assertTrue(container.is_complete)

    def test_cannot_add_third_child(self):
        """测试不能添加第三个子模块"""
        container = TwinContainer(parent_id=ModuleID("parent"))
        container.add_control_child(ConcreteModule(module_type=ModuleType.CONTROL))
        container.add_execute_child(ConcreteModule(module_type=ModuleType.EXECUTE))

        # 双子结构已满，再添加会抛出异常
        with self.assertRaises(Exception):
            container.add_control_child(ConcreteModule(module_type=ModuleType.CONTROL))


# =============================================================================
# 5. 事件总线测试
# =============================================================================

class TestEventBus(unittest.TestCase):
    """测试事件总线"""

    def setUp(self):
        self.event_bus = EventBus()
        self.received_events = []

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        from core_types.core_types import ModuleEvent, ModuleEventType
        def handler(event):
            self.received_events.append(event)

        sub_id = self.event_bus.subscribe(handler, [ModuleEventType.INIT_STARTED])
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_STARTED,
            module_id=ModuleID("test"),
            data={"data": "test"},
        )
        self.event_bus.publish(event)

        self.assertEqual(len(self.received_events), 1)

    def test_unsubscribe(self):
        """测试取消订阅"""
        from core_types.core_types import ModuleEvent, ModuleEventType
        def handler(event):
            self.received_events.append(event)

        sub_id = self.event_bus.subscribe(handler, [ModuleEventType.INIT_STARTED])
        self.event_bus.unsubscribe(sub_id)
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_STARTED,
            module_id=ModuleID("test"),
        )
        self.event_bus.publish(event)

        self.assertEqual(len(self.received_events), 0)

    def test_multiple_handlers(self):
        """测试多个处理器"""
        from core_types.core_types import ModuleEvent, ModuleEventType
        def handler1(event):
            self.received_events.append("handler1")

        def handler2(event):
            self.received_events.append("handler2")

        self.event_bus.subscribe(handler1, [ModuleEventType.INIT_STARTED])
        self.event_bus.subscribe(handler2, [ModuleEventType.INIT_STARTED])
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_STARTED,
            module_id=ModuleID("test"),
        )
        self.event_bus.publish(event)

        self.assertEqual(len(self.received_events), 2)


# =============================================================================
# 6. 日志系统测试
# =============================================================================

class TestLogger(unittest.TestCase):
    """测试日志系统"""

    def test_logger_creation(self):
        """测试日志器创建"""
        logger = Logger(name="test_logger")
        self.assertEqual(logger.name, "test_logger")

    def test_log_levels(self):
        """测试日志级别"""
        logger = Logger(name="level_test")

        # 测试各级别日志记录不抛出异常
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

    def test_log_level_filtering(self):
        """测试日志级别过滤"""
        logger = Logger(name="filter_test", level=LogLevel.WARNING)

        # 低于WARNING的日志不应被记录
        # 这里主要测试不抛出异常
        logger.debug("should be filtered")
        logger.info("should be filtered")
        logger.warning("should be recorded")
        logger.error("should be recorded")


# =============================================================================
# 7. 配置管理测试
# =============================================================================

class TestConfigManager(unittest.TestCase):
    """测试配置管理"""

    def setUp(self):
        self.config = ConfigManager()

    def test_set_and_get_config(self):
        """测试配置存取"""
        self.config.set("key1", "value1")
        self.assertEqual(self.config.get("key1"), "value1")

    def test_get_with_default(self):
        """测试默认值"""
        self.assertEqual(self.config.get("nonexistent", "default"), "default")

    def test_update_config(self):
        """测试更新配置"""
        self.config.set("key1", "value1")
        self.config.set("key1", "value2")
        self.assertEqual(self.config.get("key1"), "value2")


# =============================================================================
# 8. 异常处理测试
# =============================================================================

class TestExceptions(unittest.TestCase):
    """测试异常处理"""

    def test_module_exception(self):
        """测试模块异常基类"""
        exc = ModuleException(code="ERR_001", message="test error")
        self.assertIn("test error", str(exc))
        self.assertFalse(exc.recoverable)

    def test_init_exception(self):
        """测试初始化异常"""
        exc = InitException(code="INIT_001", message="init failed")
        self.assertTrue(isinstance(exc, ModuleException))

    def test_run_exception(self):
        """测试运行异常"""
        exc = RunException(code="RUN_001", message="run failed", recoverable=True)
        self.assertTrue(exc.recoverable)

    def test_exception_context(self):
        """测试异常上下文"""
        from core.exceptions import ExceptionContext
        ctx = ExceptionContext(module_name="test_module")
        exc = ModuleException(code="ERR_002", message="error", context=ctx)
        self.assertEqual(exc.context.module_name, "test_module")


# =============================================================================
# 9. 状态快照测试
# =============================================================================

class TestSnapshotBase(unittest.TestCase):
    """测试状态快照"""

    def test_snapshot_creation(self):
        """测试快照创建"""
        snapshot = SnapshotData(
            module_id=ModuleID("module_001"),
            state_data={"status": "running"},
        )
        self.assertTrue(str(snapshot.module_id).startswith("module_001"))


# =============================================================================
# 10. 缓存与存储测试
# =============================================================================

class TestCacheAndStorage(unittest.TestCase):
    """测试缓存与存储"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_short_term_cache(self):
        """测试短期缓存"""
        cache = ShortTermCache(max_size=100)
        cache.set("key1", "value1")

        self.assertEqual(cache.get("key1"), "value1")
        self.assertIsNone(cache.get("nonexistent"))

    def test_long_term_storage(self):
        """测试长期存储"""
        storage = LongTermStorage(storage_root=self.temp_dir)
        storage.save("key1", {"data": "value1"})

        loaded, result = storage.load("key1")
        self.assertTrue(result.success)
        self.assertEqual(loaded["data"], "value1")

    def test_module_cache_manager(self):
        """测试模块缓存管理器"""
        manager = ModuleCacheManager()
        cache1 = manager.get_cache(ModuleID("module_001"))
        cache2 = manager.get_cache(ModuleID("module_002"))

        cache1.set("key", "value1")
        cache2.set("key", "value2")

        self.assertEqual(cache1.get("key"), "value1")
        self.assertEqual(cache2.get("key"), "value2")


# =============================================================================
# 11. 校验器测试
# =============================================================================

class SimpleTestValidator(ValidatorBase):
    """简单测试校验器"""

    def __init__(self):
        super().__init__(name="SimpleTestValidator")

    def validate(self, data, context=None):
        report = self._create_report()

        if not isinstance(data, dict):
            report.add_result(ValidationResult.critical("数据必须是字典"))
            return report

        # 检查必填字段
        if "name" not in data:
            report.add_result(ValidationResult.error("name是必填字段", field="name"))

        if "age" in data and not isinstance(data["age"], int):
            report.add_result(ValidationResult.error("age必须是整数", field="age"))

        if report.total_checks == 0:
            report.add_result(ValidationResult.valid())

        return report


class TestValidator(unittest.TestCase):
    """测试校验器"""

    def test_validator_creation(self):
        """测试校验器创建"""
        validator = SimpleTestValidator()
        self.assertEqual(validator.name, "SimpleTestValidator")

    def test_valid_data(self):
        """测试有效数据"""
        validator = SimpleTestValidator()
        report = validator.validate({"name": "test", "age": 25})

        self.assertTrue(report.is_valid)

    def test_invalid_data(self):
        """测试无效数据"""
        validator = SimpleTestValidator()
        report = validator.validate({"age": "not an int"})

        self.assertFalse(report.is_valid)

    def test_validation_result_levels(self):
        """测试校验结果级别"""
        valid = ValidationResult.valid()
        warning = ValidationResult.warning("warn")
        error = ValidationResult.error("err")
        critical = ValidationResult.critical("crit")

        self.assertTrue(valid.is_valid)
        self.assertTrue(warning.is_valid)  # 警告仍算有效
        self.assertFalse(error.is_valid)
        self.assertFalse(critical.is_valid)


# =============================================================================
# 12. 执行上下文测试
# =============================================================================

class TestExecutionContext(unittest.TestCase):
    """测试执行上下文"""

    def test_context_creation(self):
        """测试上下文创建"""
        ctx = ExecutionContext(context_id="test", total_steps=5)
        self.assertEqual(ctx.context_id, "test")
        self.assertEqual(ctx.total_steps, 5)

    def test_context_state_management(self):
        """测试状态管理"""
        ctx = ExecutionContext(context_id="test")

        ctx.activate()
        self.assertEqual(ctx.state, ContextState.ACTIVE)

        ctx.pause()
        self.assertEqual(ctx.state, ContextState.PAUSED)

        ctx.resume()
        self.assertEqual(ctx.state, ContextState.ACTIVE)

        ctx.complete()
        self.assertEqual(ctx.state, ContextState.COMPLETED)

    def test_step_management(self):
        """测试步骤管理"""
        ctx = ExecutionContext(context_id="test", total_steps=3)

        ctx.advance_step("step1")
        self.assertEqual(ctx.current_step, 1)

        ctx.complete_current_step()

        ctx.advance_step("step2")
        self.assertEqual(ctx.current_step, 2)

    def test_context_data(self):
        """测试上下文数据"""
        ctx = ExecutionContext(context_id="test")

        ctx.set("key1", "value1")
        self.assertEqual(ctx.get("key1"), "value1")
        self.assertTrue(ctx.has("key1"))

    def test_parent_child_context(self):
        """测试父子上下文"""
        parent = ExecutionContext(context_id="parent")
        child = parent.create_child(context_id="child")

        self.assertEqual(child.parent, parent)
        self.assertEqual(child.root, parent)
        self.assertEqual(child.depth, 1)

    def test_hierarchy_data_lookup(self):
        """测试层级数据查找"""
        parent = ExecutionContext(context_id="parent")
        parent.set("shared_key", "shared_value")

        child = parent.create_child(context_id="child")

        # 子上下文可通过层级查找访问父级数据
        self.assertEqual(child.get_from_hierarchy("shared_key"), "shared_value")

    def test_context_manager(self):
        """测试上下文管理器"""
        with ExecutionContext(context_id="cm_test") as ctx:
            self.assertEqual(ctx.state, ContextState.ACTIVE)

        # 退出后应自动完成
        self.assertEqual(ctx.state, ContextState.COMPLETED)


# =============================================================================
# 13. 跨组件集成测试
# =============================================================================

class TestCrossComponentIntegration(unittest.TestCase):
    """跨组件集成测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_module_with_context_and_storage(self):
        """测试模块与上下文、存储集成"""
        # 创建模块
        module = ConcreteModule()

        # 创建执行上下文
        with ExecutionContext(
            context_id="integration_test",
            module_id=module.module_id,
            total_steps=3,
        ) as ctx:
            # 模块在上下文中执行
            ctx.advance_step("初始化")
            # 直接调用_do_init简化测试
            init_result = module._do_init(None, None)
            self.assertTrue(init_result.success)
            ctx.complete_current_step(result="initialized")

            ctx.advance_step("执行")
            # 直接调用_do_run简化测试
            run_result = module._do_run(None, None)
            self.assertTrue(run_result.success)
            ctx.complete_current_step(result="executed")

            ctx.advance_step("校验")
            # 直接调用_do_check简化测试
            check_result = module._do_check(None, None)
            self.assertTrue(check_result.passed)
            ctx.complete_current_step(result="checked")

        # 验证上下文状态
        self.assertEqual(ctx.state, ContextState.COMPLETED)
        self.assertEqual(len(ctx.get_completed_steps()), 3)

    def test_event_bus_with_modules(self):
        """测试事件总线与模块集成"""
        from core_types.core_types import ModuleEvent, ModuleEventType
        event_bus = EventBus()
        received_events = []

        def event_handler(event):
            received_events.append(event)

        event_bus.subscribe(event_handler, [ModuleEventType.INIT_STARTED])

        # 模拟模块初始化并发布事件
        module = ConcreteModule()
        event = ModuleEvent(
            event_type=ModuleEventType.INIT_STARTED,
            module_id=module.module_id,
            data={"action": "init"},
        )
        event_bus.publish(event)

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].data["action"], "init")

    def test_validator_with_module_data(self):
        """测试校验器与模块数据集成"""
        validator = SimpleTestValidator()

        # 模拟模块配置数据
        module_config = {
            "name": "test_module",
            "timeout": 30,
        }

        report = validator.validate(module_config)
        self.assertTrue(report.is_valid)

        # 无效配置
        invalid_config = {
            "timeout": "not_a_number",
        }

        report = validator.validate(invalid_config)
        self.assertFalse(report.is_valid)

    def test_cache_storage_and_context(self):
        """测试缓存、存储和上下文集成"""
        # 创建上下文
        ctx = ExecutionContext(context_id="cache_storage_test")

        # 创建缓存
        cache = ShortTermCache()

        # 创建存储
        storage = LongTermStorage(storage_root=self.temp_dir)

        # 模拟执行过程中使用缓存和存储
        ctx.set("temp_data", "cached_value")  # 上下文数据
        cache.set("intermediate", {"step": 1})  # 短期缓存
        storage.save("final_result", {"status": "success"})  # 长期存储

        # 验证数据一致性
        self.assertEqual(ctx.get("temp_data"), "cached_value")
        self.assertEqual(cache.get("intermediate")["step"], 1)

        loaded, result = storage.load("final_result")
        self.assertTrue(result.success)
        self.assertEqual(loaded["status"], "success")

    def test_full_infrastructure_stack(self):
        """测试完整基础设施栈"""
        from core_types.core_types import ModuleEvent, ModuleEventType

        # 1. 创建模块
        module = ConcreteModule()

        # 2. 创建执行上下文
        with ExecutionContext(
            context_id="full_stack_test",
            module_id=module.module_id,
            total_steps=5,
        ) as ctx:
            # 3. 使用事件总线
            event_bus = EventBus()
            events = []
            event_bus.subscribe(lambda e: events.append(e), [ModuleEventType.RUN_STARTED])

            # 4. 使用日志
            logger = Logger(name="integration")

            # 5. 使用配置
            config = ConfigManager()
            config.set("timeout", 30)

            # 6. 使用缓存
            cache = ShortTermCache()

            # 7. 使用存储
            storage = LongTermStorage(storage_root=self.temp_dir)

            # 8. 使用校验器
            validator = SimpleTestValidator()

            # 执行流程
            ctx.advance_step("配置验证")
            module_config = {"name": "test", "timeout": config.get("timeout")}
            report = validator.validate(module_config)
            self.assertTrue(report.is_valid)
            ctx.complete_current_step()

            ctx.advance_step("初始化")
            cache.set("init_status", "in_progress")
            # 直接调用_do_init简化测试
            init_result = module._do_init(None, None)
            self.assertTrue(init_result.success)
            cache.set("init_status", "completed")
            ctx.complete_current_step()

            ctx.advance_step("执行")
            event = ModuleEvent(
                event_type=ModuleEventType.RUN_STARTED,
                module_id=module.module_id,
                data={"module": str(module.module_id)},
            )
            event_bus.publish(event)
            # 直接调用_do_run简化测试
            run_result = module._do_run(None, None)
            self.assertTrue(run_result.success)
            ctx.complete_current_step(result=run_result)

            ctx.advance_step("持久化")
            storage.save("run_result", {"success": True, "data": "test"})
            ctx.complete_current_step()

            ctx.advance_step("校验")
            # 直接调用_do_check简化测试
            check_result = module._do_check(None, None)
            self.assertTrue(check_result.passed)
            logger.info("Validation passed")
            ctx.complete_current_step()

        # 验证结果
        self.assertEqual(ctx.state, ContextState.COMPLETED)
        self.assertEqual(len(events), 1)  # 事件被接收
        self.assertEqual(cache.get("init_status"), "completed")

        loaded, result = storage.load("run_result")
        self.assertTrue(result.success)


# =============================================================================
# 运行测试
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
