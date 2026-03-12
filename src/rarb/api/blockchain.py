"""Real-time blockchain data manager."""

from web3 import Web3
from decimal import Decimal
from rarb.config import get_settings
from rarb.utils.logging import get_logger

log = get_logger(__name__)

# USDC on Polygon
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

class BlockchainManager:
    """Handles real-time balance and on-chain status."""

    def __init__(self):
        self.settings = get_settings()
        self.w3 = Web3(Web3.HTTPProvider(self.settings.polygon_rpc_url))
        self.usdc = self.w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI)

    def get_usdc_balance(self) -> Decimal:
        """Fetch real USDC balance from Polygon."""
        if not self.settings.wallet_address:
            return Decimal("0")
        
        try:
            addr = Web3.to_checksum_address(self.settings.wallet_address)
            raw_balance = self.usdc.functions.balanceOf(addr).call()
            decimals = self.usdc.functions.decimals().call()
            return Decimal(raw_balance) / Decimal(10 ** decimals)
        except Exception as e:
            log.debug(f"Blockchain balance fetch failed: {e}")
            return Decimal("0")

    def is_connected(self) -> bool:
        return self.w3.is_connected()
