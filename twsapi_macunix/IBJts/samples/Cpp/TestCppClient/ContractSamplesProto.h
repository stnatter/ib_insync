/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */
#pragma once
#ifndef TWS_API_SAMPLES_TESTCPPCLIENT_CONTRACTSAMPLESPROTO_H
#define TWS_API_SAMPLES_TESTCPPCLIENT_CONTRACTSAMPLESPROTO_H

#include "Contract.pb.h"

class ContractSamplesProto {
public:
#if !defined(USE_WIN_DLL)
    static protobuf::Contract IBMStockAtSmart();
    static protobuf::Contract MSFTStockAtSmart();
#endif
};

#endif
