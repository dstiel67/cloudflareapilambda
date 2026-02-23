/**
 * Root App Component
 * 
 * Initializes the Failover Service and provides routing between example apps.
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { FailoverService } from './failover.service';

@Component({
  selector: 'app-root',
  template: `
    <div class="app-container">
      <!-- Navigation -->
      <nav class="navigation">
        <h2>Failover Examples</h2>
        <div class="nav-buttons">
          <button 
            [class.active]="currentView === 'app1'" 
            (click)="currentView = 'app1'">
            App 1 (Banner)
          </button>
          <button 
            [class.active]="currentView === 'app2'" 
            (click)="currentView = 'app2'">
            App 2 (Redirect)
          </button>
        </div>
        <div class="connection-info">
          <span class="connection-dot" [class.connected]="isConnected"></span>
          <span>{{ isConnected ? 'Connected' : 'Disconnected' }}</span>
        </div>
      </nav>

      <!-- Current View -->
      <div class="view-container">
        <app-app1 *ngIf="currentView === 'app1'"></app-app1>
        <app-app2 *ngIf="currentView === 'app2'"></app-app2>
      </div>
    </div>
  `,
  styles: [`
    .app-container {
      display: flex;
      flex-direction: column;
      height: 100vh;
    }

    .navigation {
      background-color: #34495e;
      color: white;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .navigation h2 {
      margin: 0;
      font-size: 20px;
    }

    .nav-buttons {
      display: flex;
      gap: 12px;
    }

    .nav-buttons button {
      padding: 8px 16px;
      border: 2px solid #ecf0f1;
      background-color: transparent;
      color: white;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;
    }

    .nav-buttons button:hover {
      background-color: #2c3e50;
    }

    .nav-buttons button.active {
      background-color: #3498db;
      border-color: #3498db;
    }

    .connection-info {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
    }

    .connection-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background-color: #e74c3c;
    }

    .connection-dot.connected {
      background-color: #2ecc71;
    }

    .view-container {
      flex: 1;
      overflow: auto;
    }
  `]
})
export class AppComponent implements OnInit, OnDestroy {
  currentView: 'app1' | 'app2' = 'app1';
  isConnected = false;
  private subscription: any;

  // Configure your Atom Store URL here
  private readonly ATOM_STORE_URL = 'ws://localhost:3000';

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    // Connect to Atom Store WebSocket
    console.log('🚀 Connecting to Atom Store:', this.ATOM_STORE_URL);
    this.failoverService.connect(this.ATOM_STORE_URL);

    // Monitor connection status
    this.subscription = this.failoverService.getConnectionStatus().subscribe(status => {
      this.isConnected = status === 'connected';
      console.log('📡 Connection status:', status);
    });
  }

  ngOnDestroy(): void {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
    this.failoverService.disconnect();
  }
}
