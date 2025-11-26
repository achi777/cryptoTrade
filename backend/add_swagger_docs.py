#!/usr/bin/env python3
"""
Script to add Swagger documentation to all API endpoints
"""

# Swagger documentation templates for remaining endpoints

WALLET_DOCS = """
from flasgger import swag_from

# /wallets - GET
WALLETS_GET = {
    'tags': ['Wallet'],
    'security': [{'Bearer': []}],
    'responses': {
        200: {
            'description': 'List of user wallets',
            'schema': {
                'type': 'object',
                'properties': {
                    'wallets': {'type': 'array'}
                }
            }
        }
    }
}

# /wallets/<currency> - GET
WALLET_GET = {
    'tags': ['Wallet'],
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'currency_symbol',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Currency symbol (e.g., BTC, ETH)'
        }
    ],
    'responses': {
        200: {'description': 'Wallet details'},
        404: {'description': 'Wallet not found'}
    }
}

# /wallets/<currency>/address - GET
DEPOSIT_ADDRESS_GET = {
    'tags': ['Wallet'],
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'currency_symbol',
            'in': 'path',
            'type': 'string',
            'required': True
        }
    ],
    'responses': {
        200: {
            'description': 'Deposit address',
            'schema': {
                'type': 'object',
                'properties': {
                    'address': {'type': 'string'},
                    'memo': {'type': 'string'},
                    'currency': {'type': 'string'},
                    'network': {'type': 'string'}
                }
            }
        }
    }
}

# /wallets/withdraw - POST
WITHDRAW_POST = {
    'tags': ['Wallet'],
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['currency', 'address', 'amount', 'totp_code'],
                'properties': {
                    'currency': {'type': 'string', 'example': 'BTC'},
                    'address': {'type': 'string', 'example': 'bc1q...'},
                    'amount': {'type': 'string', 'example': '0.01'},
                    'memo': {'type': 'string'},
                    'totp_code': {'type': 'string', 'example': '123456'}
                }
            }
        }
    ],
    'responses': {
        201: {'description': 'Withdrawal request created'},
        400: {'description': 'Invalid input or insufficient balance'},
        403: {'description': '2FA required or address blacklisted'}
    }
}
"""

USER_DOCS = """
# /user/profile - GET
PROFILE_GET = {
    'tags': ['User'],
    'security': [{'Bearer': []}],
    'responses': {
        200: {
            'description': 'User profile',
            'schema': {
                'type': 'object',
                'properties': {
                    'user': {'type': 'object'}
                }
            }
        }
    }
}

# /user/profile - PUT
PROFILE_PUT = {
    'tags': ['User'],
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'first_name': {'type': 'string'},
                    'last_name': {'type': 'string'},
                    'phone': {'type': 'string'},
                    'country': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Profile updated'}
    }
}

# /user/2fa/enable - POST
TFA_ENABLE = {
    'tags': ['User'],
    'security': [{'Bearer': []}],
    'responses': {
        200: {
            'description': '2FA setup',
            'schema': {
                'type': 'object',
                'properties': {
                    'secret': {'type': 'string'},
                    'qr_code': {'type': 'string'}
                }
            }
        }
    }
}

# /user/2fa/verify - POST
TFA_VERIFY = {
    'tags': ['User'],
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['totp_code'],
                'properties': {
                    'totp_code': {'type': 'string', 'example': '123456'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': '2FA enabled'},
        400: {'description': 'Invalid code'}
    }
}
"""

MARKET_DOCS = """
# /market/ticker/<symbol> - GET
TICKER_GET = {
    'tags': ['Market'],
    'parameters': [
        {
            'name': 'symbol',
            'in': 'path',
            'type': 'string',
            'required': True,
            'example': 'BTC/USDT'
        }
    ],
    'responses': {
        200: {
            'description': 'Market ticker data',
            'schema': {
                'type': 'object',
                'properties': {
                    'symbol': {'type': 'string'},
                    'last_price': {'type': 'string'},
                    'volume_24h': {'type': 'string'},
                    'high_24h': {'type': 'string'},
                    'low_24h': {'type': 'string'}
                }
            }
        }
    }
}

# /market/orderbook/<symbol> - GET
ORDERBOOK_GET = {
    'tags': ['Market'],
    'parameters': [
        {
            'name': 'symbol',
            'in': 'path',
            'type': 'string',
            'required': True
        }
    ],
    'responses': {
        200: {
            'description': 'Order book',
            'schema': {
                'type': 'object',
                'properties': {
                    'bids': {'type': 'array'},
                    'asks': {'type': 'array'}
                }
            }
        }
    }
}
"""

print("Swagger documentation templates created!")
print("\nTo use these, add @swag_from decorators to your endpoints.")
print("Example:")
print("  @api_v1_bp.route('/wallets', methods=['GET'])")
print("  @jwt_required()")
print("  @swag_from(WALLETS_GET)")
print("  def get_wallets():")
print("      ...")
