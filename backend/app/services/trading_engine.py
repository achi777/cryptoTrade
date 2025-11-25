"""
Trading Engine - Order matching and execution.

Implements FIFO (First-In-First-Out) price-time priority matching.
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from flask import current_app

from app import db, socketio
from app.models.trading import (
    TradingPair, Order, OrderType, OrderSide, OrderStatus, Trade
)
from app.models.balance import Balance, Transaction, TransactionType
from app.models.admin import FeeConfig


class MatchingEngine:
    """Order matching engine for a trading pair"""

    def __init__(self, trading_pair: TradingPair):
        self.pair = trading_pair

    def match_order(self, order: Order) -> List[Trade]:
        """
        Match an incoming order against the order book.
        Returns list of executed trades.
        """
        trades = []

        if order.order_type == OrderType.MARKET.value:
            trades = self._match_market_order(order)
        elif order.order_type == OrderType.LIMIT.value:
            trades = self._match_limit_order(order)
        elif order.order_type == OrderType.STOP_LIMIT.value:
            # Stop orders are activated when price reaches stop_price
            # Then they become limit orders
            if self._check_stop_triggered(order):
                order.order_type = OrderType.LIMIT.value
                trades = self._match_limit_order(order)

        return trades

    def _match_market_order(self, order: Order) -> List[Trade]:
        """Match market order - executes at best available price"""
        trades = []

        if order.side == OrderSide.BUY.value:
            # Match against sell orders (asks), lowest price first
            counter_orders = Order.query.filter(
                Order.trading_pair_id == self.pair.id,
                Order.side == OrderSide.SELL.value,
                Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
                Order.price.isnot(None)
            ).order_by(Order.price.asc(), Order.created_at.asc()).all()
        else:
            # Match against buy orders (bids), highest price first
            counter_orders = Order.query.filter(
                Order.trading_pair_id == self.pair.id,
                Order.side == OrderSide.BUY.value,
                Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
                Order.price.isnot(None)
            ).order_by(Order.price.desc(), Order.created_at.asc()).all()

        for counter_order in counter_orders:
            if order.remaining_amount <= 0:
                break

            trade = self._execute_trade(order, counter_order, counter_order.price)
            if trade:
                trades.append(trade)

        self._finalize_order(order)
        return trades

    def _match_limit_order(self, order: Order) -> List[Trade]:
        """Match limit order - executes at specified price or better"""
        trades = []
        current_app.logger.info(f"=== MATCHING LIMIT ORDER ===")
        current_app.logger.info(f"Order #{order.id}, Side={order.side}, Price={order.price}, Amount={order.amount}, Remaining={order.remaining_amount}")

        if order.side == OrderSide.BUY.value:
            # Match against sell orders at or below limit price
            counter_orders = Order.query.filter(
                Order.trading_pair_id == self.pair.id,
                Order.side == OrderSide.SELL.value,
                Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
                Order.price <= order.price,
                Order.price.isnot(None)
            ).order_by(Order.price.asc(), Order.created_at.asc()).all()
        else:
            # Match against buy orders at or above limit price
            counter_orders = Order.query.filter(
                Order.trading_pair_id == self.pair.id,
                Order.side == OrderSide.BUY.value,
                Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
                Order.price >= order.price,
                Order.price.isnot(None)
            ).order_by(Order.price.desc(), Order.created_at.asc()).all()

        current_app.logger.info(f"Found {len(counter_orders)} counter orders")
        for i, counter_order in enumerate(counter_orders):
            current_app.logger.info(f"Counter order {i+1}: #{counter_order.id}, Price={counter_order.price}, Remaining={counter_order.remaining_amount}, User={counter_order.user_id}")

            if order.remaining_amount <= 0:
                current_app.logger.info(f"Order fully filled, breaking")
                break

            # Execute at the maker's (counter order's) price
            trade = self._execute_trade(order, counter_order, counter_order.price)
            if trade:
                current_app.logger.info(f"Trade created: #{trade.id}")
                trades.append(trade)
            else:
                current_app.logger.warning(f"Trade NOT created for counter order #{counter_order.id}")

        current_app.logger.info(f"Total trades created: {len(trades)}")
        self._finalize_order(order)
        return trades

    def _execute_trade(self, taker_order: Order, maker_order: Order, price: Decimal) -> Optional[Trade]:
        """Execute a trade between two orders"""
        current_app.logger.info(f"=== EXECUTE TRADE DEBUG ===")
        current_app.logger.info(f"Taker: Order #{taker_order.id}, Side={taker_order.side}, Remaining={taker_order.remaining_amount}")
        current_app.logger.info(f"Maker: Order #{maker_order.id}, Side={maker_order.side}, Remaining={maker_order.remaining_amount}")
        current_app.logger.info(f"Price: {price}")

        # Determine trade amount
        trade_amount = min(taker_order.remaining_amount, maker_order.remaining_amount)
        current_app.logger.info(f"Trade amount: {trade_amount}")

        if trade_amount <= 0:
            current_app.logger.warning(f"Trade amount <= 0, returning None")
            return None

        trade_total = trade_amount * price
        current_app.logger.info(f"Trade total: {trade_total}")

        # Calculate fees
        maker_fee_rate = self._get_fee_rate('maker')
        taker_fee_rate = self._get_fee_rate('taker')

        # Determine buyer/seller
        if taker_order.side == OrderSide.BUY.value:
            buyer_id = taker_order.user_id
            seller_id = maker_order.user_id
            buyer_fee = trade_total * taker_fee_rate
            seller_fee = trade_amount * maker_fee_rate
        else:
            buyer_id = maker_order.user_id
            seller_id = taker_order.user_id
            buyer_fee = trade_total * maker_fee_rate
            seller_fee = trade_amount * taker_fee_rate

        # Create trade record
        trade = Trade(
            trading_pair_id=self.pair.id,
            order_id=taker_order.id,
            counter_order_id=maker_order.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            price=price,
            amount=trade_amount,
            total=trade_total,
            buyer_fee=buyer_fee,
            seller_fee=seller_fee,
            maker_order_id=maker_order.id,
            taker_order_id=taker_order.id
        )
        db.session.add(trade)

        # Update orders
        taker_order.filled_amount += trade_amount
        taker_order.remaining_amount -= trade_amount
        taker_order.fee += buyer_fee if taker_order.side == OrderSide.BUY.value else seller_fee

        maker_order.filled_amount += trade_amount
        maker_order.remaining_amount -= trade_amount
        maker_order.fee += seller_fee if taker_order.side == OrderSide.BUY.value else buyer_fee

        # Update average fill prices
        self._update_avg_fill_price(taker_order, trade_amount, price)
        self._update_avg_fill_price(maker_order, trade_amount, price)

        # Update balances
        try:
            current_app.logger.info(f"Updating balances - Buyer: {buyer_id}, Seller: {seller_id}")
            self._update_balances(trade, buyer_id, seller_id, buyer_fee, seller_fee)
            current_app.logger.info(f"Balances updated successfully")
        except Exception as e:
            current_app.logger.error(f"Balance update failed: {e}")
            raise

        # Finalize both orders
        self._finalize_order(maker_order)
        self._finalize_order(taker_order)
        current_app.logger.info(f"Orders finalized - Maker: {maker_order.status}, Taker: {taker_order.status}")

        # Update market data
        self._update_market_data(price, trade_amount)

        db.session.commit()
        current_app.logger.info(f"Trade #{trade.id} committed successfully")

        return trade

    def _update_balances(self, trade: Trade, buyer_id: int, seller_id: int,
                         buyer_fee: Decimal, seller_fee: Decimal):
        """Update user balances after trade execution"""
        base_currency_id = self.pair.base_currency_id
        quote_currency_id = self.pair.quote_currency_id

        # Buyer: receives base currency, pays quote currency
        buyer_base_balance = Balance.query.filter_by(
            user_id=buyer_id, currency_id=base_currency_id
        ).first()
        buyer_quote_balance = Balance.query.filter_by(
            user_id=buyer_id, currency_id=quote_currency_id
        ).first()

        # Seller: receives quote currency, pays base currency
        seller_base_balance = Balance.query.filter_by(
            user_id=seller_id, currency_id=base_currency_id
        ).first()
        seller_quote_balance = Balance.query.filter_by(
            user_id=seller_id, currency_id=quote_currency_id
        ).first()

        # Credit buyer with base currency (minus fee if fee is in base)
        received_base = trade.amount - (buyer_fee if self._fee_in_base_currency() else Decimal('0'))
        buyer_base_balance.available += received_base
        buyer_base_balance.update_total()

        # Debit buyer's locked quote currency
        unlock_amount = min(buyer_quote_balance.locked, trade.total)
        buyer_quote_balance.locked -= unlock_amount
        buyer_quote_balance.update_total()

        # Credit seller with quote currency (minus fee)
        received_quote = trade.total - (seller_fee if not self._fee_in_base_currency() else Decimal('0'))
        seller_quote_balance.available += received_quote
        seller_quote_balance.update_total()

        # Debit seller's locked base currency
        unlock_base_amount = min(seller_base_balance.locked, trade.amount)
        seller_base_balance.locked -= unlock_base_amount
        seller_base_balance.update_total()

    def _update_avg_fill_price(self, order: Order, trade_amount: Decimal, price: Decimal):
        """Update order's average fill price"""
        if order.avg_fill_price == 0:
            order.avg_fill_price = price
        else:
            total_filled = order.filled_amount
            prev_filled = total_filled - trade_amount
            order.avg_fill_price = (
                (order.avg_fill_price * prev_filled + price * trade_amount) / total_filled
            )

    def _finalize_order(self, order: Order):
        """Update order status based on fill amount"""
        if order.remaining_amount <= 0:
            order.status = OrderStatus.FILLED.value
            order.filled_at = datetime.utcnow()
        elif order.filled_amount > 0:
            order.status = OrderStatus.PARTIALLY_FILLED.value

    def _get_fee_rate(self, fee_type: str) -> Decimal:
        """Get fee rate (maker/taker)"""
        # Check pair-specific fee
        if fee_type == 'maker' and self.pair.maker_fee:
            return self.pair.maker_fee / Decimal('100')
        if fee_type == 'taker' and self.pair.taker_fee:
            return self.pair.taker_fee / Decimal('100')

        # Use global fee
        fee_config = FeeConfig.query.filter_by(
            fee_type=fee_type,
            trading_pair_id=None,
            is_active=True
        ).first()

        if fee_config:
            return fee_config.value / Decimal('100')

        # Default fees
        return Decimal('0.001') if fee_type == 'maker' else Decimal('0.002')

    def _fee_in_base_currency(self) -> bool:
        """Determine if fee is charged in base currency"""
        # Typically fee is charged in the received currency
        return False

    def _check_stop_triggered(self, order: Order) -> bool:
        """Check if stop price has been triggered"""
        if not order.stop_price:
            return False

        if order.side == OrderSide.BUY.value:
            return self.pair.last_price >= order.stop_price
        else:
            return self.pair.last_price <= order.stop_price

    def _update_market_data(self, price: Decimal, amount: Decimal):
        """Update trading pair market data"""
        self.pair.last_price = price
        self.pair.volume_24h += amount

        if price > self.pair.high_24h or self.pair.high_24h == 0:
            self.pair.high_24h = price
        if price < self.pair.low_24h or self.pair.low_24h == 0:
            self.pair.low_24h = price

        # Emit WebSocket update
        try:
            socketio.emit('ticker', {
                'symbol': self.pair.symbol,
                'price': str(price),
                'volume_24h': str(self.pair.volume_24h)
            }, room=f'market_{self.pair.symbol}')
        except Exception as e:
            current_app.logger.error(f"WebSocket emit failed: {e}")


def process_pending_orders():
    """Process pending orders (called periodically)"""
    # Check for expired orders
    expired = Order.query.filter(
        Order.status.in_([OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]),
        Order.expires_at.isnot(None),
        Order.expires_at < datetime.utcnow()
    ).all()

    for order in expired:
        order.status = OrderStatus.EXPIRED.value
        # Unlock remaining funds...

    db.session.commit()
