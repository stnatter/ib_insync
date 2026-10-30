from datetime import UTC, datetime
from unittest.mock import MagicMock

from ib_insync.objects import TradeLogEntry
from ib_insync.order import OrderStatus, Trade
from ib_insync.ticker import Ticker
from ib_insync.wrapper import Wrapper


def test_tickOptionComputation_sentinels_to_none():
    wrapper = Wrapper(None)
    ticker = Ticker()
    wrapper.reqId2Ticker[1] = ticker
    wrapper.tickOptionComputation(
        1, 10, 0, -1, -2, -1, -1, -2, -2, -2, -1)
    comp = ticker.bidGreeks
    assert comp.impliedVol is None
    assert comp.delta is None
    assert comp.optPrice is None
    assert comp.pvDividend is None
    assert comp.gamma is None
    assert comp.vega is None
    assert comp.theta is None
    assert comp.undPrice is None


def test_tickOptionComputation_values():
    wrapper = Wrapper(None)
    ticker = Ticker()
    wrapper.reqId2Ticker[1] = ticker
    wrapper.tickOptionComputation(
        1, 10, 0, 0.5, 0.4, 10.0, 0.1, 0.2, 0.3, 0.6, 100.0)
    comp = ticker.bidGreeks
    assert comp.impliedVol == 0.5
    assert comp.vega == 0.3
    assert comp.theta == 0.6
    assert ticker in wrapper.pendingTickers


# --- modifyVerdictEvent (order modification ack/rejection) ------------------


def _wrapper_with_modified_trade():
    wrapper = Wrapper(MagicMock())
    wrapper.clientId = 0
    trade = Trade()
    trade.orderStatus.orderId = 42
    trade.orderStatus.status = OrderStatus.Submitted
    trade.orderStatus.filled = 0.0
    trade.orderStatus.remaining = 100.0
    trade.orderStatus.avgFillPrice = 0.0
    trade.orderStatus.permId = 456
    trade.orderStatus.parentId = 0
    trade.orderStatus.lastFillPrice = 0.0
    trade.orderStatus.clientId = 0
    trade.orderStatus.whyHeld = ''
    trade.orderStatus.mktCapPrice = 0.0
    trade.log.append(
        TradeLogEntry(datetime.now(UTC), OrderStatus.Submitted, 'Modify'))
    wrapper.trades[wrapper.orderKey(0, 42, 456)] = trade
    return wrapper, trade


def _verdicts(trade):
    emitted = []
    trade.modifyVerdictEvent.connect(lambda *a: emitted.append(a))
    return emitted


def test_modifyVerdict_ack_on_status_refresh():
    """An orderStatus refresh after a modify emits an 'ack' verdict."""
    wrapper, trade = _wrapper_with_modified_trade()
    emitted = _verdicts(trade)

    wrapper.orderStatus(42, 'Submitted', 0.0, 100.0, 0.0, 456, 0, 0.0, 0,
                        '', 0.0)

    assert emitted == [(trade, 'ack', 0, '')]
    assert trade.orderStatus.status == OrderStatus.Submitted


def test_modifyVerdict_ack_on_status_change():
    """A status change right after a modify also emits an 'ack' verdict."""
    wrapper, trade = _wrapper_with_modified_trade()
    emitted = _verdicts(trade)

    wrapper.orderStatus(42, 'Submitted', 50.0, 50.0, 10.0, 456, 0, 10.0, 0,
                        '', 0.0)

    assert emitted == [(trade, 'ack', 0, '')]
    assert trade.orderStatus.filled == 50.0


def test_modifyVerdict_reject_on_error_202():
    """Error 202 on a just-modified order emits a 'rej' verdict."""
    wrapper, trade = _wrapper_with_modified_trade()
    emitted = _verdicts(trade)

    wrapper.error(42, 202, 'Order Canceled - reason: test', '')

    assert emitted == [(trade, 'rej', 202, 'Order Canceled - reason: test')]
    # Rejection must not touch the live order (warning path).
    assert trade.orderStatus.status == OrderStatus.Submitted


def test_modifyVerdict_reject_on_error_399():
    wrapper, trade = _wrapper_with_modified_trade()
    emitted = _verdicts(trade)

    wrapper.error(42, 399, 'Order message rejected - reason: test', '')

    assert emitted == [(trade, 'rej', 399, 'Order message rejected - reason: test')]
    assert trade.orderStatus.status == OrderStatus.Submitted


def test_modifyVerdict_no_reject_without_modify():
    """A 202 for an order whose last action was not a modify emits nothing."""
    wrapper, trade = _wrapper_with_modified_trade()
    trade.log[-1].message = 'Submitted'
    emitted = _verdicts(trade)

    wrapper.error(42, 202, 'Order Canceled - reason: test', '')

    assert emitted == []


def test_modifyVerdict_no_event_for_unknown_order():
    """An error with no matching trade must not raise or emit."""
    wrapper, trade = _wrapper_with_modified_trade()
    emitted = _verdicts(trade)

    wrapper.error(99, 202, 'Order Canceled - reason: test', '')

    assert emitted == []
