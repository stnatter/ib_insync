/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

package samples.testbed.orders;

import com.ib.client.protobuf.ContractProto;
import com.ib.client.protobuf.OrderProto;
import com.ib.client.protobuf.PlaceOrderRequestProto;
import com.ib.client.Decimal;

public class OrderSamplesProto {

    public static PlaceOrderRequestProto.PlaceOrderRequest createPlaceOrderRequest(int orderId, ContractProto.Contract contractProto, OrderProto.Order orderProto) {
        // ! [place_order_request]
        PlaceOrderRequestProto.PlaceOrderRequest.Builder placeOrderRequestBuilder = PlaceOrderRequestProto.PlaceOrderRequest.newBuilder();
        placeOrderRequestBuilder.setOrderId(orderId);
        placeOrderRequestBuilder.setContract(contractProto);
        placeOrderRequestBuilder.setOrder(orderProto);
        // ! [place_order_request]
        return placeOrderRequestBuilder.build();
    }

    public static OrderProto.Order LimitOrder(String action, Decimal quantity, double limitPrice, boolean transmit) {
        // ! [limit_order]
        OrderProto.Order.Builder orderProtoBuilder = OrderProto.Order.newBuilder();
        orderProtoBuilder.setAction(action);
        orderProtoBuilder.setOrderType("LMT");
        orderProtoBuilder.setTotalQuantity(quantity.toString());
        orderProtoBuilder.setLmtPrice(limitPrice);
        orderProtoBuilder.setTif("DAY");
        orderProtoBuilder.setTransmit(transmit);
        // ! [limit_order]
        return orderProtoBuilder.build();
    }

    public static OrderProto.Order BetaHedgeOrder(int parentId, String action, String hedgeParam, int hedgeMaxSize, boolean transmit) {
        // ! [beta_hedge_order]
        OrderProto.Order.Builder orderProtoBuilder = OrderProto.Order.newBuilder();
        orderProtoBuilder.setParentId(parentId);
        orderProtoBuilder.setAction(action);
        orderProtoBuilder.setOrderType("MKT");
        orderProtoBuilder.setTif("DAY");
        orderProtoBuilder.setHedgeType("B");
        orderProtoBuilder.setHedgeParam(hedgeParam);
        orderProtoBuilder.setHedgeMaxSize(hedgeMaxSize);
        orderProtoBuilder.setTransmit(transmit);
        // ! [beta_hedge_order]
        return orderProtoBuilder.build();
    }
}
