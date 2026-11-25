"""Group perpetual symbols into asset classes a trader recognises.

The lists cover well-known tickers only. Anything unknown falls back to
"Small caps & new listings", except multiplier tickers (1000PEPE, 10000SATS...), which are
almost always low-priced memecoins.
"""

from __future__ import annotations

import re
from functools import lru_cache

CLASS_ORDER = ["Bitcoin", "Ethereum", "Large caps", "Layer 1 & 2", "DeFi", "AI", "Memecoins",
               "Gaming & metaverse", "Small caps & new listings"]

_LISTS = {
    "Bitcoin": {"BTC", "WBTC"},
    "Ethereum": {"ETH", "STETH", "WETH"},
    "Memecoins": {
        "GME", "GORK", "PIGGY", "BOBBOB", "CASHCAT", "GIGGLE", "MARSCOIN", "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "FARTCOIN", "PENGU", "POPCAT", "MEW", "BOME", "BRETT",
        "TURBO", "NEIRO", "NEIROETH", "MOODENG", "GOAT", "PNUT", "ACT", "SPX", "MOG", "CHEEMS", "ELON",
        "BABYDOGE", "DOGS", "TRUMP", "MELANIA", "MEME", "LADYS", "SATS", "RATS", "MYRO", "SLERF", "WEN", "GIGA",
        "CHILLGUY", "HIPPO", "PEOPLE", "BAN", "MUBARAK", "BROCCOLI", "TUT", "APU", "CAT", "MUMU", "PONKE",
        "SUNDOG", "DEGEN", "TOSHI", "MICHI", "BOBO", "COQ", "AIDOGE", "PEPECOIN", "LUCE", "FWOG", "SIGMA",
        "BANANAS31", "KOMA", "DOG", "MOTHER", "RETARDIO", "ZEREBRO", "ANIME", "WHY", "PUMP", "PUMPFUN",
        "USELESS", "FARTBOY", "JELLYJELLY", "HOUSE", "ALCH", "VINE", "PIPPIN", "LAUNCHCOIN",
    },
    "AI": {
        "AIA", "FLOCK", "RECALL", "BLUAI", "AIN", "AIGENSYN", "SAPIEN", "COAI", "UAI", "ALLO", "FET", "RENDER", "RNDR", "TAO", "WLD", "AGIX", "OCEAN", "ARKM", "AI16Z", "VIRTUAL", "GRASS", "IO", "AIXBT",
        "GRIFFAIN", "THETA", "AKT", "PHB", "NMR", "CGPT", "AI", "SAHARA", "KAITO", "SWARMS", "COOKIE", "ARC",
        "AVAAI", "VVV", "TAI", "NFP", "GLM", "AIOZ", "PROMPT",
    },
    "DeFi": {
        "COW", "SOLV", "PUFFER", "RAYDIUM", "VELODROME", "AEVO", "APEX", "LEVER", "IDEX", "SYN", "MAV", "DOLO", "HAEDAL", "FOLKS", "ENSO", "NEWT", "TNSR", "UNI", "AAVE", "MKR", "LDO", "CRV", "COMP", "SUSHI", "SNX", "DYDX", "1INCH", "PENDLE", "JUP", "RAY", "CAKE",
        "GMX", "ENA", "ETHFI", "EIGEN", "ONDO", "JTO", "MORPHO", "HYPE", "CVX", "BAL", "YFI", "RUNE", "ASTER",
        "AERO", "VELO", "LINK", "PYTH", "LQTY", "RPL", "SSV", "FXS", "SUN", "JOE", "ORCA", "DRIFT", "KMNO",
        "USUAL", "RESOLV", "SKY", "SYRUP", "AVNT", "WLFI", "LISTA", "BB", "REZ", "OM", "TRB", "API3", "BAND", "UMA",
    },
    "Gaming & metaverse": {
        "BEAM", "GUN", "PYR", "ESPORTS", "AXS", "SAND", "MANA", "GALA", "IMX", "APE", "ENJ", "ILV", "YGG", "PIXEL", "NOT", "BEAMX", "MAGIC", "PRIME",
        "SUPER", "GMT", "RON", "ALICE", "HMSTR", "CATI", "XAI", "PORTAL", "BIGTIME", "MAVIA", "VOXEL", "GODS",
        "MBOX", "ACE", "SLP", "FLOW", "CHZ", "MOCA",
    },
    "Large caps": {"BNB", "SOL", "XRP", "ADA", "TRX", "TON", "AVAX", "DOT", "LTC", "BCH", "XLM", "HBAR", "XMR"},
    "Layer 1 & 2": {
        "0G", "SOMI", "HYPER", "AZTEC", "FUEL", "CRO", "WAL", "XION", "ZORA", "MOVR", "CYBER", "SUI", "APT", "SEI", "NEAR", "ATOM", "ALGO", "FTM", "S", "ICP", "FIL", "ETC", "EGLD", "KAS", "TIA", "INJ",
        "ARB", "OP", "MATIC", "POL", "STRK", "ZK", "MNT", "BLAST", "MOVE", "BERA", "XTZ", "EOS", "NEO", "VET", "STX",
        "CELO", "KAVA", "ONE", "ROSE", "MINA", "QNT", "TAIKO", "SCR", "MANTA", "METIS", "DYM", "SAGA", "ZRO", "W",
        "AR", "IOTA", "ZIL", "THETA", "KSM", "WAVES", "CFX", "CORE", "FLR", "XDC", "ZETA", "OMNI", "ASTR", "GLMR",
        "BSV", "ZEC", "DASH", "QTUM", "ONT", "IOTX", "LSK", "HNT", "SONIC", "INIT", "MERL", "B3", "LINEA", "PLUME",
        "PARTI", "SOON", "ERA", "HUMA", "HEMI", "SOPH", "NIL", "KAIA", "BTT", "JST", "XPL", "MON", "STABLE", "ALT", "IP",
    },
}
_LOOKUP = {}
for _cls in ["Bitcoin", "Ethereum", "Memecoins", "AI", "DeFi", "Gaming & metaverse", "Large caps", "Layer 1 & 2"]:
    for _t in _LISTS[_cls]:
        _LOOKUP.setdefault(_t, _cls)

_QUOTE = re.compile(r"(USDT|USDC|USD|PERP)$")
_MULT_PREFIX = re.compile(r"^(10+|1M)(?=[A-Z])")
_MULT_SUFFIX = re.compile(r"(?<=[A-Z])10+$")


def base_asset(symbol: str) -> tuple[str, bool]:
    """('PEPE', True) for '1000PEPEUSDT'; the flag says a price multiplier was stripped."""
    s = _QUOTE.sub("", str(symbol).upper())
    stripped = _MULT_PREFIX.sub("", s)
    stripped = _MULT_SUFFIX.sub("", stripped)
    return stripped, stripped != s


@lru_cache(maxsize=4096)
def asset_class(symbol: str) -> str:
    base, multiplied = base_asset(symbol)
    if base in _LOOKUP:
        return _LOOKUP[base]
    return "Memecoins" if multiplied else "Small caps & new listings"
