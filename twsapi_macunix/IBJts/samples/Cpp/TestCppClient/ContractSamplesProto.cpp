/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */
#include "StdAfx.h"

#include "ContractSamplesProto.h"

#if !defined(USE_WIN_DLL)
protobuf::Contract ContractSamplesProto::IBMStockAtSmart(){
    //! [IBM_stock_at_smart]
    protobuf::Contract contractProto;
    contractProto.set_symbol("IBM");
    contractProto.set_sectype("STK");
    contractProto.set_exchange("SMART");
    contractProto.set_currency("USD");
    //! [IBM_stock_at_smart]
    return contractProto;
}

protobuf::Contract ContractSamplesProto::MSFTStockAtSmart() {
    //! [MSFT_stock_at_smart]
    protobuf::Contract contractProto;
    contractProto.set_symbol("MSFT");
    contractProto.set_sectype("STK");
    contractProto.set_exchange("SMART");
    contractProto.set_currency("USD");
    //! [MSFT_stock_at_smart]
    return contractProto;
}
#endif
