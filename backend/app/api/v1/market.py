from flask import request, jsonify
from datetime import datetime, timedelta

from app.api.v1 import api_v1_bp
from app import db, redis_client, limiter
from app.models.trading import TradingPair, Order, Trade, Candle, OrderSide, OrderStatus
import json


@api_v1_bp.route('/market/tickers', methods=['GET'])
@limiter.exempt
def get_tickers():
    """
    Get All Market Tickers
    ---
    tags:
      - Market
    responses:
      200:
        description: List of all trading pair tickers
        schema:
          type: object
          properties:
            tickers:
              type: array
              items:
                type: object
                properties:
                  symbol:
                    type: string
                    example: BTC/USDT
                  last_price:
                    type: string
                    example: "50000.00"
                  price_change_24h:
                    type: string
                    example: "2.5"
                  high_24h:
                    type: string
                  low_24h:
                    type: string
                  volume_24h:
                    type: string
    """
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
@limiter.exempt
def get_ticker(symbol):
    """
    Get Specific Market Ticker
    ---
    tags:
      - Market
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol
        example: BTC/USDT
    responses:
      200:
        description: Ticker information
        schema:
          type: object
          properties:
            ticker:
              type: object
              properties:
                symbol:
                  type: string
                last_price:
                  type: string
                price_change_24h:
                  type: string
                high_24h:
                  type: string
                low_24h:
                  type: string
                volume_24h:
                  type: string
      404:
        description: Trading pair not found
    """
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
@limiter.exempt
def get_orderbook(symbol):
    """
    Get Order Book for Trading Pair
    ---
    tags:
      - Market
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol (use BTC_USDT format)
        example: BTC_USDT
      - name: limit
        in: query
        type: integer
        default: 50
        maximum: 500
        description: Number of order book levels
    responses:
      200:
        description: Order book data
        schema:
          type: object
          properties:
            symbol:
              type: string
            bids:
              type: array
              items:
                type: object
                properties:
                  price:
                    type: string
                  amount:
                    type: string
            asks:
              type: array
              items:
                type: object
            timestamp:
              type: string
              format: date-time
      404:
        description: Trading pair not found
    """
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 500)

    # Convert BTC_USDT to BTC/USDT for database query
    symbol_normalized = symbol.upper().replace('_', '/')
    pair = TradingPair.query.filter_by(symbol=symbol_normalized, is_active=True).first()
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
@limiter.exempt
def get_recent_trades(symbol):
    """
    Get Recent Trades for Trading Pair
    ---
    tags:
      - Market
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol (use BTC_USDT format)
        example: BTC_USDT
      - name: limit
        in: query
        type: integer
        default: 50
        maximum: 500
        description: Number of recent trades
    responses:
      200:
        description: List of recent trades
        schema:
          type: object
          properties:
            trades:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  price:
                    type: string
                  amount:
                    type: string
                  total:
                    type: string
                  timestamp:
                    type: string
                    format: date-time
      404:
        description: Trading pair not found
    """
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 500)

    # Convert BTC_USDT to BTC/USDT for database query
    symbol_normalized = symbol.upper().replace('_', '/')
    pair = TradingPair.query.filter_by(symbol=symbol_normalized, is_active=True).first()
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
@limiter.exempt
def get_candles(symbol):
    """
    Get OHLCV Candlestick Data
    ---
    tags:
      - Market
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol
        example: BTC/USDT
      - name: timeframe
        in: query
        type: string
        default: "1h"
        enum: ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
        description: Candle timeframe
      - name: limit
        in: query
        type: integer
        default: 100
        maximum: 1000
        description: Number of candles
    responses:
      200:
        description: Candlestick data
        schema:
          type: object
          properties:
            candles:
              type: array
              items:
                type: object
                properties:
                  timestamp:
                    type: string
                  open:
                    type: string
                  high:
                    type: string
                  low:
                    type: string
                  close:
                    type: string
                  volume:
                    type: string
      400:
        description: Invalid timeframe
      404:
        description: Trading pair not found
    """
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
@limiter.exempt
def get_depth(symbol):
    """
    Get Market Depth (Aggregated Order Book)
    ---
    tags:
      - Market
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol
        example: BTC/USDT
      - name: limit
        in: query
        type: integer
        default: 20
        description: Number of depth levels
    responses:
      200:
        description: Market depth data
        schema:
          type: object
          properties:
            bids:
              type: array
              items:
                type: array
                items:
                  type: string
                description: [price, amount]
              example: [["50000.00", "1.5"]]
            asks:
              type: array
              items:
                type: array
                items:
                  type: string
      404:
        description: Trading pair not found
    """
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
@limiter.exempt
def get_market_stats():
    """
    Get Overall Market Statistics
    ---
    tags:
      - Market
    responses:
      200:
        description: Market-wide statistics
        schema:
          type: object
          properties:
            total_pairs:
              type: integer
              example: 50
            total_volume_24h:
              type: string
              example: "1000000.00"
            total_trades_24h:
              type: integer
              example: 5000
    """
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


@api_v1_bp.route('/market/klines/<symbol>', methods=['GET'])
@limiter.exempt
def get_klines(symbol):
    """
    Get Candlestick/Kline Data for Chart
    ---
    tags:
      - Market
    parameters:
      - name: symbol
        in: path
        required: true
        type: string
        description: Trading pair symbol (use BTC_USDT format)
        example: BTC_USDT
      - name: interval
        in: query
        type: string
        default: "1h"
        enum: ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        description: Kline interval
      - name: limit
        in: query
        type: integer
        default: 100
        maximum: 1000
        description: Number of klines
    responses:
      200:
        description: Kline/candlestick data
        schema:
          type: object
          properties:
            candles:
              type: array
              items:
                type: object
                properties:
                  time:
                    type: integer
                    description: Unix timestamp
                  open:
                    type: number
                  high:
                    type: number
                  low:
                    type: number
                  close:
                    type: number
                  volume:
                    type: number
      404:
        description: Trading pair not found
    """
    from decimal import Decimal

    # Convert BTC_USDT to BTC/USDT for database query
    symbol_normalized = symbol.upper().replace('_', '/')
    pair = TradingPair.query.filter_by(symbol=symbol_normalized, is_active=True).first()
    if not pair:
        return jsonify({'error': 'Trading pair not found'}), 404

    # Get parameters
    interval = request.args.get('interval', '1h')  # 1m, 5m, 15m, 1h, 4h, 1d
    limit = min(int(request.args.get('limit', 100)), 1000)

    # For now, generate candles from trades
    # In production, you'd store pre-aggregated candles
    interval_minutes = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }.get(interval, 60)

    start_time = datetime.utcnow() - timedelta(minutes=interval_minutes * limit)
    trades = Trade.query.filter(
        Trade.trading_pair_id == pair.id,
        Trade.created_at >= start_time
    ).order_by(Trade.created_at.asc()).all()

    # Aggregate trades into candles
    candles = []
    if trades:
        current_candle_start = trades[0].created_at.replace(second=0, microsecond=0)
        current_candle = {
            'time': int(current_candle_start.timestamp()),
            'open': float(trades[0].price),
            'high': float(trades[0].price),
            'low': float(trades[0].price),
            'close': float(trades[0].price),
            'volume': 0
        }

        for trade in trades:
            trade_time = trade.created_at.replace(second=0, microsecond=0)

            # Check if we need to start a new candle
            time_diff = (trade_time - current_candle_start).total_seconds() / 60
            if time_diff >= interval_minutes:
                candles.append(current_candle)
                current_candle_start = trade_time
                current_candle = {
                    'time': int(current_candle_start.timestamp()),
                    'open': float(trade.price),
                    'high': float(trade.price),
                    'low': float(trade.price),
                    'close': float(trade.price),
                    'volume': 0
                }

            # Update current candle
            price = float(trade.price)
            current_candle['high'] = max(current_candle['high'], price)
            current_candle['low'] = min(current_candle['low'], price)
            current_candle['close'] = price
            current_candle['volume'] += float(trade.amount)

        # Add the last candle
        if current_candle:
            candles.append(current_candle)
    else:
        # No trades yet, generate a single candle with last_price
        current_time = datetime.utcnow()
        price = float(pair.last_price) if pair.last_price else 0
        candles = [{
            'time': int(current_time.timestamp()),
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0
        }]

    return jsonify({'candles': candles}), 200
