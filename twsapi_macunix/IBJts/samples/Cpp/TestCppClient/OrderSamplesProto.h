/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

#pragma once
#ifndef TWS_API_SAMPLES_TESTCPPCLIENT_ORDERSAMPLESPROTO_H
#define TWS_API_SAMPLES_TESTCPPCLIENT_ORDERSAMPLESPROTO_H

#include "Contract.pb.h"
#include "Order.pb.h"
#include "PlaceOrderRequest.pb.h"

class OrderSamplesProto {
public:
#if !defined(USE_WIN_DLL)
    static protobuf::PlaceOrderRequest CreatePlaceOrderRequest(int orderId, protobuf::Contract contractProto, protobuf::Order orderProto);
    static protobuf::Order LimitOrder(std::string action, Decimal quantity, double price, bool transmit);
    static protobuf::Order BetaHedgeOrder(int parentId, std::string action, std::string hedgeParam, int hedgeMaxSize, bool transmit);
#endif
};

#endif
