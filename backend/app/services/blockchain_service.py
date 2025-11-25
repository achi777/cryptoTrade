"""
Blockchain Service - Handles blockchain interactions for all supported networks.

Responsibilities:
- Address validation
- Transaction broadcasting
- Transaction status tracking
- Deposit detection (via polling or webhooks)
- Fee estimation
"""

import re
import hashlib
from decimal import Decimal
from typing import Optional, Dict, Any
from flask import current_app
import requests


def validate_address(network: str, address: str) -> bool:
    """Validate blockchain address format"""
    if not address:
        return False

    validators = {
        'btc_mainnet': validate_btc_address,
        'eth_mainnet': validate_eth_address,
        'trx_mainnet': validate_trx_address,
        'sol_mainnet': validate_sol_address,
        'ltc_mainnet': validate_ltc_address,
        'doge_mainnet': validate_doge_address,
        'xlm_mainnet': validate_xlm_address,
    }

    validator = validators.get(network)
    if not validator:
        return False

    try:
        return validator(address)
    except Exception:
        return False


def validate_btc_address(address: str) -> bool:
    """Validate Bitcoin address (Legacy, SegWit, Native SegWit)"""
    # Legacy (P2PKH) - starts with 1
    if re.match(r'^1[a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
        return True
    # Legacy (P2SH) - starts with 3
    if re.match(r'^3[a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
        return True
    # Native SegWit (Bech32) - starts with bc1
    if re.match(r'^bc1[ac-hj-np-z02-9]{39,59}$', address.lower()):
        return True
    return False


def validate_eth_address(address: str) -> bool:
    """Validate Ethereum address"""
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return False
    return True


def validate_trx_address(address: str) -> bool:
    """Validate Tron address"""
    if not re.match(r'^T[a-zA-Z0-9]{33}$', address):
        return False
    return True


def validate_sol_address(address: str) -> bool:
    """Validate Solana address (base58, 32-44 chars)"""
    if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return False
    return True


def validate_ltc_address(address: str) -> bool:
    """Validate Litecoin address"""
    # Legacy - starts with L or M
    if re.match(r'^[LM][a-km-zA-HJ-NP-Z1-9]{26,33}$', address):
        return True
    # Native SegWit - starts with ltc1
    if re.match(r'^ltc1[ac-hj-np-z02-9]{39,59}$', address.lower()):
        return True
    return False


def validate_doge_address(address: str) -> bool:
    """Validate Dogecoin address - starts with D or A"""
    if re.match(r'^[DA][a-km-zA-HJ-NP-Z1-9]{25,34}$', address):
        return True
    return False


def validate_xlm_address(address: str) -> bool:
    """Validate Stellar address - starts with G"""
    if re.match(r'^G[A-Z2-7]{55}$', address):
        return True
    return False


def estimate_withdrawal_fee(network: str) -> Decimal:
    """Estimate current network fee for withdrawal"""
    # In production, fetch real-time fee estimates from blockchain
    fees = {
        'btc_mainnet': Decimal('0.0001'),
        'eth_mainnet': Decimal('0.002'),
        'trx_mainnet': Decimal('1'),
        'sol_mainnet': Decimal('0.000005'),
        'ltc_mainnet': Decimal('0.001'),
        'doge_mainnet': Decimal('1'),
        'xlm_mainnet': Decimal('0.00001'),
    }
    return fees.get(network, Decimal('0'))


def broadcast_transaction(network: str, signed_tx: str) -> Optional[str]:
    """Broadcast signed transaction to the network"""
    try:
        if network == 'btc_mainnet':
            return broadcast_btc_transaction(signed_tx)
        elif network == 'eth_mainnet':
            return broadcast_eth_transaction(signed_tx)
        elif network == 'trx_mainnet':
            return broadcast_trx_transaction(signed_tx)
        # Add other networks...
    except Exception as e:
        current_app.logger.error(f"Transaction broadcast failed: {e}")
        return None


def broadcast_btc_transaction(signed_tx: str) -> Optional[str]:
    """Broadcast Bitcoin transaction"""
    try:
        # Using Blockstream API
        url = f"{current_app.config['BTC_NODE_URL']}/tx"
        response = requests.post(url, data=signed_tx, timeout=30)
        if response.status_code == 200:
            return response.text  # Returns txid
        return None
    except Exception as e:
        current_app.logger.error(f"BTC broadcast failed: {e}")
        return None


def broadcast_eth_transaction(signed_tx: str) -> Optional[str]:
    """Broadcast Ethereum transaction"""
    try:
        # Using Web3 or Infura
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(current_app.config['ETH_NODE_URL']))
        tx_hash = w3.eth.send_raw_transaction(signed_tx)
        return tx_hash.hex()
    except Exception as e:
        current_app.logger.error(f"ETH broadcast failed: {e}")
        return None


def broadcast_trx_transaction(signed_tx: dict) -> Optional[str]:
    """Broadcast Tron transaction"""
    try:
        url = f"{current_app.config['TRX_NODE_URL']}/wallet/broadcasttransaction"
        response = requests.post(url, json=signed_tx, timeout=30)
        result = response.json()
        if result.get('result'):
            return result.get('txid')
        return None
    except Exception as e:
        current_app.logger.error(f"TRX broadcast failed: {e}")
        return None


def get_transaction_status(network: str, tx_hash: str) -> Dict[str, Any]:
    """Get transaction status and confirmations"""
    try:
        if network == 'btc_mainnet':
            return get_btc_transaction_status(tx_hash)
        elif network == 'eth_mainnet':
            return get_eth_transaction_status(tx_hash)
        elif network == 'trx_mainnet':
            return get_trx_transaction_status(tx_hash)
        # Add other networks...
        return {'status': 'unknown', 'confirmations': 0}
    except Exception as e:
        current_app.logger.error(f"Failed to get tx status: {e}")
        return {'status': 'error', 'confirmations': 0}


def get_btc_transaction_status(tx_hash: str) -> Dict[str, Any]:
    """Get Bitcoin transaction status"""
    try:
        url = f"{current_app.config['BTC_NODE_URL']}/tx/{tx_hash}"
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return {'status': 'not_found', 'confirmations': 0}

        tx = response.json()
        status = tx.get('status', {})
        confirmed = status.get('confirmed', False)
        block_height = status.get('block_height')

        if not confirmed:
            return {'status': 'pending', 'confirmations': 0}

        # Get current block height
        tip_url = f"{current_app.config['BTC_NODE_URL']}/blocks/tip/height"
        tip_response = requests.get(tip_url, timeout=30)
        current_height = int(tip_response.text)
        confirmations = current_height - block_height + 1

        return {
            'status': 'confirmed',
            'confirmations': confirmations,
            'block_height': block_height
        }
    except Exception as e:
        current_app.logger.error(f"BTC tx status failed: {e}")
        return {'status': 'error', 'confirmations': 0}


def get_eth_transaction_status(tx_hash: str) -> Dict[str, Any]:
    """Get Ethereum transaction status"""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(current_app.config['ETH_NODE_URL']))

        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if not receipt:
            return {'status': 'pending', 'confirmations': 0}

        current_block = w3.eth.block_number
        confirmations = current_block - receipt['blockNumber'] + 1

        status = 'confirmed' if receipt['status'] == 1 else 'failed'
        return {
            'status': status,
            'confirmations': confirmations,
            'block_height': receipt['blockNumber']
        }
    except Exception as e:
        current_app.logger.error(f"ETH tx status failed: {e}")
        return {'status': 'error', 'confirmations': 0}


def get_trx_transaction_status(tx_hash: str) -> Dict[str, Any]:
    """Get Tron transaction status"""
    try:
        url = f"{current_app.config['TRX_NODE_URL']}/wallet/gettransactionbyid"
        response = requests.post(url, json={'value': tx_hash}, timeout=30)
        tx = response.json()

        if not tx or 'ret' not in tx:
            return {'status': 'not_found', 'confirmations': 0}

        ret = tx.get('ret', [{}])[0]
        if ret.get('contractRet') == 'SUCCESS':
            # Tron confirmations are typically fast
            return {'status': 'confirmed', 'confirmations': 19}
        return {'status': 'pending', 'confirmations': 0}
    except Exception as e:
        current_app.logger.error(f"TRX tx status failed: {e}")
        return {'status': 'error', 'confirmations': 0}


class BlockchainListener:
    """
    Listens for incoming deposits on all supported networks.

    In production, this would be a separate service running continuously.
    Options:
    1. Polling: Periodically check addresses for new transactions
    2. Webhooks: Use services like BlockCypher, Alchemy, etc.
    3. Full node: Run your own nodes with subscription to new blocks
    """

    def __init__(self):
        self.networks = ['btc_mainnet', 'eth_mainnet', 'trx_mainnet', 'sol_mainnet']

    def start_listening(self):
        """Start the deposit listener (would run in separate thread/process)"""
        pass

    def check_deposits(self, network: str, addresses: list):
        """Check for new deposits to the given addresses"""
        pass

    def process_deposit(self, address: str, tx_hash: str, amount: Decimal, currency: str):
        """Process a detected deposit"""
        from app.models.wallet import WalletAddress
        from app.models.balance import Balance, Transaction, TransactionType, TransactionStatus

        # Find wallet address
        wallet_address = WalletAddress.query.filter_by(address=address).first()
        if not wallet_address:
            current_app.logger.warning(f"Unknown deposit address: {address}")
            return

        wallet = wallet_address.wallet
        user_id = wallet.user_id
        currency_id = wallet.currency_id

        # Check if transaction already processed
        existing = Transaction.query.filter_by(tx_hash=tx_hash).first()
        if existing:
            return

        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            currency_id=currency_id,
            type=TransactionType.DEPOSIT.value,
            status=TransactionStatus.CONFIRMING.value,
            amount=amount,
            fee=Decimal('0'),
            net_amount=amount,
            tx_hash=tx_hash,
            to_address=address
        )
        db.session.add(transaction)

        # Credit will be applied after sufficient confirmations
        db.session.commit()
