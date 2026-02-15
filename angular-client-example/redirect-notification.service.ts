import { Injectable, NgZone } from '@angular/core';
import { Observable, Subject, BehaviorSubject } from 'rxjs';

export interface RedirectStatusUpdate {
  key: string;
  value: string;
  timestamp: string;
  event_type: 'insert' | 'modify';
}

export interface SSEEvent {
  type: string;
  data: any;
  id: string;
  timestamp: string;
}

@Injectable({
  providedIn: 'root'
})
export class RedirectNotificationService {
  private eventSource: EventSource | null = null;
  private connectionStatus = new BehaviorSubject<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  private redirectUpdates = new Subject<RedirectStatusUpdate>();
  private allEvents = new Subject<SSEEvent>();
  
  // Replace with your actual API Gateway URL from Terraform output
  private readonly SSE_ENDPOINT = 'https://YOUR_API_GATEWAY_ID.execute-api.YOUR_REGION.amazonaws.com/prod/events';
  
  constructor(private ngZone: NgZone) {}

  /**
   * Connect to the SSE endpoint
   */
  connect(clientId?: string): void {
    if (this.eventSource) {
      this.disconnect();
    }

    this.connectionStatus.next('connecting');
    
    const url = clientId 
      ? `${this.SSE_ENDPOINT}?client_id=${encodeURIComponent(clientId)}`
      : this.SSE_ENDPOINT;

    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      this.ngZone.run(() => {
        console.log('SSE connection opened');
        this.connectionStatus.next('connected');
      });
    };

    this.eventSource.onerror = (error) => {
      this.ngZone.run(() => {
        console.error('SSE connection error:', error);
        this.connectionStatus.next('error');
      });
    };

    // Listen for connection events
    this.eventSource.addEventListener('connection', (event: MessageEvent) => {
      this.ngZone.run(() => {
        const data = JSON.parse(event.data);
        console.log('Connected to SSE:', data);
      });
    });

    // Listen for redirect status updates
    this.eventSource.addEventListener('redirect_status_update', (event: MessageEvent) => {
      this.ngZone.run(() => {
        try {
          const data: RedirectStatusUpdate = JSON.parse(event.data);
          console.log('Redirect status update:', data);
          this.redirectUpdates.next(data);
          
          // Also emit as general event
          this.allEvents.next({
            type: 'redirect_status_update',
            data: data,
            id: event.lastEventId || '',
            timestamp: new Date().toISOString()
          });
        } catch (error) {
          console.error('Error parsing redirect status update:', error);
        }
      });
    });

    // Listen for keepalive events
    this.eventSource.addEventListener('keepalive', (event: MessageEvent) => {
      this.ngZone.run(() => {
        console.log('SSE keepalive received');
      });
    });

    // Listen for generic messages
    this.eventSource.onmessage = (event: MessageEvent) => {
      this.ngZone.run(() => {
        try {
          const data = JSON.parse(event.data);
          this.allEvents.next({
            type: 'message',
            data: data,
            id: event.lastEventId || '',
            timestamp: new Date().toISOString()
          });
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      });
    };
  }

  /**
   * Disconnect from the SSE endpoint
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.connectionStatus.next('disconnected');
      console.log('SSE connection closed');
    }
  }

  /**
   * Get connection status observable
   */
  getConnectionStatus(): Observable<'disconnected' | 'connecting' | 'connected' | 'error'> {
    return this.connectionStatus.asObservable();
  }

  /**
   * Get redirect status updates observable
   */
  getRedirectUpdates(): Observable<RedirectStatusUpdate> {
    return this.redirectUpdates.asObservable();
  }

  /**
   * Get all SSE events observable
   */
  getAllEvents(): Observable<SSEEvent> {
    return this.allEvents.asObservable();
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.connectionStatus.value === 'connected';
  }

  /**
   * Get current connection status
   */
  getCurrentStatus(): 'disconnected' | 'connecting' | 'connected' | 'error' {
    return this.connectionStatus.value;
  }

  /**
   * Reconnect with exponential backoff
   */
  reconnect(maxAttempts: number = 5, baseDelay: number = 1000): void {
    let attempts = 0;
    
    const attemptReconnect = () => {
      if (attempts >= maxAttempts) {
        console.error('Max reconnection attempts reached');
        return;
      }
      
      attempts++;
      const delay = baseDelay * Math.pow(2, attempts - 1);
      
      console.log(`Reconnection attempt ${attempts}/${maxAttempts} in ${delay}ms`);
      
      setTimeout(() => {
        if (this.connectionStatus.value !== 'connected') {
          this.connect();
          
          // Check if connection was successful after a short delay
          setTimeout(() => {
            if (this.connectionStatus.value !== 'connected') {
              attemptReconnect();
            }
          }, 2000);
        }
      }, delay);
    };
    
    attemptReconnect();
  }
}