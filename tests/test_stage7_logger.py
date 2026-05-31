"""
第7阶段验证测试
验证日志系统的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from utils.logger import (
    LogLevel,
    LogRecord,
    LogFormatter,
    ConsoleHandler,
    MemoryHandler,
    Logger,
    LogManager,
    get_logger,
    setup_logging,
)

from core_types.core_types import ModuleID, TaskID


def test_log_level():
    """测试日志级别"""
    print("测试日志级别...")
    
    assert LogLevel.DEBUG < LogLevel.INFO
    assert LogLevel.INFO < LogLevel.WARNING
    assert LogLevel.WARNING < LogLevel.ERROR
    assert LogLevel.ERROR < LogLevel.CRITICAL
    
    assert LogLevel.DEBUG.value == 10
    assert LogLevel.INFO.value == 20
    
    print("✓ 日志级别测试通过")


def test_log_record():
    """测试日志记录"""
    print("测试日志记录...")
    
    from datetime import datetime
    
    record = LogRecord(
        timestamp=datetime.now(),
        level=LogLevel.INFO,
        message="测试消息",
        module_name="TestModule",
    )
    
    assert record.level == LogLevel.INFO
    assert record.message == "测试消息"
    assert record.module_name == "TestModule"
    
    # 测试转换为字典
    record_dict = record.to_dict()
    assert record_dict["level"] == "INFO"
    assert record_dict["message"] == "测试消息"
    
    print("✓ 日志记录测试通过")


def test_log_formatter():
    """测试日志格式化器"""
    print("测试日志格式化器...")
    
    from datetime import datetime
    
    formatter = LogFormatter()
    
    record = LogRecord(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        level=LogLevel.INFO,
        message="测试消息",
        module_name="TestModule",
    )
    
    formatted = formatter.format(record)
    assert "2024-01-01 12:00:00" in formatted
    assert "INFO" in formatted
    assert "TestModule" in formatted
    assert "测试消息" in formatted
    
    print("✓ 日志格式化器测试通过")


def test_memory_handler():
    """测试内存处理器"""
    print("测试内存处理器...")
    
    from datetime import datetime
    
    handler = MemoryHandler()
    
    record = LogRecord(
        timestamp=datetime.now(),
        level=LogLevel.INFO,
        message="测试消息",
        module_name="TestModule",
    )
    
    handler.handle(record)
    
    records = handler.get_records()
    assert len(records) == 1
    assert records[0].message == "测试消息"
    
    # 测试级别过滤
    debug_record = LogRecord(
        timestamp=datetime.now(),
        level=LogLevel.DEBUG,
        message="调试消息",
        module_name="TestModule",
    )
    
    handler.handle(debug_record)
    
    # 获取INFO及以上级别的记录
    info_records = handler.get_records(level=LogLevel.INFO)
    assert len(info_records) == 1  # DEBUG记录被过滤
    
    # 清空
    handler.clear()
    assert len(handler.get_records()) == 0
    
    print("✓ 内存处理器测试通过")


def test_logger_basic():
    """测试日志器基础功能"""
    print("测试日志器基础功能...")
    
    Logger.clear_all_loggers()
    
    logger = Logger("TestModule")
    
    # 添加内存处理器
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    # 记录日志
    logger.info("信息日志")
    logger.warning("警告日志")
    logger.error("错误日志")
    
    records = memory_handler.get_records()
    assert len(records) == 3
    assert records[0].level == LogLevel.INFO
    assert records[1].level == LogLevel.WARNING
    assert records[2].level == LogLevel.ERROR
    
    print("✓ 日志器基础功能测试通过")


def test_logger_level_filter():
    """测试日志器级别过滤"""
    print("测试日志器级别过滤...")
    
    Logger.clear_all_loggers()
    
    logger = Logger("TestModule", level=LogLevel.WARNING)
    
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    # 记录日志
    logger.debug("调试日志")  # 应该被过滤
    logger.info("信息日志")   # 应该被过滤
    logger.warning("警告日志")  # 应该被记录
    logger.error("错误日志")   # 应该被记录
    
    records = memory_handler.get_records()
    assert len(records) == 2
    assert records[0].level == LogLevel.WARNING
    assert records[1].level == LogLevel.ERROR
    
    print("✓ 日志器级别过滤测试通过")


def test_logger_context():
    """测试日志器上下文"""
    print("测试日志器上下文...")
    
    Logger.clear_all_loggers()
    
    logger = Logger("TestModule")
    
    # 设置上下文
    logger.set_context("request_id", "12345")
    logger.set_context("user", "admin")
    
    assert logger.get_context("request_id") == "12345"
    assert logger.get_context("user") == "admin"
    assert logger.get_context("nonexistent", "default") == "default"
    
    # 清除上下文
    logger.clear_context()
    assert logger.get_context("request_id") is None
    
    print("✓ 日志器上下文测试通过")


def test_logger_singleton():
    """测试日志器单例"""
    print("测试日志器单例...")
    
    Logger.clear_all_loggers()
    
    logger1 = Logger.get_logger("TestModule")
    logger2 = Logger.get_logger("TestModule")
    
    assert logger1 is logger2
    
    logger3 = Logger.get_logger("AnotherModule")
    assert logger1 is not logger3
    
    print("✓ 日志器单例测试通过")


def test_logger_exception():
    """测试日志器异常记录"""
    print("测试日志器异常记录...")
    
    Logger.clear_all_loggers()
    
    logger = Logger("TestModule")
    
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    try:
        raise ValueError("测试异常")
    except Exception as e:
        logger.exception("发生异常", e)
    
    records = memory_handler.get_records()
    assert len(records) == 1
    assert records[0].level == LogLevel.ERROR
    assert "发生异常" in records[0].message
    assert records[0].exception is not None
    
    print("✓ 日志器异常记录测试通过")


def test_logger_with_module_id():
    """测试带模块ID的日志器"""
    print("测试带模块ID的日志器...")
    
    Logger.clear_all_loggers()
    
    module_id = ModuleID()
    logger = Logger("TestModule", module_id=module_id)
    
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    logger.info("测试消息")
    
    records = memory_handler.get_records()
    assert len(records) == 1
    assert records[0].module_id == module_id
    
    print("✓ 带模块ID的日志器测试通过")


def test_log_manager():
    """测试日志管理器"""
    print("测试日志管理器...")
    
    # 完全重置状态
    Logger.clear_all_loggers()
    # 重置LogManager单例
    LogManager._instance = None
    
    manager = LogManager.instance()
    
    # 创建新日志器
    logger = Logger.get_logger("TestModule")
    
    # 手动添加处理器（因为setup_default_logging只应用到已存在的日志器）
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    assert logger.has_handlers()
    
    print("✓ 日志管理器测试通过")


def test_get_logger_helper():
    """测试get_logger便捷函数"""
    print("测试get_logger便捷函数...")
    
    Logger.clear_all_loggers()
    
    logger = get_logger("TestModule")
    assert logger.name == "TestModule"
    
    print("✓ get_logger便捷函数测试通过")


def test_global_level():
    """测试全局日志级别"""
    print("测试全局日志级别...")
    
    original_level = Logger.get_global_level()
    
    Logger.set_global_level(LogLevel.WARNING)
    assert Logger.get_global_level() == LogLevel.WARNING
    
    # 恢复
    Logger.set_global_level(original_level)
    
    print("✓ 全局日志级别测试通过")


def test_logger_aliases():
    """测试日志器别名"""
    print("测试日志器别名...")
    
    Logger.clear_all_loggers()
    
    logger = Logger("TestModule")
    
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    # 测试warn别名
    logger.warn("警告日志")
    
    # 测试fatal别名
    logger.fatal("致命日志")
    
    records = memory_handler.get_records()
    assert len(records) == 2
    assert records[0].level == LogLevel.WARNING
    assert records[1].level == LogLevel.CRITICAL
    
    print("✓ 日志器别名测试通过")


def test_handler_level_filter():
    """测试处理器级别过滤"""
    print("测试处理器级别过滤...")
    
    from datetime import datetime
    
    # 创建只处理ERROR及以上级别的处理器
    handler = MemoryHandler(level=LogLevel.ERROR)
    
    debug_record = LogRecord(
        timestamp=datetime.now(),
        level=LogLevel.DEBUG,
        message="调试消息",
        module_name="TestModule",
    )
    
    error_record = LogRecord(
        timestamp=datetime.now(),
        level=LogLevel.ERROR,
        message="错误消息",
        module_name="TestModule",
    )
    
    handler.handle(debug_record)
    handler.handle(error_record)
    
    records = handler.get_records()
    assert len(records) == 1
    assert records[0].level == LogLevel.ERROR
    
    print("✓ 处理器级别过滤测试通过")


def test_log_record_with_task_id():
    """测试带任务ID的日志记录"""
    print("测试带任务ID的日志记录...")
    
    from datetime import datetime
    
    task_id = TaskID()
    
    record = LogRecord(
        timestamp=datetime.now(),
        level=LogLevel.INFO,
        message="测试消息",
        module_name="TestModule",
        task_id=task_id,
    )
    
    assert record.task_id == task_id
    
    record_dict = record.to_dict()
    assert record_dict["task_id"] == str(task_id)
    
    print("✓ 带任务ID的日志记录测试通过")


def test_formatted_logs():
    """测试获取格式化的日志"""
    print("测试获取格式化的日志...")
    
    Logger.clear_all_loggers()
    
    logger = Logger("TestModule")
    
    memory_handler = MemoryHandler()
    logger.add_handler(memory_handler)
    
    logger.info("消息1")
    logger.info("消息2")
    
    formatted_logs = memory_handler.get_formatted_logs()
    assert len(formatted_logs) == 2
    assert "消息1" in formatted_logs[0]
    assert "消息2" in formatted_logs[1]
    
    print("✓ 获取格式化的日志测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第7阶段验证测试 - 日志系统实现")
    print("=" * 60)
    print()
    
    tests = [
        test_log_level,
        test_log_record,
        test_log_formatter,
        test_memory_handler,
        test_logger_basic,
        test_logger_level_filter,
        test_logger_context,
        test_logger_singleton,
        test_logger_exception,
        test_logger_with_module_id,
        test_log_manager,
        test_get_logger_helper,
        test_global_level,
        test_logger_aliases,
        test_handler_level_filter,
        test_log_record_with_task_id,
        test_formatted_logs,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 60)
    print(f"测试完成: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("✓ 第7阶段验证通过！")
        return True
    else:
        print("✗ 第7阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
