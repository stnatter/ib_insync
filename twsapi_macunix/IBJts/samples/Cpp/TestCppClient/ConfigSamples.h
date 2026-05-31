/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

#pragma once
#ifndef TWS_API_SAMPLES_TESTCPPCLIENT_CONFIGSAMPLES_H
#define TWS_API_SAMPLES_TESTCPPCLIENT_CONFIGAMPLES_H

#include "UpdateConfigRequest.pb.h"

class ConfigSamples {
public:
    static protobuf::UpdateConfigRequest UpdateConfigApiSettings(int reqId);
    static protobuf::UpdateConfigRequest UpdateOrdersConfig(int reqId);
    static protobuf::UpdateConfigRequest UpdateMessageConfigConfirmMandatoryCapPriceAccepted(int reqId);
    static protobuf::UpdateConfigRequest UpdateConfigOrderIdReset(int reqId);
};

#endif
