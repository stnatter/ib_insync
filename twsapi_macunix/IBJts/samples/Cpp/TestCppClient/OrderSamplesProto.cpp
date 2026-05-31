/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */
#include "StdAfx.h"

#include "Decimal.h"
#include "OrderSamplesProto.h"

#if !defined(USE_WIN_DLL)
protobuf::PlaceOrderRequest OrderSamplesProto::CreatePlaceOrderRequest(int orderId, protobuf::Contract contractProto, protobuf::Order orderProto) {
    // ! [place_order_request]
    protobuf::PlaceOrderRequest placeOrderRequestProto;
    placeOrderRequestProto.set_orderid(orderId);
    placeOrderRequestProto.mutable_contract()->CopyFrom(contractProto);
    placeOrderRequestProto.mutable_order()->CopyFrom(orderProto);
    // ! [place_order_request]
    return placeOrderRequestProto;
}

protobuf::Order OrderSamplesProto::LimitOrder(std::string action, Decimal quantity, double limitPrice, bool transmit) {
    //! [limit_order]
    protobuf::Order orderProto;
    orderProto.set_action(action);
    orderProto.set_ordertype("LMT");
    orderProto.set_totalquantity(DecimalFunctions::decimalStringToDisplay(quantity));
    orderProto.set_lmtprice(limitPrice);
    orderProto.set_tif("DAY");
    orderProto.set_transmit(transmit);
    //! [limit_order]
    return orderProto;
}

protobuf::Order OrderSamplesProto::BetaHedgeOrder(int parentId, std::string action, std::string hedgeParam, int hedgeMaxSize, bool transmit) {
    //! [beta_hedge_order]
    protobuf::Order orderProto;
    orderProto.set_parentid(parentId);
    orderProto.set_action(action);
    orderProto.set_ordertype("MKT");
    orderProto.set_tif("DAY");
    orderProto.set_hedgetype("B");
    orderProto.set_hedgeparam(hedgeParam);
    orderProto.set_hedgemaxsize(hedgeMaxSize);
    orderProto.set_transmit(transmit);
    //! [beta_hedge_order]
    return orderProto;
}
#endif
