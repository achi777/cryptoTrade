import { io, Socket } from 'socket.io-client';
import { store } from '../store';
import { updateTicker, updateOrderBook, addRecentTrade } from '../store/slices/marketSlice';
import { updateOrder } from '../store/slices/tradingSlice';
import { updateBalance } from '../store/slices/walletSlice';

const WS_URL = process.env.REACT_APP_WS_URL || 'http://localhost:5000';

class WebSocketService {
  private socket: Socket | null = null;
  private subscribedChannels: Set<string> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(): void {
    if (this.socket?.connected) return;

    this.socket = io(WS_URL, {
      transports: ['websocket'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
    });

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.authenticate();
      this.resubscribe();
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
    });

    // Market data events
    this.socket.on('ticker', (data) => {
      store.dispatch(updateTicker(data));
    });

    this.socket.on('orderbook', (data) => {
      store.dispatch(updateOrderBook(data));
    });

    this.socket.on('trade', (data) => {
      store.dispatch(addRecentTrade(data));
    });

    // User events
    this.socket.on('order_update', (data) => {
      store.dispatch(updateOrder(data));
    });

    this.socket.on('balance_update', (data) => {
      store.dispatch(updateBalance(data));
    });

    this.socket.on('notification', (data) => {
      // Handle notifications (could use react-hot-toast)
      console.log('Notification:', data);
    });
  }

  authenticate(): void {
    const token = localStorage.getItem('access_token');
    if (token && this.socket) {
      this.socket.emit('authenticate', { token });
    }
  }

  subscribe(channels: { type: string; symbol: string }[]): void {
    if (!this.socket) return;

    channels.forEach((channel) => {
      const key = `${channel.type}_${channel.symbol}`;
      this.subscribedChannels.add(key);
    });

    this.socket.emit('subscribe', { channels });
  }

  unsubscribe(channels: { type: string; symbol: string }[]): void {
    if (!this.socket) return;

    channels.forEach((channel) => {
      const key = `${channel.type}_${channel.symbol}`;
      this.subscribedChannels.delete(key);
    });

    this.socket.emit('unsubscribe', { channels });
  }

  private resubscribe(): void {
    if (!this.socket || this.subscribedChannels.size === 0) return;

    const channels = Array.from(this.subscribedChannels).map((key) => {
      const [type, symbol] = key.split('_');
      return { type, symbol };
    });

    this.socket.emit('subscribe', { channels });
  }

  subscribeToMarket(symbol: string): void {
    this.subscribe([
      { type: 'ticker', symbol },
      { type: 'orderbook', symbol },
      { type: 'trades', symbol },
    ]);
  }

  unsubscribeFromMarket(symbol: string): void {
    this.unsubscribe([
      { type: 'ticker', symbol },
      { type: 'orderbook', symbol },
      { type: 'trades', symbol },
    ]);
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.subscribedChannels.clear();
  }
}

export const wsService = new WebSocketService();
export default wsService;
