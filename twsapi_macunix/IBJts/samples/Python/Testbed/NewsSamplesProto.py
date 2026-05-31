"""
Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable.
"""

from ibapi.protobuf.HistoricalNewsRequest_pb2 import HistoricalNewsRequest as HistoricalNewsRequestProto
from datetime import datetime, timedelta

class NewsSamplesProto:

    @staticmethod
    def HistoricalNewsRequestWithEndTime(reqId: int) -> HistoricalNewsRequestProto:
        #! [historical_news_request_with_end_time]
        historicalNewsRequestProto = HistoricalNewsRequestProto()
        historicalNewsRequestProto.reqId = reqId
        historicalNewsRequestProto.conId = 8314
        historicalNewsRequestProto.providerCodes = "BRFUPDN+BRFG"
        date_10_days_ago = datetime.now() - timedelta(days=10)
        historicalNewsRequestProto.endDateTime = date_10_days_ago.strftime("%Y-%m-%d %H:%M:%S.0")
        historicalNewsRequestProto.totalResults = 10
        #! [historical_news_request_with_end_time]
        return historicalNewsRequestProto

    @staticmethod
    def HistoricalNewsRequestWithStartTime(reqId: int) -> HistoricalNewsRequestProto:
        #! [historical_news_request_with_start_time]
        historicalNewsRequestProto = HistoricalNewsRequestProto()
        historicalNewsRequestProto.reqId = reqId
        historicalNewsRequestProto.conId = 8314
        historicalNewsRequestProto.providerCodes = "BRFUPDN+BRFG"
        date_10_days_ago = datetime.now() - timedelta(days=10)
        historicalNewsRequestProto.startDateTime = date_10_days_ago.strftime("%Y-%m-%d %H:%M:%S.0")
        historicalNewsRequestProto.totalResults = 10
        #! [historical_news_request_with_start_time]
        return historicalNewsRequestProto

def Test():
    from ibapi.utils import ExerciseStaticMethods
    ExerciseStaticMethods(NewsSamplesProto)

if "__main__" == __name__:
    Test()

