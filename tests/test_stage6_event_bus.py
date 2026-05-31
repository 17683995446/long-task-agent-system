"""
第6阶段验证测试
验证事件总线的完整性和正确性
"""

import sys
sys.path.insert(0, '/workspace')

from core.event_bus import (
    EventBusError,
    EventTypeNotFoundError,
    SubscriberNotFoundError,
    EventDeliveryError,
    SubscriberInfo,
    EventDeliveryRecord,
    EventBusConfig,
    EventBus,
    ModuleEventHelper,
)

from core_types.core_types import (
    ModuleID, TaskID,
    ModuleState,
    ModuleEvent, ModuleEventType,
)


def setup_event_bus():
    """创建并初始化一个测试用的事件总线"""
    EventBus.reset()
    return EventBus.instance()


def test_singleton():
    """测试单例模式"""
    print("测试单例模式...")
    
    EventBus.reset()
    bus1 = EventBus.instance()
    bus2 = EventBus.instance()
    
    assert bus1 is bus2
    
    EventBus.reset()
    bus3 = EventBus.instance()
    assert bus1 is not bus3
    
    print("✓ 单例模式测试通过")


def test_subscribe_and_publish():
    """测试订阅和发布"""
    print("测试订阅和发布...")
    
    bus = setup_event_bus()
    
    received_events = []
    
    def handler(event):
        received_events.append(event)
    
    # 订阅
    subscriber_id = bus.subscribe(
        handler,
        [ModuleEventType.INIT_STARTED, ModuleEventType.INIT_COMPLETED],
    )
    
    assert subscriber_id is not None
    assert bus.get_subscriber_count() == 1
    
    # 发布事件
    module_id = ModuleID()
    event = ModuleEvent(
        event_type=ModuleEventType.INIT_STARTED,
        module_id=module_id,
    )
    
    delivered = bus.publish(event)
    assert delivered == 1
    assert len(received_events) == 1
    assert received_events[0].event_type == ModuleEventType.INIT_STARTED
    
    print("✓ 订阅和发布测试通过")


def test_unsubscribe():
    """测试取消订阅"""
    print("测试取消订阅...")
    
    bus = setup_event_bus()
    
    def handler(event):
        pass
    
    subscriber_id = bus.subscribe(handler, [ModuleEventType.RUN_STARTED])
    assert bus.get_subscriber_count() == 1
    
    # 取消订阅
    result = bus.unsubscribe(subscriber_id)
    assert result == True
    assert bus.get_subscriber_count() == 0
    
    # 再次取消应该失败
    result = bus.unsubscribe(subscriber_id)
    assert result == False
    
    print("✓ 取消订阅测试通过")


def test_priority():
    """测试优先级"""
    print("测试优先级...")
    
    bus = setup_event_bus()
    
    execution_order = []
    
    def high_priority_handler(event):
        execution_order.append("high")
    
    def low_priority_handler(event):
        execution_order.append("low")
    
    # 先订阅低优先级
    bus.subscribe(low_priority_handler, [ModuleEventType.RUN_STARTED], priority=1)
    # 再订阅高优先级
    bus.subscribe(high_priority_handler, [ModuleEventType.RUN_STARTED], priority=10)
    
    event = ModuleEvent(
        event_type=ModuleEventType.RUN_STARTED,
        module_id=ModuleID(),
    )
    
    bus.publish(event)
    
    # 高优先级应该先执行
    assert execution_order == ["high", "low"]
    
    print("✓ 优先级测试通过")


def test_subscribe_once():
    """测试一次性订阅"""
    print("测试一次性订阅...")
    
    bus = setup_event_bus()
    
    call_count = 0
    
    def handler(event):
        nonlocal call_count
        call_count += 1
    
    bus.subscribe_once(handler, [ModuleEventType.RUN_COMPLETED])
    
    event = ModuleEvent(
        event_type=ModuleEventType.RUN_COMPLETED,
        module_id=ModuleID(),
    )
    
    # 第一次发布
    bus.publish(event)
    assert call_count == 1
    assert bus.get_subscriber_count() == 0  # 已自动取消订阅
    
    # 第二次发布
    bus.publish(event)
    assert call_count == 1  # 不再被调用
    
    print("✓ 一次性订阅测试通过")


def test_event_history():
    """测试事件历史"""
    print("测试事件历史...")
    
    bus = setup_event_bus()
    
    def handler(event):
        pass
    
    bus.subscribe(handler, [ModuleEventType.RUN_STARTED])
    
    # 发布多个事件
    for i in range(5):
        event = ModuleEvent(
            event_type=ModuleEventType.RUN_STARTED,
            module_id=ModuleID(),
            data={"index": i},
        )
        bus.publish(event)
    
    # 获取历史
    history = bus.get_event_history()
    assert len(history) == 5
    
    # 获取限制数量的历史
    limited_history = bus.get_event_history(limit=3)
    assert len(limited_history) == 3
    
    # 清除历史
    bus.clear_history()
    history = bus.get_event_history()
    assert len(history) == 0
    
    print("✓ 事件历史测试通过")


def test_get_subscribers():
    """测试获取订阅者"""
    print("测试获取订阅者...")
    
    bus = setup_event_bus()
    
    def handler1(event):
        pass
    
    def handler2(event):
        pass
    
    bus.subscribe(handler1, [ModuleEventType.RUN_STARTED])
    bus.subscribe(handler2, [ModuleEventType.RUN_STARTED])
    
    subscribers = bus.get_subscribers(ModuleEventType.RUN_STARTED)
    assert len(subscribers) == 2
    
    # 没有订阅者的事件类型
    no_subscribers = bus.get_subscribers(ModuleEventType.ERROR_OCCURRED)
    assert len(no_subscribers) == 0
    
    print("✓ 获取订阅者测试通过")


def test_statistics():
    """测试统计信息"""
    print("测试统计信息...")
    
    bus = setup_event_bus()
    
    def handler(event):
        pass
    
    bus.subscribe(handler, [ModuleEventType.RUN_STARTED])
    bus.subscribe(handler, [ModuleEventType.RUN_COMPLETED])
    
    stats = bus.get_statistics()
    assert stats["total_subscribers"] == 2
    assert stats["async_mode"] == False
    
    print("✓ 统计信息测试通过")


def test_unsubscribe_all():
    """测试取消所有订阅"""
    print("测试取消所有订阅...")
    
    bus = setup_event_bus()
    
    def handler(event):
        pass
    
    # 同一个回调订阅多个事件类型
    bus.subscribe(handler, [ModuleEventType.RUN_STARTED])
    bus.subscribe(handler, [ModuleEventType.RUN_COMPLETED])
    bus.subscribe(handler, [ModuleEventType.INIT_STARTED])
    
    assert bus.get_subscriber_count() == 3
    
    # 取消所有与该回调关联的订阅
    count = bus.unsubscribe_all(handler)
    assert count == 3
    assert bus.get_subscriber_count() == 0
    
    print("✓ 取消所有订阅测试通过")


def test_module_event_helper():
    """测试模块事件助手"""
    print("测试模块事件助手...")
    
    bus = setup_event_bus()
    helper = ModuleEventHelper(bus)
    
    received_events = []
    
    def handler(event):
        received_events.append(event)
    
    bus.subscribe(handler, [
        ModuleEventType.INIT_STARTED,
        ModuleEventType.INIT_COMPLETED,
        ModuleEventType.RUN_STARTED,
        ModuleEventType.RUN_COMPLETED,
    ])
    
    module_id = ModuleID()
    
    # 发射各种事件
    helper.emit_init_started(module_id)
    helper.emit_init_completed(module_id)
    helper.emit_run_started(module_id)
    helper.emit_run_completed(module_id, 100)
    
    assert len(received_events) == 4
    assert received_events[0].event_type == ModuleEventType.INIT_STARTED
    assert received_events[1].event_type == ModuleEventType.INIT_COMPLETED
    assert received_events[2].event_type == ModuleEventType.RUN_STARTED
    assert received_events[3].event_type == ModuleEventType.RUN_COMPLETED
    assert received_events[3].data["execution_time_ms"] == 100
    
    print("✓ 模块事件助手测试通过")


def test_emit_init_failed():
    """测试发射初始化失败事件"""
    print("测试发射初始化失败事件...")
    
    bus = setup_event_bus()
    helper = ModuleEventHelper(bus)
    
    received_events = []
    
    def handler(event):
        received_events.append(event)
    
    bus.subscribe(handler, [ModuleEventType.INIT_FAILED])
    
    module_id = ModuleID()
    helper.emit_init_failed(module_id, "ERR_001", "初始化失败")
    
    assert len(received_events) == 1
    assert received_events[0].data["error_code"] == "ERR_001"
    assert received_events[0].data["error_detail"] == "初始化失败"
    
    print("✓ 发射初始化失败事件测试通过")


def test_emit_state_changed():
    """测试发射状态变更事件"""
    print("测试发射状态变更事件...")
    
    bus = setup_event_bus()
    helper = ModuleEventHelper(bus)
    
    received_events = []
    
    def handler(event):
        received_events.append(event)
    
    bus.subscribe(handler, [ModuleEventType.STATE_CHANGED])
    
    module_id = ModuleID()
    helper.emit_state_changed(module_id, ModuleState.UNINITIALIZED, ModuleState.READY)
    
    assert len(received_events) == 1
    assert received_events[0].data["old_state"] == "UNINITIALIZED"
    assert received_events[0].data["new_state"] == "READY"
    
    print("✓ 发射状态变更事件测试通过")


def test_no_subscribers():
    """测试无订阅者"""
    print("测试无订阅者...")
    
    bus = setup_event_bus()
    
    event = ModuleEvent(
        event_type=ModuleEventType.ERROR_OCCURRED,
        module_id=ModuleID(),
    )
    
    delivered = bus.publish(event)
    assert delivered == 0
    
    print("✓ 无订阅者测试通过")


def test_multiple_event_types():
    """测试多个事件类型"""
    print("测试多个事件类型...")
    
    bus = setup_event_bus()
    
    received_events = []
    
    def handler(event):
        received_events.append(event.event_type)
    
    # 订阅多个事件类型
    bus.subscribe(handler, [
        ModuleEventType.INIT_STARTED,
        ModuleEventType.INIT_COMPLETED,
        ModuleEventType.RUN_STARTED,
    ])
    
    # 发布不同类型的事件
    bus.publish(ModuleEvent(event_type=ModuleEventType.INIT_STARTED, module_id=ModuleID()))
    bus.publish(ModuleEvent(event_type=ModuleEventType.INIT_COMPLETED, module_id=ModuleID()))
    bus.publish(ModuleEvent(event_type=ModuleEventType.RUN_STARTED, module_id=ModuleID()))
    bus.publish(ModuleEvent(event_type=ModuleEventType.RUN_COMPLETED, module_id=ModuleID()))  # 未订阅
    
    assert len(received_events) == 3
    assert ModuleEventType.RUN_COMPLETED not in received_events
    
    print("✓ 多个事件类型测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第6阶段验证测试 - 事件总线实现")
    print("=" * 60)
    print()
    
    tests = [
        test_singleton,
        test_subscribe_and_publish,
        test_unsubscribe,
        test_priority,
        test_subscribe_once,
        test_event_history,
        test_get_subscribers,
        test_statistics,
        test_unsubscribe_all,
        test_module_event_helper,
        test_emit_init_failed,
        test_emit_state_changed,
        test_no_subscribers,
        test_multiple_event_types,
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
        print("✓ 第6阶段验证通过！")
        return True
    else:
        print("✗ 第6阶段验证失败！")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
