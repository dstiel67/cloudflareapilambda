/**
 * Example Application 1 - Failover Integration
 * 
 * This example shows how an Angular application subscribes to its failover status
 * and reacts to failover status changes.
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { FailoverService, FailoverStatus, ConnectionStatus } from './failover.service';

@Component({
  selector: 'app-app1',
  template: `
    <div class="app">
      <!-- Failover Banner -->
      <div *ngIf="failoverStatus?.failoverActive" class="failover-banner">
        <div class="banner-content">
          <span class="icon">⚠️</span>
          <span class="message">System is currently in failover mode</span>
          <span class="reason" *ngIf="failoverStatus.reason">
            - {{ failoverStatus.reason }}
          </span>
        </div>
        <div class="banner-details">
          Last updated: {{ failoverStatus.lastUpdated | date:'medium' }}
          <span *ngIf="connectionStatus === 'connected'"> • Connected</span>
          <span *ngIf="connectionStatus === 'error'"> • Connection Error</span>
        </div>
      </div>

      <!-- Header -->
      <header class="header">
        <h1>Application 1</h1>
        <div class="failover-indicator">
          <div class="status-dot" [class.failover]="failoverStatus?.failoverActive"></div>
          <span>{{ getStatusText() }}</span>
        </div>
      </header>

      <!-- Main Content -->
      <main class="main-content">
        <h2>Main Content</h2>
        <div *ngIf="failoverStatus?.failoverActive; else normalContent" class="failover-content">
          <p>Running in limited mode due to failover.</p>
          <p>Some features may be unavailable.</p>
        </div>
        <ng-template #normalContent>
          <div class="normal-content">
            <p>All systems operational.</p>
            <p>Full functionality available.</p>
          </div>
        </ng-template>

        <!-- Status Card -->
        <div class="status-card" *ngIf="failoverStatus">
          <h3>Current Status</h3>
          <div class="status-details">
            <div><strong>App ID:</strong> {{ failoverStatus.appId }}</div>
            <div><strong>Failover Active:</strong> {{ failoverStatus.failoverActive ? 'Yes' : 'No' }}</div>
            <div><strong>Last Updated:</strong> {{ failoverStatus.lastUpdated | date:'medium' }}</div>
            <div *ngIf="failoverStatus.reason"><strong>Reason:</strong> {{ failoverStatus.reason }}</div>
            <div *ngIf="failoverStatus.updatedBy"><strong>Updated By:</strong> {{ failoverStatus.updatedBy }}</div>
          </div>
        </div>

        <!-- Connection Status -->
        <div class="connection-status" [ngClass]="connectionStatus">
          <strong>Connection Status:</strong> {{ connectionStatus | titlecase }}
        </div>
      </main>

      <!-- Footer -->
      <footer class="footer">
        <p>Application 1 © 2024</p>
      </footer>
    </div>
  `,
  styles: [`
    .app {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    .failover-banner {
      background-color: #ff6b6b;
      color: white;
      padding: 16px;
      text-align: center;
      font-weight: bold;
    }

    .banner-content {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
    }

    .banner-details {
      font-size: 12px;
      margin-top: 8px;
      opacity: 0.9;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      background-color: #2c3e50;
      color: white;
    }

    .header h1 {
      margin: 0;
    }

    .failover-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background-color: #2ecc71;
      transition: background-color 0.3s;
    }

    .status-dot.failover {
      background-color: #e74c3c;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .main-content {
      flex: 1;
      padding: 24px;
    }

    .main-content h2 {
      color: #2c3e50;
      margin-bottom: 16px;
    }

    .failover-content,
    .normal-content {
      padding: 16px;
      border-radius: 8px;
      margin-bottom: 24px;
    }

    .failover-content {
      background-color: #fff3cd;
      border: 1px solid #ffc107;
      color: #856404;
    }

    .normal-content {
      background-color: #d4edda;
      border: 1px solid #c3e6cb;
      color: #155724;
    }

    .status-card {
      background-color: #f8f9fa;
      border: 1px solid #dee2e6;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }

    .status-card h3 {
      margin-top: 0;
      color: #495057;
    }

    .status-details > div {
      margin-bottom: 8px;
    }

    .connection-status {
      padding: 12px;
      border-radius: 4px;
      margin-top: 16px;
    }

    .connection-status.connected {
      background-color: #d4edda;
      color: #155724;
    }

    .connection-status.connecting {
      background-color: #fff3cd;
      color: #856404;
    }

    .connection-status.disconnected,
    .connection-status.error {
      background-color: #f8d7da;
      color: #721c24;
    }

    .footer {
      padding: 16px;
      background-color: #34495e;
      color: white;
      text-align: center;
    }

    .footer p {
      margin: 0;
    }
  `]
})
export class App1Component implements OnInit, OnDestroy {
  failoverStatus: FailoverStatus | undefined;
  connectionStatus: ConnectionStatus = 'disconnected';
  private subscriptions: Subscription[] = [];

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    // Subscribe to failover status for app1
    this.subscriptions.push(
      this.failoverService.getFailoverStatus('app1').subscribe(status => {
        this.failoverStatus = status;
        
        if (status?.failoverActive) {
          console.log('🚨 App is in failover mode - adjusting behavior');
          // Disable certain features
          // Redirect to backup systems
          // Show limited functionality
        } else {
          console.log('✅ App is in normal operation mode');
        }
      })
    );

    // Subscribe to connection status
    this.subscriptions.push(
      this.failoverService.getConnectionStatus().subscribe(status => {
        this.connectionStatus = status;
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  getStatusText(): string {
    if (!this.failoverStatus) {
      return 'Status Unknown';
    }
    return this.failoverStatus.failoverActive ? 'Failover Active' : 'Normal Operation';
  }
}
