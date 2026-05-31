"""Deserialize and dispatch messages."""

import dataclasses
import logging
from datetime import datetime, timezone
from typing import Any, cast

from .contract import (
    ComboLeg, Contract, ContractDescription, ContractDetails,
    DeltaNeutralContract)
from .objects import (
    BarData, CommissionReport, DepthMktDataDescription, Execution, FamilyCode,
    HistogramData, HistoricalSession, HistoricalTick, HistoricalTickBidAsk,
    HistoricalTickLast, NewsProvider, PriceIncrement, SmartComponent,
    SoftDollarTier, TagValue, TickAttribBidAsk, TickAttribLast)
from .order import Order, OrderComboLeg, OrderCondition, OrderState
from .util import UNSET_DOUBLE, ZoneInfo, parseIBDatetime
from .wrapper import Wrapper

# Lazy import helpers for protobuf — only imported when a protobuf message arrives
def _pb(name: str):
    import importlib
    mod = importlib.import_module(f'.protobuf.{name}_pb2', package='ib_insync')
    return getattr(mod, name)


def _contract_from_proto(p) -> Contract:
    c = Contract()
    c.conId = p.conId
    c.symbol = p.symbol
    c.secType = p.secType
    c.lastTradeDateOrContractMonth = p.lastTradeDateOrContractMonth
    c.lastTradeDate = p.lastTradeDate
    c.strike = p.strike
    c.right = p.right
    c.multiplier = p.multiplier
    c.exchange = p.exchange
    c.primaryExchange = p.primaryExch
    c.currency = p.currency
    c.localSymbol = p.localSymbol
    c.tradingClass = p.tradingClass
    c.secIdType = p.secIdType
    c.secId = p.secId
    c.description = p.description
    c.issuerId = p.issuerId
    c.comboLegsDescrip = p.comboLegsDescrip
    if p.HasField('deltaNeutralContract'):
        dnc = p.deltaNeutralContract
        c.deltaNeutralContract = DeltaNeutralContract(dnc.conId, dnc.delta, dnc.price)
    for leg_p in p.comboLegs:
        leg = ComboLeg()
        leg.conId = leg_p.conId
        leg.ratio = leg_p.ratio
        leg.action = leg_p.action
        leg.exchange = leg_p.exchange
        leg.openClose = leg_p.openClose
        leg.shortSaleSlot = leg_p.shortSaleSlot
        leg.designatedLocation = leg_p.designatedLocation
        leg.exemptCode = leg_p.exemptCode
        c.comboLegs.append(leg)
    return c


def _order_from_proto(p) -> Order:
    o = Order()
    o.clientId = p.clientId
    o.orderId = p.orderId
    o.permId = p.permId
    o.parentId = p.parentId
    o.action = p.action
    o.totalQuantity = float(p.totalQuantity) if p.totalQuantity else 0.0
    o.displaySize = p.displaySize
    o.orderType = p.orderType
    o.lmtPrice = p.lmtPrice if p.HasField('lmtPrice') else UNSET_DOUBLE
    o.auxPrice = p.auxPrice if p.HasField('auxPrice') else UNSET_DOUBLE
    o.tif = p.tif
    o.account = p.account
    o.settlingFirm = p.settlingFirm
    o.clearingAccount = p.clearingAccount
    o.clearingIntent = p.clearingIntent
    o.allOrNone = p.allOrNone
    o.blockOrder = p.blockOrder
    o.hidden = p.hidden
    o.outsideRth = p.outsideRth
    o.sweepToFill = p.sweepToFill
    o.percentOffset = p.percentOffset if p.HasField('percentOffset') else UNSET_DOUBLE
    o.trailingPercent = p.trailingPercent if p.HasField('trailingPercent') else UNSET_DOUBLE
    o.trailStopPrice = p.trailStopPrice if p.HasField('trailStopPrice') else UNSET_DOUBLE
    o.minQty = p.minQty if p.HasField('minQty') else UNSET_DOUBLE
    o.goodAfterTime = p.goodAfterTime
    o.goodTillDate = p.goodTillDate
    o.ocaGroup = p.ocaGroup
    o.orderRef = p.orderRef
    o.rule80A = p.rule80A
    o.ocaType = p.ocaType
    o.triggerMethod = p.triggerMethod
    o.activeStartTime = p.activeStartTime
    o.activeStopTime = p.activeStopTime
    o.faGroup = p.faGroup
    o.faMethod = p.faMethod
    o.faPercentage = p.faPercentage
    o.volatility = p.volatility if p.HasField('volatility') else UNSET_DOUBLE
    o.volatilityType = p.volatilityType if p.HasField('volatilityType') else UNSET_DOUBLE
    o.continuousUpdate = p.continuousUpdate
    o.referencePriceType = p.referencePriceType if p.HasField('referencePriceType') else UNSET_DOUBLE
    o.deltaNeutralOrderType = p.deltaNeutralOrderType
    o.deltaNeutralAuxPrice = p.deltaNeutralAuxPrice if p.HasField('deltaNeutralAuxPrice') else UNSET_DOUBLE
    o.deltaNeutralConId = p.deltaNeutralConId
    o.deltaNeutralOpenClose = p.deltaNeutralOpenClose
    o.deltaNeutralShortSale = p.deltaNeutralShortSale
    o.deltaNeutralShortSaleSlot = p.deltaNeutralShortSaleSlot
    o.deltaNeutralDesignatedLocation = p.deltaNeutralDesignatedLocation
    o.scaleInitLevelSize = p.scaleInitLevelSize if p.HasField('scaleInitLevelSize') else UNSET_DOUBLE
    o.scaleSubsLevelSize = p.scaleSubsLevelSize if p.HasField('scaleSubsLevelSize') else UNSET_DOUBLE
    o.scalePriceIncrement = p.scalePriceIncrement if p.HasField('scalePriceIncrement') else UNSET_DOUBLE
    o.scalePriceAdjustValue = p.scalePriceAdjustValue if p.HasField('scalePriceAdjustValue') else UNSET_DOUBLE
    o.scalePriceAdjustInterval = p.scalePriceAdjustInterval if p.HasField('scalePriceAdjustInterval') else UNSET_DOUBLE
    o.scaleProfitOffset = p.scaleProfitOffset if p.HasField('scaleProfitOffset') else UNSET_DOUBLE
    o.scaleAutoReset = p.scaleAutoReset
    o.scaleInitPosition = p.scaleInitPosition if p.HasField('scaleInitPosition') else UNSET_DOUBLE
    o.scaleInitFillQty = p.scaleInitFillQty if p.HasField('scaleInitFillQty') else UNSET_DOUBLE
    o.scaleRandomPercent = p.scaleRandomPercent
    o.scaleTable = p.scaleTable
    o.hedgeType = p.hedgeType
    o.hedgeParam = p.hedgeParam
    o.algoStrategy = p.algoStrategy
    o.algoParams = [TagValue(k, v) for k, v in p.algoParams.items()]
    o.algoId = p.algoId
    o.smartComboRoutingParams = [TagValue(k, v) for k, v in p.smartComboRoutingParams.items()]
    o.whatIf = p.whatIf
    o.transmit = p.transmit
    o.overridePercentageConstraints = p.overridePercentageConstraints
    o.openClose = p.openClose
    o.origin = p.origin
    o.shortSaleSlot = p.shortSaleSlot
    o.designatedLocation = p.designatedLocation
    o.exemptCode = p.exemptCode
    o.deltaNeutralSettlingFirm = p.deltaNeutralSettlingFirm
    o.deltaNeutralClearingAccount = p.deltaNeutralClearingAccount
    o.deltaNeutralClearingIntent = p.deltaNeutralClearingIntent
    o.discretionaryAmt = p.discretionaryAmt
    o.optOutSmartRouting = p.optOutSmartRouting
    o.startingPrice = p.startingPrice if p.HasField('startingPrice') else UNSET_DOUBLE
    o.stockRefPrice = p.stockRefPrice if p.HasField('stockRefPrice') else UNSET_DOUBLE
    o.delta = p.delta if p.HasField('delta') else UNSET_DOUBLE
    o.stockRangeLower = p.stockRangeLower if p.HasField('stockRangeLower') else UNSET_DOUBLE
    o.stockRangeUpper = p.stockRangeUpper if p.HasField('stockRangeUpper') else UNSET_DOUBLE
    o.notHeld = p.notHeld
    o.orderMiscOptions = [TagValue(k, v) for k, v in p.orderMiscOptions.items()]
    o.solicited = p.solicited
    o.randomizeSize = p.randomizeSize
    o.randomizePrice = p.randomizePrice
    o.referenceContractId = p.referenceContractId
    o.peggedChangeAmount = p.peggedChangeAmount
    o.isPeggedChangeAmountDecrease = p.isPeggedChangeAmountDecrease
    o.referenceChangeAmount = p.referenceChangeAmount
    o.referenceExchangeId = p.referenceExchangeId
    o.adjustedOrderType = p.adjustedOrderType
    o.triggerPrice = p.triggerPrice if p.HasField('triggerPrice') else UNSET_DOUBLE
    o.adjustedStopPrice = p.adjustedStopPrice if p.HasField('adjustedStopPrice') else UNSET_DOUBLE
    o.adjustedStopLimitPrice = p.adjustedStopLimitPrice if p.HasField('adjustedStopLimitPrice') else UNSET_DOUBLE
    o.adjustedTrailingAmount = p.adjustedTrailingAmount if p.HasField('adjustedTrailingAmount') else UNSET_DOUBLE
    o.adjustableTrailingUnit = p.adjustableTrailingUnit
    o.lmtPriceOffset = p.lmtPriceOffset if p.HasField('lmtPriceOffset') else UNSET_DOUBLE
    o.conditionsCancelOrder = p.conditionsCancelOrder
    o.conditionsIgnoreRth = p.conditionsIgnoreRth
    o.modelCode = p.modelCode
    o.extOperator = p.extOperator
    if p.HasField('softDollarTier'):
        o.softDollarTier = SoftDollarTier(p.softDollarTier.name, p.softDollarTier.value, p.softDollarTier.displayName)
    o.cashQty = p.cashQty if p.HasField('cashQty') else UNSET_DOUBLE
    o.mifid2DecisionMaker = p.mifid2DecisionMaker
    o.mifid2DecisionAlgo = p.mifid2DecisionAlgo
    o.mifid2ExecutionTrader = p.mifid2ExecutionTrader
    o.mifid2ExecutionAlgo = p.mifid2ExecutionAlgo
    o.dontUseAutoPriceForHedge = p.dontUseAutoPriceForHedge
    o.isOmsContainer = p.isOmsContainer
    o.discretionaryUpToLimitPrice = p.discretionaryUpToLimitPrice
    o.autoCancelDate = p.autoCancelDate
    o.filledQuantity = p.filledQuantity if p.HasField('filledQuantity') else UNSET_DOUBLE
    o.refFuturesConId = p.refFuturesConId
    o.autoCancelParent = p.autoCancelParent
    o.shareholder = p.shareholder
    o.imbalanceOnly = p.imbalanceOnly
    o.routeMarketableToBbo = p.routeMarketableToBbo
    o.parentPermId = p.parentPermId
    o.usePriceMgmtAlgo = p.usePriceMgmtAlgo
    o.duration = p.duration if p.HasField('duration') else UNSET_DOUBLE
    o.postToAts = p.postToAts if p.HasField('postToAts') else UNSET_DOUBLE
    o.advancedErrorOverride = p.advancedErrorOverride
    o.manualOrderTime = p.manualOrderTime
    o.minTradeQty = p.minTradeQty if p.HasField('minTradeQty') else UNSET_DOUBLE
    o.minCompeteSize = p.minCompeteSize if p.HasField('minCompeteSize') else UNSET_DOUBLE
    o.competeAgainstBestOffset = p.competeAgainstBestOffset if p.HasField('competeAgainstBestOffset') else UNSET_DOUBLE
    o.midOffsetAtWhole = p.midOffsetAtWhole if p.HasField('midOffsetAtWhole') else UNSET_DOUBLE
    o.midOffsetAtHalf = p.midOffsetAtHalf if p.HasField('midOffsetAtHalf') else UNSET_DOUBLE
    o.customerAccount = p.customerAccount
    o.professionalCustomer = p.professionalCustomer
    o.bondAccruedInterest = p.bondAccruedInterest
    o.includeOvernight = p.includeOvernight
    o.manualOrderIndicator = p.manualOrderIndicator if p.HasField('manualOrderIndicator') else UNSET_DOUBLE
    o.submitter = p.submitter
    o.hedgeMaxSize = p.hedgeMaxSize if p.HasField('hedgeMaxSize') else UNSET_DOUBLE
    for cond_p in p.conditions:
        cond_cls = OrderCondition.createClass(cond_p.condType)
        cond = cond_cls(cond_p.condType)
        cond.conjunction = 'a' if cond_p.conjunction == 0 else 'o'
        if hasattr(cond, 'isMore'):
            cond.isMore = cond_p.isMore
        if hasattr(cond, 'price') and cond_p.HasField('price'):
            cond.price = cond_p.price
        if hasattr(cond, 'conId') and cond_p.HasField('conId'):
            cond.conId = cond_p.conId
        if hasattr(cond, 'exch'):
            cond.exch = cond_p.exch
        if hasattr(cond, 'secType'):
            cond.secType = cond_p.secType
        if hasattr(cond, 'triggerMethod') and cond_p.HasField('triggerMethod'):
            cond.triggerMethod = cond_p.triggerMethod
        if hasattr(cond, 'time'):
            cond.time = cond_p.time
        if hasattr(cond, 'percent') and cond_p.HasField('percent'):
            cond.percent = cond_p.percent
        if hasattr(cond, 'volume') and cond_p.HasField('volume'):
            cond.volume = cond_p.volume
        if hasattr(cond, 'changePercent') and cond_p.HasField('changePercent'):
            cond.changePercent = cond_p.changePercent
        o.conditions.append(cond)
    return o


def _order_state_from_proto(p) -> 'OrderState':
    st = OrderState()
    st.status = p.status
    st.initMarginBefore = p.initMarginBefore
    st.maintMarginBefore = p.maintMarginBefore
    st.equityWithLoanBefore = p.equityWithLoanBefore
    st.initMarginChange = p.initMarginChange
    st.maintMarginChange = p.maintMarginChange
    st.equityWithLoanChange = p.equityWithLoanChange
    st.initMarginAfter = p.initMarginAfter
    st.maintMarginAfter = p.maintMarginAfter
    st.equityWithLoanAfter = p.equityWithLoanAfter
    st.commission = p.commissionAndFees if p.HasField('commissionAndFees') else UNSET_DOUBLE
    st.minCommission = p.minCommissionAndFees if p.HasField('minCommissionAndFees') else UNSET_DOUBLE
    st.maxCommission = p.maxCommissionAndFees if p.HasField('maxCommissionAndFees') else UNSET_DOUBLE
    st.commissionCurrency = p.commissionAndFeesCurrency
    st.warningText = p.warningText
    st.completedTime = p.completedTime
    st.completedStatus = p.completedStatus
    return st


def _contract_details_from_proto(contract_p, details_p) -> ContractDetails:
    cd = ContractDetails()
    cd.contract = _contract_from_proto(contract_p)
    cd.marketName = details_p.marketName
    cd.minTick = details_p.minTick
    cd.orderTypes = details_p.orderTypes
    cd.validExchanges = details_p.validExchanges
    cd.priceMagnifier = details_p.priceMagnifier
    cd.underConId = details_p.underConId
    cd.longName = details_p.longName
    cd.contractMonth = details_p.contractMonth
    cd.industry = details_p.industry
    cd.category = details_p.category
    cd.subcategory = details_p.subcategory
    cd.timeZoneId = details_p.timeZoneId
    cd.tradingHours = details_p.tradingHours
    cd.liquidHours = details_p.liquidHours
    cd.evRule = details_p.evRule
    cd.evMultiplier = details_p.evMultiplier
    cd.secIdList = [TagValue(k, v) for k, v in details_p.secIdList.items()]
    cd.aggGroup = details_p.aggGroup
    cd.underSymbol = details_p.underSymbol
    cd.underSecType = details_p.underSecType
    cd.marketRuleIds = details_p.marketRuleIds
    cd.realExpirationDate = details_p.realExpirationDate
    cd.stockType = details_p.stockType
    cd.minSize = details_p.minSize
    cd.sizeIncrement = details_p.sizeIncrement
    cd.suggestedSizeIncrement = details_p.suggestedSizeIncrement
    cd.fundName = details_p.fundName
    cd.fundFamily = details_p.fundFamily
    cd.fundType = details_p.fundType
    cd.fundFrontLoad = details_p.fundFrontLoad
    cd.fundBackLoad = details_p.fundBackLoad
    cd.fundBackLoadTimeInterval = details_p.fundBackLoadTimeInterval
    cd.fundManagementFee = details_p.fundManagementFee
    cd.fundClosed = details_p.fundClosed
    cd.fundClosedForNewInvestors = details_p.fundClosedForNewInvestors
    cd.fundClosedForNewMoney = details_p.fundClosedForNewMoney
    cd.fundNotifyAmount = details_p.fundNotifyAmount
    cd.fundMinimumInitialPurchase = details_p.fundMinimumInitialPurchase
    cd.fundSubsequentMinimumPurchase = details_p.fundMinimumSubsequentPurchase
    cd.fundBlueSkyStates = details_p.fundBlueSkyStates
    cd.fundBlueSkyTerritories = details_p.fundBlueSkyTerritories
    return cd


def _bar_from_proto(p) -> BarData:
    return BarData(
        date=p.date, open=p.open, high=p.high, low=p.low, close=p.close,
        volume=float(p.volume) if p.volume else 0.0,
        average=float(p.WAP) if p.WAP else 0.0,
        barCount=p.barCount)


def _execution_from_proto(p) -> Execution:
    e = Execution()
    e.orderId = p.orderId
    e.execId = p.execId
    e.time = p.time
    e.acctNumber = p.acctNumber
    e.exchange = p.exchange
    e.side = p.side
    e.shares = float(p.shares) if p.shares else 0.0
    e.price = p.price
    e.permId = p.permId
    e.clientId = p.clientId
    e.isLiquidation = p.isLiquidation
    e.cumQty = float(p.cumQty) if p.cumQty else 0.0
    e.avgPrice = p.avgPrice
    e.orderRef = p.orderRef
    e.evRule = p.evRule
    e.evMultiplier = p.evMultiplier if p.HasField('evMultiplier') else 0
    e.modelCode = p.modelCode
    e.lastLiquidity = p.lastLiquidity
    e.pendingPriceRevision = p.pendingPriceRevision
    return e


class Decoder:
    """Decode IB messages and invoke corresponding wrapper methods."""

    def __init__(self, wrapper: Wrapper, serverVersion: int):
        self.wrapper = wrapper
        self.serverVersion = serverVersion
        self.logger = logging.getLogger('ib_insync.Decoder')
        self.handlers = {
            1: self.priceSizeTick,
            2: self.wrap(
                'tickSize', [int, int, float]),
            3: self.wrap(
                'orderStatus', [
                    int, str, float, float, float, int, int,
                    float, int, str, float], skip=1),
            4: self.errorMsg,
            5: self.openOrder,
            6: self.wrap(
                'updateAccountValue', [str, str, str, str]),
            7: self.updatePortfolio,
            8: self.wrap(
                'updateAccountTime', [str]),
            9: self.wrap(
                'nextValidId', [int]),
            10: self.contractDetails,
            11: self.execDetails,
            12: self.wrap(
                'updateMktDepth', [int, int, int, int, float, float]),
            13: self.wrap(
                'updateMktDepthL2',
                [int, int, str, int, int, float, float, bool]),
            14: self.wrap(
                'updateNewsBulletin', [int, int, str, str]),
            15: self.wrap(
                'managedAccounts', [str]),
            16: self.wrap(
                'receiveFA', [int, str]),
            17: self.historicalData,
            18: self.bondContractDetails,
            19: self.wrap(
                'scannerParameters', [str]),
            20: self.scannerData,
            21: self.tickOptionComputation,
            45: self.wrap(
                'tickGeneric', [int, int, float]),
            46: self.wrap(
                'tickString', [int, int, str]),
            47: self.wrap(
                'tickEFP',
                [int, int, float, str, float, int, str, float, float]),
            49: self.wrap(
                'currentTime', [int]),
            50: self.wrap(
                'realtimeBar',
                [int, int, float, float, float, float, float, float, int]),
            51: self.wrap(
                'fundamentalData', [int, str]),
            52: self.wrap(
                'contractDetailsEnd', [int]),
            53: self.wrap(
                'openOrderEnd', []),
            54: self.wrap(
                'accountDownloadEnd', [str]),
            55: self.wrap(
                'execDetailsEnd', [int]),
            56: self.deltaNeutralValidation,
            57: self.wrap(
                'tickSnapshotEnd', [int]),
            58: self.wrap(
                'marketDataType', [int, int]),
            59: self.commissionReport,
            61: self.position,
            62: self.wrap(
                'positionEnd', []),
            63: self.wrap(
                'accountSummary', [int, str, str, str, str]),
            64: self.wrap(
                'accountSummaryEnd', [int]),
            65: self.wrap(
                'verifyMessageAPI', [str]),
            66: self.wrap(
                'verifyCompleted', [bool, str]),
            67: self.wrap(
                'displayGroupList', [int, str]),
            68: self.wrap(
                'displayGroupUpdated', [int, str]),
            69: self.wrap(
                'verifyAndAuthMessageAPI', [str, str]),
            70: self.wrap(
                'verifyAndAuthCompleted', [bool, str]),
            71: self.positionMulti,
            72: self.wrap(
                'positionMultiEnd', [int]),
            73: self.wrap(
                'accountUpdateMulti', [int, str, str, str, str, str]),
            74: self.wrap(
                'accountUpdateMultiEnd', [int]),
            75: self.securityDefinitionOptionParameter,
            76: self.wrap(
                'securityDefinitionOptionParameterEnd', [int], skip=1),
            77: self.softDollarTiers,
            78: self.familyCodes,
            79: self.symbolSamples,
            80: self.mktDepthExchanges,
            81: self.wrap(
                'tickReqParams', [int, float, str, int], skip=1),
            82: self.smartComponents,
            83: self.wrap(
                'newsArticle', [int, int, str], skip=1),
            84: self.wrap(
                'tickNews', [int, int, str, str, str, str], skip=1),
            85: self.newsProviders,
            86: self.wrap(
                'historicalNews', [int, str, str, str, str], skip=1),
            87: self.wrap(
                'historicalNewsEnd', [int, bool], skip=1),
            88: self.wrap(
                'headTimestamp', [int, str], skip=1),
            89: self.histogramData,
            90: self.historicalDataUpdate,
            91: self.wrap(
                'rerouteMktDataReq', [int, int, str], skip=1),
            92: self.wrap(
                'rerouteMktDepthReq', [int, int, str], skip=1),
            93: self.marketRule,
            94: self.wrap(
                'pnl', [int, float, float, float], skip=1),
            95: self.wrap(
                'pnlSingle', [int, float, float, float, float, float], skip=1),
            96: self.historicalTicks,
            97: self.historicalTicksBidAsk,
            98: self.historicalTicksLast,
            99: self.tickByTick,
            100: self.wrap(
                'orderBound', [int, int, int], skip=1),
            101: self.completedOrder,
            102: self.wrap(
                'completedOrdersEnd', [], skip=1),
            103: self.wrap(
                'replaceFAEnd', [int, str], skip=1),
            104: self.wrap(
                'wshMetaData', [int, str], skip=1),
            105: self.wrap(
                'wshEventData', [int, str], skip=1),
            106: self.historicalSchedule,
            107: self.wrap(
                'userInfo', [int, str], skip=1)
        }

    def wrap(self, methodName, types, skip=2):
        """
        Create a message handler that invokes a wrapper method
        with the in-order message fields as parameters, skipping over
        the first ``skip`` fields, and parsed according to the ``types`` list.
        """

        def handler(fields):
            method = getattr(self.wrapper, methodName, None)
            if method:
                try:
                    args = [
                        field if typ is str else
                        int(field or 0) if typ is int else
                        float(field or 0) if typ is float else
                        bool(int(field or 0))
                        for (typ, field) in zip(types, fields[skip:])]
                    method(*args)
                except Exception:
                    self.logger.exception(f'Error for {methodName}:')

        return handler

    def interpretProtoBuf(self, msgId: int, payload: bytes) -> None:
        """Decode a protobuf message and invoke the corresponding wrapper method."""
        try:
            handler = self._protoHandlers.get(msgId)
            if handler:
                handler(self, payload)
            else:
                self.logger.debug('No protobuf handler for msgId %d', msgId)
        except Exception:
            self.logger.exception(f'Error handling protobuf msgId={msgId}')

    # ---- protobuf handler methods ----------------------------------------

    def _proto_error(self, payload: bytes) -> None:
        p = _pb('ErrorMessage')()
        p.ParseFromString(payload)
        self.wrapper.error(p.id, p.errorCode, p.errorMsg, p.advancedOrderRejectJson)

    def _proto_order_status(self, payload: bytes) -> None:
        p = _pb('OrderStatus')()
        p.ParseFromString(payload)
        self.wrapper.orderStatus(
            p.orderId, p.status,
            float(p.filled) if p.filled else 0.0,
            float(p.remaining) if p.remaining else 0.0,
            p.avgFillPrice, p.permId, p.parentId, p.lastFillPrice,
            p.clientId, p.whyHeld, p.mktCapPrice)

    def _proto_open_order(self, payload: bytes) -> None:
        p = _pb('OpenOrder')()
        p.ParseFromString(payload)
        c = _contract_from_proto(p.contract)
        o = _order_from_proto(p.order)
        st = _order_state_from_proto(p.orderState)
        self.wrapper.openOrder(p.orderId, c, o, st)

    def _proto_open_orders_end(self, payload: bytes) -> None:
        self.wrapper.openOrderEnd()

    def _proto_completed_order(self, payload: bytes) -> None:
        p = _pb('CompletedOrder')()
        p.ParseFromString(payload)
        c = _contract_from_proto(p.contract)
        o = _order_from_proto(p.order)
        st = _order_state_from_proto(p.orderState)
        self.wrapper.completedOrder(c, o, st)

    def _proto_completed_orders_end(self, payload: bytes) -> None:
        self.wrapper.completedOrdersEnd()

    def _proto_order_bound(self, payload: bytes) -> None:
        p = _pb('OrderBound')()
        p.ParseFromString(payload)
        self.wrapper.orderBound(p.permId, p.clientId, p.orderId)

    def _proto_execution_details(self, payload: bytes) -> None:
        p = _pb('ExecutionDetails')()
        p.ParseFromString(payload)
        c = _contract_from_proto(p.contract)
        e = _execution_from_proto(p.execution)
        self.wrapper.execDetails(p.reqId, c, e)

    def _proto_execution_details_end(self, payload: bytes) -> None:
        p = _pb('ExecutionDetailsEnd')()
        p.ParseFromString(payload)
        self.wrapper.execDetailsEnd(p.reqId)

    def _proto_contract_data(self, payload: bytes) -> None:
        p = _pb('ContractData')()
        p.ParseFromString(payload)
        cd = _contract_details_from_proto(p.contract, p.contractDetails)
        self.wrapper.contractDetails(p.reqId, cd)

    def _proto_contract_data_end(self, payload: bytes) -> None:
        p = _pb('ContractDataEnd')()
        p.ParseFromString(payload)
        self.wrapper.contractDetailsEnd(p.reqId)

    # Mapping from price tick type to corresponding size tick type
    _PRICE_TO_SIZE_TICK: dict[int, int] = {
        1: 0,   # BID → BID_SIZE
        2: 3,   # ASK → ASK_SIZE
        4: 5,   # LAST → LAST_SIZE
        66: 69, # DELAYED_BID → DELAYED_BID_SIZE
        67: 70, # DELAYED_ASK → DELAYED_ASK_SIZE
        68: 71, # DELAYED_LAST → DELAYED_LAST_SIZE
    }

    def _proto_tick_price(self, payload: bytes) -> None:
        p = _pb('TickPrice')()
        p.ParseFromString(payload)
        from .objects import TickAttrib
        attrib = TickAttrib()
        attrib.canAutoExecute = bool(p.attrMask & 1)
        attrib.pastLimit = bool(p.attrMask & 2)
        attrib.preOpen = bool(p.attrMask & 4)
        self.wrapper.tickPrice(p.reqId, p.tickType, p.price, attrib)
        size_tick = self._PRICE_TO_SIZE_TICK.get(p.tickType)
        if size_tick is not None and p.HasField('size'):
            self.wrapper.tickSize(p.reqId, size_tick, float(p.size) if p.size else 0.0)

    def _proto_tick_size(self, payload: bytes) -> None:
        p = _pb('TickSize')()
        p.ParseFromString(payload)
        self.wrapper.tickSize(p.reqId, p.tickType, float(p.size) if p.size else 0.0)

    def _proto_tick_option(self, payload: bytes) -> None:
        p = _pb('TickOptionComputation')()
        p.ParseFromString(payload)
        self.wrapper.tickOptionComputation(
            p.reqId, p.tickType, p.tickAttrib,
            p.impliedVol if p.HasField('impliedVol') else UNSET_DOUBLE,
            p.delta if p.HasField('delta') else UNSET_DOUBLE,
            p.optPrice if p.HasField('optPrice') else UNSET_DOUBLE,
            p.pvDividend if p.HasField('pvDividend') else UNSET_DOUBLE,
            p.gamma if p.HasField('gamma') else UNSET_DOUBLE,
            p.vega if p.HasField('vega') else UNSET_DOUBLE,
            p.theta if p.HasField('theta') else UNSET_DOUBLE,
            p.undPrice if p.HasField('undPrice') else UNSET_DOUBLE)

    def _proto_tick_generic(self, payload: bytes) -> None:
        p = _pb('TickGeneric')()
        p.ParseFromString(payload)
        self.wrapper.tickGeneric(p.reqId, p.tickType, p.value)

    def _proto_tick_string(self, payload: bytes) -> None:
        p = _pb('TickString')()
        p.ParseFromString(payload)
        self.wrapper.tickString(p.reqId, p.tickType, p.value)

    def _proto_tick_snapshot_end(self, payload: bytes) -> None:
        p = _pb('TickSnapshotEnd')()
        p.ParseFromString(payload)
        self.wrapper.tickSnapshotEnd(p.reqId)

    def _proto_tick_req_params(self, payload: bytes) -> None:
        p = _pb('TickReqParams')()
        p.ParseFromString(payload)
        self.wrapper.tickReqParams(p.reqId, p.minTick, p.bboExchange, p.snapshotPermissions)

    def _proto_market_depth(self, payload: bytes) -> None:
        p = _pb('MarketDepth')()
        p.ParseFromString(payload)
        for d in p.marketDepthData:
            self.wrapper.updateMktDepth(p.reqId, d.position, d.operation, d.side, d.price, d.size)

    def _proto_market_depth_l2(self, payload: bytes) -> None:
        p = _pb('MarketDepthL2')()
        p.ParseFromString(payload)
        for d in p.marketDepthData:
            self.wrapper.updateMktDepthL2(p.reqId, d.position, d.marketMaker, d.operation, d.side, d.price, d.size, d.isSmartDepth)

    def _proto_market_data_type(self, payload: bytes) -> None:
        p = _pb('MarketDataType')()
        p.ParseFromString(payload)
        self.wrapper.marketDataType(p.reqId, p.marketDataType)

    def _proto_account_value(self, payload: bytes) -> None:
        p = _pb('AccountValue')()
        p.ParseFromString(payload)
        self.wrapper.updateAccountValue(p.key, p.value, p.currency, p.accountName)

    def _proto_portfolio_value(self, payload: bytes) -> None:
        p = _pb('PortfolioValue')()
        p.ParseFromString(payload)
        c = _contract_from_proto(p.contract)
        self.wrapper.updatePortfolio(c, float(p.position) if p.position else 0.0,
                                     p.marketPrice, p.marketValue,
                                     p.averageCost, p.unrealizedPNL, p.realizedPNL, p.accountName)

    def _proto_account_update_time(self, payload: bytes) -> None:
        p = _pb('AccountUpdateTime')()
        p.ParseFromString(payload)
        self.wrapper.updateAccountTime(p.timeStamp)

    def _proto_account_data_end(self, payload: bytes) -> None:
        p = _pb('AccountDataEnd')()
        p.ParseFromString(payload)
        self.wrapper.accountDownloadEnd(p.accountName)

    def _proto_managed_accounts(self, payload: bytes) -> None:
        p = _pb('ManagedAccounts')()
        p.ParseFromString(payload)
        self.wrapper.managedAccounts(p.accountsList)

    def _proto_position(self, payload: bytes) -> None:
        p = _pb('Position')()
        p.ParseFromString(payload)
        c = _contract_from_proto(p.contract)
        self.wrapper.position(p.account, c, float(p.position) if p.position else 0.0, p.avgCost)

    def _proto_position_end(self, payload: bytes) -> None:
        self.wrapper.positionEnd()

    def _proto_account_summary(self, payload: bytes) -> None:
        p = _pb('AccountSummary')()
        p.ParseFromString(payload)
        self.wrapper.accountSummary(p.reqId, p.account, p.tag, p.value, p.currency)

    def _proto_account_summary_end(self, payload: bytes) -> None:
        p = _pb('AccountSummaryEnd')()
        p.ParseFromString(payload)
        self.wrapper.accountSummaryEnd(p.reqId)

    def _proto_position_multi(self, payload: bytes) -> None:
        p = _pb('PositionMulti')()
        p.ParseFromString(payload)
        c = _contract_from_proto(p.contract)
        self.wrapper.positionMulti(p.reqId, p.account, p.modelCode, c,
                                   float(p.position) if p.position else 0.0, p.avgCost)

    def _proto_position_multi_end(self, payload: bytes) -> None:
        p = _pb('PositionMultiEnd')()
        p.ParseFromString(payload)
        self.wrapper.positionMultiEnd(p.reqId)

    def _proto_account_update_multi(self, payload: bytes) -> None:
        p = _pb('AccountUpdateMulti')()
        p.ParseFromString(payload)
        self.wrapper.accountUpdateMulti(p.reqId, p.account, p.modelCode, p.key, p.value, p.currency)

    def _proto_account_update_multi_end(self, payload: bytes) -> None:
        p = _pb('AccountUpdateMultiEnd')()
        p.ParseFromString(payload)
        self.wrapper.accountUpdateMultiEnd(p.reqId)

    def _proto_historical_data(self, payload: bytes) -> None:
        p = _pb('HistoricalData')()
        p.ParseFromString(payload)
        for bar_p in p.historicalDataBars:
            self.wrapper.historicalData(p.reqId, _bar_from_proto(bar_p))

    def _proto_historical_data_end(self, payload: bytes) -> None:
        p = _pb('HistoricalDataEnd')()
        p.ParseFromString(payload)
        self.wrapper.historicalDataEnd(p.reqId, p.startDateStr, p.endDateStr)

    def _proto_historical_data_update(self, payload: bytes) -> None:
        p = _pb('HistoricalDataUpdate')()
        p.ParseFromString(payload)
        if p.HasField('historicalDataBar'):
            self.wrapper.historicalDataUpdate(p.reqId, _bar_from_proto(p.historicalDataBar))

    def _proto_realtime_bar(self, payload: bytes) -> None:
        p = _pb('RealTimeBarTick')()
        p.ParseFromString(payload)
        self.wrapper.realtimeBar(p.reqId, p.time, p.open, p.high, p.low, p.close,
                                 float(p.volume) if p.volume else 0.0,
                                 float(p.WAP) if p.WAP else 0.0, p.count)

    def _proto_head_timestamp(self, payload: bytes) -> None:
        p = _pb('HeadTimestamp')()
        p.ParseFromString(payload)
        self.wrapper.headTimestamp(p.reqId, p.headTimestamp)

    def _proto_histogram_data(self, payload: bytes) -> None:
        p = _pb('HistogramData')()
        p.ParseFromString(payload)
        items = [HistogramData(e.price, e.size) for e in p.histogramDataEntries]
        self.wrapper.histogramData(p.reqId, items)

    def _proto_historical_ticks(self, payload: bytes) -> None:
        p = _pb('HistoricalTicks')()
        p.ParseFromString(payload)
        ticks = [HistoricalTick(t.time, t.price, float(t.size) if t.size else 0.0) for t in p.historicalTicks]
        self.wrapper.historicalTicks(p.reqId, ticks, p.isDone)

    def _proto_historical_ticks_bid_ask(self, payload: bytes) -> None:
        p = _pb('HistoricalTicksBidAsk')()
        p.ParseFromString(payload)
        ticks = []
        for t in p.historicalTicksBidAsk:
            a = t.tickAttribBidAsk
            attrib = TickAttribBidAsk(a.bidPastLow, a.askPastHigh)
            ticks.append(HistoricalTickBidAsk(
                t.time, attrib, t.priceBid, t.priceAsk,
                float(t.sizeBid) if t.sizeBid else 0.0,
                float(t.sizeAsk) if t.sizeAsk else 0.0))
        self.wrapper.historicalTicksBidAsk(p.reqId, ticks, p.isDone)

    def _proto_historical_ticks_last(self, payload: bytes) -> None:
        p = _pb('HistoricalTicksLast')()
        p.ParseFromString(payload)
        ticks = []
        for t in p.historicalTicksLast:
            a = t.tickAttribLast
            attrib = TickAttribLast(a.pastLimit, a.unreported)
            ticks.append(HistoricalTickLast(
                t.time, attrib, t.price,
                float(t.size) if t.size else 0.0,
                t.exchange, t.specialConditions))
        self.wrapper.historicalTicksLast(p.reqId, ticks, p.isDone)

    def _proto_tick_by_tick(self, payload: bytes) -> None:
        p = _pb('TickByTickData')()
        p.ParseFromString(payload)
        tick_type = p.tickType
        if p.HasField('historicalTickLast'):
            t = p.historicalTickLast
            a = t.tickAttribLast
            attrib = TickAttribLast(a.pastLimit, a.unreported)
            self.wrapper.tickByTickAllLast(p.reqId, tick_type, t.time, t.price, t.size, attrib, t.exchange, t.specialConditions)
        elif p.HasField('historicalTickBidAsk'):
            t = p.historicalTickBidAsk
            a = t.tickAttribBidAsk
            attrib = TickAttribBidAsk(a.bidPastLow, a.askPastHigh)
            self.wrapper.tickByTickBidAsk(p.reqId, t.time, t.priceBid, t.priceAsk, t.sizeBid, t.sizeAsk, attrib)
        elif p.HasField('historicalTickMidPoint'):
            t = p.historicalTickMidPoint
            self.wrapper.tickByTickMidPoint(p.reqId, t.time, t.price)

    def _proto_news_bulletin(self, payload: bytes) -> None:
        p = _pb('NewsBulletin')()
        p.ParseFromString(payload)
        self.wrapper.updateNewsBulletin(p.newsMsgId, p.newsMsgType, p.newsMessage, p.originatingExch)

    def _proto_news_article(self, payload: bytes) -> None:
        p = _pb('NewsArticle')()
        p.ParseFromString(payload)
        self.wrapper.newsArticle(p.reqId, p.articleType, p.articleText)

    def _proto_news_providers(self, payload: bytes) -> None:
        p = _pb('NewsProviders')()
        p.ParseFromString(payload)
        providers = [NewsProvider(code=np.providerCode, name=np.providerName) for np in p.newsProviders]
        self.wrapper.newsProviders(providers)

    def _proto_historical_news(self, payload: bytes) -> None:
        p = _pb('HistoricalNews')()
        p.ParseFromString(payload)
        self.wrapper.historicalNews(p.reqId, p.time, p.providerCode, p.articleId, p.headline)

    def _proto_historical_news_end(self, payload: bytes) -> None:
        p = _pb('HistoricalNewsEnd')()
        p.ParseFromString(payload)
        self.wrapper.historicalNewsEnd(p.reqId, p.hasMore)

    def _proto_tick_news(self, payload: bytes) -> None:
        p = _pb('TickNews')()
        p.ParseFromString(payload)
        self.wrapper.tickNews(p.reqId, p.timestamp, p.providerCode, p.articleId, p.headline, p.extraData)

    def _proto_wsh_meta_data(self, payload: bytes) -> None:
        p = _pb('WshMetaData')()
        p.ParseFromString(payload)
        self.wrapper.wshMetaData(p.reqId, p.dataJson)

    def _proto_wsh_event_data(self, payload: bytes) -> None:
        p = _pb('WshEventData')()
        p.ParseFromString(payload)
        self.wrapper.wshEventData(p.reqId, p.dataJson)

    def _proto_scanner_parameters(self, payload: bytes) -> None:
        p = _pb('ScannerParameters')()
        p.ParseFromString(payload)
        self.wrapper.scannerParameters(p.xml)

    def _proto_scanner_data(self, payload: bytes) -> None:
        p = _pb('ScannerData')()
        p.ParseFromString(payload)
        from .contract import ScanData
        items = []
        for el in p.scannerDataElement:
            cd = _contract_details_from_proto(el.contract, type('_CD', (), {
                'marketName': el.marketName, 'minTick': 0, 'orderTypes': '',
                'validExchanges': '', 'priceMagnifier': 0, 'underConId': 0,
                'longName': '', 'contractMonth': '', 'industry': '', 'category': '',
                'subcategory': '', 'timeZoneId': '', 'tradingHours': '',
                'liquidHours': '', 'evRule': '', 'evMultiplier': 0,
                'secIdList': {}, 'aggGroup': 0, 'underSymbol': '',
                'underSecType': '', 'marketRuleIds': '', 'realExpirationDate': '',
                'stockType': '', 'minSize': 0, 'sizeIncrement': 0,
                'suggestedSizeIncrement': 0,
                'fundName': '', 'fundFamily': '', 'fundType': '',
                'fundFrontLoad': '', 'fundBackLoad': '', 'fundBackLoadTimeInterval': '',
                'fundManagementFee': '', 'fundClosed': False,
                'fundClosedForNewInvestors': False, 'fundClosedForNewMoney': False,
                'fundNotifyAmount': '', 'fundMinimumInitialPurchase': '',
                'fundSubsequentMinimumPurchase': '', 'fundBlueSkyStates': '',
                'fundBlueSkyTerritories': '',
                'HasField': lambda _: False,
            })())
            items.append(ScanData(rank=el.rank, contractDetails=cd,
                                  distance=el.distance, benchmark=el.benchmark,
                                  projection=el.projection, legsStr=el.comboKey))
        self.wrapper.scannerData(p.reqId, items)

    def _proto_fundamental_data(self, payload: bytes) -> None:
        p = _pb('FundamentalsData')()
        p.ParseFromString(payload)
        self.wrapper.fundamentalData(p.reqId, p.data)

    def _proto_pnl(self, payload: bytes) -> None:
        p = _pb('PnL')()
        p.ParseFromString(payload)
        self.wrapper.pnl(p.reqId, p.dailyPnL,
                         p.unrealizedPnL if p.HasField('unrealizedPnL') else UNSET_DOUBLE,
                         p.realizedPnL if p.HasField('realizedPnL') else UNSET_DOUBLE)

    def _proto_pnl_single(self, payload: bytes) -> None:
        p = _pb('PnLSingle')()
        p.ParseFromString(payload)
        self.wrapper.pnlSingle(p.reqId, float(p.position) if p.position else 0.0, p.dailyPnL,
                               p.unrealizedPnL if p.HasField('unrealizedPnL') else UNSET_DOUBLE,
                               p.realizedPnL if p.HasField('realizedPnL') else UNSET_DOUBLE,
                               p.value if p.HasField('value') else UNSET_DOUBLE)

    def _proto_receive_fa(self, payload: bytes) -> None:
        p = _pb('ReceiveFA')()
        p.ParseFromString(payload)
        self.wrapper.receiveFA(p.faDataType, p.cxml)

    def _proto_replace_fa_end(self, payload: bytes) -> None:
        p = _pb('ReplaceFAEnd')()
        p.ParseFromString(payload)
        self.wrapper.replaceFAEnd(p.reqId, p.text)

    def _proto_commission_report(self, payload: bytes) -> None:
        p = _pb('CommissionAndFeesReport')()
        p.ParseFromString(payload)
        report = CommissionReport()
        report.execId = p.execId
        report.commission = p.commissionAndFees
        report.currency = p.currency
        report.realizedPNL = p.realizedPNL
        report.yield_ = p.bondYield
        report.yieldRedemptionDate = p.yieldRedemptionDate
        self.wrapper.commissionAndFeesReport(report)

    def _proto_historical_schedule(self, payload: bytes) -> None:
        p = _pb('HistoricalSchedule')()
        p.ParseFromString(payload)
        sessions = [HistoricalSession(s.startDateTime, s.endDateTime, s.refDate) for s in p.historicalSessions]
        self.wrapper.historicalSchedule(p.reqId, p.startDateTime, p.endDateTime, p.timeZone, sessions)

    def _proto_reroute_mkt_data(self, payload: bytes) -> None:
        p = _pb('RerouteMarketDataRequest')()
        p.ParseFromString(payload)
        self.wrapper.rerouteMktDataReq(p.reqId, p.conId, p.exchange)

    def _proto_reroute_mkt_depth(self, payload: bytes) -> None:
        p = _pb('RerouteMarketDepthRequest')()
        p.ParseFromString(payload)
        self.wrapper.rerouteMktDepthReq(p.reqId, p.conId, p.exchange)

    def _proto_sec_def_opt_param(self, payload: bytes) -> None:
        p = _pb('SecDefOptParameter')()
        p.ParseFromString(payload)
        self.wrapper.securityDefinitionOptionParameter(
            p.reqId, p.exchange, p.underlyingConId, p.tradingClass,
            p.multiplier, list(p.expirations), list(p.strikes))

    def _proto_sec_def_opt_param_end(self, payload: bytes) -> None:
        p = _pb('SecDefOptParameterEnd')()
        p.ParseFromString(payload)
        self.wrapper.securityDefinitionOptionParameterEnd(p.reqId)

    def _proto_soft_dollar_tiers(self, payload: bytes) -> None:
        p = _pb('SoftDollarTiers')()
        p.ParseFromString(payload)
        tiers = [SoftDollarTier(t.name, t.value, t.displayName) for t in p.softDollarTiers]
        self.wrapper.softDollarTiers(p.reqId, tiers)

    def _proto_family_codes(self, payload: bytes) -> None:
        p = _pb('FamilyCodes')()
        p.ParseFromString(payload)
        codes = [FamilyCode(fc.accountId, fc.familyCode) for fc in p.familyCodes]
        self.wrapper.familyCodes(codes)

    def _proto_symbol_samples(self, payload: bytes) -> None:
        p = _pb('SymbolSamples')()
        p.ParseFromString(payload)
        descriptions = []
        for cd_p in p.contractDescriptions:
            cd = ContractDescription()
            cd.contract = _contract_from_proto(cd_p.contract)
            cd.derivativeSecTypes = list(cd_p.derivativeSecTypes)
            descriptions.append(cd)
        self.wrapper.symbolSamples(p.reqId, descriptions)

    def _proto_mkt_depth_exchanges(self, payload: bytes) -> None:
        p = _pb('MarketDepthExchanges')()
        p.ParseFromString(payload)
        descriptions = [
            DepthMktDataDescription(
                exchange=d.exchange, secType=d.secType,
                listingExch=d.listingExch, serviceDataType=d.serviceDataType,
                aggGroup=d.aggGroup)
            for d in p.depthMarketDataDescriptions]
        self.wrapper.mktDepthExchanges(descriptions)

    def _proto_smart_components(self, payload: bytes) -> None:
        p = _pb('SmartComponents')()
        p.ParseFromString(payload)
        components = {sc.bitNumber: SmartComponent(sc.bitNumber, sc.exchange, sc.exchangeLetter)
                      for sc in p.smartComponents}
        self.wrapper.smartComponents(p.reqId, components)

    def _proto_market_rule(self, payload: bytes) -> None:
        p = _pb('MarketRule')()
        p.ParseFromString(payload)
        increments = [PriceIncrement(inc.lowEdge, inc.increment) for inc in p.priceIncrements]
        self.wrapper.marketRule(p.marketRuleId, increments)

    def _proto_user_info(self, payload: bytes) -> None:
        p = _pb('UserInfo')()
        p.ParseFromString(payload)
        self.wrapper.userInfo(p.reqId, p.whiteBrandingId)

    def _proto_next_valid_id(self, payload: bytes) -> None:
        p = _pb('NextValidId')()
        p.ParseFromString(payload)
        self.wrapper.nextValidId(p.orderId)

    def _proto_current_time(self, payload: bytes) -> None:
        p = _pb('CurrentTime')()
        p.ParseFromString(payload)
        self.wrapper.currentTime(p.time)

    _protoHandlers: dict[int, Any] = {
        1: _proto_tick_price,
        2: _proto_tick_size,
        3: _proto_order_status,
        4: _proto_error,
        5: _proto_open_order,
        6: _proto_account_value,
        7: _proto_portfolio_value,
        8: _proto_account_update_time,
        9: _proto_next_valid_id,
        10: _proto_contract_data,
        11: _proto_execution_details,
        12: _proto_market_depth,
        13: _proto_market_depth_l2,
        14: _proto_news_bulletin,
        15: _proto_managed_accounts,
        16: _proto_receive_fa,
        17: _proto_historical_data,
        18: _proto_contract_data,      # BOND_CONTRACT_DATA reuses contractDetails path
        19: _proto_scanner_parameters,
        20: _proto_scanner_data,
        21: _proto_tick_option,
        45: _proto_tick_generic,
        46: _proto_tick_string,
        49: _proto_current_time,
        50: _proto_realtime_bar,
        51: _proto_fundamental_data,
        52: _proto_contract_data_end,
        53: _proto_open_orders_end,
        54: _proto_account_data_end,
        55: _proto_execution_details_end,
        57: _proto_tick_snapshot_end,
        58: _proto_market_data_type,
        59: _proto_commission_report,
        61: _proto_position,
        62: _proto_position_end,
        63: _proto_account_summary,
        64: _proto_account_summary_end,
        71: _proto_position_multi,
        72: _proto_position_multi_end,
        73: _proto_account_update_multi,
        74: _proto_account_update_multi_end,
        75: _proto_sec_def_opt_param,
        76: _proto_sec_def_opt_param_end,
        77: _proto_soft_dollar_tiers,
        78: _proto_family_codes,
        79: _proto_symbol_samples,
        80: _proto_mkt_depth_exchanges,
        81: _proto_tick_req_params,
        82: _proto_smart_components,
        83: _proto_news_article,
        84: _proto_tick_news,
        85: _proto_news_providers,
        86: _proto_historical_news,
        87: _proto_historical_news_end,
        88: _proto_head_timestamp,
        89: _proto_histogram_data,
        90: _proto_historical_data_update,
        91: _proto_reroute_mkt_data,
        92: _proto_reroute_mkt_depth,
        93: _proto_market_rule,
        94: _proto_pnl,
        95: _proto_pnl_single,
        96: _proto_historical_ticks,
        97: _proto_historical_ticks_bid_ask,
        98: _proto_historical_ticks_last,
        99: _proto_tick_by_tick,
        100: _proto_order_bound,
        101: _proto_completed_order,
        102: _proto_completed_orders_end,
        103: _proto_replace_fa_end,
        104: _proto_wsh_meta_data,
        105: _proto_wsh_event_data,
        106: _proto_historical_schedule,
        107: _proto_user_info,
    }

    def interpret(self, fields):
        """Decode fields and invoke corresponding wrapper method."""
        try:
            msgId = int(fields[0])
            handler = self.handlers[msgId]
            handler(fields)
        except Exception:
            self.logger.exception(f'Error handling fields: {fields}')

    def parse(self, obj):
        """Parse the object's properties according to its default types."""
        for field in dataclasses.fields(obj):
            typ = type(field.default)
            if typ is str:
                continue
            v = getattr(obj, field.name)
            if typ is int:
                setattr(obj, field.name, int(v) if v else field.default)
            elif typ is float:
                setattr(obj, field.name, float(v) if v else field.default)
            elif typ is bool:
                setattr(obj, field.name, bool(int(v)) if v else field.default)

    def priceSizeTick(self, fields):
        _, _, reqId, tickType, price, size, _ = fields

        if price:
            self.wrapper.priceSizeTick(
                int(reqId), int(tickType), float(price), float(size or 0))

    def errorMsg(self, fields):
        _, _, reqId, errorCode, errorString, *fields = fields
        advancedOrderRejectJson = ''
        if self.serverVersion >= 166:
            advancedOrderRejectJson, *fields = fields
        self.wrapper.error(
            int(reqId), int(errorCode), errorString, advancedOrderRejectJson)

    def updatePortfolio(self, fields):
        c = Contract()
        (
            _, _,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.primaryExchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            marketPrice,
            marketValue,
            averageCost,
            unrealizedPNL,
            realizedPNL,
            accountName) = fields

        self.parse(c)
        self.wrapper.updatePortfolio(
            c, float(position), float(marketPrice),
            float(marketValue), float(averageCost), float(unrealizedPNL),
            float(realizedPNL), accountName)

    def contractDetails(self, fields):
        cd = ContractDetails()
        cd.contract = c = Contract()
        if self.serverVersion < 164:
            fields.pop(0)
        (
            _,
            reqId,
            c.symbol,
            c.secType,
            lastTimes,
            c.strike,
            c.right,
            c.exchange,
            c.currency,
            c.localSymbol,
            cd.marketName,
            c.tradingClass,
            c.conId,
            cd.minTick,
            *fields) = fields
        if self.serverVersion < 164:
            fields.pop(0)  # obsolete mdSizeMultiplier
        (
            c.multiplier,
            cd.orderTypes,
            cd.validExchanges,
            cd.priceMagnifier,
            cd.underConId,
            cd.longName,
            c.primaryExchange,
            cd.contractMonth,
            cd.industry,
            cd.category,
            cd.subcategory,
            cd.timeZoneId,
            cd.tradingHours,
            cd.liquidHours,
            cd.evRule,
            cd.evMultiplier,
            numSecIds,
            *fields) = fields

        numSecIds = int(numSecIds)
        if numSecIds > 0:
            cd.secIdList = []
            for _ in range(numSecIds):
                tag, value, *fields = fields
                cd.secIdList += [TagValue(tag, value)]
        (
            cd.aggGroup,
            cd.underSymbol,
            cd.underSecType,
            cd.marketRuleIds,
            cd.realExpirationDate,
            cd.stockType,
            *fields) = fields
        if self.serverVersion == 163:
            cd.suggestedSizeIncrement, *fields = fields
        if self.serverVersion >= 164:
            (
                cd.minSize,
                cd.sizeIncrement,
                cd.suggestedSizeIncrement,
                # cd.minCashQtySize,
                *fields) = fields

        if self.serverVersion >= 182:
            c.lastTradeDate = fields.pop(0)
        if self.serverVersion >= 179 and c.secType == 'FUND':
            (
                cd.fundName,
                cd.fundFamily,
                cd.fundType,
                cd.fundFrontLoad,
                cd.fundBackLoad,
                cd.fundBackLoadTimeInterval,
                cd.fundManagementFee,
                cd.fundClosed,
                cd.fundClosedForNewInvestors,
                cd.fundClosedForNewMoney,
                cd.fundNotifyAmount,
                cd.fundMinimumInitialPurchase,
                cd.fundSubsequentMinimumPurchase,
                cd.fundBlueSkyStates,
                cd.fundBlueSkyTerritories,
                cd.fundDistributionPolicyIndicator,
                cd.fundAssetType,
                *fields) = fields
        if self.serverVersion >= 186:
            numInelig = int(fields.pop(0))
            if numInelig > 0:
                cd.ineligibilityReasonList = []
                for _ in range(numInelig):
                    reason_id, reason_desc, *fields = fields
                    cd.ineligibilityReasonList.append((reason_id, reason_desc))

        times = lastTimes.split('-' if '-' in lastTimes else None)
        if len(times) > 0:
            c.lastTradeDateOrContractMonth = times[0]
        if len(times) > 1:
            cd.lastTradeTime = times[1]
        if len(times) > 2:
            cd.timeZoneId = times[2]

        cd.longName = cd.longName.encode().decode('unicode-escape')
        self.parse(cd)
        self.parse(c)
        self.wrapper.contractDetails(int(reqId), cd)

    def bondContractDetails(self, fields):
        cd = ContractDetails()
        cd.contract = c = Contract()
        if self.serverVersion < 164:
            fields.pop(0)
        (
            _,
            reqId,
            c.symbol,
            c.secType,
            cd.cusip,
            cd.coupon,
            lastTimes,
            cd.issueDate,
            cd.ratings,
            cd.bondType,
            cd.couponType,
            cd.convertible,
            cd.callable,
            cd.putable,
            cd.descAppend,
            c.exchange,
            c.currency,
            cd.marketName,
            c.tradingClass,
            c.conId,
            cd.minTick,
            *fields) = fields
        if self.serverVersion < 164:
            fields.pop(0)  # obsolete mdSizeMultiplier
        (
            cd.orderTypes,
            cd.validExchanges,
            cd.nextOptionDate,
            cd.nextOptionType,
            cd.nextOptionPartial,
            cd.notes,
            cd.longName,
            cd.evRule,
            cd.evMultiplier,
            numSecIds,
            *fields) = fields

        numSecIds = int(numSecIds)
        if numSecIds > 0:
            cd.secIdList = []
            for _ in range(numSecIds):
                tag, value, *fields = fields
                cd.secIdList += [TagValue(tag, value)]

        cd.aggGroup, cd.marketRuleIds, *fields = fields
        if self.serverVersion >= 164:
            (
                cd.minSize,
                cd.sizeIncrement,
                cd.suggestedSizeIncrement,
                # cd.minCashQtySize,
                *fields) = fields

        times = lastTimes.split('-' if '-' in lastTimes else None)
        if len(times) > 0:
            cd.maturity = times[0]
        if len(times) > 1:
            cd.lastTradeTime = times[1]
        if len(times) > 2:
            cd.timeZoneId = times[2]

        self.parse(cd)
        self.parse(c)
        self.wrapper.bondContractDetails(int(reqId), cd)

    def execDetails(self, fields):
        c = Contract()
        ex = Execution()
        (
            _,
            reqId,
            ex.orderId,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            ex.execId,
            timeStr,
            ex.acctNumber,
            ex.exchange,
            ex.side,
            ex.shares,
            ex.price,
            ex.permId,
            ex.clientId,
            ex.liquidation,
            ex.cumQty,
            ex.avgPrice,
            ex.orderRef,
            ex.evRule,
            ex.evMultiplier,
            ex.modelCode,
            ex.lastLiquidity,
            *fields) = fields
        if self.serverVersion >= 178:
            ex.pendingPriceRevision, *fields = fields

        self.parse(c)
        self.parse(ex)
        time = cast(datetime, parseIBDatetime(timeStr))
        if not time.tzinfo:
            tz = self.wrapper.ib.TimezoneTWS
            if tz:
                time = time.replace(tzinfo=ZoneInfo(str(tz)))
        ex.time = time.astimezone(timezone.utc)
        self.wrapper.execDetails(int(reqId), c, ex)

    def historicalData(self, fields):
        _, reqId, startDateStr, endDateStr, numBars, *fields = fields
        get = iter(fields).__next__

        for _ in range(int(numBars)):
            bar = BarData(
                date=get(),
                open=float(get()),
                high=float(get()),
                low=float(get()),
                close=float(get()),
                volume=float(get()),
                average=float(get()),
                barCount=int(get()))
            self.wrapper.historicalData(int(reqId), bar)

        self.wrapper.historicalDataEnd(int(reqId), startDateStr, endDateStr)

    def historicalDataUpdate(self, fields):
        _, reqId, *fields = fields
        get = iter(fields).__next__

        bar = BarData(
            barCount=int(get() or 0),
            date=get(),
            open=float(get() or 0),
            close=float(get() or 0),
            high=float(get() or 0),
            low=float(get() or 0),
            average=float(get() or 0),
            volume=float(get() or 0))

        self.wrapper.historicalDataUpdate(int(reqId), bar)

    def scannerData(self, fields):
        _, _, reqId, n, *fields = fields

        for _ in range(int(n)):
            cd = ContractDetails()
            cd.contract = c = Contract()
            (
                rank,
                c.conId,
                c.symbol,
                c.secType,
                c.lastTradeDateOrContractMonth,
                c.strike,
                c.right,
                c.exchange,
                c.currency,
                c.localSymbol,
                cd.marketName,
                c.tradingClass,
                distance,
                benchmark,
                projection,
                legsStr,
                *fields) = fields

            self.parse(cd)
            self.parse(c)
            self.wrapper.scannerData(
                int(reqId), int(rank), cd,
                distance, benchmark, projection, legsStr)

        self.wrapper.scannerDataEnd(int(reqId))

    def tickOptionComputation(self, fields):
        _, reqId, tickTypeInt, tickAttrib, *fields = fields
        impliedVol, delta, optPrice, pvDividend, \
            gamma, vega, theta, undPrice = fields

        self.wrapper.tickOptionComputation(
            int(reqId), int(tickTypeInt), int(tickAttrib),
            float(impliedVol), float(delta), float(optPrice),
            float(pvDividend), float(gamma), float(vega),
            float(theta), float(undPrice))

    def deltaNeutralValidation(self, fields):
        _, _, reqId, conId, delta, price = fields

        self.wrapper.deltaNeutralValidation(
            int(reqId), DeltaNeutralContract(
                int(conId), float(delta or 0), float(price or 0)))

    def commissionReport(self, fields):
        _, _, execId, commission, currency, realizedPNL, \
            yield_, yieldRedemptionDate = fields

        self.wrapper.commissionReport(
            CommissionReport(
                execId, float(commission or 0), currency,
                float(realizedPNL or 0), float(yield_ or 0),
                int(yieldRedemptionDate or 0)))

    def position(self, fields):
        c = Contract()
        (
            _, _,
            account,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            avgCost) = fields

        self.parse(c)
        self.wrapper.position(
            account, c, float(position or 0), float(avgCost or 0))

    def positionMulti(self, fields):
        c = Contract()
        (
            _, _,
            reqId,
            account,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            position,
            avgCost,
            modelCode) = fields

        self.parse(c)
        self.wrapper.positionMulti(
            int(reqId), account, modelCode, c,
            float(position or 0), float(avgCost or 0))

    def securityDefinitionOptionParameter(self, fields):
        _, reqId, exchange, underlyingConId, tradingClass, multiplier, \
            n, *fields = fields
        n = int(n)

        expirations = fields[:n]
        strikes = [float(field) for field in fields[n + 1:]]

        self.wrapper.securityDefinitionOptionParameter(
            int(reqId), exchange, underlyingConId, tradingClass,
            multiplier, expirations, strikes)

    def softDollarTiers(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        tiers = [
            SoftDollarTier(
                name=get(),
                val=get(),
                displayName=get())
            for _ in range(int(n))]

        self.wrapper.softDollarTiers(int(reqId), tiers)

    def familyCodes(self, fields):
        _, n, *fields = fields
        get = iter(fields).__next__

        familyCodes = [
            FamilyCode(
                accountID=get(),
                familyCodeStr=get())
            for _ in range(int(n))]

        self.wrapper.familyCodes(familyCodes)

    def symbolSamples(self, fields):
        _, reqId, n, *fields = fields

        cds = []
        for _ in range(int(n)):
            cd = ContractDescription()
            cd.contract = c = Contract()
            c.conId, c.symbol, c.secType, c.primaryExchange, c.currency, \
                m, *fields = fields
            c.conId = int(c.conId)
            m = int(m)
            cd.derivativeSecTypes = fields[:m]
            fields = fields[m:]
            if self.serverVersion >= 176:
                (
                    cd.contract.description,
                    cd.contract.issuerId,
                    *fields) = fields
            cds.append(cd)

        self.wrapper.symbolSamples(int(reqId), cds)

    def smartComponents(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        components = [
            SmartComponent(
                bitNumber=int(get()),
                exchange=get(),
                exchangeLetter=get())
            for _ in range(int(n))]

        self.wrapper.smartComponents(int(reqId), components)

    def mktDepthExchanges(self, fields):
        _, n, *fields = fields
        get = iter(fields).__next__

        descriptions = [
            DepthMktDataDescription(
                exchange=get(),
                secType=get(),
                listingExch=get(),
                serviceDataType=get(),
                aggGroup=int(get()))
            for _ in range(int(n))]

        self.wrapper.mktDepthExchanges(descriptions)

    def newsProviders(self, fields):
        _, n, *fields = fields
        get = iter(fields).__next__

        providers = [
            NewsProvider(
                code=get(),
                name=get())
            for _ in range(int(n))]

        self.wrapper.newsProviders(providers)

    def histogramData(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        histogram = [
            HistogramData(
                price=float(get()),
                count=int(get()))
            for _ in range(int(n))]

        self.wrapper.histogramData(int(reqId), histogram)

    def marketRule(self, fields):
        _, marketRuleId, n, *fields = fields
        get = iter(fields).__next__

        increments = [
            PriceIncrement(
                lowEdge=float(get()),
                increment=float(get()))
            for _ in range(int(n))]

        self.wrapper.marketRule(int(marketRuleId), increments)

    def historicalTicks(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        ticks = []
        for _ in range(int(n)):
            time = int(get())
            get()
            price = float(get())
            size = float(get())
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(
                HistoricalTick(dt, price, size))

        done = bool(int(get()))
        self.wrapper.historicalTicks(int(reqId), ticks, done)

    def historicalTicksBidAsk(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        ticks = []
        for _ in range(int(n)):
            time = int(get())
            mask = int(get())
            attrib = TickAttribBidAsk(
                askPastHigh=bool(mask & 1),
                bidPastLow=bool(mask & 2))
            priceBid = float(get())
            priceAsk = float(get())
            sizeBid = float(get())
            sizeAsk = float(get())
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(
                HistoricalTickBidAsk(
                    dt, attrib, priceBid, priceAsk, sizeBid, sizeAsk))

        done = bool(int(get()))
        self.wrapper.historicalTicksBidAsk(int(reqId), ticks, done)

    def historicalTicksLast(self, fields):
        _, reqId, n, *fields = fields
        get = iter(fields).__next__

        ticks = []
        for _ in range(int(n)):
            time = int(get())
            mask = int(get())
            attrib = TickAttribLast(
                pastLimit=bool(mask & 1),
                unreported=bool(mask & 2))
            price = float(get())
            size = float(get())
            exchange = get()
            specialConditions = get()
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(
                HistoricalTickLast(
                    dt, attrib, price, size, exchange, specialConditions))

        done = bool(int(get()))
        self.wrapper.historicalTicksLast(int(reqId), ticks, done)

    def tickByTick(self, fields):
        _, reqId, tickType, time, *fields = fields
        reqId = int(reqId)
        tickType = int(tickType)
        time = int(time)

        if tickType in (1, 2):
            price, size, mask, exchange, specialConditions = fields
            mask = int(mask)
            attrib: Any = TickAttribLast(
                pastLimit=bool(mask & 1),
                unreported=bool(mask & 2))

            self.wrapper.tickByTickAllLast(
                reqId, tickType, time, float(price), float(size),
                attrib, exchange, specialConditions)

        elif tickType == 3:
            bidPrice, askPrice, bidSize, askSize, mask = fields
            mask = int(mask)
            attrib = TickAttribBidAsk(
                bidPastLow=bool(mask & 1),
                askPastHigh=bool(mask & 2))

            self.wrapper.tickByTickBidAsk(
                reqId, time, float(bidPrice), float(askPrice),
                float(bidSize), float(askSize), attrib)

        elif tickType == 4:
            midPoint, = fields

            self.wrapper.tickByTickMidPoint(reqId, time, float(midPoint))

    def openOrder(self, fields):
        o = Order()
        c = Contract()
        st = OrderState()
        (
            _,
            o.orderId,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            o.action,
            o.totalQuantity,
            o.orderType,
            o.lmtPrice,
            o.auxPrice,
            o.tif,
            o.ocaGroup,
            o.account,
            o.openClose,
            o.origin,
            o.orderRef,
            o.clientId,
            o.permId,
            o.outsideRth,
            o.hidden,
            o.discretionaryAmt,
            o.goodAfterTime,
            _,
            o.faGroup,
            o.faMethod,
            o.faPercentage,
            *fields) = fields
        if self.serverVersion < 177:
            o.faProfile, *fields = fields
        (
            o.modelCode,
            o.goodTillDate,
            o.rule80A,
            o.percentOffset,
            o.settlingFirm,
            o.shortSaleSlot,
            o.designatedLocation,
            o.exemptCode,
            o.auctionStrategy,
            o.startingPrice,
            o.stockRefPrice,
            o.delta,
            o.stockRangeLower,
            o.stockRangeUpper,
            o.displaySize,
            o.blockOrder,
            o.sweepToFill,
            o.allOrNone,
            o.minQty,
            o.ocaType,
            o.eTradeOnly,
            o.firmQuoteOnly,
            o.nbboPriceCap,
            o.parentId,
            o.triggerMethod,
            o.volatility,
            o.volatilityType,
            o.deltaNeutralOrderType,
            o.deltaNeutralAuxPrice,
            *fields) = fields

        if o.deltaNeutralOrderType:
            (
                o.deltaNeutralConId,
                o.deltaNeutralSettlingFirm,
                o.deltaNeutralClearingAccount,
                o.deltaNeutralClearingIntent,
                o.deltaNeutralOpenClose,
                o.deltaNeutralShortSale,
                o.deltaNeutralShortSaleSlot,
                o.deltaNeutralDesignatedLocation,
                *fields) = fields
        (
            o.continuousUpdate,
            o.referencePriceType,
            o.trailStopPrice,
            o.trailingPercent,
            o.basisPoints,
            o.basisPointsType,
            c.comboLegsDescrip,
            *fields) = fields

        numLegs = int(fields.pop(0))
        c.comboLegs = []
        for _ in range(numLegs):
            leg: Any = ComboLeg()
            (
                leg.conId,
                leg.ratio,
                leg.action,
                leg.exchange,
                leg.openClose,
                leg.shortSaleSlot,
                leg.designatedLocation,
                leg.exemptCode,
                *fields) = fields
            self.parse(leg)
            c.comboLegs.append(leg)

        numOrderLegs = int(fields.pop(0))
        o.orderComboLegs = []
        for _ in range(numOrderLegs):
            leg = OrderComboLeg()
            leg.price = fields.pop(0)
            self.parse(leg)
            o.orderComboLegs.append(leg)

        numParams = int(fields.pop(0))
        if numParams > 0:
            o.smartComboRoutingParams = []
            for _ in range(numParams):
                tag, value, *fields = fields
                o.smartComboRoutingParams.append(
                    TagValue(tag, value))

        (
            o.scaleInitLevelSize,
            o.scaleSubsLevelSize,
            increment,
            *fields) = fields

        o.scalePriceIncrement = float(increment or UNSET_DOUBLE)
        if 0 < o.scalePriceIncrement < UNSET_DOUBLE:
            (
                o.scalePriceAdjustValue,
                o.scalePriceAdjustInterval,
                o.scaleProfitOffset,
                o.scaleAutoReset,
                o.scaleInitPosition,
                o.scaleInitFillQty,
                o.scaleRandomPercent,
                *fields) = fields

        o.hedgeType = fields.pop(0)
        if o.hedgeType:
            o.hedgeParam = fields.pop(0)

        (
            o.optOutSmartRouting,
            o.clearingAccount,
            o.clearingIntent,
            o.notHeld,
            dncPresent,
            *fields) = fields

        if int(dncPresent):
            conId, delta, price, *fields = fields
            c.deltaNeutralContract = DeltaNeutralContract(
                int(conId or 0), float(delta or 0), float(price or 0))

        o.algoStrategy = fields.pop(0)
        if o.algoStrategy:
            numParams = int(fields.pop(0))
            if numParams > 0:
                o.algoParams = []
                for _ in range(numParams):
                    tag, value, *fields = fields
                    o.algoParams.append(
                        TagValue(tag, value))

        (
            o.solicited,
            o.whatIf,
            st.status,
            st.initMarginBefore,
            st.maintMarginBefore,
            st.equityWithLoanBefore,
            st.initMarginChange,
            st.maintMarginChange,
            st.equityWithLoanChange,
            st.initMarginAfter,
            st.maintMarginAfter,
            st.equityWithLoanAfter,
            st.commission,
            st.minCommission,
            st.maxCommission,
            st.commissionCurrency,
            st.warningText,
            o.randomizeSize,
            o.randomizePrice,
            *fields) = fields

        if o.orderType in ('PEG BENCH', 'PEGBENCH'):
            (
                o.referenceContractId,
                o.isPeggedChangeAmountDecrease,
                o.peggedChangeAmount,
                o.referenceChangeAmount,
                o.referenceExchangeId,
                *fields) = fields

        numConditions = int(fields.pop(0))
        if numConditions > 0:
            for _ in range(numConditions):
                condType = int(fields.pop(0))
                condCls = OrderCondition.createClass(condType)
                n = len(dataclasses.fields(condCls)) - 1
                cond = condCls(condType, *fields[:n])
                self.parse(cond)
                o.conditions.append(cond)
                fields = fields[n:]
            (
                o.conditionsIgnoreRth,
                o.conditionsCancelOrder,
                *fields) = fields

        (
            o.adjustedOrderType,
            o.triggerPrice,
            o.trailStopPrice,
            o.lmtPriceOffset,
            o.adjustedStopPrice,
            o.adjustedStopLimitPrice,
            o.adjustedTrailingAmount,
            o.adjustableTrailingUnit,
            o.softDollarTier.name,
            o.softDollarTier.val,
            o.softDollarTier.displayName,
            o.cashQty,
            o.dontUseAutoPriceForHedge,
            o.isOmsContainer,
            o.discretionaryUpToLimitPrice,
            o.usePriceMgmtAlgo,
            *fields) = fields

        if self.serverVersion >= 159:
            o.duration = fields.pop(0)
        if self.serverVersion >= 160:
            o.postToAts = fields.pop(0)
        if self.serverVersion >= 162:
            o.autoCancelParent = fields.pop(0)
        if self.serverVersion >= 170:
            (
                o.minTradeQty,
                o.minCompeteSize,
                o.competeAgainstBestOffset,
                o.midOffsetAtWhole,
                o.midOffsetAtHalf,
                *fields) = fields
        if self.serverVersion >= 183:
            o.customerAccount = fields.pop(0)
        if self.serverVersion >= 184:
            o.professionalCustomer = fields.pop(0)
        if self.serverVersion >= 185:
            o.bondAccruedInterest = fields.pop(0)
        if self.serverVersion >= 189:
            o.includeOvernight = fields.pop(0)
        if self.serverVersion >= 193:
            o.extOperator = fields.pop(0)
            o.manualOrderIndicator = fields.pop(0)
        if self.serverVersion >= 198:
            o.submitter = fields.pop(0)
        if self.serverVersion >= 199:
            o.imbalanceOnly = fields.pop(0)

        self.parse(c)
        self.parse(o)
        self.parse(st)
        self.wrapper.openOrder(o.orderId, c, o, st)

    def completedOrder(self, fields):
        o = Order()
        c = Contract()
        st = OrderState()

        (
            _,
            c.conId,
            c.symbol,
            c.secType,
            c.lastTradeDateOrContractMonth,
            c.strike,
            c.right,
            c.multiplier,
            c.exchange,
            c.currency,
            c.localSymbol,
            c.tradingClass,
            o.action,
            o.totalQuantity,
            o.orderType,
            o.lmtPrice,
            o.auxPrice,
            o.tif,
            o.ocaGroup,
            o.account,
            o.openClose,
            o.origin,
            o.orderRef,
            o.permId,
            o.outsideRth,
            o.hidden,
            o.discretionaryAmt,
            o.goodAfterTime,
            o.faGroup,
            o.faMethod,
            o.faPercentage,
            *fields) = fields
        if self.serverVersion < 177:
            o.faProfile, *fields = fields
        (
            o.modelCode,
            o.goodTillDate,
            o.rule80A,
            o.percentOffset,
            o.settlingFirm,
            o.shortSaleSlot,
            o.designatedLocation,
            o.exemptCode,
            o.startingPrice,
            o.stockRefPrice,
            o.delta,
            o.stockRangeLower,
            o.stockRangeUpper,
            o.displaySize,
            o.sweepToFill,
            o.allOrNone,
            o.minQty,
            o.ocaType,
            o.triggerMethod,
            o.volatility,
            o.volatilityType,
            o.deltaNeutralOrderType,
            o.deltaNeutralAuxPrice,
            *fields) = fields

        if o.deltaNeutralOrderType:
            (
                o.deltaNeutralConId,
                o.deltaNeutralShortSale,
                o.deltaNeutralShortSaleSlot,
                o.deltaNeutralDesignatedLocation,
                *fields) = fields
        (
            o.continuousUpdate,
            o.referencePriceType,
            o.trailStopPrice,
            o.trailingPercent,
            c.comboLegsDescrip,
            *fields) = fields

        numLegs = int(fields.pop(0))
        c.comboLegs = []
        for _ in range(numLegs):
            leg: Any = ComboLeg()
            (
                leg.conId,
                leg.ratio,
                leg.action,
                leg.exchange,
                leg.openClose,
                leg.shortSaleSlot,
                leg.designatedLocation,
                leg.exemptCode,
                *fields) = fields
            self.parse(leg)
            c.comboLegs.append(leg)

        numOrderLegs = int(fields.pop(0))
        o.orderComboLegs = []
        for _ in range(numOrderLegs):
            leg = OrderComboLeg()
            leg.price = fields.pop(0)
            self.parse(leg)
            o.orderComboLegs.append(leg)

        numParams = int(fields.pop(0))
        if numParams > 0:
            o.smartComboRoutingParams = []
            for _ in range(numParams):
                tag, value, *fields = fields
                o.smartComboRoutingParams.append(
                    TagValue(tag, value))
        (
            o.scaleInitLevelSize,
            o.scaleSubsLevelSize,
            increment,
            *fields) = fields

        o.scalePriceIncrement = float(increment or UNSET_DOUBLE)
        if 0 < o.scalePriceIncrement < UNSET_DOUBLE:
            (
                o.scalePriceAdjustValue,
                o.scalePriceAdjustInterval,
                o.scaleProfitOffset,
                o.scaleAutoReset,
                o.scaleInitPosition,
                o.scaleInitFillQty,
                o.scaleRandomPercent,
                *fields) = fields

        o.hedgeType = fields.pop(0)
        if o.hedgeType:
            o.hedgeParam = fields.pop(0)

        (
            o.clearingAccount,
            o.clearingIntent,
            o.notHeld,
            dncPresent,
            *fields) = fields

        if int(dncPresent):
            conId, delta, price, *fields = fields
            c.deltaNeutralContract = DeltaNeutralContract(
                int(conId or 0), float(delta or 0), float(price or 0))

        o.algoStrategy = fields.pop(0)
        if o.algoStrategy:
            numParams = int(fields.pop(0))
            if numParams > 0:
                o.algoParams = []
                for _ in range(numParams):
                    tag, value, *fields = fields
                    o.algoParams.append(
                        TagValue(tag, value))
        (
            o.solicited,
            st.status,
            o.randomizeSize,
            o.randomizePrice,
            *fields) = fields

        if o.orderType in ('PEG BENCH', 'PEGBENCH'):
            (
                o.referenceContractId,
                o.isPeggedChangeAmountDecrease,
                o.peggedChangeAmount,
                o.referenceChangeAmount,
                o.referenceExchangeId,
                *fields) = fields

        numConditions = int(fields.pop(0))
        if numConditions > 0:
            for _ in range(numConditions):
                condType = int(fields.pop(0))
                condCls = OrderCondition.createClass(condType)
                n = len(dataclasses.fields(condCls)) - 1
                cond = condCls(condType, *fields[:n])
                self.parse(cond)
                o.conditions.append(cond)
                fields = fields[n:]
            (
                o.conditionsIgnoreRth,
                o.conditionsCancelOrder,
                *fields) = fields

        (
            o.trailStopPrice,
            o.lmtPriceOffset,
            o.cashQty,
            o.dontUseAutoPriceForHedge,
            o.isOmsContainer,
            o.autoCancelDate,
            o.filledQuantity,
            o.refFuturesConId,
            o.autoCancelParent,
            o.shareholder,
            o.imbalanceOnly,
            o.routeMarketableToBbo,
            o.parentPermId,
            st.completedTime,
            st.completedStatus,
            *fields) = fields

        if self.serverVersion >= 170:
            (
                o.minTradeQty,
                o.minCompeteSize,
                o.competeAgainstBestOffset,
                o.midOffsetAtWhole,
                o.midOffsetAtHalf,
                *fields) = fields
        if self.serverVersion >= 183:
            o.customerAccount = fields.pop(0)
        if self.serverVersion >= 184:
            o.professionalCustomer = fields.pop(0)
        if self.serverVersion >= 198:
            o.submitter = fields.pop(0)

        self.parse(c)
        self.parse(o)
        self.parse(st)
        self.wrapper.completedOrder(c, o, st)

    def historicalSchedule(self, fields):
        (
            _,
            reqId,
            startDateTime,
            endDateTime,
            timeZone,
            count, *fields) = fields
        get = iter(fields).__next__
        sessions = [HistoricalSession(
            startDateTime=get(), endDateTime=get(), refDate=get())
            for _ in range(int(count))]
        self.wrapper.historicalSchedule(
            int(reqId), startDateTime, endDateTime, timeZone, sessions)
