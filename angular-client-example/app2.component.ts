/**
 * Example Application 2 - Failover Integration with Redirect
 * 
 * This example shows an Angular app that redirects users to a backup system
 * when failover is active.
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription, interval } from 'rxjs';
import { take } from 'rxjs/operators';
import { FailoverService, FailoverStatus } from './failover.service';

@Component({
  selector: 'app-app2',
  template: `
    <div class="app">
      <!-- Failover Redirect Overlay -->
      <div *ngIf="showRedirectOverlay" class="redirect-overlay">
        <div class="redirect-content">
          <h1>System Failover Active</h1>
          <p class="reason" *ngIf="failoverStatus?.reason">
            {{ failoverStatus.reason }}
          </p>
          <p class="countdown">
            Redirecting to backup system in {{ countdown }} seconds...
          </p>
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="progressPercent"></div>
          </div>
          <button class="cancel-btn" (click)="cancelRedirect()">
            Cancel Redirect
          </button>
        </div>
      </div>

      <!-- Header -->
      <header class="header">
        <h1>Application 2</h1>
        <div class="status-badge" [class.failover]="failoverStatus?.failoverActive">
          {{ failoverStatus?.failoverActive ? 'Failover Mode' : 'Normal' }}
        </div>
      </header>

      <!-- Main Content -->
      <main class="main-content">
        <h2>Welcome to Application 2</h2>
        <p>This application automatically redirects to a backup system during failover.</p>

        <!-- Current Status Card -->
        <div class="status-card" *ngIf="failoverStatus">
          <h3>Current Status</h3>
          <div class="status-grid">
            <div class="status-item">
              <span class="label">Failover Active:</span>
              <span class="value" [class.active]="failoverStatus.failoverActive">
                {{ failoverStatus.failoverActive ? 'Yes' : 'No' }}
              </span>
            </div>
            <div class="status-item">
              <span class="label">Last Updated:</span>
              <span class="value">{{ failoverStatus.lastUpdated | date:'medium' }}</span>
            </div>
            <div class="status-item" *ngIf="failoverStatus.reason">
              <span class="label">Reason:</span>
              <span class="value">{{ failoverStatus.reason }}</span>
            </div>
            <div class="status-item" *ngIf="failoverStatus.updatedBy">
              <span class="label">Updated By:</span>
              <span class="value">{{ failoverStatus.updatedBy }}</span>
            </div>
          </div>
        </div>

        <!-- Info Box -->
        <div class="info-box">
          <h3>ℹ️ About Automatic Redirect</h3>
          <p>
            When a failover event is detected, this application will automatically
            redirect you to the backup system after a 5-second countdown.
          </p>
          <p>
            You can cancel the redirect if needed by clicking the "Cancel Redirect" button.
          </p>
        </div>
      </main>
    </div>
  `,
  styles: [`
    .app {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      position: relative;
    }

    .redirect-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.95);
      color: white;
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 9999;
      animation: fadeIn 0.3s;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .redirect-content {
      text-align: center;
      max-width: 600px;
      padding: 40px;
    }

    .redirect-content h1 {
      font-size: 32px;
      margin-bottom: 16px;
      color: #ff6b6b;
    }

    .reason {
      font-size: 18px;
      margin: 16px 0;
      color: #f1f3f5;
    }

    .countdown {
      font-size: 20px;
      margin: 24px 0;
      font-weight: bold;
    }

    .progress-bar {
      width: 100%;
      height: 8px;
      background-color: #333;
      border-radius: 4px;
      overflow: hidden;
      margin: 24px 0;
    }

    .progress-fill {
      height: 100%;
      background-color: #3498db;
      transition: width 0.1s linear;
    }

    .cancel-btn {
      margin-top: 24px;
      padding: 12px 24px;
      font-size: 16px;
      background-color: #e74c3c;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.2s;
    }

    .cancel-btn:hover {
      background-color: #c0392b;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      background-color: #16a085;
      color: white;
    }

    .header h1 {
      margin: 0;
    }

    .status-badge {
      padding: 8px 16px;
      border-radius: 20px;
      background-color: #2ecc71;
      font-weight: bold;
      font-size: 14px;
    }

    .status-badge.failover {
      background-color: #e74c3c;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }

    .main-content {
      flex: 1;
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
      width: 100%;
    }

    .main-content h2 {
      color: #2c3e50;
      margin-bottom: 8px;
    }

    .main-content > p {
      color: #7f8c8d;
      margin-bottom: 24px;
    }

    .status-card {
      background-color: #f8f9fa;
      border: 1px solid #dee2e6;
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 24px;
    }

    .status-card h3 {
      margin-top: 0;
      color: #495057;
      margin-bottom: 16px;
    }

    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
    }

    .status-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .status-item .label {
      font-weight: bold;
      color: #6c757d;
      font-size: 14px;
    }

    .status-item .value {
      color: #212529;
      font-size: 16px;
    }

    .status-item .value.active {
      color: #e74c3c;
      font-weight: bold;
    }

    .info-box {
      background-color: #e3f2fd;
      border: 1px solid #90caf9;
      border-radius: 8px;
      padding: 20px;
    }

    .info-box h3 {
      margin-top: 0;
      color: #1976d2;
    }

    .info-box p {
      color: #424242;
      line-height: 1.6;
      margin-bottom: 8px;
    }

    .info-box p:last-child {
      margin-bottom: 0;
    }
  `]
})
export class App2Component implements OnInit, OnDestroy {
  failoverStatus: FailoverStatus | undefined;
  showRedirectOverlay = false;
  countdown = 5;
  progressPercent = 0;
  private subscriptions: Subscription[] = [];
  private redirectCancelled = false;

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    // Subscribe to failover status for app2
    this.subscriptions.push(
      this.failoverService.getFailoverStatus('app2').subscribe(status => {
        this.failoverStatus = status;
        
        if (status?.failoverActive && !this.redirectCancelled) {
          this.startRedirectCountdown();
        } else {
          this.showRedirectOverlay = false;
          this.countdown = 5;
          this.progressPercent = 0;
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  startRedirectCountdown(): void {
    if (this.showRedirectOverlay) {
      return; // Already counting down
    }

    this.showRedirectOverlay = true;
    this.countdown = 5;
    this.progressPercent = 0;

    console.log('🚨 Failover active - starting redirect countdown');

    // Countdown timer
    const countdownSub = interval(1000)
      .pipe(take(5))
      .subscribe({
        next: (tick) => {
          this.countdown = 5 - tick - 1;
          this.progressPercent = ((tick + 1) / 5) * 100;
        },
        complete: () => {
          if (!this.redirectCancelled) {
            console.log('🔄 Redirecting to backup system...');
            // Redirect to backup system
            window.location.href = 'https://backup.example.com/app2';
          }
        }
      });

    this.subscriptions.push(countdownSub);
  }

  cancelRedirect(): void {
    console.log('❌ Redirect cancelled by user');
    this.redirectCancelled = true;
    this.showRedirectOverlay = false;
    this.countdown = 5;
    this.progressPercent = 0;
  }
}
