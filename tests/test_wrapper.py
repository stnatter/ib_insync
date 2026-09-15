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
