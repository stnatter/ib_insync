/* Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */
#include "StdAfx.h"

#include "ConfigSamples.h"

protobuf::UpdateConfigRequest ConfigSamples::UpdateConfigApiSettings(int reqId)
{
    //! [UpdateApiSettingsConfig]
    protobuf::UpdateConfigRequest updateConfigRequestProto;
    protobuf::ApiConfig apiConfigProto;
    protobuf::ApiSettingsConfig apiSettingsConfigProto;

    apiSettingsConfigProto.set_totalquantityformutualfunds(true);
    apiSettingsConfigProto.set_downloadopenordersonconnection(true);
    apiSettingsConfigProto.set_includevirtualfxpositions(true);
    apiSettingsConfigProto.set_preparedailypnl(true);
    apiSettingsConfigProto.set_sendstatusupdatesforvolatilityorders(true);
    apiSettingsConfigProto.set_encodeapimessages("osCodePage");
    apiSettingsConfigProto.set_socketport(7497);
    apiSettingsConfigProto.set_usenegativeautorange(true);
    apiSettingsConfigProto.set_createapimessagelogfile(true);
    apiSettingsConfigProto.set_includemarketdatainlogfile(true);
    apiSettingsConfigProto.set_exposetradingscheduletoapi(true);
    apiSettingsConfigProto.set_splitinsureddepositfromcashbalance(true);
    apiSettingsConfigProto.set_sendzeropositionsfortodayonly(true);
    apiSettingsConfigProto.set_useaccountgroupswithallocationmethods(true);
    apiSettingsConfigProto.set_logginglevel("error");
    apiSettingsConfigProto.set_masterclientid(3);
    apiSettingsConfigProto.set_bulkdatatimeout(25);
    apiSettingsConfigProto.set_componentexchseparator("#");
    apiSettingsConfigProto.set_roundaccountvaluestonearestwholenumber(true);
    apiSettingsConfigProto.set_showadvancedorderrejectinui(true);
    apiSettingsConfigProto.set_rejectmessagesabovemaxrate(true);
    apiSettingsConfigProto.set_maintainconnectiononincorrectfields(true);
    apiSettingsConfigProto.set_compatibilitymodenasdaqstocks(true);
    apiSettingsConfigProto.set_sendinstrumenttimezone("utc");
    apiSettingsConfigProto.set_sendforexdataincompatibilitymode(true);
    apiSettingsConfigProto.set_maintainandresubmitordersonreconnect(true);
    apiSettingsConfigProto.set_historicaldatamaxsize(4);
    apiSettingsConfigProto.set_autoreportnettingeventcontracttrades(true);
    apiSettingsConfigProto.set_optionexerciserequesttype("final");
    apiSettingsConfigProto.add_trustedips()->append("127.0.0.1");
    *apiConfigProto.mutable_settings() = std::move(apiSettingsConfigProto);
    updateConfigRequestProto.set_reqid(reqId);
    *updateConfigRequestProto.mutable_api() = std::move(apiConfigProto);

    return updateConfigRequestProto;
    //! [UpdateApiSettingsConfig]
}

protobuf::UpdateConfigRequest ConfigSamples::UpdateOrdersConfig(int reqId)
{
    //! [UpdateOrderConfig]
    protobuf::UpdateConfigRequest updateConfigRequestProto;
    protobuf::OrdersConfig ordersConfigProto;
    protobuf::OrdersSmartRoutingConfig ordersSmartRoutingConfigProto;
    ordersSmartRoutingConfigProto.set_seekpriceimprovement(true);
    ordersSmartRoutingConfigProto.set_donotroutetodarkpools(true);
    *ordersConfigProto.mutable_smartrouting() = std::move(ordersSmartRoutingConfigProto);
    updateConfigRequestProto.set_reqid(reqId);
    *updateConfigRequestProto.mutable_orders() = std::move(ordersConfigProto);
    return updateConfigRequestProto;
    //! [UpdateOrderConfig]
}

protobuf::UpdateConfigRequest ConfigSamples::UpdateMessageConfigConfirmMandatoryCapPriceAccepted(int reqId)
{
    //! [UpdateMessageConfigConfirmMandatoryCapPriceAccepted]
    protobuf::UpdateConfigRequest updateConfigRequestProto;
    protobuf::MessageConfig messageConfigProto;
    messageConfigProto.set_id(131);
    messageConfigProto.set_enabled(false);
    updateConfigRequestProto.set_reqid(reqId);
    *updateConfigRequestProto.add_messages() = std::move(messageConfigProto);
    protobuf::UpdateConfigWarning updateConfigWarningProto;
    updateConfigWarningProto.set_messageid(131);
    *updateConfigRequestProto.add_acceptedwarnings() = std::move(updateConfigWarningProto);
    return updateConfigRequestProto;
    //! [UpdateMessageConfigConfirmMandatoryCapPriceAccepted]
}

protobuf::UpdateConfigRequest ConfigSamples::UpdateConfigOrderIdReset(int reqId)
{
    //! [ UpdateConfigOrderIdReset]
    protobuf::UpdateConfigRequest updateConfigRequestProto;
    updateConfigRequestProto.set_reqid(reqId);
    updateConfigRequestProto.set_resetapiordersequence(true);
    return updateConfigRequestProto;
    //! [ UpdateConfigOrderIdReset]
}
