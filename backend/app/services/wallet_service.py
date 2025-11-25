"""
Wallet Service - Handles wallet creation and address generation for all supported cryptocurrencies.

Supported networks:
- Bitcoin (BTC)
- Ethereum (ETH)
- Tron (TRX) / USDT-TRC20
- Solana (SOL)
- Litecoin (LTC)
- Dogecoin (DOGE)
- Stellar (XLM)
"""

import os
import hashlib
import secrets
from decimal import Decimal
from flask import current_app

from app import db
from app.models.wallet import Wallet, WalletAddress, Currency
from app.models.balance import Balance


def create_user_wallets(user_id: int):
    """Create wallets for all active currencies when user registers"""
    currencies = Currency.query.filter_by(is_active=True).all()

    for currency in currencies:
        try:
            # Check if wallet already exists
            existing = Wallet.query.filter_by(user_id=user_id, currency_id=currency.id).first()
            if existing:
                # Check if address exists, if not generate one
                if not WalletAddress.query.filter_by(wallet_id=existing.id).first():
                    try:
                        generate_deposit_address(existing)
                    except Exception as e:
                        current_app.logger.error(f"Failed to generate address for existing wallet {currency.symbol}: {e}")
                continue

            # Create wallet
            wallet = Wallet(user_id=user_id, currency_id=currency.id)
            db.session.add(wallet)
            db.session.flush()

            # Create initial balance if not exists
            existing_balance = Balance.query.filter_by(user_id=user_id, currency_id=currency.id).first()
            if not existing_balance:
                balance = Balance(
                    user_id=user_id,
                    currency_id=currency.id,
                    available=Decimal('0'),
                    locked=Decimal('0'),
                    total=Decimal('0')
                )
                db.session.add(balance)

            # Generate deposit address
            try:
                generate_deposit_address(wallet)
            except Exception as e:
                current_app.logger.error(f"Failed to generate address for {currency.symbol}: {e}")
                db.session.rollback()
                continue

            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to create wallet for {currency.symbol}: {e}")
            db.session.rollback()
            continue


def generate_deposit_address(wallet: Wallet) -> WalletAddress:
    """Generate a new deposit address for a wallet"""
    currency = wallet.currency

    # Get next derivation index
    last_address = WalletAddress.query.filter_by(wallet_id=wallet.id).order_by(
        WalletAddress.derivation_index.desc()
    ).first()
    derivation_index = (last_address.derivation_index + 1) if last_address else 0

    # Generate address based on network
    network = currency.network
    address = None
    memo = None

    if network == 'btc_mainnet':
        address = generate_btc_address(wallet.user_id, derivation_index)
    elif network == 'eth_mainnet':
        address = generate_eth_address(wallet.user_id, derivation_index)
    elif network == 'trx_mainnet':
        address = generate_trx_address(wallet.user_id, derivation_index, currency.symbol)
    elif network == 'sol_mainnet':
        address = generate_sol_address(wallet.user_id, derivation_index)
    elif network == 'ltc_mainnet':
        address = generate_ltc_address(wallet.user_id, derivation_index)
    elif network == 'doge_mainnet':
        address = generate_doge_address(wallet.user_id, derivation_index)
    elif network == 'xlm_mainnet':
        address, memo = generate_xlm_address(wallet.user_id, derivation_index)
    else:
        raise ValueError(f"Unsupported network: {network}")

    # Create address record
    wallet_address = WalletAddress(
        wallet_id=wallet.id,
        address=address,
        memo=memo,
        derivation_index=derivation_index
    )
    db.session.add(wallet_address)
    db.session.commit()

    return wallet_address


def generate_btc_address(user_id: int, index: int) -> str:
    """
    Generate Bitcoin address using HD wallet derivation.

    In production, use proper HD wallet with xpub:
    - Path: m/84'/0'/0'/0/{index} for native segwit
    - Or use a custody solution API
    """
    try:
        # Production: Use bitcoinlib or external custody service
        # from bitcoinlib.wallets import Wallet as BTCWallet
        # wallet = BTCWallet('platform_wallet')
        # key = wallet.get_key(index)
        # return key.address

        # Development placeholder - generates unique deterministic address
        seed = f"btc:{os.getenv('BTC_XPUB', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        # Generate P2WPKH-style address (starts with bc1)
        address = f"bc1q{hash_bytes[:20].hex()}"
        return address

    except Exception as e:
        current_app.logger.error(f"BTC address generation failed: {e}")
        raise


def generate_eth_address(user_id: int, index: int) -> str:
    """
    Generate Ethereum address.

    In production, use web3.py with HD wallet:
    - Path: m/44'/60'/0'/0/{index}
    """
    try:
        # Production: Use eth-account
        # from eth_account import Account
        # Account.enable_unaudited_hdwallet_features()
        # acct = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{index}")
        # return acct.address

        # Development placeholder
        seed = f"eth:{os.getenv('ETH_XPUB', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        address = f"0x{hash_bytes[:20].hex()}"
        return address

    except Exception as e:
        current_app.logger.error(f"ETH address generation failed: {e}")
        raise


def generate_trx_address(user_id: int, index: int, currency_symbol: str = 'TRX') -> str:
    """
    Generate Tron address for TRX and TRC20 tokens (USDT).

    In production, use tronpy or TronGrid API.
    """
    try:
        # Production: Use tronpy
        # from tronpy.keys import PrivateKey
        # Generate from HD path or use address pool

        # Development placeholder - include currency to ensure uniqueness
        seed = f"trx:{currency_symbol}:{os.getenv('TRX_XPUB', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        # Tron addresses start with 'T'
        import base58
        address_bytes = b'\x41' + hash_bytes[:20]
        checksum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
        address = base58.b58encode(address_bytes + checksum).decode()
        return address

    except Exception as e:
        current_app.logger.error(f"TRX address generation failed: {e}")
        raise


def generate_sol_address(user_id: int, index: int) -> str:
    """
    Generate Solana address.

    In production, use solana-py or Solana Web3.
    """
    try:
        # Production: Use solders/solana-py
        # from solders.keypair import Keypair

        # Development placeholder
        seed = f"sol:{os.getenv('SOL_XPUB', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        import base58
        address = base58.b58encode(hash_bytes).decode()
        return address

    except Exception as e:
        current_app.logger.error(f"SOL address generation failed: {e}")
        raise


def generate_ltc_address(user_id: int, index: int) -> str:
    """
    Generate Litecoin address.

    In production, use proper LTC library with HD derivation.
    Path: m/84'/2'/0'/0/{index} for native segwit
    """
    try:
        # Development placeholder
        seed = f"ltc:{os.getenv('LTC_XPUB', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        # LTC native segwit starts with 'ltc1'
        address = f"ltc1q{hash_bytes[:20].hex()}"
        return address

    except Exception as e:
        current_app.logger.error(f"LTC address generation failed: {e}")
        raise


def generate_doge_address(user_id: int, index: int) -> str:
    """
    Generate Dogecoin address.

    In production, use proper DOGE library.
    """
    try:
        # Development placeholder
        seed = f"doge:{os.getenv('DOGE_XPUB', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        # DOGE addresses start with 'D'
        import base58
        address_bytes = b'\x1e' + hash_bytes[:20]
        checksum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
        address = base58.b58encode(address_bytes + checksum).decode()
        return address

    except Exception as e:
        current_app.logger.error(f"DOGE address generation failed: {e}")
        raise


def generate_xlm_address(user_id: int, index: int) -> tuple:
    """
    Generate Stellar address with memo.

    For Stellar, typically use a single receiving address with unique memo per user.
    In production, this would be a real Stellar address.
    """
    try:
        # Production: Use stellar-sdk with real hot wallet
        # In most cases, exchanges use one hot wallet address with unique memos

        # Development: Generate unique addresses per user (to avoid unique constraint issues)
        seed = f"xlm:{os.getenv('XLM_HOT_WALLET', 'dev')}:{user_id}:{index}"
        hash_bytes = hashlib.sha256(seed.encode()).digest()
        # Stellar addresses start with 'G' - generate unique per user for dev
        address = f"G{hash_bytes[:28].hex().upper()}"

        # Generate unique memo for this user
        memo = f"{user_id:010d}"  # 10-digit user ID as memo

        return address, memo

    except Exception as e:
        current_app.logger.error(f"XLM address generation failed: {e}")
        raise


def get_wallet_balance(wallet: Wallet) -> dict:
    """Get on-chain balance for a wallet (for reconciliation)"""
    # This would query the actual blockchain
    # Implementation depends on the specific blockchain
    pass


def validate_withdrawal_address(currency_symbol: str, address: str) -> bool:
    """Validate that an address is valid for the given currency"""
    from app.services.blockchain_service import validate_address

    currency = Currency.query.filter_by(symbol=currency_symbol.upper()).first()
    if not currency:
        return False

    return validate_address(currency.network, address)
