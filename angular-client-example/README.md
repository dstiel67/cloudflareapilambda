# Angular Client for Failover Status Management

This directory contains complete Angular examples for integrating with the Atom Store failover status management system.

## Overview

The Angular client connects to the Atom Store WebSocket server to receive real-time failover status updates. It uses RxJS Observables for reactive state management and provides two example applications:

- **App 1**: Displays a failover banner when failover is active
- **App 2**: Automatically redirects to a backup system during failover

## Files

- `failover.service.ts` - Angular service for managing Atom Store WebSocket connection
- `app.component.ts` - Root component with navigation between examples
- `app1.component.ts` - Example app with failover banner
- `app2.component.ts` - Example app with automatic redirect
- `app.module.ts` - Angular module configuration
- `main.ts` - Application bootstrap
- `README.md` - This file

## Architecture

```
Atom Store (WebSocket) → FailoverService → Components (via Observables)
```

The `FailoverService` maintains a WebSocket connection to the Atom Store server and exposes failover status updates through RxJS Observables. Components subscribe to these Observables to receive real-time updates.

## Setup Instructions

### 1. Prerequisites

- Angular 15+ (or compatible version)
- Node.js 18+
- Atom Store Server running (see main README.md)

### 2. Install Dependencies

```bash
npm install @angular/core @angular/common @angular/platform-browser @angular/platform-browser-dynamic
npm install rxjs
```

### 3. Configure Atom Store URL

In `app.component.ts`, update the `ATOM_STORE_URL` constant:

```typescript
private readonly ATOM_STORE_URL = 'ws://localhost:3000';
```

For production, use your actual Atom Store server URL:
```typescript
private readonly ATOM_STORE_URL = 'wss://atom-store.example.com';
```

### 4. Add to Your Angular Project

Copy the files to your Angular project:

```bash
# Copy service
cp failover.service.ts src/app/

# Copy components
cp app1.component.ts src/app/
cp app2.component.ts src/app/
cp app.component.ts src/app/

# Copy module (or integrate into your existing module)
cp app.module.ts src/app/
```

### 5. Import in Your Module

If you have an existing Angular module, add the components and service:

```typescript
import { HttpClientModule } from '@angular/common/http';
import { FailoverService } from './failover.service';
import { App1Component } from './app1.component';
import { App2Component } from './app2.component';

@NgModule({
  imports: [
    HttpClientModule,  // Required for REST API calls
    // ... other imports
  ],
  providers: [
    FailoverService,   // Singleton service
    // ... other providers
  ],
  declarations: [
    App1Component,
    App2Component,
    // ... other components
  ]
})
export class AppModule { }
```

### 6. Initialize in App Component

In your root component, initialize the Failover Service:

```typescript
import { Component, OnInit } from '@angular/core';
import { FailoverService } from './failover.service';

@Component({
  selector: 'app-root',
  template: `<router-outlet></router-outlet>`
})
export class AppComponent implements OnInit {
  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    // Connect to Atom Store
    this.failoverService.connect('ws://localhost:3000');
  }
}
```

## Usage Examples

### Basic Usage - Subscribe to Failover Status

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { FailoverService, FailoverStatus } from './failover.service';

@Component({
  selector: 'app-my-component',
  template: `
    <div *ngIf="failoverStatus?.failoverActive" class="alert">
      ⚠️ System is in failover mode: {{ failoverStatus.reason }}
    </div>
  `
})
export class MyComponent implements OnInit, OnDestroy {
  failoverStatus: FailoverStatus | undefined;
  private subscription: Subscription | null = null;

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    this.subscription = this.failoverService
      .getFailoverStatus('app1')
      .subscribe(status => {
        this.failoverStatus = status;
        
        if (status?.failoverActive) {
          console.log('Failover active:', status.reason);
          // Handle failover state
        }
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }
}
```

### Monitor Connection Status

```typescript
import { Component, OnInit } from '@angular/core';
import { FailoverService, ConnectionStatus } from './failover.service';

@Component({
  selector: 'app-status-monitor',
  template: `
    <div class="connection-status" [ngClass]="connectionStatus">
      Status: {{ connectionStatus }}
    </div>
  `
})
export class StatusMonitorComponent implements OnInit {
  connectionStatus: ConnectionStatus = 'disconnected';

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    this.failoverService.getConnectionStatus().subscribe(status => {
      this.connectionStatus = status;
      
      if (status === 'error') {
        console.error('Connection error - will attempt reconnect');
      }
    });
  }
}
```

### Get All Failover Statuses

```typescript
import { Component, OnInit } from '@angular/core';
import { FailoverService, FailoverStatus } from './failover.service';

@Component({
  selector: 'app-dashboard',
  template: `
    <div *ngFor="let status of allStatuses | keyvalue">
      <h3>{{ status.key }}</h3>
      <p>Failover: {{ status.value.failoverActive ? 'Active' : 'Inactive' }}</p>
    </div>
  `
})
export class DashboardComponent implements OnInit {
  allStatuses: Map<string, FailoverStatus> = new Map();

  constructor(private failoverService: FailoverService) {}

  ngOnInit(): void {
    this.failoverService.getAllFailoverStatuses().subscribe(statuses => {
      this.allStatuses = statuses;
    });
  }
}
```

## Service API

### FailoverService

#### Methods

- `connect(atomStoreUrl: string): void` - Connect to Atom Store WebSocket
- `disconnect(): void` - Disconnect from Atom Store
- `isConnected(): boolean` - Check if currently connected
- `getFailoverStatus(appId: string): Observable<FailoverStatus | undefined>` - Get status for specific app
- `getAllFailoverStatuses(): Observable<Map<string, FailoverStatus>>` - Get all statuses
- `getConnectionStatus(): Observable<ConnectionStatus>` - Get connection status

#### Interfaces

```typescript
interface FailoverStatus {
  appId: string;
  failoverActive: boolean;
  lastUpdated: string;
  reason: string;
  updatedBy: string;
}

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';
```

## Features

### Automatic Reconnection

The service automatically attempts to reconnect if the WebSocket connection is lost:
- Exponential backoff (2s, 4s, 8s, 16s, 32s)
- Maximum 5 reconnection attempts
- Automatic status fetch on reconnection

### Change Detection

The service uses Angular's `NgZone` to ensure all WebSocket events trigger change detection properly.

### Memory Management

All subscriptions should be properly unsubscribed in `ngOnDestroy()` to prevent memory leaks:

```typescript
ngOnDestroy(): void {
  this.subscription?.unsubscribe();
}
```

## Testing

### Test with Local Atom Store

1. Start the Atom Store server:
   ```bash
   cd atom_store/server
   npm install
   npm start
   ```

2. Start your Angular app:
   ```bash
   ng serve
   ```

3. Open http://localhost:4200

4. Trigger a failover event via Ansible or Kafka

5. Verify the UI updates in real-time

### Test WebSocket Connection

```bash
# Test WebSocket connection directly
wscat -c ws://localhost:3000

# You should see connection confirmation
```

### Test REST API

```bash
# Get current status
curl http://localhost:3000/api/failover/status

# Should return JSON with all app statuses
```

## Troubleshooting

### WebSocket Connection Fails

**Symptoms**: `connectionStatus` shows 'error' or 'disconnected'

**Solutions**:
1. Verify Atom Store server is running: `curl http://localhost:3000/health`
2. Check WebSocket URL is correct (ws:// for local, wss:// for production)
3. Check browser console for CORS or network errors
4. Verify firewall allows WebSocket connections

### No Status Updates

**Symptoms**: Component doesn't receive failover status updates

**Solutions**:
1. Verify subscription is active (check `ngOnInit`)
2. Check browser console for errors
3. Verify app ID matches the one in DynamoDB
4. Test REST API: `curl http://localhost:3000/api/failover/status`

### Memory Leaks

**Symptoms**: Application slows down over time

**Solutions**:
1. Ensure all subscriptions are unsubscribed in `ngOnDestroy()`
2. Use `takeUntil()` operator for automatic cleanup
3. Check for circular references

### Change Detection Issues

**Symptoms**: UI doesn't update when status changes

**Solutions**:
1. Service uses `NgZone.run()` - verify it's working
2. Try manual change detection: `ChangeDetectorRef.detectChanges()`
3. Check if component is using OnPush strategy

## Production Considerations

### Security

1. **Use WSS (WebSocket Secure)** in production:
   ```typescript
   this.failoverService.connect('wss://atom-store.example.com');
   ```

2. **Add authentication** to Atom Store API if needed

3. **Validate data** from WebSocket messages

### Performance

1. **Limit subscriptions**: Only subscribe to apps you need
2. **Use OnPush change detection** for better performance
3. **Implement virtual scrolling** for large lists

### Monitoring

1. **Log connection events** for debugging
2. **Track reconnection attempts** in analytics
3. **Monitor WebSocket latency**

## Example Applications

### App 1: Failover Banner

Shows a prominent banner when failover is active. Good for:
- Informing users of system status
- Displaying maintenance messages
- Showing limited functionality warnings

### App 2: Automatic Redirect

Automatically redirects to backup system during failover. Good for:
- Critical applications requiring immediate failover
- Systems with dedicated backup infrastructure
- Scenarios where continued operation on primary is not possible

## Integration with Existing Apps

To integrate into an existing Angular application:

1. Copy `failover.service.ts` to your services directory
2. Add `HttpClientModule` to your app module
3. Initialize service in root component
4. Subscribe to status in components that need it
5. Style failover UI to match your design system

## Support

For issues or questions:
1. Check browser console for errors
2. Verify Atom Store server is running
3. Test WebSocket connection with `wscat`
4. Review service logs for connection issues
5. Consult main project documentation

## Additional Resources

- [Main README](../README.md) - Complete system documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md) - Deployment guide
- [Angular Documentation](https://angular.io/docs)
- [RxJS Documentation](https://rxjs.dev/)


## Files

- `redirect-notification.service.ts` - Angular service for managing SSE connection
- `redirect-update.service.ts` - Angular service for updating redirect status
- `redirect-status.component.ts` - Angular component for displaying and updating redirect status
- `README.md` - This file

## Setup Instructions

### 1. Install Dependencies

No additional dependencies are required beyond standard Angular packages (`@angular/common/http` for HTTP requests).

### 2. Update API Endpoints

#### SSE Endpoint

In `redirect-notification.service.ts`, update the `SSE_ENDPOINT` constant with your actual API Gateway URL:

```typescript
// Get this URL from Terraform output: sse_events_endpoint
private readonly SSE_ENDPOINT = 'https://YOUR_API_GATEWAY_ID.execute-api.YOUR_REGION.amazonaws.com/prod/events';
```

You can get the correct URL by running:
```bash
terraform output sse_events_endpoint
```

#### Update API Endpoint

In `redirect-update.service.ts`, update the `UPDATE_API_URL` constant with your actual API Gateway URL:

```typescript
// Get this URL from Terraform output: update_api_base_url
private readonly UPDATE_API_URL = 'https://YOUR_API_GATEWAY_ID.execute-api.YOUR_REGION.amazonaws.com/prod';
```

You can get the correct URL by running:
```bash
terraform output update_api_base_url
```

#### API Key Configuration

The Update API requires authentication via API key. Update the `API_KEY` constant in `redirect-update.service.ts`:

```typescript
// Get this from Terraform output: update_api_key_value
private readonly API_KEY = 'YOUR_API_KEY_HERE';
```

You can get the API key by running:
```bash
terraform output -raw update_api_key_value
```

**IMPORTANT SECURITY NOTE:** In production, do NOT hardcode the API key in your client code. Instead:
- Store it in environment variables
- Retrieve it from a secure backend service
- Use a secrets management solution
- Never commit API keys to version control

### 3. Add to Your Angular Module

```typescript
import { RedirectNotificationService } from './redirect-notification.service';
import { RedirectUpdateService } from './redirect-update.service';
import { HttpClientModule } from '@angular/common/http';

@NgModule({
  imports: [
    HttpClientModule,  // Required for RedirectUpdateService
    // ... other imports
  ],
  providers: [
    RedirectNotificationService,
    RedirectUpdateService,
    // ... other providers
  ],
  // ...
})
export class AppModule { }
```

### 4. Use in Your Component

```typescript
import { Component, OnInit } from '@angular/core';
import { RedirectNotificationService } from './redirect-notification.service';

@Component({
  selector: 'app-my-component',
  template: `
    <app-redirect-status></app-redirect-status>
  `
})
export class MyComponent implements OnInit {
  constructor(private redirectService: RedirectNotificationService) {}

  ngOnInit() {
    // The component will automatically connect
    // You can also manually control the connection:
    // this.redirectService.connect('my-client-id');
  }
}
```

## Service APIs

### RedirectNotificationService

#### Methods

- `connect(clientId?: string)` - Connect to SSE endpoint
- `disconnect()` - Disconnect from SSE endpoint
- `reconnect(maxAttempts?, baseDelay?)` - Reconnect with exponential backoff
- `isConnected()` - Check if currently connected
- `getCurrentStatus()` - Get current connection status

#### Observables

- `getConnectionStatus()` - Connection status changes
- `getRedirectUpdates()` - Redirect status updates only
- `getAllEvents()` - All SSE events

### RedirectUpdateService

#### Methods

- `updateRedirectStatus(request)` - Update redirect status (ON/OFF)
- `getCurrentRedirectStatus()` - Get current redirect status from API
- `turnRedirectOn(updatedBy?, reason?)` - Turn redirect ON
- `turnRedirectOff(updatedBy?, reason?)` - Turn redirect OFF
- `toggleRedirectStatus(currentValue, updatedBy?, reason?)` - Toggle status
- `checkHealth()` - Check Update API health

### Event Types

#### RedirectStatusUpdate
```typescript
interface RedirectStatusUpdate {
  key: string;                    // 'redirect-all-users-to-essentials'
  value: string;                  // 'ON' or 'OFF'
  timestamp: string;              // ISO timestamp
  event_type: 'insert' | 'modify'; // Type of change
}
```

#### SSEEvent
```typescript
interface SSEEvent {
  type: string;      // Event type
  data: any;         // Event data
  id: string;        // Event ID
  timestamp: string; // Client timestamp
}
```

## Component Features

The `RedirectStatusComponent` provides:

- **Real-time connection status** with visual indicators
- **Current redirect status** display with color coding
- **Update controls** to change redirect status (ON/OFF/Toggle)
- **Recent updates history** (last 10 updates)
- **Auto-reconnection** on connection loss
- **Error handling** for update operations
- **Debug information** for troubleshooting
- **Manual connect/disconnect** controls
- **Refresh status** button to fetch current status

## Usage Examples

### Basic Usage - Read-Only Notifications

```typescript
export class MyComponent implements OnInit, OnDestroy {
  private subscription: Subscription;

  constructor(private redirectService: RedirectNotificationService) {}

  ngOnInit() {
    this.redirectService.connect();
    
    this.subscription = this.redirectService.getRedirectUpdates().subscribe(
      update => {
        console.log('Redirect status changed:', update);
        
        if (update.value === 'ON') {
          // Handle redirect enabled
          this.showRedirectNotification();
        } else {
          // Handle redirect disabled
          this.hideRedirectNotification();
        }
      }
    );
  }

  ngOnDestroy() {
    this.subscription?.unsubscribe();
    this.redirectService.disconnect();
  }
}
```

### Update Redirect Status

```typescript
export class AdminComponent implements OnInit {
  constructor(
    private redirectService: RedirectNotificationService,
    private updateService: RedirectUpdateService
  ) {}

  ngOnInit() {
    // Connect to receive real-time updates
    this.redirectService.connect();
  }

  enableRedirect() {
    this.updateService.turnRedirectOn('admin-user', 'Maintenance mode').subscribe({
      next: (response) => {
        console.log('Redirect enabled:', response);
        // The SSE connection will automatically receive the update
      },
      error: (error) => {
        console.error('Failed to enable redirect:', error);
      }
    });
  }

  disableRedirect() {
    this.updateService.turnRedirectOff('admin-user', 'Maintenance complete').subscribe({
      next: (response) => {
        console.log('Redirect disabled:', response);
      },
      error: (error) => {
        console.error('Failed to disable redirect:', error);
      }
    });
  }

  toggleRedirect(currentValue: 'ON' | 'OFF') {
    this.updateService.toggleRedirectStatus(currentValue, 'admin-user').subscribe({
      next: (response) => {
        console.log('Redirect toggled:', response);
      },
      error: (error) => {
        console.error('Failed to toggle redirect:', error);
      }
    });
  }
}
```

### Get Current Status

```typescript
export class StatusCheckComponent implements OnInit {
  currentStatus: string = 'UNKNOWN';

  constructor(private updateService: RedirectUpdateService) {}

  ngOnInit() {
    this.checkCurrentStatus();
  }

  checkCurrentStatus() {
    this.updateService.getCurrentRedirectStatus().subscribe({
      next: (response) => {
        this.currentStatus = response.data.value;
        console.log('Current redirect status:', this.currentStatus);
      },
      error: (error) => {
        console.error('Failed to get status:', error);
      }
    });
  }
}
```

### Advanced Usage with Error Handling

```typescript
export class AdvancedComponent implements OnInit {
  constructor(private redirectService: RedirectNotificationService) {}

  ngOnInit() {
    // Monitor connection status
    this.redirectService.getConnectionStatus().subscribe(status => {
      switch (status) {
        case 'connected':
          console.log('✅ Connected to notifications');
          break;
        case 'error':
          console.log('❌ Connection error, attempting reconnect...');
          this.redirectService.reconnect(5, 2000); // 5 attempts, 2s base delay
          break;
        case 'disconnected':
          console.log('🔌 Disconnected from notifications');
          break;
      }
    });

    // Listen to all events for debugging
    this.redirectService.getAllEvents().subscribe(event => {
      console.log('SSE Event:', event);
    });

    this.redirectService.connect('my-app-client');
  }
}
```

## Testing

### Test the SSE Endpoint

You can test the SSE endpoint directly in your browser:

1. Get the endpoint URL:
   ```bash
   terraform output sse_events_endpoint
   ```

2. Open the URL in your browser or use curl:
   ```bash
   curl -N -H "Accept: text/event-stream" "https://YOUR_API_GATEWAY_ID.execute-api.YOUR_REGION.amazonaws.com/prod/events"
   ```

3. Trigger a redirect status change using the Update API:
   ```bash
   API_KEY=$(terraform output -raw update_api_key_value)
   curl -X POST "https://YOUR_API_GATEWAY_ID.execute-api.YOUR_REGION.amazonaws.com/prod/redirect-status" \
     -H "Content-Type: application/json" \
     -H "x-api-key: $API_KEY" \
     -d '{"value": "ON", "updated_by": "test-user"}'
   ```

### Test the Update API

Test updating the redirect status:

```bash
# Get API key
API_KEY=$(terraform output -raw update_api_key_value)

# Turn redirect ON
curl -X POST "$(terraform output -raw update_api_base_url)/redirect-status" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "ON", "updated_by": "admin", "reason": "Testing"}'

# Turn redirect OFF
curl -X POST "$(terraform output -raw update_api_base_url)/redirect-status" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"value": "OFF", "updated_by": "admin", "reason": "Testing complete"}'

# Get current status
curl -H "x-api-key: $API_KEY" "$(terraform output -raw update_api_base_url)/redirect-status"
```

### Health Checks

Test the health endpoints:
```bash
# SSE endpoint health
curl "$(terraform output -raw sse_health_endpoint)"

# Update API health
curl "$(terraform output -raw update_api_base_url)/health"
```

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Both API Gateways are configured with CORS headers
   - Ensure you're using the correct endpoint URLs
   - Check browser console for specific CORS errors

2. **Connection Timeouts**
   - Lambda functions have a 30-second timeout for SSE
   - The service includes auto-reconnection logic
   - Check network connectivity

3. **No Events Received**
   - Check that the DynamoDB Stream is enabled
   - Verify the notification Lambda function is working
   - Check CloudWatch logs for errors
   - Ensure you've triggered an update after connecting

4. **Update API Errors**
   - Verify the API Gateway URL is correct
   - Check that the request body is valid JSON
   - Ensure `value` is either "ON" or "OFF"
   - Verify the API key is included in the `x-api-key` header
   - Check that the API key is valid and not expired
   - Check CloudWatch logs for Lambda errors

### Debug Information

Enable debug info in the component to see:
- Connection status
- Total updates received
- Last event ID
- Client ID
- Update operation status

### CloudWatch Logs

Check the Lambda function logs:
```bash
# SSE endpoint logs
aws logs tail "/aws/lambda/cloudflare-sse-endpoint" --follow

# Notification handler logs
aws logs tail "/aws/lambda/cloudflare-notification-handler" --follow

# Update API logs
aws logs tail "/aws/lambda/redirect-status-update" --follow
```

## Security Considerations

- The SSE endpoint is publicly accessible (no authentication required)
- **The Update API requires API key authentication** via the `x-api-key` header
- API key provides rate limiting (1000 req/s, 2000 burst) and quota (1M req/month)
- Consider additional security measures for production:
  - AWS IAM authentication
  - Lambda authorizers
  - Cognito user pools
  - IP whitelisting
- **Never hardcode API keys in client code** - use environment variables or backend services
- The endpoints only provide access to redirect status (no sensitive data)
- All sensitive data (Cloudflare credentials) remains secure in Lambda
- Add audit logging for update operations (already included in Lambda)
- Monitor API Gateway metrics for unusual activity

## Performance Notes

- SSE connections are lightweight and efficient
- The service includes automatic reconnection with exponential backoff
- Messages are stored temporarily in DynamoDB with TTL (1 hour)
- API Gateway has built-in rate limiting and DDoS protection
- Update operations trigger DynamoDB Streams for real-time notifications
- End-to-end latency: ~150-700ms from update to client notification

## Architecture Flow

1. **User updates status** via Angular component
2. **Update API** receives request and validates
3. **DynamoDB** stores new status value
4. **DynamoDB Stream** triggers notification Lambda
5. **Notification Lambda** creates SSE message
6. **SSE Endpoint** delivers message to connected clients
7. **Angular component** receives update and refreshes UI

This creates a complete real-time feedback loop where updates are immediately visible to all connected clients.