from flask import jsonify
from app.api.v1 import api_v1_bp


@api_v1_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'CryptoTrade API is running'
    }), 200
