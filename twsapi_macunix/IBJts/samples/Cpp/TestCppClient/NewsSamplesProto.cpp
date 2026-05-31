/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

#include "StdAfx.h"

#include "NewsSamplesProto.h"

#if !defined(USE_WIN_DLL)

protobuf::HistoricalNewsRequest NewsSamplesProto::HistoricalNewsRequestWithEndTime(int reqId){
    //! [historical_news_request_with_end_time]
    protobuf::HistoricalNewsRequest historicalNewsRequestProto;
    historicalNewsRequestProto.set_reqid(reqId);
    historicalNewsRequestProto.set_conid(8314);
    historicalNewsRequestProto.set_providercodes("BRFUPDN+BRFG");
    time_t now = time(nullptr);
    now -= 10 * 24 * 60 * 60; // subtract 10 days in seconds
    struct tm timeinfo;
#if defined(IB_WIN32)
    localtime_s(&timeinfo, &now);
#else
    localtime_r(&now, &timeinfo);
#endif
    char buffer[80];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);
    historicalNewsRequestProto.set_enddatetime(std::string(buffer) + ".0");
    historicalNewsRequestProto.set_totalresults(10);
    //! [historical_news_request_with_end_time]
    return historicalNewsRequestProto;
}

protobuf::HistoricalNewsRequest NewsSamplesProto::HistoricalNewsRequestWithStartTime(int reqId){
    //! [historical_news_request_with_start_time]
    protobuf::HistoricalNewsRequest historicalNewsRequestProto;
    historicalNewsRequestProto.set_reqid(reqId);
    historicalNewsRequestProto.set_conid(8314);
    historicalNewsRequestProto.set_providercodes("BRFUPDN+BRFG");
    time_t now = time(nullptr);
    now -= 10 * 24 * 60 * 60; // subtract 10 days in seconds
    struct tm timeinfo;
#if defined(IB_WIN32)
    localtime_s(&timeinfo, &now);
#else
    localtime_r(&now, &timeinfo);
#endif
    char buffer[80];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);
    historicalNewsRequestProto.set_startdatetime(std::string(buffer) + ".0");
    historicalNewsRequestProto.set_totalresults(10);
    //! [historical_news_request_with_start_time]
    return historicalNewsRequestProto;
}

#endif
