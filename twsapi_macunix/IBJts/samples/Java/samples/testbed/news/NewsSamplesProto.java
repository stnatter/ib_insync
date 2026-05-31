/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

package samples.testbed.news;

import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Calendar;

import com.ib.client.protobuf.HistoricalNewsRequestProto;

public class NewsSamplesProto {

    public static HistoricalNewsRequestProto.HistoricalNewsRequest HistoricalNewsRequestWithEndTime(int reqId) {
        //! [historical_news_request_with_end_time]
        HistoricalNewsRequestProto.HistoricalNewsRequest.Builder historicalNewsRequestBuilder = HistoricalNewsRequestProto.HistoricalNewsRequest.newBuilder();
        historicalNewsRequestBuilder.setReqId(reqId);
        historicalNewsRequestBuilder.setConId(8314);
        historicalNewsRequestBuilder.setProviderCodes("BRFUPDN+BRFG");
        DateFormat df = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.0");
        Calendar cal = Calendar.getInstance();
        cal.add(Calendar.DATE, -10);
        historicalNewsRequestBuilder.setEndDateTime(df.format(cal.getTime()));
        historicalNewsRequestBuilder.setTotalResults(10);
        return historicalNewsRequestBuilder.build();
        //! [historical_news_request_with_end_time]
    }

    public static HistoricalNewsRequestProto.HistoricalNewsRequest HistoricalNewsRequestWithStartTime(int reqId) {
        //! [historical_news_request_with_start_time]
        HistoricalNewsRequestProto.HistoricalNewsRequest.Builder historicalNewsRequestBuilder = HistoricalNewsRequestProto.HistoricalNewsRequest.newBuilder();
        historicalNewsRequestBuilder.setReqId(reqId);
        historicalNewsRequestBuilder.setConId(8314);
        historicalNewsRequestBuilder.setProviderCodes("BRFUPDN+BRFG");
        DateFormat df = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.0");
        Calendar cal = Calendar.getInstance();
        cal.add(Calendar.DATE, -10);
        historicalNewsRequestBuilder.setStartDateTime(df.format(cal.getTime()));
        historicalNewsRequestBuilder.setTotalResults(10);
        return historicalNewsRequestBuilder.build();
        //! [historical_news_request_with_start_time]
    }
}