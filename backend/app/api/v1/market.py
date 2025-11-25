from flask import request, jsonify
from datetime import datetime, timedelta

from app.api.v1 import api_v1_bp
from app import db, redis_client
from app.models.trading import TradingPair, Order, Trade, Candle, OrderSide, OrderStatus
import json


@api_v1_bp.route('/market/tickers', methods=['GET'])
def get_tickers():
    """Get all market tickers"""
    pairs = TradingPair.query.filter_by(is_active=True).all()

    tickers = []
    for pair in pairs:
        tickers.append({
            'symbol': pair.symbol,
            'last_price': str(pair.last_price),
            'price_change_24h': str(pair.price_change_24h),
            'high_24h': str(pair.high_24h),
            'low_24h': str(pair.low_24h),
            'volume_24h': str(pair.volume_24h)
        })

    return jsonify({'tickers': tickers}), 200


@api_v1_bp.route('/market/ticker/<symbol>', methods=['GET'])
def get_ticker(symbol):
    """Get specific market ticker"""
    pair = TradingPair.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    return jsonify({
        'ticker': {
            'symbol': pair.symbol,
            'last_price': str(pair.last_price),
            'price_change_24h': str(pair.price_change_24h),
            'high_24h': str(pair.high_24h),
            'low_24h': str(pair.low_24h),
            'volume_24h': str(pair.volume_24h)
        }
    }), 200


@api_v1_bp.route('/market/orderbook/<symbol>', methods=['GET'])
def get_orderbook(symbol):
    """Get order book for trading pair"""
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 500)

    pair = TradingPair.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    # Try cache first
    cache_key = f'orderbook:{symbol.upper()}'
    cached = None
    try:
        if redis_client:
            cached = redis_client.get(cache_key)
    except Exception:
        pass  # Redis not available, continue without cache

    if cached:
        return jsonify(json.loads(cached)), 200

    # Get open orders
    buy_orders = Order.query.filter(
        Order.trading_pair_id == pair.id,
        Order.side == OrderSide.BUY.value,
        Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
        Order.price.isnot(None)
    ).order_by(Order.price.desc()).limit(limit).all()

    sell_orders = Order.query.filter(
        Order.trading_pair_id == pair.id,
        Order.side == OrderSide.SELL.value,
        Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
        Order.price.isnot(None)
    ).order_by(Order.price.asc()).limit(limit).all()

    # Aggregate by price level
    bids = {}
    for order in buy_orders:
        price_str = str(order.price)
        if price_str not in bids:
            bids[price_str] = {'price': price_str, 'amount': '0'}
        bids[price_str]['amount'] = str(float(bids[price_str]['amount']) + float(order.remaining_amount))

    asks = {}
    for order in sell_orders:
        price_str = str(order.price)
        if price_str not in asks:
            asks[price_str] = {'price': price_str, 'amount': '0'}
        asks[price_str]['amount'] = str(float(asks[price_str]['amount']) + float(order.remaining_amount))

    orderbook = {
        'symbol': pair.symbol,
        'bids': list(bids.values()),
        'asks': list(asks.values()),
        'timestamp': datetime.utcnow().isoformat()
    }

    # Cache for 1 second
    try:
        if redis_client:
            redis_client.setex(cache_key, 1, json.dumps(orderbook))
    except Exception:
        pass  # Redis not available, continue without cache

    return jsonify(orderbook), 200


@api_v1_bp.route('/market/trades/<symbol>', methods=['GET'])
def get_recent_trades(symbol):
    """Get recent trades for trading pair"""
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 500)

    pair = TradingPair.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    trades = Trade.query.filter_by(trading_pair_id=pair.id).order_by(
        Trade.created_at.desc()
    ).limit(limit).all()

    return jsonify({
        'trades': [{
            'id': t.id,
            'price': str(t.price),
            'amount': str(t.amount),
            'total': str(t.total),
            'timestamp': t.created_at.isoformat()
        } for t in trades]
    }), 200


@api_v1_bp.route('/market/candles/<symbol>', methods=['GET'])
def get_candles(symbol):
    """Get OHLCV candlestick data"""
    timeframe = request.args.get('timeframe', '1h')
    limit = request.args.get('limit', 100, type=int)
    limit = min(limit, 1000)

    valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
    if timeframe not in valid_timeframes:
        return jsonify({'error': f'Invalid timeframe. Valid options: {valid_timeframes}'}), 400

    pair = TradingPair.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    candles = Candle.query.filter_by(
        trading_pair_id=pair.id,
        timeframe=timeframe
    ).order_by(Candle.timestamp.desc()).limit(limit).all()

    return jsonify({
        'candles': [c.to_dict() for c in reversed(candles)]
    }), 200


@api_v1_bp.route('/market/depth/<symbol>', methods=['GET'])
def get_depth(symbol):
    """Get market depth (aggregated order book)"""
    limit = request.args.get('limit', 20, type=int)

    pair = TradingPair.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    # Get aggregated depth
    buy_orders = db.session.query(
        Order.price,
        db.func.sum(Order.remaining_amount).label('total_amount')
    ).filter(
        Order.trading_pair_id == pair.id,
        Order.side == OrderSide.BUY.value,
        Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
        Order.price.isnot(None)
    ).group_by(Order.price).order_by(Order.price.desc()).limit(limit).all()

    sell_orders = db.session.query(
        Order.price,
        db.func.sum(Order.remaining_amount).label('total_amount')
    ).filter(
        Order.trading_pair_id == pair.id,
        Order.side == OrderSide.SELL.value,
        Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
        Order.price.isnot(None)
    ).group_by(Order.price).order_by(Order.price.asc()).limit(limit).all()

    return jsonify({
        'bids': [[str(o.price), str(o.total_amount)] for o in buy_orders],
        'asks': [[str(o.price), str(o.total_amount)] for o in sell_orders]
    }), 200


@api_v1_bp.route('/market/stats', methods=['GET'])
def get_market_stats():
    """Get overall market statistics"""
    pairs = TradingPair.query.filter_by(is_active=True).all()

    total_volume = sum(float(p.volume_24h) for p in pairs)
    total_pairs = len(pairs)

    # Get 24h trade count
    day_ago = datetime.utcnow() - timedelta(days=1)
    trade_count = Trade.query.filter(Trade.created_at >= day_ago).count()

    return jsonify({
        'total_pairs': total_pairs,
        'total_volume_24h': str(total_volume),
        'total_trades_24h': trade_count
    }), 200
