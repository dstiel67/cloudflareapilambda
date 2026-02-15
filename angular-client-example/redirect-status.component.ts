import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { RedirectNotificationService, RedirectStatusUpdate } from './redirect-notification.service';
import { RedirectUpdateService } from './redirect-update.service';

@Component({
  selector: 'app-redirect-status',
  template: `
    <div class="redirect-status-container">
      <div class="connection-status" [ngClass]="connectionStatusClass">
        <span class="status-indicator"></span>
        <span class="status-text">{{ connectionStatusText }}</span>
        <button 
          *ngIf="connectionStatus === 'disconnected' || connectionStatus === 'error'"
          (click)="connect()"
          class="connect-btn">
          Connect
        </button>
        <button 
          *ngIf="connectionStatus === 'connected'"
          (click)="disconnect()"
          class="disconnect-btn">
          Disconnect
        </button>
      </div>

      <div class="current-status" *ngIf="currentRedirectStatus">
        <h3>Current Redirect Status</h3>
        <div class="status-card" [ngClass]="redirectStatusClass">
          <div class="status-value">{{ currentRedirectStatus.value }}</div>
          <div class="status-details">
            <div>Key: {{ currentRedirectStatus.key }}</div>
            <div>Updated: {{ currentRedirectStatus.timestamp | date:'medium' }}</div>
            <div>Type: {{ currentRedirectStatus.event_type }}</div>
          </div>
          
          <!-- Update Controls -->
          <div class="update-controls">
            <button 
              (click)="updateStatus('ON')"
              [disabled]="isUpdating || currentRedirectStatus.value === 'ON'"
              class="update-btn on-btn">
              Turn ON
            </button>
            <button 
              (click)="updateStatus('OFF')"
              [disabled]="isUpdating || currentRedirectStatus.value === 'OFF'"
              class="update-btn off-btn">
              Turn OFF
            </button>
            <button 
              (click)="toggleStatus()"
              [disabled]="isUpdating"
              class="update-btn toggle-btn">
              Toggle
            </button>
          </div>
          
          <div *ngIf="isUpdating" class="updating-indicator">
            Updating...
          </div>
          
          <div *ngIf="updateError" class="error-message">
            {{ updateError }}
          </div>
        </div>
      </div>

      <div class="recent-updates" *ngIf="recentUpdates.length > 0">
        <h3>Recent Updates</h3>
        <div class="updates-list">
          <div 
            *ngFor="let update of recentUpdates; trackBy: trackByTimestamp"
            class="update-item"
            [ngClass]="getUpdateClass(update)">
            <div class="update-header">
              <span class="update-value">{{ update.value }}</span>
              <span class="update-time">{{ update.timestamp | date:'short' }}</span>
            </div>
            <div class="update-details">
              <span>{{ update.event_type | titlecase }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="debug-info" *ngIf="showDebugInfo">
        <h4>Debug Information</h4>
        <div class="debug-content">
          <div>Connection Status: {{ connectionStatus }}</div>
          <div>Total Updates Received: {{ totalUpdatesReceived }}</div>
          <div>Last Event ID: {{ lastEventId }}</div>
          <div>Client ID: {{ clientId }}</div>
        </div>
      </div>

      <div class="controls">
        <button (click)="toggleDebugInfo()" class="debug-toggle">
          {{ showDebugInfo ? 'Hide' : 'Show' }} Debug Info
        </button>
        <button (click)="clearHistory()" class="clear-btn">
          Clear History
        </button>
        <button (click)="refreshStatus()" class="refresh-btn">
          Refresh Status
        </button>
      </div>
    </div>
  `,
  styles: [`
    .redirect-status-container {
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
      font-family: Arial, sans-serif;
    }

    .connection-status {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 20px;
    }

    .connection-status.connected {
      background-color: #d4edda;
      border: 1px solid #c3e6cb;
      color: #155724;
    }

    .connection-status.connecting {
      background-color: #fff3cd;
      border: 1px solid #ffeaa7;
      color: #856404;
    }

    .connection-status.disconnected {
      background-color: #f8d7da;
      border: 1px solid #f5c6cb;
      color: #721c24;
    }

    .connection-status.error {
      background-color: #f8d7da;
      border: 1px solid #f5c6cb;
      color: #721c24;
    }

    .status-indicator {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }

    .connected .status-indicator {
      background-color: #28a745;
    }

    .connecting .status-indicator {
      background-color: #ffc107;
      animation: pulse 1.5s infinite;
    }

    .disconnected .status-indicator,
    .error .status-indicator {
      background-color: #dc3545;
    }

    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.5; }
      100% { opacity: 1; }
    }

    .current-status {
      margin-bottom: 30px;
    }

    .status-card {
      padding: 20px;
      border-radius: 8px;
      border: 2px solid #ddd;
    }

    .status-card.redirect-on {
      background-color: #fff3cd;
      border-color: #ffc107;
    }

    .status-card.redirect-off {
      background-color: #d4edda;
      border-color: #28a745;
    }

    .status-value {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 10px;
    }

    .status-details {
      font-size: 14px;
      color: #666;
    }

    .status-details > div {
      margin-bottom: 5px;
    }

    .update-controls {
      margin-top: 15px;
      padding-top: 15px;
      border-top: 1px solid #ddd;
      display: flex;
      gap: 10px;
    }

    .update-btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .update-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .on-btn {
      background-color: #ffc107;
      color: #000;
    }

    .on-btn:hover:not(:disabled) {
      background-color: #ffb300;
    }

    .off-btn {
      background-color: #28a745;
      color: white;
    }

    .off-btn:hover:not(:disabled) {
      background-color: #218838;
    }

    .toggle-btn {
      background-color: #007bff;
      color: white;
    }

    .toggle-btn:hover:not(:disabled) {
      background-color: #0056b3;
    }

    .updating-indicator {
      margin-top: 10px;
      padding: 8px;
      background-color: #e3f2fd;
      border-radius: 4px;
      color: #1976d2;
      font-size: 14px;
      text-align: center;
    }

    .error-message {
      margin-top: 10px;
      padding: 8px;
      background-color: #ffebee;
      border-radius: 4px;
      color: #c62828;
      font-size: 14px;
    }

    .refresh-btn {
      background-color: #17a2b8;
      color: white;
    }

    .refresh-btn:hover {
      background-color: #138496;
    }

    .updates-list {
      max-height: 400px;
      overflow-y: auto;
    }

    .update-item {
      padding: 12px;
      border: 1px solid #ddd;
      border-radius: 6px;
      margin-bottom: 10px;
      background-color: #f8f9fa;
    }

    .update-item.new-update {
      animation: highlight 2s ease-out;
    }

    @keyframes highlight {
      0% { background-color: #cce5ff; }
      100% { background-color: #f8f9fa; }
    }

    .update-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 5px;
    }

    .update-value {
      font-weight: bold;
      font-size: 16px;
    }

    .update-time {
      font-size: 12px;
      color: #666;
    }

    .update-details {
      font-size: 12px;
      color: #888;
    }

    .debug-info {
      margin-top: 30px;
      padding: 15px;
      background-color: #f1f3f4;
      border-radius: 6px;
      font-family: monospace;
      font-size: 12px;
    }

    .debug-content > div {
      margin-bottom: 5px;
    }

    .controls {
      margin-top: 20px;
      display: flex;
      gap: 10px;
    }

    button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }

    .connect-btn {
      background-color: #28a745;
      color: white;
    }

    .disconnect-btn {
      background-color: #dc3545;
      color: white;
    }

    .debug-toggle, .clear-btn {
      background-color: #6c757d;
      color: white;
    }

    button:hover {
      opacity: 0.8;
    }

    h3, h4 {
      color: #333;
      margin-bottom: 15px;
    }
  `]
})
export class RedirectStatusComponent implements OnInit, OnDestroy {
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error' = 'disconnected';
  currentRedirectStatus: RedirectStatusUpdate | null = null;
  recentUpdates: RedirectStatusUpdate[] = [];
  showDebugInfo = false;
  totalUpdatesReceived = 0;
  lastEventId = '';
  clientId = `angular-client-${Date.now()}`;

  private subscriptions: Subscription[] = [];
  isUpdating = false;
  updateError: string | null = null;

  constructor(
    private redirectService: RedirectNotificationService,
    private updateService: RedirectUpdateService
  ) {}

  ngOnInit(): void {
    // Subscribe to connection status
    this.subscriptions.push(
      this.redirectService.getConnectionStatus().subscribe(status => {
        this.connectionStatus = status;
      })
    );

    // Subscribe to redirect updates
    this.subscriptions.push(
      this.redirectService.getRedirectUpdates().subscribe(update => {
        this.handleRedirectUpdate(update);
      })
    );

    // Subscribe to all events for debugging
    this.subscriptions.push(
      this.redirectService.getAllEvents().subscribe(event => {
        this.lastEventId = event.id;
        if (event.type === 'redirect_status_update') {
          this.totalUpdatesReceived++;
        }
      })
    );

    // Auto-connect on component initialization
    this.connect();
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.redirectService.disconnect();
  }

  connect(): void {
    this.redirectService.connect(this.clientId);
  }

  disconnect(): void {
    this.redirectService.disconnect();
  }

  private handleRedirectUpdate(update: RedirectStatusUpdate): void {
    // Update current status
    this.currentRedirectStatus = update;

    // Add to recent updates (keep last 10)
    this.recentUpdates.unshift({
      ...update,
      // Add a flag for animation
      isNew: true
    } as any);

    if (this.recentUpdates.length > 10) {
      this.recentUpdates = this.recentUpdates.slice(0, 10);
    }

    // Remove the new flag after animation
    setTimeout(() => {
      this.recentUpdates.forEach(u => (u as any).isNew = false);
    }, 2000);

    // You can add custom logic here based on the redirect status
    if (update.value === 'ON') {
      console.log('🔄 Redirect is now ON - users will be redirected to essentials');
      // Maybe show a notification, update UI, etc.
    } else if (update.value === 'OFF') {
      console.log('✅ Redirect is now OFF - normal operation');
    }
  }

  get connectionStatusText(): string {
    switch (this.connectionStatus) {
      case 'connected': return 'Connected to notifications';
      case 'connecting': return 'Connecting...';
      case 'disconnected': return 'Disconnected';
      case 'error': return 'Connection error';
      default: return 'Unknown';
    }
  }

  get connectionStatusClass(): string {
    return this.connectionStatus;
  }

  get redirectStatusClass(): string {
    if (!this.currentRedirectStatus) return '';
    return this.currentRedirectStatus.value === 'ON' ? 'redirect-on' : 'redirect-off';
  }

  getUpdateClass(update: RedirectStatusUpdate): string {
    return (update as any).isNew ? 'new-update' : '';
  }

  trackByTimestamp(index: number, update: RedirectStatusUpdate): string {
    return update.timestamp;
  }

  toggleDebugInfo(): void {
    this.showDebugInfo = !this.showDebugInfo;
  }

  clearHistory(): void {
    this.recentUpdates = [];
    this.totalUpdatesReceived = 0;
  }

  updateStatus(value: 'ON' | 'OFF'): void {
    this.isUpdating = true;
    this.updateError = null;

    this.updateService.updateRedirectStatus({ value }).subscribe({
      next: (response) => {
        console.log('Status updated successfully:', response);
        this.isUpdating = false;
        // The SSE connection will automatically receive the update
      },
      error: (error) => {
        console.error('Failed to update status:', error);
        this.updateError = error.error?.message || 'Failed to update status';
        this.isUpdating = false;
      }
    });
  }

  toggleStatus(): void {
    if (!this.currentRedirectStatus) {
      this.updateError = 'No current status available';
      return;
    }

    this.isUpdating = true;
    this.updateError = null;

    this.updateService.toggleRedirectStatus(
      this.currentRedirectStatus.value as 'ON' | 'OFF'
    ).subscribe({
      next: (response) => {
        console.log('Status toggled successfully:', response);
        this.isUpdating = false;
      },
      error: (error) => {
        console.error('Failed to toggle status:', error);
        this.updateError = error.error?.message || 'Failed to toggle status';
        this.isUpdating = false;
      }
    });
  }

  refreshStatus(): void {
    this.updateService.getCurrentRedirectStatus().subscribe({
      next: (response) => {
        console.log('Current status:', response);
        if (response.data) {
          // Update the current status display
          this.currentRedirectStatus = {
            key: response.data.key,
            value: response.data.value,
            timestamp: response.data.timestamp,
            event_type: 'refresh'
          };
        }
      },
      error: (error) => {
        console.error('Failed to refresh status:', error);
        this.updateError = error.error?.message || 'Failed to refresh status';
      }
    });
  }
}