/* Copyright (C) 2025 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 * and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable. */

#pragma once
#ifndef TWS_API_CLIENT_CONTRACT_H
#define TWS_API_CLIENT_CONTRACT_H

#include "TagValue.h"
#include "Decimal.h"
#include "CommonDefs.h"
#include "IneligibilityReason.h"
#include <cfloat>
#include <memory>

/*
	SAME_POS    = open/close leg value is same as combo
	OPEN_POS    = open
	CLOSE_POS   = close
	UNKNOWN_POS = unknown
*/
enum LegOpenClose { SAME_POS, OPEN_POS, CLOSE_POS, UNKNOWN_POS };

struct ComboLeg
{
	ComboLeg()
		: conId(0)
		, ratio(0)
		, openClose(0)
		, shortSaleSlot(0)
		, exemptCode(-1)
	{
	}

	int		conId;
	int		ratio;
	std::string	action; //BUY/SELL/SSHORT

	std::string	exchange;
	int		openClose; // LegOpenClose enum values

	// for stock legs when doing short sale
	int		shortSaleSlot; // 1 = clearing broker, 2 = third party
	std::string	designatedLocation;
	int		exemptCode;

	bool operator==( const ComboLeg& other) const
	{
		return (conId == other.conId &&
			ratio == other.ratio &&
			openClose == other.openClose &&
			shortSaleSlot == other.shortSaleSlot &&
			exemptCode == other.exemptCode &&
			action == other.action &&
			exchange == other.exchange &&
			designatedLocation == other.designatedLocation);
	}
};

struct DeltaNeutralContract
{
	DeltaNeutralContract()
		: conId(0)
		, delta(0)
		, price(0)
	{}

	int 	conId;
	double	delta;
	double	price;
};

typedef std::shared_ptr<ComboLeg> ComboLegSPtr;

struct Contract
{
	Contract()
		: conId(0)
		, strike(UNSET_DOUBLE)
		, includeExpired(false)
		, comboLegs(NULL)
	{
	}

	Contract(const Contract& other)
		: conId(other.conId)
		, symbol(other.symbol)
		, secType(other.secType)
		, lastTradeDateOrContractMonth(other.lastTradeDateOrContractMonth)
		, lastTradeDate(other.lastTradeDate)
		, strike(other.strike)
		, right(other.right)
		, multiplier(other.multiplier)
		, exchange(other.exchange)
		, primaryExchange(other.primaryExchange)
		, currency(other.currency)
		, localSymbol(other.localSymbol)
		, tradingClass(other.tradingClass)
		, includeExpired(other.includeExpired)
		, secIdType(other.secIdType)
		, secId(other.secId)
		, description(other.description)
		, issuerId(other.issuerId)
		, comboLegsDescrip(other.comboLegsDescrip)
		, comboLegs(other.comboLegs)
		, deltaNeutralContract(other.deltaNeutralContract
			? std::unique_ptr<DeltaNeutralContract>(new DeltaNeutralContract(*other.deltaNeutralContract))
			: nullptr)
	{
	}

	Contract& operator=(const Contract& other)
	{
		if (this != &other) {
			conId = other.conId;
			symbol = other.symbol;
			secType = other.secType;
			lastTradeDateOrContractMonth = other.lastTradeDateOrContractMonth;
			lastTradeDate = other.lastTradeDate;
			strike = other.strike;
			right = other.right;
			multiplier = other.multiplier;
			exchange = other.exchange;
			primaryExchange = other.primaryExchange;
			currency = other.currency;
			localSymbol = other.localSymbol;
			tradingClass = other.tradingClass;
			includeExpired = other.includeExpired;
			secIdType = other.secIdType;
			secId = other.secId;
			description = other.description;
			issuerId = other.issuerId;
			comboLegsDescrip = other.comboLegsDescrip;
			comboLegs = other.comboLegs;

			deltaNeutralContract = other.deltaNeutralContract
				? std::unique_ptr<DeltaNeutralContract>(new DeltaNeutralContract(*other.deltaNeutralContract))
				: nullptr;
		}
		return *this;
	}

	int 		conId;
	std::string	symbol;
	std::string	secType;
	std::string	lastTradeDateOrContractMonth;
	std::string lastTradeDate;
	double		strike;
	std::string	right;
	std::string	multiplier;
	std::string	exchange;
	std::string	primaryExchange; // pick an actual (ie non-aggregate) exchange that the contract trades on.  DO NOT SET TO SMART.
	std::string	currency;
	std::string	localSymbol;
	std::string	tradingClass;
	bool		includeExpired;
	std::string	secIdType;		// CUSIP;SEDOL;ISIN;RIC
	std::string	secId;
	std::string description;
	std::string issuerId;

	// COMBOS
	std::string comboLegsDescrip; // received in open order 14 and up for all combos

	// combo legs
	typedef std::vector<ComboLegSPtr> ComboLegList;
	typedef std::shared_ptr<ComboLegList> ComboLegListSPtr;

	ComboLegListSPtr comboLegs;

	// delta neutral contract
	std::unique_ptr<DeltaNeutralContract> deltaNeutralContract;

public:

	// Helpers
	static void CloneComboLegs(ComboLegListSPtr& dst, const ComboLegListSPtr& src);
};

struct ContractDetails
{
	ContractDetails()
		: minTick(0)
		, priceMagnifier(0)
		, underConId(0)
		, evMultiplier(0)
		, aggGroup(UNSET_INTEGER)
		, minSize(UNSET_DECIMAL)
		, sizeIncrement(UNSET_DECIMAL)
		, suggestedSizeIncrement(UNSET_DECIMAL)
		, minAlgoSize(UNSET_DECIMAL)
		, lastPricePrecision(UNSET_DECIMAL)
		, lastSizePrecision(UNSET_DECIMAL)
		, callable(false)
		, putable(false)
		, coupon(0)
		, convertible(false)
		, nextOptionPartial(false)
		, fundClosed(false)
		, fundClosedForNewInvestors(false)
		, fundClosedForNewMoney(false)
		, fundDistributionPolicyIndicator(FundDistributionPolicyIndicator::None)
		, fundAssetType(FundAssetType::None)
		, ineligibilityReasonList(NULL)
	{
	}

	Contract	contract;
	std::string	marketName;
	double		minTick;
	std::string	orderTypes;
	std::string	validExchanges;
	int 		priceMagnifier;
	int 		underConId;
	std::string	longName;
	std::string	contractMonth;
	std::string	industry;
	std::string	category;
	std::string	subcategory;
	std::string	timeZoneId;
	std::string	tradingHours;
	std::string	liquidHours;
	std::string	evRule;
	double		evMultiplier;
	int 		aggGroup;
	std::string	underSymbol;
	std::string	underSecType;
	std::string marketRuleIds;
	std::string realExpirationDate;
	std::string lastTradeTime;
	std::string stockType;
	Decimal		minSize;
	Decimal		sizeIncrement;
	Decimal		suggestedSizeIncrement;
	Decimal		minAlgoSize;
	Decimal		lastPricePrecision;
	Decimal		lastSizePrecision;

	TagValueListSPtr secIdList;

	// BOND values
	std::string	cusip;
	std::string	ratings;
	std::string	descAppend;
	std::string	bondType;
	std::string	couponType;
	bool		callable;
	bool		putable;
	double		coupon;
	bool		convertible;
	std::string	maturity;
	std::string	issueDate;
	std::string	nextOptionDate;
	std::string	nextOptionType;
	bool		nextOptionPartial;
	std::string	notes;

	// FUND values
	std::string fundName;
	std::string fundFamily;
	std::string fundType;
	std::string fundFrontLoad;
	std::string fundBackLoad;
	std::string fundBackLoadTimeInterval;
	std::string fundManagementFee;
	bool		fundClosed;
	bool		fundClosedForNewInvestors;
	bool		fundClosedForNewMoney;
	std::string fundNotifyAmount;
	std::string fundMinimumInitialPurchase;
	std::string fundSubsequentMinimumPurchase;
	std::string fundBlueSkyStates;
	std::string fundBlueSkyTerritories;
	FundDistributionPolicyIndicator fundDistributionPolicyIndicator;
	FundAssetType fundAssetType;

	// ineligibility reason list
	IneligibilityReasonListSPtr ineligibilityReasonList;

	std::string eventContract1;
	std::string eventContractDescription1;
	std::string eventContractDescription2;
};

struct ContractDescription
{
	Contract contract;
	typedef std::vector<std::string> DerivativeSecTypesList;
	DerivativeSecTypesList derivativeSecTypes;
};

inline void
Contract::CloneComboLegs(ComboLegListSPtr& dst, const ComboLegListSPtr& src)
{
	if (!src.get())
		return;

	dst->reserve(src->size());

	ComboLegList::const_iterator iter = src->begin();
	const ComboLegList::const_iterator iterEnd = src->end();

	for (; iter != iterEnd; ++iter) {
		const ComboLeg* leg = iter->get();
		if (!leg)
			continue;
		dst->push_back(ComboLegSPtr(new ComboLeg(*leg)));
	}
}


#endif
