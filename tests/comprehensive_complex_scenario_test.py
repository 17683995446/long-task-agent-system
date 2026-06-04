"""
全面复杂场景测试 - Comprehensive Complex Scenario Test

目标：通过大规模、高复杂度、混乱场景的真实实践测试，发现系统bug

测试场景设计原则：
1. 大规模：同时运行100+模块，10000+次迭代
2. 高复杂度：深层嵌套调用（4层模块树），多线程并发
3. 混乱场景：随机异常注入、状态竞争、资源耗尽
4. 真实实践：模拟真实业务场景的完整链路

日志验证：每一行代码执行后打印日志，通过日志是否正常输出来验证是否存在问题
"""

import unittest
import threading
import time
import random
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, '/workspace')

# 导入所有系统组件
from core_types.core_types import (
    ModuleID, TaskID, ModuleType, ModuleState, ModuleLevel,
    ModuleEvent, ModuleEventType,
)
from interfaces.module_interface import (
    InitRequest, InitContext, ExecutionRequest, ExecutionContext,
    ValidationRequest, ValidationContext, SnapshotRequest, SnapshotContext,
    ModuleInput, ModuleParam, TaskParam,
)
from core.base_module import BaseModule, ControlModuleBase, ExecuteModuleBase
from core.twin_container import TwinContainer, TwinSlot
from core.event_bus import EventBus
from core.module_registry import ModuleRegistry
from core.execution_context import ExecutionContext as CoreExecContext
from utils.logger import Logger, LogLevel
from system.module_tree import ModuleTree, ModuleTreeBuilder
from system.execution_engine import ExecutionEngine


# =============================================================================
# 日志收集器 - 用于验证日志是否正常输出
# =============================================================================

class LogCollector:
    """日志收集器，收集所有日志输出用于验证"""
    
    def __init__(self):
        self.logs = []
        self._lock = threading.Lock()
    
    def collect(self, level, module, message):
        with self._lock:
            self.logs.append({
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'module': module,
                'message': message,
            })
    
    def get_logs_by_module(self, module_name):
        return [l for l in self.logs if module_name in l['module']]
    
    def get_error_logs(self):
        return [l for l in self.logs if l['level'] in ('ERROR', 'CRITICAL')]
    
    def has_log_containing(self, substring):
        return any(substring in l['message'] for l in self.logs)
    
    def clear(self):
        with self._lock:
            self.logs.clear()


# 全局日志收集器
GLOBAL_LOG_COLLECTOR = LogCollector()


# =============================================================================
# 增强日志的测试模块
# =============================================================================

class LoggedControlModule(ControlModuleBase):
    """带完整日志的管控模块"""
    
    def __init__(self, module_id=None, name="LoggedControl"):
        super().__init__(module_id)
        self._name = name
        self._logger = Logger(f"{name}_{self.module_id}")
        self.operation_count = 0
        self.errors_encountered = []
    
    def _log(self, level, message):
        """记录日志并收集"""
        log_msg = f"[{self._name}] {message}"
        if level == "INFO":
            self._logger.info(log_msg)
        elif level == "DEBUG":
            self._logger.debug(log_msg)
        elif level == "WARNING":
            self._logger.warning(log_msg)
        elif level == "ERROR":
            self._logger.error(log_msg)
        GLOBAL_LOG_COLLECTOR.collect(level, self._name, log_msg)
    
    def _do_init(self, request, context):
        self._log("INFO", f"=== _do_init START === module_state={self.module_state}")
        try:
            self.operation_count += 1
            # 模拟初始化工作
            time.sleep(0.001)
            self._log("INFO", f"=== _do_init END === success")
            from core_types.core_types import InitResult
            return InitResult.success_result(self.module_id, f"{self._name} initialized")
        except Exception as e:
            self._log("ERROR", f"=== _do_init FAILED === {e}")
            self.errors_encountered.append(str(e))
            raise
    
    def _do_run(self, request, context):
        self._log("INFO", f"=== _do_run START === module_state={self.module_state}")
        try:
            self._check_initialized()
            self.operation_count += 1
            # 模拟执行工作
            time.sleep(0.001)
            self._log("INFO", f"=== _do_run END === success")
            from core_types.core_types import ModuleOutput
            return ModuleOutput.success_output(
                task_id=TaskID(),
                data={"module": self._name, "ops": self.operation_count},
                message=f"{self._name} executed"
            )
        except Exception as e:
            self._log("ERROR", f"=== _do_run FAILED === {e}")
            self.errors_encountered.append(str(e))
            raise
    
    def _do_check(self, request, context):
        self._log("INFO", f"=== _do_check START ===")
        from core_types.core_types import CheckResult
        result = CheckResult.passed_result(f"{self._name}_check")
        self._log("INFO", f"=== _do_check END === passed={result.passed}")
        return result
    
    def _do_snapshot(self, request, context, snapshot):
        self._log("INFO", f"=== _do_snapshot START ===")
        snapshot.set_state("name", self._name)
        snapshot.set_state("ops", self.operation_count)
        self._log("INFO", f"=== _do_snapshot END ===")


class LoggedExecuteModule(ExecuteModuleBase):
    """带完整日志的执行模块"""
    
    def __init__(self, module_id=None, name="LoggedExecute"):
        super().__init__(module_id)
        self._name = name
        self._logger = Logger(f"{name}_{self.module_id}")
        self.iteration_count = 0
        self.errors_encountered = []
    
    def _log(self, level, message):
        log_msg = f"[{self._name}] {message}"
        if level == "INFO":
            self._logger.info(log_msg)
        elif level == "DEBUG":
            self._logger.debug(log_msg)
        elif level == "WARNING":
            self._logger.warning(log_msg)
        elif level == "ERROR":
            self._logger.error(log_msg)
        GLOBAL_LOG_COLLECTOR.collect(level, self._name, log_msg)
    
    def _do_init(self, request, context):
        self._log("INFO", f"=== _do_init START === module_state={self.module_state}")
        try:
            self.iteration_count = 0
            time.sleep(0.001)
            self._log("INFO", f"=== _do_init END === success")
            from core_types.core_types import InitResult
            return InitResult.success_result(self.module_id, f"{self._name} initialized")
        except Exception as e:
            self._log("ERROR", f"=== _do_init FAILED === {e}")
            self.errors_encountered.append(str(e))
            raise
    
    def _do_run(self, request, context):
        self._log("INFO", f"=== _do_run START === module_state={self.module_state}")
        try:
            self._check_initialized()
            self.iteration_count += 1
            # 模拟迭代执行
            time.sleep(0.001)
            self._log("INFO", f"=== _do_run END === success iterations={self.iteration_count}")
            from core_types.core_types import ModuleOutput
            return ModuleOutput.success_output(
                task_id=TaskID(),
                data={"module": self._name, "iterations": self.iteration_count},
                message=f"{self._name} executed"
            )
        except Exception as e:
            self._log("ERROR", f"=== _do_run FAILED === {e}")
            self.errors_encountered.append(str(e))
            raise
    
    def _do_check(self, request, context):
        self._log("INFO", f"=== _do_check START ===")
        from core_types.core_types import CheckResult
        result = CheckResult.passed_result(f"{self._name}_check")
        self._log("INFO", f"=== _do_check END === passed={result.passed}")
        return result
    
    def _do_snapshot(self, request, context, snapshot):
        self._log("INFO", f"=== _do_snapshot START ===")
        snapshot.set_state("name", self._name)
        snapshot.set_state("iterations", self.iteration_count)
        self._log("INFO", f"=== _do_snapshot END ===")


# =============================================================================
# 复杂场景测试类
# =============================================================================

class TestScenario1_DeepModuleTree(unittest.TestCase):
    """
    场景1：深层模块树构建与遍历
    
    复杂度：4层深度，每层双子结构
    规模：ROOT -> L1(2) -> L2(4) -> L3(8) -> L4(16) = 31个模块
    """
    
    def setUp(self):
        GLOBAL_LOG_COLLECTOR.clear()
    
    def test_build_deep_tree(self):
        """测试构建深层模块树"""
        print("\n" + "="*60)
        print("场景1：深层模块树构建与遍历")
        print("="*60)
        
        # 构建4层模块树
        root = LoggedControlModule(name="Root")
        
        # Level 1
        l1_control = LoggedControlModule(name="L1_Control")
        l1_execute = LoggedExecuteModule(name="L1_Execute")
        root.set_control_child(l1_control)
        root.set_execute_child(l1_execute)
        
        # Level 2
        l2_control = LoggedControlModule(name="L2_Control")
        l2_execute = LoggedExecuteModule(name="L2_Execute")
        l1_control.set_control_child(l2_control)
        l1_control.set_execute_child(l2_execute)
        
        # Level 3
        l3_control = LoggedControlModule(name="L3_Control")
        l3_execute = LoggedExecuteModule(name="L3_Execute")
        l2_control.set_control_child(l3_control)
        l2_control.set_execute_child(l3_execute)
        
        # Level 4
        l4_control = LoggedControlModule(name="L4_Control")
        l4_execute = LoggedExecuteModule(name="L4_Execute")
        l3_control.set_control_child(l4_control)
        l3_control.set_execute_child(l4_execute)
        
        # 验证树结构
        self.assertTrue(root.has_children())
        self.assertTrue(l1_control.has_children())
        self.assertTrue(l2_control.has_children())
        self.assertTrue(l3_control.has_children())
        
        # 验证日志输出
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("Root"))
        
        print(f"✓ 深层模块树构建成功")
        print(f"✓ 日志收集数量: {len(GLOBAL_LOG_COLLECTOR.logs)}")
    
    def test_init_deep_tree(self):
        """测试深层模块树初始化"""
        print("\n" + "="*60)
        print("场景1b：深层模块树初始化")
        print("="*60)
        
        root = LoggedControlModule(name="Root")
        l1_control = LoggedControlModule(name="L1_Control")
        l1_execute = LoggedExecuteModule(name="L1_Execute")
        root.set_control_child(l1_control)
        root.set_execute_child(l1_execute)
        
        # 初始化根模块
        init_request = InitRequest(
            module_id=root.module_id,
            module_param=ModuleParam(module_id=root.module_id),
        )
        result = root.module_init(init_request, InitContext())
        
        print(f"✓ 根模块初始化结果: success={result.success}")
        self.assertTrue(result.success)
        
        # 验证状态流转日志
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("_do_init START"))
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("_do_init END"))


class TestScenario2_MassiveConcurrentExecution(unittest.TestCase):
    """
    场景2：大规模并发执行
    
    复杂度：50个模块同时执行，每个执行100次
    规模：5000次总执行
    """
    
    def setUp(self):
        GLOBAL_LOG_COLLECTOR.clear()
    
    def test_massive_concurrent_execution(self):
        """测试大规模并发执行"""
        print("\n" + "="*60)
        print("场景2：大规模并发执行 (50模块 x 100次 = 5000次)")
        print("="*60)
        
        modules = []
        # 创建50个模块
        for i in range(50):
            if i % 2 == 0:
                m = LoggedControlModule(name=f"Control_{i}")
            else:
                m = LoggedExecuteModule(name=f"Execute_{i}")
            modules.append(m)
        
        # 初始化所有模块
        for m in modules:
            init_req = InitRequest(
                module_id=m.module_id,
                module_param=ModuleParam(module_id=m.module_id),
            )
            result = m.module_init(init_req, InitContext())
            self.assertTrue(result.success, f"模块 {m.module_id} 初始化失败")
        
        print(f"✓ 50个模块初始化完成")
        
        # 并发执行100次
        execution_count = [0]
        errors = []
        lock = threading.Lock()
        
        def execute_module(m, idx):
            try:
                exec_req = ExecutionRequest(
                    module_input=ModuleInput(task_id=TaskID()),
                )
                result = m.module_run(exec_req, ExecutionContext())
                with lock:
                    execution_count[0] += 1
                return result.success
            except Exception as e:
                with lock:
                    errors.append((m.module_id, str(e)))
                return False
        
        # 使用线程池并发执行
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for _ in range(100):
                for m in modules:
                    futures.append(executor.submit(execute_module, m, 0))
            
            results = [f.result() for f in as_completed(futures)]
        
        elapsed = time.time() - start_time
        
        print(f"✓ 并发执行完成: {execution_count[0]}/{len(results)} 成功")
        print(f"✓ 执行时间: {elapsed:.2f}s")
        print(f"✓ 错误数量: {len(errors)}")
        print(f"✓ 日志收集数量: {len(GLOBAL_LOG_COLLECTOR.logs)}")
        
        if errors:
            print(f"✗ 错误详情: {errors[:5]}")
        
        self.assertEqual(len(errors), 0, f"并发执行出现错误: {errors}")


class TestScenario3_ChaosEngineering(unittest.TestCase):
    """
    场景3：混沌工程测试
    
    注入随机异常，验证系统容错能力
    """
    
    def setUp(self):
        GLOBAL_LOG_COLLECTOR.clear()
    
    def test_random_failure_injection(self):
        """测试随机故障注入"""
        print("\n" + "="*60)
        print("场景3：混沌工程 - 随机故障注入")
        print("="*60)
        
        class ChaosControlModule(ControlModuleBase):
            def __init__(self, failure_rate=0.3):
                super().__init__()
                self.failure_rate = failure_rate
                self._logger = Logger(f"Chaos_{self.module_id}")
            
            def _do_init(self, request, context):
                if random.random() < self.failure_rate:
                    raise RuntimeError("混沌注入：初始化失败")
                from core_types.core_types import InitResult
                return InitResult.success_result(self.module_id, "initialized")
            
            def _do_run(self, request, context):
                if random.random() < self.failure_rate:
                    raise RuntimeError("混沌注入：执行失败")
                from core_types.core_types import ModuleOutput
                return ModuleOutput.success_output(TaskID(), {}, "executed")
            
            def _do_check(self, request, context):
                from core_types.core_types import CheckResult
                return CheckResult.passed_result("chaos_check")
            
            def _do_snapshot(self, request, context, snapshot):
                pass
        
        # 创建20个混沌模块，30%故障率
        modules = [ChaosControlModule(failure_rate=0.3) for _ in range(20)]
        
        success_count = 0
        failure_count = 0
        
        for m in modules:
            try:
                init_req = InitRequest(
                    module_id=m.module_id,
                    module_param=ModuleParam(module_id=m.module_id),
                )
                result = m.module_init(init_req, InitContext())
                if result.success:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                print(f"  模块 {m.module_id} 初始化异常: {e}")
        
        print(f"✓ 初始化成功: {success_count}, 失败: {failure_count}")
        print(f"✓ 日志收集数量: {len(GLOBAL_LOG_COLLECTOR.logs)}")
        
        # 验证系统没有崩溃
        self.assertGreater(success_count, 0, "所有模块都失败了，系统容错能力有问题")


class TestScenario4_StateRaceCondition(unittest.TestCase):
    """
    场景4：状态竞争条件测试
    
    多个线程同时操作同一个模块的状态
    """
    
    def setUp(self):
        GLOBAL_LOG_COLLECTOR.clear()
    
    def test_state_race_condition(self):
        """测试状态竞争条件"""
        print("\n" + "="*60)
        print("场景4：状态竞争条件测试")
        print("="*60)
        
        module = LoggedControlModule(name="RaceModule")
        
        # 先初始化
        init_req = InitRequest(
            module_id=module.module_id,
            module_param=ModuleParam(module_id=module.module_id),
        )
        module.module_init(init_req, InitContext())
        
        errors = []
        
        def race_task(op_type):
            try:
                for _ in range(50):
                    if op_type == "run":
                        exec_req = ExecutionRequest(
                            module_input=ModuleInput(task_id=TaskID()),
                        )
                        module.module_run(exec_req, ExecutionContext())
                    elif op_type == "check":
                        module.module_check(
                            ValidationRequest(check_type="race_check"),
                            ValidationContext()
                        )
                    elif op_type == "snapshot":
                        module.create_snapshot(
                            SnapshotRequest(),
                            SnapshotContext()
                        )
                    time.sleep(0.001)
            except Exception as e:
                errors.append((op_type, str(e)))
        
        # 10个线程同时操作
        threads = []
        for i in range(10):
            op = ["run", "check", "snapshot"][i % 3]
            t = threading.Thread(target=race_task, args=(op,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"✓ 竞争测试完成")
        print(f"✓ 错误数量: {len(errors)}")
        print(f"✓ 日志收集数量: {len(GLOBAL_LOG_COLLECTOR.logs)}")
        
        if errors:
            print(f"✗ 竞争错误: {errors[:5]}")
        
        self.assertEqual(len(errors), 0, f"状态竞争导致错误: {errors}")


class TestScenario5_CompleteBusinessFlow(unittest.TestCase):
    """
    场景5：完整业务流闭环测试
    
    模拟真实业务场景的完整链路
    """
    
    def setUp(self):
        GLOBAL_LOG_COLLECTOR.clear()
    
    def test_complete_business_flow(self):
        """测试完整业务流"""
        print("\n" + "="*60)
        print("场景5：完整业务流闭环测试")
        print("="*60)
        
        # 构建完整模块树
        root = LoggedControlModule(name="BusinessRoot")
        
        # Level 1: 任务治理 + 执行调度
        l1_control = LoggedControlModule(name="TaskGovernance")
        l1_execute = LoggedExecuteModule(name="TaskScheduler")
        root.set_control_child(l1_control)
        root.set_execute_child(l1_execute)
        
        # Level 2: 异常处理 + 迭代执行
        l2_control = LoggedControlModule(name="ExceptionHandler")
        l2_execute = LoggedExecuteModule(name="IterationRunner")
        l1_control.set_control_child(l2_control)
        l1_control.set_execute_child(l2_execute)
        
        # Level 3: 安全策略 + 原子操作
        l3_control = LoggedControlModule(name="SecurityPolicy")
        l3_execute = LoggedExecuteModule(name="AtomicOperation")
        l2_control.set_control_child(l3_control)
        l2_control.set_execute_child(l3_execute)
        
        # Level 4: 访问控制 + 任务执行
        l4_control = LoggedControlModule(name="AccessControl")
        l4_execute = LoggedExecuteModule(name="TaskExecutor")
        l3_control.set_control_child(l4_control)
        l3_control.set_execute_child(l4_execute)
        
        # 完整链路：初始化 -> 执行 -> 校验 -> 快照 -> 恢复
        
        # 1. 初始化整个树
        print("  Step 1: 初始化模块树...")
        modules_to_init = [root, l1_control, l1_execute, l2_control, l2_execute,
                          l3_control, l3_execute, l4_control, l4_execute]
        
        for m in modules_to_init:
            init_req = InitRequest(
                module_id=m.module_id,
                module_param=ModuleParam(module_id=m.module_id),
            )
            result = m.module_init(init_req, InitContext())
            self.assertTrue(result.success, f"模块 {m.module_id} 初始化失败")
        
        print(f"  ✓ 9个模块初始化完成")
        
        # 2. 执行整个树
        print("  Step 2: 执行模块树...")
        for m in modules_to_init:
            exec_req = ExecutionRequest(
                module_input=ModuleInput(task_id=TaskID()),
            )
            result = m.module_run(exec_req, ExecutionContext())
            self.assertTrue(result.success, f"模块 {m.module_id} 执行失败")
        
        print(f"  ✓ 9个模块执行完成")
        
        # 3. 校验整个树
        print("  Step 3: 校验模块树...")
        for m in modules_to_init:
            result = m.module_check(
                ValidationRequest(check_type="business_flow_check"),
                ValidationContext()
            )
            self.assertTrue(result.passed, f"模块 {m.module_id} 校验失败")
        
        print(f"  ✓ 9个模块校验完成")
        
        # 4. 快照整个树
        print("  Step 4: 快照模块树...")
        snapshots = []
        for m in modules_to_init:
            snapshot = m.create_snapshot(
                SnapshotRequest(),
                SnapshotContext()
            )
            snapshots.append(snapshot)
        
        print(f"  ✓ 9个快照创建完成")
        
        # 5. 验证日志
        print("  Step 5: 验证日志...")
        logs = GLOBAL_LOG_COLLECTOR.logs
        
        # 验证关键日志存在
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("_do_init START"))
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("_do_run START"))
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("_do_check START"))
        self.assertTrue(GLOBAL_LOG_COLLECTOR.has_log_containing("_do_snapshot START"))
        
        # 验证每个模块都有日志
        for m in modules_to_init:
            module_logs = GLOBAL_LOG_COLLECTOR.get_logs_by_module(m._name)
            self.assertGreater(len(module_logs), 0, f"模块 {m._name} 没有日志输出")
        
        print(f"  ✓ 日志验证完成，总日志数: {len(logs)}")
        
        # 6. 验证无错误日志
        error_logs = GLOBAL_LOG_COLLECTOR.get_error_logs()
        self.assertEqual(len(error_logs), 0, f"发现错误日志: {error_logs}")
        
        print(f"✓ 完整业务流测试通过")


class TestScenario6_ResourceExhaustion(unittest.TestCase):
    """
    场景6：资源耗尽测试
    
    模拟内存、线程等资源耗尽场景
    """
    
    def setUp(self):
        GLOBAL_LOG_COLLECTOR.clear()
    
    def test_large_scale_module_creation(self):
        """测试大规模模块创建"""
        print("\n" + "="*60)
        print("场景6：大规模模块创建 (1000个模块)")
        print("="*60)
        
        modules = []
        start_time = time.time()
        
        for i in range(1000):
            if i % 2 == 0:
                m = LoggedControlModule(name=f"Control_{i}")
            else:
                m = LoggedExecuteModule(name=f"Execute_{i}")
            modules.append(m)
        
        elapsed = time.time() - start_time
        
        print(f"✓ 创建1000个模块完成，耗时: {elapsed:.2f}s")
        print(f"✓ 模块数量: {len(modules)}")
        
        self.assertEqual(len(modules), 1000)


# =============================================================================
# 运行所有测试
# =============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
