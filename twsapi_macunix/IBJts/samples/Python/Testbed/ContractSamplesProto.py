"""
Copyright (C) 2026 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable.
"""

from ibapi.protobuf.Contract_pb2 import Contract as ContractProto

class ContractSamplesProto:

    @staticmethod
    def IBMStockAtSmart() -> ContractProto:
        #! [IBM_stock_at_smart]
        contract = ContractProto()
        contract.symbol = "IBM"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        #! [IBM_stock_at_smart]
        return contract

    @staticmethod
    def MSFTStockAtSmart() -> ContractProto:
        #! [MSFT_stock_at_smart]
        contract = ContractProto()
        contract.symbol = "MSFT"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        #! [MSFT_stock_at_smart]
        return contract

def Test():
    from ibapi.utils import ExerciseStaticMethods
    ExerciseStaticMethods(ContractSamplesProto)

if "__main__" == __name__:
    Test()

