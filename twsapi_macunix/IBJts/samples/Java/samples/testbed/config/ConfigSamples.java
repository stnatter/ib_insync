/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

package samples.testbed.config;

import com.ib.client.protobuf.ApiConfigProto;
import com.ib.client.protobuf.ApiSettingsConfigProto;
import com.ib.client.protobuf.MessageConfigProto;
import com.ib.client.protobuf.OrdersConfigProto;
import com.ib.client.protobuf.OrdersSmartRoutingConfigProto;
import com.ib.client.protobuf.UpdateConfigRequestProto;
import com.ib.client.protobuf.UpdateConfigWarningProto;

public class ConfigSamples {

    public static UpdateConfigRequestProto.UpdateConfigRequest UpdateConfigApiSettings(int reqId) {
        //! [UpdateApiSettingsConfig]
        UpdateConfigRequestProto.UpdateConfigRequest.Builder updateConfigRequestBuilder = UpdateConfigRequestProto.UpdateConfigRequest.newBuilder();
        ApiConfigProto.ApiConfig.Builder apiConfigBuilder = ApiConfigProto.ApiConfig.newBuilder();

        ApiSettingsConfigProto.ApiSettingsConfig.Builder apiSettingsConfigBuilder = ApiSettingsConfigProto.ApiSettingsConfig.newBuilder();
        apiSettingsConfigBuilder.setTotalQuantityForMutualFunds(true);
        apiSettingsConfigBuilder.setDownloadOpenOrdersOnConnection(true);
        apiSettingsConfigBuilder.setIncludeVirtualFxPositions(true);
        apiSettingsConfigBuilder.setPrepareDailyPnL(true);
        apiSettingsConfigBuilder.setSendStatusUpdatesForVolatilityOrders(true);
        apiSettingsConfigBuilder.setEncodeApiMessages("osCodePage");
        apiSettingsConfigBuilder.setSocketPort(7497);
        apiSettingsConfigBuilder.setUseNegativeAutoRange(true);
        apiSettingsConfigBuilder.setCreateApiMessageLogFile(true);
        apiSettingsConfigBuilder.setIncludeMarketDataInLogFile(true);
        apiSettingsConfigBuilder.setExposeTradingScheduleToApi(true);
        apiSettingsConfigBuilder.setSplitInsuredDepositFromCashBalance(true);
        apiSettingsConfigBuilder.setSendZeroPositionsForTodayOnly(true);
        apiSettingsConfigBuilder.setUseAccountGroupsWithAllocationMethods(true);
        apiSettingsConfigBuilder.setLoggingLevel("error");
        apiSettingsConfigBuilder.setMasterClientId(3);
        apiSettingsConfigBuilder.setBulkDataTimeout(25);
        apiSettingsConfigBuilder.setComponentExchSeparator("#");
        apiSettingsConfigBuilder.setRoundAccountValuesToNearestWholeNumber(true);
        apiSettingsConfigBuilder.setShowAdvancedOrderRejectInUi(true);
        apiSettingsConfigBuilder.setRejectMessagesAboveMaxRate(true);
        apiSettingsConfigBuilder.setMaintainConnectionOnIncorrectFields(true);
        apiSettingsConfigBuilder.setCompatibilityModeNasdaqStocks(true);
        apiSettingsConfigBuilder.setSendInstrumentTimezone("utc");
        apiSettingsConfigBuilder.setSendForexDataInCompatibilityMode(true);
        apiSettingsConfigBuilder.setMaintainAndResubmitOrdersOnReconnect(true);
        apiSettingsConfigBuilder.setHistoricalDataMaxSize(4);
        apiSettingsConfigBuilder.setAutoReportNettingEventContractTrades(true);
        apiSettingsConfigBuilder.setOptionExerciseRequestType("final");
        apiSettingsConfigBuilder.addTrustedIPs("127.0.0.1");
        
        apiConfigBuilder.setSettings(apiSettingsConfigBuilder.build());
        updateConfigRequestBuilder.setReqId(reqId);
        updateConfigRequestBuilder.setApi(apiConfigBuilder.build());

        return updateConfigRequestBuilder.build();
        //! [UpdateApiSettingsConfig]
    }

    public static UpdateConfigRequestProto.UpdateConfigRequest UpdateOrdersConfig(int reqId) {
        //! [UpdateOrderConfig]
        UpdateConfigRequestProto.UpdateConfigRequest.Builder updateConfigRequestBuilder = UpdateConfigRequestProto.UpdateConfigRequest.newBuilder();
        OrdersConfigProto.OrdersConfig.Builder ordersConfigBuilder = OrdersConfigProto.OrdersConfig.newBuilder();
        OrdersSmartRoutingConfigProto.OrdersSmartRoutingConfig.Builder ordersSmartRoutingConfigBuilder = OrdersSmartRoutingConfigProto.OrdersSmartRoutingConfig.newBuilder();
        ordersSmartRoutingConfigBuilder.setSeekPriceImprovement(true);
        ordersSmartRoutingConfigBuilder.setDoNotRouteToDarkPools(true);
        ordersConfigBuilder.setSmartRouting(ordersSmartRoutingConfigBuilder.build());
        updateConfigRequestBuilder.setReqId(reqId);
        updateConfigRequestBuilder.setOrders(ordersConfigBuilder.build());
        return updateConfigRequestBuilder.build();
        //! [UpdateOrderConfig]
    }

    public static UpdateConfigRequestProto.UpdateConfigRequest UpdateMessageConfigConfirmMandatoryCapPriceAccepted(int reqId) {
        //! [UpdateMessageConfigConfirmMandatoryCapPriceAccepted]
        UpdateConfigRequestProto.UpdateConfigRequest.Builder updateConfigRequestBuilder = UpdateConfigRequestProto.UpdateConfigRequest.newBuilder();

        MessageConfigProto.MessageConfig.Builder messageConfigBuilder = MessageConfigProto.MessageConfig.newBuilder();
        messageConfigBuilder.setId(131);
        messageConfigBuilder.setEnabled(false);
        updateConfigRequestBuilder.setReqId(reqId);
        updateConfigRequestBuilder.addMessages(messageConfigBuilder.build());

        UpdateConfigWarningProto.UpdateConfigWarning.Builder updateConfigWarningBuilder = UpdateConfigWarningProto.UpdateConfigWarning.newBuilder();
        updateConfigWarningBuilder.setMessageId(131);
        updateConfigRequestBuilder.addAcceptedWarnings(updateConfigWarningBuilder.build());

        return updateConfigRequestBuilder.build();
        //! [UpdateMessageConfigConfirmMandatoryCapPriceAccepted]
    }

    public static UpdateConfigRequestProto.UpdateConfigRequest UpdateConfigOrderIdReset(int reqId) {
        //! [ UpdateConfigOrderIdReset]
        UpdateConfigRequestProto.UpdateConfigRequest.Builder updateConfigRequestBuilder = UpdateConfigRequestProto.UpdateConfigRequest.newBuilder();
        updateConfigRequestBuilder.setReqId(reqId);
        updateConfigRequestBuilder.setResetAPIOrderSequence(true);
        return updateConfigRequestBuilder.build();
        //! [ UpdateConfigOrderIdReset]
    }

}