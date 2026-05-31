"""
Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable.
"""


from ibapi.protobuf.Contract_pb2 import Contract as ContractProto
from ibapi.protobuf.Order_pb2 import Order as OrderProto
from ibapi.protobuf.PlaceOrderRequest_pb2 import PlaceOrderRequest as PlaceOrderRequestProto
from decimal import Decimal

class OrderSamplesProto:

    @staticmethod
    def createPlaceOrderRequest(orderId:int, contractProto:ContractProto, orderProto:OrderProto) -> PlaceOrderRequestProto:
        # ! [place_order_request]
        placeOrderRequestProto = PlaceOrderRequestProto()
        placeOrderRequestProto.orderId = orderId
        placeOrderRequestProto.contract.CopyFrom(contractProto)
        placeOrderRequestProto.order.CopyFrom(orderProto)
        # ! [place_order_request]
        return placeOrderRequestProto

    @staticmethod
    def LimitOrder(action:str, quantity:Decimal, limitPrice:float, transmit: bool) -> OrderProto:
        #! [limit_order]
        order = OrderProto()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = str(quantity)
        order.lmtPrice = limitPrice
        order.tif = "DAY"
        order.transmit = transmit
        #! [limit_order]
        return order

    @staticmethod
    def BetaHedgeOrder(parentId: int, action:str, hedgeParam: str, hedgeMaxSize: int, transmit: bool) -> OrderProto:
        #! [beta_hedge_order]
        order = OrderProto()
        order.parentId = parentId
        order.action = action
        order.orderType = "MKT"
        order.tif = "DAY"
        order.hedgeType  = "B"
        order.hedgeParam = hedgeParam
        order.hedgeMaxSize = hedgeMaxSize

        order.transmit = transmit
        #! [beta_hedge_order]
        return order

def Test():
    from ibapi.utils import ExerciseStaticMethods
    ExerciseStaticMethods(OrderSamplesProto)

if "__main__" == __name__:
    Test()

