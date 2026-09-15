from ib_insync.client import Client
from ib_insync.contract import ComboLeg, Contract
from ib_insync.decoder import _contract_from_proto, _order_from_proto
from ib_insync.order import Order
from ib_insync.util import UNSET_DOUBLE


def test_contract_roundtrip():
    contract = Contract(
        conId=265598, symbol='AAPL', secType='STK', exchange='SMART',
        primaryExchange='NASDAQ', currency='USD')
    proto = Client._contractToProto(contract)
    assert proto.conId == 265598
    assert proto.symbol == 'AAPL'
    assert proto.primaryExch == 'NASDAQ'
    decoded = _contract_from_proto(proto)
    assert decoded.conId == contract.conId
    assert decoded.symbol == contract.symbol
    assert decoded.primaryExchange == contract.primaryExchange
    assert decoded.currency == contract.currency


def test_contract_combo_legs_roundtrip():
    contract = Contract(symbol='EUR', secType='BAG', currency='USD')
    contract.comboLegs = [
        ComboLeg(conId=1, ratio=2, action='BUY', exchange='SMART')]
    decoded = _contract_from_proto(Client._contractToProto(contract))
    assert decoded.comboLegs[0].conId == 1
    assert decoded.comboLegs[0].ratio == 2
    assert decoded.comboLegs[0].action == 'BUY'


def test_order_roundtrip():
    order = Order(
        orderId=7, action='BUY', totalQuantity=10.0, orderType='LMT',
        lmtPrice=100.5)
    proto = Client._orderToProto(order)
    assert proto.totalQuantity == '10.0'
    decoded = _order_from_proto(proto)
    assert decoded.orderId == 7
    assert decoded.action == 'BUY'
    assert decoded.totalQuantity == 10.0
    assert decoded.lmtPrice == 100.5


def test_order_unset_prices():
    decoded = _order_from_proto(
        Client._orderToProto(Order(orderId=1, action='BUY', totalQuantity=1)))
    assert decoded.lmtPrice == UNSET_DOUBLE
    assert decoded.auxPrice == UNSET_DOUBLE
