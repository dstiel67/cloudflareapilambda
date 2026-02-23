/**
 * Failover Service - Angular Integration with Atom Store
 * 
 * This service connects to the Atom Store WebSocket server and provides
 * reactive failover status updates via RxJS Observables.
 */

import { Injectable, NgZone, OnDestroy } from '@angular/core';
import { Observable, BehaviorSubject } from 'rxjs';
import { HttpClient } from '@angular/common/http';

export interface FailoverStatus {
  appId: string;
  failoverActive: boolean;
  lastUpdated: string;
  reason: string;
  updatedBy: string;
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

@Injectable({
  providedIn: 'root'
})
export class FailoverService implements OnDestroy {
  private ws: WebSocket | null = null;
  private failoverStatus = new BehaviorSubject<Map<string, FailoverStatus>>(new Map());
  private connectionStatus = new BehaviorSubject<ConnectionStatus>('disconnected');
  private atomStoreUrl: string = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private reconnectTimer: any = null;

  constructor(
    private ngZone: NgZone,
    private http: HttpClient
  ) {}

  /**
   * Connect to Atom Store WebSocket server
   */
  connect(atomStoreUrl: string): void {
    this.atomStoreUrl = atomStoreUrl;
    this.connectionStatus.next('connecting');

    // Close existing connection if any
    if (this.ws) {
      this.ws.close();
    }

    try {
      this.ws = new WebSocket(atomStoreUrl);

      this.ws.onopen = () => {
        this.ngZone.run(() => {
          console.log('✅ Connected to Atom Store');
          this.connectionStatus.next('connected');
          this.reconnectAttempts = 0;
          this.fetchCurrentStatus();
        });
      };

      this.ws.onmessage = (event) => {
        this.ngZone.run(() => {
          try {
            const data = JSON.parse(event.data);
            console.log('📨 Received update from Atom Store:', data);
            this.updateFailoverStatus(data);
          } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error);
          }
        });
      };

      this.ws.onerror = (error) => {
        this.ngZone.run(() => {
          console.error('❌ WebSocket error:', error);
          this.connectionStatus.next('error');
        });
      };

      this.ws.onclose = () => {
        this.ngZone.run(() => {
          console.log('🔌 Disconnected from Atom Store');
          this.connectionStatus.next('disconnected');
          this.attemptReconnect();
        });
      };
    } catch (error) {
      console.error('❌ Failed to create WebSocket connection:', error);
      this.connectionStatus.next('error');
      this.attemptReconnect();
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`🔄 Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      if (this.atomStoreUrl) {
        this.connect(this.atomStoreUrl);
      }
    }, delay);
  }

  /**
   * Fetch current status from Atom Store REST API
   */
  private async fetchCurrentStatus(): Promise<void> {
    try {
      const httpUrl = this.atomStoreUrl
        .replace('ws://', 'http://')
        .replace('wss://', 'https://');

      const data = await this.http.get<any>(`${httpUrl}/api/failover/status`).toPromise();
      
      const statusMap = new Map<string, FailoverStatus>();
      Object.entries(data).forEach(([appId, status]) => {
        statusMap.set(appId, status as FailoverStatus);
      });
      
      this.failoverStatus.next(statusMap);
      console.log('✅ Fetched current status:', statusMap.size, 'apps');
    } catch (error) {
      console.error('❌ Failed to fetch current status:', error);
    }
  }

  /**
   * Update failover status from WebSocket message
   */
  private updateFailoverStatus(data: any): void {
    const currentMap = new Map(this.failoverStatus.value);
    
    Object.entries(data).forEach(([appId, status]) => {
      currentMap.set(appId, status as FailoverStatus);
      console.log(`📊 Updated status for ${appId}:`, status);
    });
    
    this.failoverStatus.next(currentMap);
  }

  /**
   * Get failover status for a specific app
   */
  getFailoverStatus(appId: string): Observable<FailoverStatus | undefined> {
    return new Observable(observer => {
      const subscription = this.failoverStatus.subscribe(statusMap => {
        observer.next(statusMap.get(appId));
      });
      return () => subscription.unsubscribe();
    });
  }

  /**
   * Get all failover statuses
   */
  getAllFailoverStatuses(): Observable<Map<string, FailoverStatus>> {
    return this.failoverStatus.asObservable();
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): Observable<ConnectionStatus> {
    return this.connectionStatus.asObservable();
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connectionStatus.value === 'connected';
  }

  /**
   * Disconnect from Atom Store
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.connectionStatus.next('disconnected');
    console.log('🔌 Manually disconnected from Atom Store');
  }

  /**
   * Cleanup on service destroy
   */
  ngOnDestroy(): void {
    this.disconnect();
  }
}
