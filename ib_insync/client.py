"""Socket client for communicating with Interactive Brokers."""

import asyncio
import io
import logging
import math
import struct
import time
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wrapper import Wrapper

from eventkit import Event

from .connection import Connection
from .contract import Contract
from .decoder import Decoder
from .objects import ConnectionStats, WshEventData
from .util import UNSET_DOUBLE, UNSET_INTEGER, dataclassAsTuple, getLoop, run


class Client:
    """
    Replacement for ``ibapi.client.EClient`` that uses asyncio.

    The client is fully asynchronous and has its own
    event-driven networking code that replaces the
    networking code of the standard EClient.
    It also replaces the infinite loop of ``EClient.run()``
    with the asyncio event loop. It can be used as a drop-in
    replacement for the standard EClient as provided by IBAPI.

    Compared to the standard EClient this client has the following
    additional features:

    * ``client.connect()`` will block until the client is ready to
      serve requests; It is not necessary to wait for ``nextValidId``
      to start requests as the client has already done that.
      The reqId is directly available with :py:meth:`.getReqId()`.

    * ``client.connectAsync()`` is a coroutine for connecting asynchronously.

    * When blocking, ``client.connect()`` can be made to time out with
      the timeout parameter (default 2 seconds).

    * Optional ``wrapper.priceSizeTick(reqId, tickType, price, size)`` that
      combines price and size instead of the two wrapper methods
      priceTick and sizeTick.

    * Automatic request throttling.

    * Optional ``wrapper.tcpDataArrived()`` method;
      If the wrapper has this method it is invoked directly after
      a network packet has arrived.
      A possible use is to timestamp all data in the packet with
      the exact same time.

    * Optional ``wrapper.tcpDataProcessed()`` method;
      If the wrapper has this method it is invoked after the
      network packet's data has been handled.
      A possible use is to write or evaluate the newly arrived data in
      one batch instead of item by item.

    Parameters:
      MaxRequests (int):
        Throttle the number of requests to ``MaxRequests`` per
        ``RequestsInterval`` seconds. Set to 0 to disable throttling.
      RequestsInterval (float):
        Time interval (in seconds) for request throttling.
      MinClientVersion (int):
        Client protocol version.
      MaxClientVersion (int):
        Client protocol version.

    Events:
      * ``apiStart`` ()
      * ``apiEnd`` ()
      * ``apiError`` (errorMsg: str)
      * ``throttleStart`` ()
      * ``throttleEnd`` ()
    """

    events = ('apiStart', 'apiEnd', 'apiError', 'throttleStart', 'throttleEnd')

    MaxRequests = 45
    RequestsInterval = 1

    MinClientVersion = 157
    MaxClientVersion = 225

    # Server version gates added between v179 and v225
    MIN_SERVER_VER_FUND_DATA_FIELDS = 179
    MIN_SERVER_VER_LAST_TRADE_DATE = 182
    MIN_SERVER_VER_CUSTOMER_ACCOUNT = 183
    MIN_SERVER_VER_PROFESSIONAL_CUSTOMER = 184
    MIN_SERVER_VER_BOND_ACCRUED_INTEREST = 185
    MIN_SERVER_VER_INELIGIBILITY_REASONS = 186
    MIN_SERVER_VER_RFQ_FIELDS = 187
    MIN_SERVER_VER_BOND_TRADING_HOURS = 188
    MIN_SERVER_VER_INCLUDE_OVERNIGHT = 189
    MIN_SERVER_VER_UNDO_RFQ_FIELDS = 190
    MIN_SERVER_VER_CME_TAGGING_FIELDS = 192
    MIN_SERVER_VER_CME_TAGGING_FIELDS_IN_OPEN_ORDER = 193
    MIN_SERVER_VER_ERROR_TIME = 194
    MIN_SERVER_VER_HISTORICAL_DATA_END = 196
    MIN_SERVER_VER_SUBMITTER = 198
    MIN_SERVER_VER_IMBALANCE_ONLY = 199
    MIN_SERVER_VER_PARAMETRIZED_DAYS_OF_EXECUTIONS = 200
    MIN_SERVER_VER_PROTOBUF = 201
    MIN_SERVER_VER_PROTOBUF_PLACE_ORDER = 203
    MIN_SERVER_VER_PROTOBUF_COMPLETED_ORDER = 204
    MIN_SERVER_VER_PROTOBUF_CONTRACT_DATA = 205
    MIN_SERVER_VER_PROTOBUF_MARKET_DATA = 206
    MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS = 207
    MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA = 208
    MIN_SERVER_VER_PROTOBUF_NEWS_DATA = 209
    MIN_SERVER_VER_PROTOBUF_SCAN_DATA = 210
    MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_1 = 211
    MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2 = 212
    MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_3 = 213
    MIN_SERVER_VER_CANCEL_CONTRACT_DATA = 215
    MIN_SERVER_VER_ADDITIONAL_ORDER_PARAMS_1 = 216
    MIN_SERVER_VER_ADDITIONAL_ORDER_PARAMS_2 = 217
    MIN_SERVER_VER_ATTACHED_ORDERS = 218
    MIN_SERVER_VER_HEDGE_MAX_SIZE = 223
    MIN_SERVER_VER_ODD_LOT_BID_ASK_QUOTES = 225

    PROTOBUF_MSG_ID = 200

    # Maps outbound message id -> minimum server version for protobuf encoding
    PROTOBUF_MSG_IDS: dict[int, int] = {
        7: MIN_SERVER_VER_PROTOBUF,           # REQ_EXECUTIONS
        3: MIN_SERVER_VER_PROTOBUF_PLACE_ORDER,  # PLACE_ORDER
        4: MIN_SERVER_VER_PROTOBUF_PLACE_ORDER,  # CANCEL_ORDER
        58: MIN_SERVER_VER_PROTOBUF_PLACE_ORDER,  # REQ_GLOBAL_CANCEL
        16: MIN_SERVER_VER_PROTOBUF_COMPLETED_ORDER,  # REQ_ALL_OPEN_ORDERS
        15: MIN_SERVER_VER_PROTOBUF_COMPLETED_ORDER,  # REQ_AUTO_OPEN_ORDERS
        26: MIN_SERVER_VER_PROTOBUF_COMPLETED_ORDER,  # REQ_OPEN_ORDERS
        86: MIN_SERVER_VER_PROTOBUF_COMPLETED_ORDER,  # REQ_COMPLETED_ORDERS
        9: MIN_SERVER_VER_PROTOBUF_CONTRACT_DATA,    # REQ_CONTRACT_DATA
        1: MIN_SERVER_VER_PROTOBUF_MARKET_DATA,      # REQ_MKT_DATA
        2: MIN_SERVER_VER_PROTOBUF_MARKET_DATA,      # CANCEL_MKT_DATA
        10: MIN_SERVER_VER_PROTOBUF_MARKET_DATA,     # REQ_MKT_DEPTH
        11: MIN_SERVER_VER_PROTOBUF_MARKET_DATA,     # CANCEL_MKT_DEPTH
        59: MIN_SERVER_VER_PROTOBUF_MARKET_DATA,     # REQ_MARKET_DATA_TYPE
        6: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,   # REQ_ACCT_DATA
        17: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # REQ_MANAGED_ACCTS
        61: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # REQ_POSITIONS
        64: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # CANCEL_POSITIONS
        62: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # REQ_ACCOUNT_SUMMARY
        63: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # CANCEL_ACCOUNT_SUMMARY
        74: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # REQ_POSITIONS_MULTI
        75: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # CANCEL_POSITIONS_MULTI
        76: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # REQ_ACCOUNT_UPDATES_MULTI
        77: MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS,  # CANCEL_ACCOUNT_UPDATES_MULTI
        20: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # REQ_HISTORICAL_DATA
        25: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # CANCEL_HISTORICAL_DATA
        50: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # REQ_REAL_TIME_BARS
        51: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # CANCEL_REAL_TIME_BARS
        87: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # REQ_HEAD_TIMESTAMP
        88: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # CANCEL_HEAD_TIMESTAMP
        89: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # REQ_HISTOGRAM_DATA
        90: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # CANCEL_HISTOGRAM_DATA
        96: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # REQ_HISTORICAL_TICKS
        97: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # REQ_TICK_BY_TICK_DATA
        98: MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA,     # CANCEL_TICK_BY_TICK_DATA
        12: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,           # REQ_NEWS_BULLETINS
        13: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,           # CANCEL_NEWS_BULLETINS
        84: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,           # REQ_NEWS_ARTICLE
        85: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,           # REQ_NEWS_PROVIDERS
        83: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,           # REQ_HISTORICAL_NEWS
        100: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,          # REQ_WSH_META_DATA
        101: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,          # CANCEL_WSH_META_DATA
        102: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,          # REQ_WSH_EVENT_DATA
        103: MIN_SERVER_VER_PROTOBUF_NEWS_DATA,          # CANCEL_WSH_EVENT_DATA
        24: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # REQ_SCANNER_PARAMETERS
        22: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # REQ_SCANNER_SUBSCRIPTION
        23: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # CANCEL_SCANNER_SUBSCRIPTION
        52: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # REQ_FUNDAMENTAL_DATA
        53: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # CANCEL_FUNDAMENTAL_DATA
        92: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # REQ_PNL
        93: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # CANCEL_PNL
        94: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # REQ_PNL_SINGLE
        95: MIN_SERVER_VER_PROTOBUF_SCAN_DATA,           # CANCEL_PNL_SINGLE
        18: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_1,     # REQ_FA
        19: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_1,     # REPLACE_FA
        78: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,     # REQ_SEC_DEF_OPT_PARAMS
        79: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,     # REQ_SOFT_DOLLAR_TIERS
        80: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,     # REQ_FAMILY_CODES
        81: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,     # REQ_MATCHING_SYMBOLS
        60: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,     # REQ_SMART_COMPONENTS
        91: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,     # REQ_MARKET_RULE
        104: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2,    # REQ_USER_INFO
        8: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_3,      # REQ_IDS
        49: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_3,     # REQ_CURRENT_TIME
        71: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_3,     # START_API
        14: MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_3,     # SET_SERVER_LOGLEVEL
    }

    (DISCONNECTED, CONNECTING, CONNECTED) = range(3)

    def __init__(self, wrapper: "Wrapper") -> None:
        self.wrapper = wrapper
        self.decoder = Decoder(wrapper, 0)
        self.apiStart = Event('apiStart')
        self.apiEnd = Event('apiEnd')
        self.apiError = Event('apiError')
        self.throttleStart = Event('throttleStart')
        self.throttleEnd = Event('throttleEnd')
        self._logger = logging.getLogger('ib_insync.client')

        self.conn = Connection()
        self.conn.hasData += self._onSocketHasData
        self.conn.disconnected += self._onSocketDisconnected

        # extra optional wrapper methods
        self._priceSizeTick = getattr(wrapper, 'priceSizeTick', None)
        self._tcpDataArrived = getattr(wrapper, 'tcpDataArrived', None)
        self._tcpDataProcessed = getattr(wrapper, 'tcpDataProcessed', None)

        self.host = ''
        self.port = -1
        self.clientId = -1
        self.optCapab = ''
        self.connectOptions = b''
        self.reset()

    def reset(self):
        self.connState = Client.DISCONNECTED
        self._apiReady = False
        self._serverVersion = 0
        self._data = b''
        self._hasReqId = False
        self._reqIdSeq = 0
        self._accounts = []
        self._startTime = time.time()
        self._numBytesRecv = 0
        self._numMsgRecv = 0
        self._isThrottling = False
        self._msgQ: deque[str | bytes] = deque()
        self._timeQ: deque[float] = deque()

    def serverVersion(self) -> int:
        return self._serverVersion

    def run(self):
        loop = getLoop()
        loop.run_forever()

    def isConnected(self):
        return self.connState == Client.CONNECTED

    def isReady(self) -> bool:
        """Is the API connection up and running?"""
        return self._apiReady

    def connectionStats(self) -> ConnectionStats:
        """Get statistics about the connection."""
        if not self.isReady():
            raise ConnectionError('Not connected')
        return ConnectionStats(
            self._startTime,
            time.time() - self._startTime,
            self._numBytesRecv, self.conn.numBytesSent,
            self._numMsgRecv, self.conn.numMsgSent)

    def getReqId(self) -> int:
        """Get new request ID."""
        if not self.isReady():
            raise ConnectionError('Not connected')
        newId = self._reqIdSeq
        self._reqIdSeq += 1
        return newId

    def updateReqId(self, minReqId):
        """Update the next reqId to be at least ``minReqId``."""
        self._reqIdSeq = max(self._reqIdSeq, minReqId)

    def getAccounts(self) -> list[str]:
        """Get the list of account names that are under management."""
        if not self.isReady():
            raise ConnectionError('Not connected')
        return self._accounts

    def setConnectOptions(self, connectOptions: str):
        """
        Set additional connect options.

        Args:
            connectOptions: Use "+PACEAPI" to use request-pacing built
                into TWS/gateway 974+ (obsolete).
        """
        self.connectOptions = connectOptions.encode()

    def connect(
            self, host: str, port: int, clientId: int,
            timeout: float | None = 2.0):
        """
        Connect to a running TWS or IB gateway application.

        Args:
            host: Host name or IP address.
            port: Port number.
            clientId: ID number to use for this client; must be unique per
                connection.
            timeout: If establishing the connection takes longer than
                ``timeout`` seconds then the ``asyncio.TimeoutError`` exception
                is raised. Set to 0 to disable timeout.
        """
        run(self.connectAsync(host, port, clientId, timeout))

    async def connectAsync(self, host, port, clientId, timeout=2.0):
        try:
            self._logger.info(
                f'Connecting to {host}:{port} with clientId {clientId}...')
            self.host = host
            self.port = int(port)
            self.clientId = int(clientId)
            self.connState = Client.CONNECTING
            timeout = timeout or None
            await asyncio.wait_for(self.conn.connectAsync(host, port), timeout)
            self._logger.info('Connected')
            connectOpts = b' ' + self.connectOptions if self.connectOptions else b''
            msg = b'API\0' + self._prefix(f'v{self.MinClientVersion}..{self.MaxClientVersion}{connectOpts.decode()}'.encode())
            self.conn.sendMsg(msg)
            await asyncio.wait_for(self.apiStart, timeout)
            self._logger.info('API connection ready')
        except BaseException as e:
            self.disconnect()
            msg = f'API connection failed: {e!r}'
            self._logger.error(msg)
            self.apiError.emit(msg)
            if isinstance(e, ConnectionRefusedError):
                self._logger.error('Make sure API port on TWS/IBG is open')
            raise

    def disconnect(self):
        """Disconnect from IB connection."""
        self._logger.info('Disconnecting')
        self.connState = Client.DISCONNECTED
        self.conn.disconnect()
        self.reset()

    def send(self, *fields, makeEmpty=True):
        """Serialize and send the given fields using the IB socket protocol."""
        if not self.isConnected():
            raise ConnectionError('Not connected')

        msg = io.StringIO()
        empty = (None, UNSET_INTEGER, UNSET_DOUBLE) if makeEmpty else (None,)
        for field in fields:
            typ = type(field)
            if field in empty:
                s = ''
            elif typ is str:
                s = field
            elif type is int:
                s = str(field)
            elif typ is float:
                s = 'Infinite' if field == math.inf else str(field)
            elif typ is bool:
                s = '1' if field else '0'
            elif typ is list:
                # list of TagValue
                s = ''.join(f'{v.tag}={v.value};' for v in field)
            elif isinstance(field, Contract):
                c = field
                s = '\0'.join(str(f) for f in (
                    c.conId, c.symbol, c.secType,
                    c.lastTradeDateOrContractMonth, c.strike,
                    c.right, c.multiplier, c.exchange,
                    c.primaryExchange, c.currency,
                    c.localSymbol, c.tradingClass))
            else:
                s = str(field)
            msg.write(s)
            msg.write('\0')
        self.sendMsg(msg.getvalue())

    def useProtoBuf(self, msgId: int) -> bool:
        """True when the server supports protobuf encoding for this outbound message id."""
        min_ver = self.PROTOBUF_MSG_IDS.get(msgId)
        return min_ver is not None and self._serverVersion >= min_ver

    def sendProto(self, msgId: int, proto_msg) -> None:
        """Serialize and queue a protobuf outbound message."""
        payload = proto_msg.SerializeToString()
        self.sendMsg((msgId + self.PROTOBUF_MSG_ID).to_bytes(4, 'big') + payload)

    @staticmethod
    def _contractToProto(contract: 'Contract'):
        from .protobuf.Contract_pb2 import Contract as ContractProto
        p = ContractProto()
        p.conId = contract.conId
        p.symbol = contract.symbol
        p.secType = contract.secType
        p.lastTradeDateOrContractMonth = contract.lastTradeDateOrContractMonth
        p.strike = contract.strike
        p.right = contract.right
        p.multiplier = float(contract.multiplier) if contract.multiplier else 0.0
        p.exchange = contract.exchange
        p.primaryExch = contract.primaryExchange
        p.currency = contract.currency
        p.localSymbol = contract.localSymbol
        p.tradingClass = contract.tradingClass
        p.secIdType = contract.secIdType
        p.secId = contract.secId
        p.description = contract.description
        p.issuerId = contract.issuerId
        p.comboLegsDescrip = contract.comboLegsDescrip
        for leg in (contract.comboLegs or []):
            leg_p = p.comboLegs.add()
            leg_p.conId = leg.conId
            leg_p.ratio = leg.ratio
            leg_p.action = leg.action
            leg_p.exchange = leg.exchange
            leg_p.openClose = leg.openClose
            leg_p.shortSaleSlot = leg.shortSaleSlot
            leg_p.designatedLocation = leg.designatedLocation
            leg_p.exemptCode = leg.exemptCode
        if contract.deltaNeutralContract:
            dnc = contract.deltaNeutralContract
            p.deltaNeutralContract.conId = dnc.conId
            p.deltaNeutralContract.delta = dnc.delta
            p.deltaNeutralContract.price = dnc.price
        return p

    @staticmethod
    def _orderToProto(order):
        from .protobuf.Order_pb2 import Order as OrderProto
        p = OrderProto()
        p.clientId = order.clientId
        p.orderId = order.orderId
        p.permId = order.permId
        p.parentId = order.parentId
        p.action = order.action
        p.totalQuantity = str(order.totalQuantity)
        p.displaySize = order.displaySize
        p.orderType = order.orderType
        if order.lmtPrice != UNSET_DOUBLE:
            p.lmtPrice = order.lmtPrice
        if order.auxPrice != UNSET_DOUBLE:
            p.auxPrice = order.auxPrice
        p.tif = order.tif
        p.account = order.account
        p.settlingFirm = order.settlingFirm
        p.clearingAccount = order.clearingAccount
        p.clearingIntent = order.clearingIntent
        p.allOrNone = order.allOrNone
        p.blockOrder = order.blockOrder
        p.hidden = order.hidden
        p.outsideRth = order.outsideRth
        p.sweepToFill = order.sweepToFill
        if order.percentOffset != UNSET_DOUBLE:
            p.percentOffset = order.percentOffset
        p.trailingPercent = order.trailingPercent
        p.trailStopPrice = order.trailStopPrice
        if order.minQty != UNSET_INTEGER:
            p.minQty = order.minQty
        p.goodAfterTime = order.goodAfterTime
        p.goodTillDate = order.goodTillDate
        p.ocaGroup = order.ocaGroup
        p.orderRef = order.orderRef
        p.rule80A = order.rule80A
        p.ocaType = order.ocaType
        p.triggerMethod = order.triggerMethod
        p.activeStartTime = order.activeStartTime
        p.activeStopTime = order.activeStopTime
        p.faGroup = order.faGroup
        p.faMethod = order.faMethod
        p.faPercentage = order.faPercentage
        p.modelCode = order.modelCode
        p.openClose = order.openClose
        p.origin = order.origin
        p.shortSaleSlot = order.shortSaleSlot
        p.designatedLocation = order.designatedLocation
        p.exemptCode = order.exemptCode
        p.discretionaryAmt = order.discretionaryAmt
        if order.volatility != UNSET_DOUBLE:
            p.volatility = order.volatility
        if order.volatilityType != UNSET_INTEGER:
            p.volatilityType = order.volatilityType
        p.deltaNeutralOrderType = order.deltaNeutralOrderType
        if order.deltaNeutralAuxPrice != UNSET_DOUBLE:
            p.deltaNeutralAuxPrice = order.deltaNeutralAuxPrice
        p.deltaNeutralConId = order.deltaNeutralConId
        p.deltaNeutralOpenClose = order.deltaNeutralOpenClose
        p.deltaNeutralShortSale = order.deltaNeutralShortSale
        p.deltaNeutralShortSaleSlot = order.deltaNeutralShortSaleSlot
        p.deltaNeutralDesignatedLocation = order.deltaNeutralDesignatedLocation
        p.deltaNeutralSettlingFirm = order.deltaNeutralSettlingFirm
        p.deltaNeutralClearingAccount = order.deltaNeutralClearingAccount
        p.deltaNeutralClearingIntent = order.deltaNeutralClearingIntent
        if order.scaleInitLevelSize != UNSET_INTEGER:
            p.scaleInitLevelSize = order.scaleInitLevelSize
        if order.scaleSubsLevelSize != UNSET_INTEGER:
            p.scaleSubsLevelSize = order.scaleSubsLevelSize
        if order.scalePriceIncrement != UNSET_DOUBLE:
            p.scalePriceIncrement = order.scalePriceIncrement
        p.scaleAutoReset = order.scaleAutoReset
        if order.scaleInitPosition != UNSET_INTEGER:
            p.scaleInitPosition = order.scaleInitPosition
        if order.scaleInitFillQty != UNSET_INTEGER:
            p.scaleInitFillQty = order.scaleInitFillQty
        p.scaleRandomPercent = order.scaleRandomPercent
        p.scaleTable = order.scaleTable
        p.hedgeType = order.hedgeType
        p.hedgeParam = order.hedgeParam
        p.algoStrategy = order.algoStrategy
        for tv in (order.algoParams or []):
            p.algoParams[tv.tag] = tv.value
        p.algoId = order.algoId
        for tv in (order.smartComboRoutingParams or []):
            p.smartComboRoutingParams[tv.tag] = tv.value
        p.whatIf = order.whatIf
        p.transmit = order.transmit
        p.overridePercentageConstraints = order.overridePercentageConstraints
        p.notHeld = order.notHeld
        p.solicited = order.solicited
        p.randomizeSize = order.randomizeSize
        p.randomizePrice = order.randomizePrice
        p.referenceContractId = order.referenceContractId
        p.peggedChangeAmount = order.peggedChangeAmount
        p.isPeggedChangeAmountDecrease = order.isPeggedChangeAmountDecrease
        p.referenceChangeAmount = order.referenceChangeAmount
        p.referenceExchangeId = order.referenceExchangeId
        p.adjustedOrderType = order.adjustedOrderType
        if order.triggerPrice != UNSET_DOUBLE:
            p.triggerPrice = order.triggerPrice
        p.adjustedStopPrice = order.adjustedStopPrice
        p.adjustedStopLimitPrice = order.adjustedStopLimitPrice
        p.adjustedTrailingAmount = order.adjustedTrailingAmount
        p.adjustableTrailingUnit = order.adjustableTrailingUnit
        if order.lmtPriceOffset != UNSET_DOUBLE:
            p.lmtPriceOffset = order.lmtPriceOffset
        p.conditionsCancelOrder = order.conditionsCancelOrder
        p.conditionsIgnoreRth = order.conditionsIgnoreRth
        p.extOperator = order.extOperator
        p.softDollarTier.name = order.softDollarTier.name
        p.softDollarTier.value = order.softDollarTier.val
        p.softDollarTier.displayName = order.softDollarTier.displayName
        if order.cashQty != UNSET_DOUBLE:
            p.cashQty = order.cashQty
        p.mifid2DecisionMaker = order.mifid2DecisionMaker
        p.mifid2DecisionAlgo = order.mifid2DecisionAlgo
        p.mifid2ExecutionTrader = order.mifid2ExecutionTrader
        p.mifid2ExecutionAlgo = order.mifid2ExecutionAlgo
        p.dontUseAutoPriceForHedge = order.dontUseAutoPriceForHedge
        p.isOmsContainer = order.isOmsContainer
        p.discretionaryUpToLimitPrice = order.discretionaryUpToLimitPrice
        p.autoCancelDate = order.autoCancelDate
        if order.filledQuantity != UNSET_DOUBLE:
            p.filledQuantity = str(order.filledQuantity)
        p.refFuturesConId = order.refFuturesConId
        p.autoCancelParent = order.autoCancelParent
        p.shareholder = order.shareholder
        p.imbalanceOnly = order.imbalanceOnly
        p.routeMarketableToBbo = order.routeMarketableToBbo
        p.parentPermId = order.parentPermId
        p.usePriceMgmtAlgo = order.usePriceMgmtAlgo
        if order.duration != UNSET_INTEGER:
            p.duration = order.duration
        if order.postToAts != UNSET_INTEGER:
            p.postToAts = order.postToAts
        p.advancedErrorOverride = order.advancedErrorOverride
        p.manualOrderTime = order.manualOrderTime
        if order.minTradeQty != UNSET_INTEGER:
            p.minTradeQty = order.minTradeQty
        if order.minCompeteSize != UNSET_INTEGER:
            p.minCompeteSize = order.minCompeteSize
        if order.competeAgainstBestOffset != UNSET_DOUBLE:
            p.competeAgainstBestOffset = order.competeAgainstBestOffset
        if order.midOffsetAtWhole != UNSET_DOUBLE:
            p.midOffsetAtWhole = order.midOffsetAtWhole
        if order.midOffsetAtHalf != UNSET_DOUBLE:
            p.midOffsetAtHalf = order.midOffsetAtHalf
        p.customerAccount = order.customerAccount
        p.professionalCustomer = order.professionalCustomer
        p.bondAccruedInterest = order.bondAccruedInterest
        p.includeOvernight = order.includeOvernight
        if order.manualOrderIndicator != UNSET_INTEGER:
            p.manualOrderIndicator = order.manualOrderIndicator
        p.submitter = order.submitter
        if order.hedgeMaxSize != UNSET_DOUBLE:
            p.hedgeMaxSize = order.hedgeMaxSize
        return p

    def sendMsg(self, msg: str | bytes):
        loop = getLoop()
        t = loop.time()
        times = self._timeQ
        msgs = self._msgQ
        while times and t - times[0] > self.RequestsInterval:
            times.popleft()
        if msg:
            msgs.append(msg)
        while msgs and (len(times) < self.MaxRequests or not self.MaxRequests):
            msg = msgs.popleft()
            if isinstance(msg, bytes):
                raw = msg
            elif self._serverVersion >= self.MIN_SERVER_VER_PROTOBUF:
                # v201+: msgId is a 4-byte big-endian integer, not ASCII
                sep = msg.index('\0')
                raw = int(msg[:sep]).to_bytes(4, 'big') + msg[sep + 1:].encode()
            else:
                raw = msg.encode()
            self.conn.sendMsg(self._prefix(raw))
            times.append(t)
            if self._logger.isEnabledFor(logging.DEBUG):
                if isinstance(msg, str):
                    self._logger.debug('>>> %s', msg[:-1].replace('\0', ','))
                else:
                    self._logger.debug('>>> <proto %d bytes>', len(msg))
        if msgs:
            if not self._isThrottling:
                self._isThrottling = True
                self.throttleStart.emit()
                self._logger.debug('Started to throttle requests')
            loop.call_at(
                times[0] + self.RequestsInterval,
                self.sendMsg, None)
        else:
            if self._isThrottling:
                self._isThrottling = False
                self.throttleEnd.emit()
                self._logger.debug('Stopped to throttle requests')

    def _prefix(self, msg):
        # prefix a message with its length
        return struct.pack('>I', len(msg)) + msg

    def _onSocketHasData(self, data):
        debug = self._logger.isEnabledFor(logging.DEBUG)
        if self._tcpDataArrived:
            self._tcpDataArrived()

        self._data += data
        self._numBytesRecv += len(data)

        while True:
            if len(self._data) <= 4:
                break
            # 4-byte prefix tells the message length
            msgEnd = 4 + struct.unpack('>I', self._data[:4])[0]
            if len(self._data) < msgEnd:
                # insufficient data for now
                break
            raw = self._data[4:msgEnd]
            self._data = self._data[msgEnd:]
            self._numMsgRecv += 1

            if not self._serverVersion:
                # Handshake: always the old ASCII NUL-delimited format
                msg = raw.decode(errors='backslashreplace')
                fields = msg.split('\0')
                fields.pop()
                if len(fields) == 2:
                    version, _connTime = fields
                    self._serverVersion = int(version)
                    if self._serverVersion < self.MinClientVersion:
                        self._onSocketDisconnected(
                            'TWS/gateway version must be >= 972')
                        return
                    self.decoder.serverVersion = self._serverVersion
                    self.connState = Client.CONNECTED
                    self.startApi()
                    self.wrapper.connectAck()
                    self._logger.info(
                        f'Logged on to server version {self._serverVersion}')
                continue

            # v201+: msgId is a raw 4-byte big-endian integer
            # <v201: msgId is ASCII digits followed by \0
            if self._serverVersion >= self.MIN_SERVER_VER_PROTOBUF:
                msgId = int.from_bytes(raw[:4], 'big')
                body = raw[4:]
            else:
                sep = raw.index(b'\0')
                msgId = int(raw[:sep])
                body = raw[sep + 1:]

            if msgId > self.PROTOBUF_MSG_ID:
                # protobuf message
                realMsgId = msgId - self.PROTOBUF_MSG_ID
                if debug:
                    self._logger.debug('<<< proto msgId=%d %d bytes', realMsgId, len(body))
                if not self._apiReady:
                    self._snoopProtoApiReady(realMsgId, body)
                self.decoder.interpretProtoBuf(realMsgId, body)
            else:
                # legacy NUL-delimited message
                msg = body.decode(errors='backslashreplace')
                fields_body = msg.split('\0')
                if fields_body and fields_body[-1] == '':
                    fields_body.pop()
                fields = [str(msgId)] + fields_body

                if debug:
                    self._logger.debug('<<< %s', ','.join(fields))

                if not self._apiReady:
                    if msgId == 9:
                        _, _, validId = fields
                        self.updateReqId(int(validId))
                        self._hasReqId = True
                    elif msgId == 15:
                        _, _, accts = fields
                        self._accounts = [a for a in accts.split(',') if a]
                    if self._hasReqId and self._accounts:
                        self._apiReady = True
                        self.apiStart.emit()

                self.decoder.interpret(fields)

        if self._tcpDataProcessed:
            self._tcpDataProcessed()

    def _snoopProtoApiReady(self, msgId: int, payload: bytes) -> None:
        """Snoop nextValidId and managedAccounts from protobuf messages for _apiReady."""
        try:
            if msgId == 9:  # NEXT_VALID_ID
                from .protobuf.NextValidId_pb2 import NextValidId
                msg = NextValidId()
                msg.ParseFromString(payload)
                self.updateReqId(msg.orderId)
                self._hasReqId = True
            elif msgId == 15:  # MANAGED_ACCTS
                from .protobuf.ManagedAccounts_pb2 import ManagedAccounts
                msg = ManagedAccounts()
                msg.ParseFromString(payload)
                self._accounts = [a for a in msg.accountsList.split(',') if a]
            if self._hasReqId and self._accounts:
                self._apiReady = True
                self.apiStart.emit()
        except Exception:
            pass

    def _onSocketDisconnected(self, msg):
        wasReady = self.isReady()
        if not self.isConnected():
            self._logger.info('Disconnected.')
        elif not msg:
            msg = 'Peer closed connection.'
            if not wasReady:
                msg += f' clientId {self.clientId} already in use?'
        if msg:
            self._logger.error(msg)
            self.apiError.emit(msg)
        self.wrapper.setEventsDone()
        if wasReady:
            self.wrapper.connectionClosed()
        self.reset()
        if wasReady:
            self.apiEnd.emit()

    # client request methods
    # the message type id is sent first, often followed by a version number

    def reqMktData(
            self, reqId, contract, genericTickList, snapshot,
            regulatorySnapshot, mktDataOptions):
        if self.useProtoBuf(1):
            from .protobuf.MarketDataRequest_pb2 import MarketDataRequest
            req = MarketDataRequest()
            req.reqId = reqId
            req.contract.CopyFrom(self._contractToProto(contract))
            req.genericTickList = genericTickList
            req.snapshot = snapshot
            req.regulatorySnapshot = regulatorySnapshot
            self.sendProto(1, req)
            return
        fields = [1, 11, reqId, contract]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.conId, leg.ratio, leg.action, leg.exchange]

        dnc = contract.deltaNeutralContract
        if dnc:
            fields += [True, dnc.conId, dnc.delta, dnc.price]
        else:
            fields += [False]

        fields += [
            genericTickList, snapshot, regulatorySnapshot, mktDataOptions]
        self.send(*fields)

    def cancelMktData(self, reqId):
        if self.useProtoBuf(2):
            from .protobuf.CancelMarketData_pb2 import CancelMarketData
            req = CancelMarketData()
            req.reqId = reqId
            self.sendProto(2, req)
            return
        self.send(2, 2, reqId)

    def placeOrder(self, orderId, contract, order):
        if self.useProtoBuf(3):
            from .protobuf.PlaceOrderRequest_pb2 import PlaceOrderRequest
            req = PlaceOrderRequest()
            req.orderId = orderId
            req.contract.CopyFrom(self._contractToProto(contract))
            req.order.CopyFrom(self._orderToProto(order))
            self.sendProto(3, req)
            return
        version = self.serverVersion()
        fields = [
            3, orderId,
            contract,
            contract.secIdType,
            contract.secId,
            order.action,
            order.totalQuantity,
            order.orderType,
            order.lmtPrice,
            order.auxPrice,
            order.tif,
            order.ocaGroup,
            order.account,
            order.openClose,
            order.origin,
            order.orderRef,
            order.transmit,
            order.parentId,
            order.blockOrder,
            order.sweepToFill,
            order.displaySize,
            order.triggerMethod,
            order.outsideRth,
            order.hidden]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [
                    leg.conId,
                    leg.ratio,
                    leg.action,
                    leg.exchange,
                    leg.openClose,
                    leg.shortSaleSlot,
                    leg.designatedLocation,
                    leg.exemptCode]

            legs = order.orderComboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.price]

            params = order.smartComboRoutingParams or []
            fields += [len(params)]
            for param in params:
                fields += [param.tag, param.value]

        fields += [
            '',
            order.discretionaryAmt,
            order.goodAfterTime,
            order.goodTillDate,
            order.faGroup,
            order.faMethod,
            order.faPercentage]
        if version < 177:
            fields += [order.faProfile]
        fields += [
            order.modelCode,
            order.shortSaleSlot,
            order.designatedLocation,
            order.exemptCode,
            order.ocaType,
            order.rule80A,
            order.settlingFirm,
            order.allOrNone,
            order.minQty,
            order.percentOffset,
            order.eTradeOnly,
            order.firmQuoteOnly,
            order.nbboPriceCap,
            order.auctionStrategy,
            order.startingPrice,
            order.stockRefPrice,
            order.delta,
            order.stockRangeLower,
            order.stockRangeUpper,
            order.overridePercentageConstraints,
            order.volatility,
            order.volatilityType,
            order.deltaNeutralOrderType,
            order.deltaNeutralAuxPrice]

        if order.deltaNeutralOrderType:
            fields += [
                order.deltaNeutralConId,
                order.deltaNeutralSettlingFirm,
                order.deltaNeutralClearingAccount,
                order.deltaNeutralClearingIntent,
                order.deltaNeutralOpenClose,
                order.deltaNeutralShortSale,
                order.deltaNeutralShortSaleSlot,
                order.deltaNeutralDesignatedLocation]

        fields += [
            order.continuousUpdate,
            order.referencePriceType,
            order.trailStopPrice,
            order.trailingPercent,
            order.scaleInitLevelSize,
            order.scaleSubsLevelSize,
            order.scalePriceIncrement]

        if (0 < order.scalePriceIncrement < UNSET_DOUBLE):
            fields += [
                order.scalePriceAdjustValue,
                order.scalePriceAdjustInterval,
                order.scaleProfitOffset,
                order.scaleAutoReset,
                order.scaleInitPosition,
                order.scaleInitFillQty,
                order.scaleRandomPercent]

        fields += [
            order.scaleTable,
            order.activeStartTime,
            order.activeStopTime,
            order.hedgeType]

        if order.hedgeType:
            fields += [order.hedgeParam]

        fields += [
            order.optOutSmartRouting,
            order.clearingAccount,
            order.clearingIntent,
            order.notHeld]

        dnc = contract.deltaNeutralContract
        if dnc:
            fields += [True, dnc.conId, dnc.delta, dnc.price]
        else:
            fields += [False]

        fields += [order.algoStrategy]
        if order.algoStrategy:
            params = order.algoParams or []
            fields += [len(params)]
            for param in params:
                fields += [param.tag, param.value]

        fields += [
            order.algoId,
            order.whatIf,
            order.orderMiscOptions,
            order.solicited,
            order.randomizeSize,
            order.randomizePrice]

        if order.orderType in ('PEG BENCH', 'PEGBENCH'):
            fields += [
                order.referenceContractId,
                order.isPeggedChangeAmountDecrease,
                order.peggedChangeAmount,
                order.referenceChangeAmount,
                order.referenceExchangeId]

        fields += [len(order.conditions)]
        if order.conditions:
            for cond in order.conditions:
                fields += dataclassAsTuple(cond)
            fields += [
                order.conditionsIgnoreRth,
                order.conditionsCancelOrder]

        fields += [
            order.adjustedOrderType,
            order.triggerPrice,
            order.lmtPriceOffset,
            order.adjustedStopPrice,
            order.adjustedStopLimitPrice,
            order.adjustedTrailingAmount,
            order.adjustableTrailingUnit,
            order.extOperator,
            order.softDollarTier.name,
            order.softDollarTier.val,
            order.cashQty,
            order.mifid2DecisionMaker,
            order.mifid2DecisionAlgo,
            order.mifid2ExecutionTrader,
            order.mifid2ExecutionAlgo,
            order.dontUseAutoPriceForHedge,
            order.isOmsContainer,
            order.discretionaryUpToLimitPrice,
            order.usePriceMgmtAlgo]

        if version >= 158:
            fields += [order.duration]
        if version >= 160:
            fields += [order.postToAts]
        if version >= 162:
            fields += [order.autoCancelParent]
        if version >= 166:
            fields += [order.advancedErrorOverride]
        if version >= 169:
            fields += [order.manualOrderTime]
        if version >= 170:
            if contract.exchange == 'IBKRATS':
                fields += [order.minTradeQty]
            if order.orderType in ('PEG BEST', 'PEGBEST'):
                fields += [
                    order.minCompeteSize,
                    order.competeAgainstBestOffset]
                if order.competeAgainstBestOffset == math.inf:
                    fields += [order.midOffsetAtWhole, order.midOffsetAtHalf]
            elif order.orderType in ('PEG MID', 'PEGMID'):
                fields += [order.midOffsetAtWhole, order.midOffsetAtHalf]
        if version >= self.MIN_SERVER_VER_CUSTOMER_ACCOUNT:
            fields += [order.customerAccount]
        if version >= self.MIN_SERVER_VER_PROFESSIONAL_CUSTOMER:
            fields += [order.professionalCustomer]
        if self.MIN_SERVER_VER_RFQ_FIELDS <= version < self.MIN_SERVER_VER_UNDO_RFQ_FIELDS:
            fields += ['', UNSET_INTEGER]  # obsolete rfq fields, send empty
        if version >= self.MIN_SERVER_VER_INCLUDE_OVERNIGHT:
            fields += [order.includeOvernight]
        if version >= self.MIN_SERVER_VER_CME_TAGGING_FIELDS:
            fields += [order.manualOrderIndicator]
        if version >= self.MIN_SERVER_VER_IMBALANCE_ONLY:
            fields += [order.imbalanceOnly]

        self.send(*fields)

    def cancelOrder(self, orderId, manualCancelOrderTime='', extOperator='', manualOrderIndicator=UNSET_INTEGER):
        if self.useProtoBuf(4):
            from .protobuf.CancelOrderRequest_pb2 import CancelOrderRequest
            req = CancelOrderRequest()
            req.orderId = orderId
            req.orderCancel.manualOrderCancelTime = manualCancelOrderTime
            req.orderCancel.extOperator = extOperator
            if manualOrderIndicator != UNSET_INTEGER:
                req.orderCancel.manualOrderIndicator = manualOrderIndicator
            self.sendProto(4, req)
            return
        version = self.serverVersion()
        fields = [4, 1, orderId]
        if version >= 169:
            fields += [manualCancelOrderTime]
        if version >= self.MIN_SERVER_VER_CME_TAGGING_FIELDS:
            fields += [extOperator, manualOrderIndicator]
        self.send(*fields)

    def reqOpenOrders(self):
        self.send(5, 1)

    def reqAccountUpdates(self, subscribe, acctCode):
        self.send(6, 2, subscribe, acctCode)

    def reqExecutions(self, reqId, execFilter):
        if self.useProtoBuf(7):
            from .protobuf.ExecutionRequest_pb2 import ExecutionRequest
            req = ExecutionRequest()
            req.reqId = reqId
            req.executionFilter.clientId = execFilter.clientId
            req.executionFilter.acctCode = execFilter.acctCode
            req.executionFilter.time = execFilter.time
            req.executionFilter.symbol = execFilter.symbol
            req.executionFilter.secType = execFilter.secType
            req.executionFilter.exchange = execFilter.exchange
            req.executionFilter.side = execFilter.side
            self.sendProto(7, req)
            return
        fields = [
            7, 3, reqId,
            execFilter.clientId,
            execFilter.acctCode,
            execFilter.time,
            execFilter.symbol,
            execFilter.secType,
            execFilter.exchange,
            execFilter.side]
        if self.serverVersion() >= self.MIN_SERVER_VER_PARAMETRIZED_DAYS_OF_EXECUTIONS:
            fields += [getattr(execFilter, 'lastNDays', '')]
        self.send(*fields)

    def reqIds(self, numIds):
        self.send(8, 1, numIds)

    def reqContractDetails(self, reqId, contract):
        fields = [
            9, 8, reqId,
            contract,
            contract.includeExpired,
            contract.secIdType,
            contract.secId]
        if self.serverVersion() >= 176:
            fields += [contract.issuerId]
        self.send(*fields)

    def reqMktDepth(
            self, reqId, contract, numRows, isSmartDepth, mktDepthOptions):
        self.send(
            10, 5, reqId,
            contract.conId,
            contract.symbol,
            contract.secType,
            contract.lastTradeDateOrContractMonth,
            contract.strike,
            contract.right,
            contract.multiplier,
            contract.exchange,
            contract.primaryExchange,
            contract.currency,
            contract.localSymbol,
            contract.tradingClass,
            numRows,
            isSmartDepth,
            mktDepthOptions)

    def cancelMktDepth(self, reqId, isSmartDepth):
        self.send(11, 1, reqId, isSmartDepth)

    def reqNewsBulletins(self, allMsgs):
        self.send(12, 1, allMsgs)

    def cancelNewsBulletins(self):
        self.send(13, 1)

    def setServerLogLevel(self, logLevel):
        self.send(14, 1, logLevel)

    def reqAutoOpenOrders(self, bAutoBind):
        self.send(15, 1, bAutoBind)

    def reqAllOpenOrders(self):
        self.send(16, 1)

    def reqManagedAccts(self):
        self.send(17, 1)

    def requestFA(self, faData):
        self.send(18, 1, faData)

    def replaceFA(self, reqId, faData, cxml):
        self.send(19, 1, faData, cxml, reqId)

    def reqHistoricalData(
            self, reqId, contract, endDateTime, durationStr, barSizeSetting,
            whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        fields = [
            20, reqId, contract, contract.includeExpired,
            endDateTime, barSizeSetting, durationStr, useRTH,
            whatToShow, formatDate]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.conId, leg.ratio, leg.action, leg.exchange]

        fields += [keepUpToDate, chartOptions]
        self.send(*fields)

    def exerciseOptions(
            self, reqId, contract, exerciseAction,
            exerciseQuantity, account, override):
        self.send(
            21, 2, reqId,
            contract.conId,
            contract.symbol,
            contract.secType,
            contract.lastTradeDateOrContractMonth,
            contract.strike,
            contract.right,
            contract.multiplier,
            contract.exchange,
            contract.currency,
            contract.localSymbol,
            contract.tradingClass,
            exerciseAction, exerciseQuantity, account, override)

    def reqScannerSubscription(
            self, reqId, subscription, scannerSubscriptionOptions,
            scannerSubscriptionFilterOptions):
        sub = subscription
        self.send(
            22, reqId,
            sub.numberOfRows,
            sub.instrument,
            sub.locationCode,
            sub.scanCode,
            sub.abovePrice,
            sub.belowPrice,
            sub.aboveVolume,
            sub.marketCapAbove,
            sub.marketCapBelow,
            sub.moodyRatingAbove,
            sub.moodyRatingBelow,
            sub.spRatingAbove,
            sub.spRatingBelow,
            sub.maturityDateAbove,
            sub.maturityDateBelow,
            sub.couponRateAbove,
            sub.couponRateBelow,
            sub.excludeConvertible,
            sub.averageOptionVolumeAbove,
            sub.scannerSettingPairs,
            sub.stockTypeFilter,
            scannerSubscriptionFilterOptions,
            scannerSubscriptionOptions)

    def cancelScannerSubscription(self, reqId):
        self.send(23, 1, reqId)

    def reqScannerParameters(self):
        self.send(24, 1)

    def cancelHistoricalData(self, reqId):
        self.send(25, 1, reqId)

    def reqCurrentTime(self):
        self.send(49, 1)

    def reqRealTimeBars(
            self, reqId, contract, barSize, whatToShow,
            useRTH, realTimeBarsOptions):
        self.send(
            50, 3, reqId, contract, barSize, whatToShow,
            useRTH, realTimeBarsOptions)

    def cancelRealTimeBars(self, reqId):
        self.send(51, 1, reqId)

    def reqFundamentalData(
            self, reqId, contract, reportType, fundamentalDataOptions):
        options = fundamentalDataOptions or []
        self.send(
            52, 2, reqId,
            contract.conId,
            contract.symbol,
            contract.secType,
            contract.exchange,
            contract.primaryExchange,
            contract.currency,
            contract.localSymbol,
            reportType, len(options), options)

    def cancelFundamentalData(self, reqId):
        self.send(53, 1, reqId)

    def calculateImpliedVolatility(
            self, reqId, contract, optionPrice, underPrice, implVolOptions):
        self.send(
            54, 3, reqId, contract, optionPrice, underPrice,
            len(implVolOptions), implVolOptions)

    def calculateOptionPrice(
            self, reqId, contract, volatility, underPrice, optPrcOptions):
        self.send(
            55, 3, reqId, contract, volatility, underPrice,
            len(optPrcOptions), optPrcOptions)

    def cancelCalculateImpliedVolatility(self, reqId):
        self.send(56, 1, reqId)

    def cancelCalculateOptionPrice(self, reqId):
        self.send(57, 1, reqId)

    def reqGlobalCancel(self):
        self.send(58, 1)

    def reqMarketDataType(self, marketDataType):
        self.send(59, 1, marketDataType)

    def reqPositions(self):
        self.send(61, 1)

    def reqAccountSummary(self, reqId, groupName, tags):
        self.send(62, 1, reqId, groupName, tags)

    def cancelAccountSummary(self, reqId):
        self.send(63, 1, reqId)

    def cancelPositions(self):
        self.send(64, 1)

    def verifyRequest(self, apiName, apiVersion):
        self.send(65, 1, apiName, apiVersion)

    def verifyMessage(self, apiData):
        self.send(66, 1, apiData)

    def queryDisplayGroups(self, reqId):
        self.send(67, 1, reqId)

    def subscribeToGroupEvents(self, reqId, groupId):
        self.send(68, 1, reqId, groupId)

    def updateDisplayGroup(self, reqId, contractInfo):
        self.send(69, 1, reqId, contractInfo)

    def unsubscribeFromGroupEvents(self, reqId):
        self.send(70, 1, reqId)

    def startApi(self):
        self.send(71, 2, self.clientId, self.optCapab)

    def verifyAndAuthRequest(self, apiName, apiVersion, opaqueIsvKey):
        self.send(72, 1, apiName, apiVersion, opaqueIsvKey)

    def verifyAndAuthMessage(self, apiData, xyzResponse):
        self.send(73, 1, apiData, xyzResponse)

    def reqPositionsMulti(self, reqId, account, modelCode):
        self.send(74, 1, reqId, account, modelCode)

    def cancelPositionsMulti(self, reqId):
        self.send(75, 1, reqId)

    def reqAccountUpdatesMulti(self, reqId, account, modelCode, ledgerAndNLV):
        self.send(76, 1, reqId, account, modelCode, ledgerAndNLV)

    def cancelAccountUpdatesMulti(self, reqId):
        self.send(77, 1, reqId)

    def reqSecDefOptParams(
            self, reqId, underlyingSymbol, futFopExchange,
            underlyingSecType, underlyingConId):
        self.send(
            78, reqId, underlyingSymbol, futFopExchange,
            underlyingSecType, underlyingConId)

    def reqSoftDollarTiers(self, reqId):
        self.send(79, reqId)

    def reqFamilyCodes(self):
        self.send(80)

    def reqMatchingSymbols(self, reqId, pattern):
        self.send(81, reqId, pattern)

    def reqMktDepthExchanges(self):
        self.send(82)

    def reqSmartComponents(self, reqId, bboExchange):
        self.send(83, reqId, bboExchange)

    def reqNewsArticle(
            self, reqId, providerCode, articleId, newsArticleOptions):
        self.send(84, reqId, providerCode, articleId, newsArticleOptions)

    def reqNewsProviders(self):
        self.send(85)

    def reqHistoricalNews(
            self, reqId, conId, providerCodes, startDateTime, endDateTime,
            totalResults, historicalNewsOptions):
        self.send(
            86, reqId, conId, providerCodes, startDateTime, endDateTime,
            totalResults, historicalNewsOptions)

    def reqHeadTimeStamp(
            self, reqId, contract, whatToShow, useRTH, formatDate):
        self.send(
            87, reqId, contract, contract.includeExpired,
            useRTH, whatToShow, formatDate)

    def reqHistogramData(self, tickerId, contract, useRTH, timePeriod):
        self.send(
            88, tickerId, contract, contract.includeExpired,
            useRTH, timePeriod)

    def cancelHistogramData(self, tickerId):
        self.send(89, tickerId)

    def cancelHeadTimeStamp(self, reqId):
        self.send(90, reqId)

    def reqMarketRule(self, marketRuleId):
        self.send(91, marketRuleId)

    def reqPnL(self, reqId, account, modelCode):
        self.send(92, reqId, account, modelCode)

    def cancelPnL(self, reqId):
        self.send(93, reqId)

    def reqPnLSingle(self, reqId, account, modelCode, conid):
        self.send(94, reqId, account, modelCode, conid)

    def cancelPnLSingle(self, reqId):
        self.send(95, reqId)

    def reqHistoricalTicks(
            self, reqId, contract, startDateTime, endDateTime,
            numberOfTicks, whatToShow, useRth, ignoreSize, miscOptions):
        self.send(
            96, reqId, contract, contract.includeExpired,
            startDateTime, endDateTime, numberOfTicks, whatToShow,
            useRth, ignoreSize, miscOptions)

    def reqTickByTickData(
            self, reqId, contract, tickType, numberOfTicks, ignoreSize):
        self.send(97, reqId, contract, tickType, numberOfTicks, ignoreSize)

    def cancelTickByTickData(self, reqId):
        self.send(98, reqId)

    def reqCompletedOrders(self, apiOnly):
        self.send(99, apiOnly)

    def reqWshMetaData(self, reqId):
        self.send(100, reqId)

    def cancelWshMetaData(self, reqId):
        self.send(101, reqId)

    def reqWshEventData(self, reqId, data: WshEventData):
        fields = [102, reqId, data.conId]
        if self.serverVersion() >= 171:
            fields += [
                data.filter,
                data.fillWatchlist,
                data.fillPortfolio,
                data.fillCompetitors]
        if self.serverVersion() >= 173:
            fields += [
                data.startDate,
                data.endDate,
                data.totalLimit]
        self.send(*fields, makeEmpty=False)

    def cancelWshEventData(self, reqId):
        self.send(103, reqId)

    def reqUserInfo(self, reqId):
        self.send(104, reqId)
