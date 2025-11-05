## Problem Description
# 0025 - scripts/get_top50.py 设计错误
目前获取 市值前 50 的crypto 的方法错误，导致输出的结果不正确。

Status: CLOSED
Created: 2025-11-05
Author: watson
Resolved: 2025-11-05

## Solution
需要参考下面的方法，重新设计，并且进行测试

✅ 获取 CoinGecko 市值前 50
✅ 匹配 OKX 上存在的永续合约（`-USDT-SWAP`）
✅ 输出最终可交易的永续合约合约列表
✅ 兼容大写/小写、特殊符号问题
✅ 可用于你的 trading bot 自动更新交易范围

## Complete Final Solution

### OpenSpec Change Implementation
The issue was resolved through OpenSpec change 0002, which implemented a comprehensive market cap-based symbol selection system. The solution includes:

1. **Market Cap Data Fetching**: Integration with CoinGecko API to get accurate market capitalization rankings
2. **OKX Contract Discovery**: CCXT-based discovery of all available OKX perpetual swap contracts
3. **Symbol Filtering**: Intelligent matching of market cap ranked symbols with tradable OKX contracts
4. **Caching System**: Performance optimization with appropriate cache expiration
5. **Error Handling**: Robust error handling with graceful fallbacks

### Key Changes Made
- Replaced `get_okx_funding_top50()` (funding rate based) with `get_top50_by_marketcap()` (market cap based)
- Added CoinGecko API integration with caching (1-hour expiry)
- Added OKX contract discovery with caching (15-minute expiry)
- Implemented symbol filtering logic to ensure tradability
- Updated configuration integration with workflow.json
- Added comprehensive unit tests (25 test cases)

### Results
- **Before**: Selected symbols by funding rate, potentially biased toward volatile pairs
- **After**: Selects top 25 cryptocurrencies by market cap that are actually tradable on OKX
- Current top symbols: BTC, ETH, XRP, BNB, SOL, USDC, TRX, DOGE, ADA, etc.

## Update Log

### 2025-11-05 - Issue Resolution Completed
1. **Problem Identification**: Confirmed that `scripts/get_top50.py` was incorrectly ranking cryptocurrencies by funding rate instead of market capitalization
2. **OpenSpec Proposal**: Created comprehensive change 0002 with full documentation (proposal.md, design.md, tasks.md, spec.md)
3. **Validation Fixes**: Resolved OpenSpec validation issues with requirement formatting and scenario structure
4. **Implementation**: 
   - Implemented CoinGecko API integration for market cap data
   - Added OKX perpetual swap contract discovery using CCXT
   - Created symbol filtering logic to match market cap with tradable contracts
   - Added caching system for performance optimization
   - Integrated with existing configuration system
5. **Testing**: Added 25 comprehensive unit tests covering all functions and error conditions
6. **Integration Testing**: Verified end-to-end functionality with real APIs
7. **Results Validation**: Confirmed correct selection of 25 major cryptocurrencies by market cap available on OKX

### Files Modified
- `scripts/get_top50.py`: Complete refactoring with new market cap based logic
- `tests/test_get_top50.py`: Added comprehensive test coverage
- `openspec/changes/0002/`: Full OpenSpec change documentation
- `config/top50_symbols.json`: Updated with correct symbol selection and CCXT format
- `cache/`: New caching system for API responses

### Format Correction (2025-11-05)
**Issue**: The symbols were saved in `BTC-USDT-SWAP` format, but CCXT and downstream consumers expect `BTC/USDT` format.

**Root Cause**: The original implementation was designed to return OKX contract names, but the symbols are consumed by CCXT library which expects `BASE/QUOTE` format for trading operations.

**Solution**: Updated `filter_top_swap_symbols()` and `get_top50_by_marketcap()` to return CCXT compatible `BASE/USDT` format instead of `BASE-USDT-SWAP` format.

**Changes Made**:
- **scripts/get_top50.py**:
  - Modified `filter_top_swap_symbols()` to return `BTC/USDT` format instead of `BTC-USDT-SWAP`
  - Updated `get_top50_by_marketcap()` documentation and fallback logic
  - Changed return format from contract names to CCXT symbol format
- **tests/test_get_top50.py**:
  - Updated `test_filter_top_swap_symbols()` expectations
  - Updated `test_get_top50_by_marketcap_success()` and `test_get_top50_by_marketcap_okx_failure()` expectations
  - All test assertions now expect `BTC/USDT` format
- **openspec/changes/0002/specs/symbol-selection/spec.md**:
  - Updated requirement descriptions to specify CCXT compatible format
  - Updated scenario examples to show `BTC/USDT` format
  - Changed "OKX perpetual contract format" to "CCXT compatible format"
- **config/top50_symbols.json**:
  - Regenerated with correct `BTC/USDT` format symbols

**Verification**:
- Format validation: All symbols now match `BASE/USDT` pattern
- CCXT compatibility: Symbols can be directly used with CCXT library
- Downstream consumers: `okx_data_collector.py` can process symbols without format conversion

### Testing Results
- **Unit Tests**: All 25 unit tests pass, including updated format validation tests
- **Integration Test**: End-to-end pipeline successful with real API calls
- **Format Validation**: All symbols validated to be in correct `BASE/USDT` format
- **CCXT Compatibility**: Symbols can be directly consumed by CCXT library without conversion
- **Symbol Selection**: Returns 25 tradable symbols from top 50 market cap coins
- **OpenSpec Validation**: Specification passes strict validation requirements
- **Regression Testing**: No existing functionality broken by format changes

---

# ✅ 完整代码：获取市值 Top50 + 筛选 OKX 永续合约

```python
import requests
import ccxt
import time

def get_top_marketcap_symbols(top_n=50):
    """
    从 CoinGecko 获取市值前 N 币种
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": top_n,
        "page": 1
    }
    
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    # 只取 symbol，并转成大写
    return [coin["symbol"].upper() for coin in data]


def get_okx_swap_symbols():
    """
    从 OKX 获取所有支持的永续合约：例如 BTC-USDT-SWAP
    """
    exchange = ccxt.okx()
    markets = exchange.load_markets()
    return [m for m in markets if m.endswith("-USDT-SWAP")]


def filter_top_swap_symbols():
    # 1) 市值前50币种
    top_symbols = get_top_marketcap_symbols()

    print("市值前50符号：", top_symbols)

    # 2) OKX 所有可交易的永续合约
    okx_swaps = get_okx_swap_symbols()

    # 输出形式是 BTC-USDT-SWAP
    result = []

    for symbol in top_symbols:
        # 币种 symbol 在永续合约命名中是前缀
        # 例如 BTC (from CoinGecko) → BTC-USDT-SWAP
        for inst in okx_swaps:
            # inst.split('-')[0] 取币名
            inst_base = inst.split("-")[0].upper()
            if inst_base == symbol:
                result.append(inst)

    return result


if __name__ == "__main__":
    swaps = filter_top_swap_symbols()
    print("\n✅ OKX 市值前50可交易的永续合约：")
    for s in swaps:
        print(s)

    print("\n总数量：", len(swaps))
```

---

# ✅ 输出示例（实际跑出来会类似）

```
✅ OKX 市值前50可交易的永续合约：
BTC-USDT-SWAP
ETH-USDT-SWAP
SOL-USDT-SWAP
XRP-USDT-SWAP
ADA-USDT-SWAP
...
总数量： 33
```

（数量可能少于 50，因为不是每个币都有永续合约）

---

# ✅ 换成你的 trading bot 使用方式

你可以把 `swaps` 作为可选交易标的：

```python
tradable_symbols = filter_top_swap_symbols()

for symbol in tradable_symbols:
    print("执行网格策略：", symbol)
    # 你的策略逻辑，例如 place_order(symbol, ...)
```

---

# ✅ 完整代码：获取市值 Top50 + 筛选 OKX 永续合约

```python
import requests
import ccxt
import time

def get_top_marketcap_symbols(top_n=50):
    """
    从 CoinGecko 获取市值前 N 币种
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": top_n,
        "page": 1
    }
    
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    # 只取 symbol，并转成大写
    return [coin["symbol"].upper() for coin in data]


def get_okx_swap_symbols():
    """
    从 OKX 获取所有支持的永续合约：例如 BTC-USDT-SWAP
    """
    exchange = ccxt.okx()
    markets = exchange.load_markets()
    return [m for m in markets if m.endswith("-USDT-SWAP")]


def filter_top_swap_symbols():
    # 1) 市值前50币种
    top_symbols = get_top_marketcap_symbols()

    print("市值前50符号：", top_symbols)

    # 2) OKX 所有可交易的永续合约
    okx_swaps = get_okx_swap_symbols()

    # 输出形式是 BTC-USDT-SWAP
    result = []

    for symbol in top_symbols:
        # 币种 symbol 在永续合约命名中是前缀
        # 例如 BTC (from CoinGecko) → BTC-USDT-SWAP
        for inst in okx_swaps:
            # inst.split('-')[0] 取币名
            inst_base = inst.split("-")[0].upper()
            if inst_base == symbol:
                result.append(inst)

    return result


if __name__ == "__main__":
    swaps = filter_top_swap_symbols()
    print("\n✅ OKX 市值前50可交易的永续合约：")
    for s in swaps:
        print(s)

    print("\n总数量：", len(swaps))
```

---

# ✅ 输出示例（实际跑出来会类似）

```
✅ OKX 市值前50可交易的永续合约：
BTC-USDT-SWAP
ETH-USDT-SWAP
SOL-USDT-SWAP
XRP-USDT-SWAP
ADA-USDT-SWAP
...
总数量： 33
```

（数量可能少于 50，因为不是每个币都有永续合约）

---

# ✅ 换成你的 trading bot 使用方式

你可以把 `swaps` 作为可选交易标的：

```python
tradable_symbols = filter_top_swap_symbols()

for symbol in tradable_symbols:
    print("执行网格策略：", symbol)
    # 你的策略逻辑，例如 place_order(symbol, ...)
```

 


---

## Final Resolution Summary

**Issue**: `scripts/get_top50.py` incorrectly selected cryptocurrencies by funding rate instead of market capitalization, and returned symbols in wrong format for CCXT consumption.

**Solution**: Complete rewrite using OpenSpec change 0002 with market cap based selection and proper CCXT formatting.

**Key Achievements**:
1. ✅ **Correct Selection Methodology**: Now uses CoinGecko market cap API instead of funding rates
2. ✅ **Proper Symbol Format**: Returns `BTC/USDT` format compatible with CCXT library
3. ✅ **Tradability Filtering**: Only includes symbols actually available on OKX exchange
4. ✅ **Comprehensive Testing**: 25 unit tests with full coverage
5. ✅ **OpenSpec Compliance**: Properly documented change management process
6. ✅ **Caching & Resilience**: Added intelligent caching and error handling

**Current Status**: ✅ **FULLY RESOLVED** - Issue closed with complete solution implemented and validated.
