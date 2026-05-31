/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

package samples.testbed.contracts;

import com.ib.client.protobuf.ContractProto;

public class ContractSamplesProto {

    public static ContractProto.Contract IBMStockAtSmart() {
        //! [IBM_stock_at_smart]
        ContractProto.Contract.Builder contractProtoBuilder = ContractProto.Contract.newBuilder();
        contractProtoBuilder.setSymbol("IBM");
        contractProtoBuilder.setSecType("STK");
        contractProtoBuilder.setExchange("SMART");
        contractProtoBuilder.setCurrency("USD");
        //! [IBM_stock_at_smart]
        return contractProtoBuilder.build();
    }

    public static ContractProto.Contract MSFTStockAtSmart() {
        //! [MSFT_stock_at_smart]
        ContractProto.Contract.Builder contractProtoBuilder = ContractProto.Contract.newBuilder();
        contractProtoBuilder.setSymbol("MSFT");
        contractProtoBuilder.setSecType("STK");
        contractProtoBuilder.setExchange("SMART");
        contractProtoBuilder.setCurrency("USD");
        //! [MSFT_stock_at_smart]
        return contractProtoBuilder.build();
    }
}