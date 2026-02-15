/**
 * Failover Service
 * 
 * Handles communication with Read Flags Service and updates Recoil atoms.
 */

import { SetterOrUpdater } from 'recoil';
import { FailoverStatus } from '../atoms/failoverAtoms';

export class FailoverService {
  private apiUrl: string;
  private pollingInterval: number;
  private intervalId: NodeJS.Timeout | null = null;
  
  constructor(apiUrl: string, pollingInterval: number = 10000) {
    this.apiUrl = apiUrl;
    this.pollingInterval = pollingInterval;
  }
  
  /**
   * Start polling for failover updates
   */
  startPolling(
    updateAllStatuses: SetterOrUpdater<Record<string, FailoverStatus>>,
    updateConnectionStatus: SetterOrUpdater<'connected' | 'disconnected' | 'error'>,
    updateLastTimestamp: SetterOrUpdater<string>
  ): void {
    console.log('Starting failover polling...');
    
    // Initial fetch
    this.fetchFailoverStatus(updateAllStatuses, updateConnectionStatus, updateLastTimestamp);
    
    // Set up polling
    this.intervalId = setInterval(() => {
      this.fetchFailoverStatus(updateAllStatuses, updateConnectionStatus, updateLastTimestamp);
    }, this.pollingInterval);
  }
  
  /**
   * Stop polling
   */
  stopPolling(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      console.log('Stopped failover polling');
    }
  }
  
  /**
   * Fetch current failover status from API
   */
  private async fetchFailoverStatus(
    updateAllStatuses: SetterOrUpdater<Record<string, FailoverStatus>>,
    updateConnectionStatus: SetterOrUpdater<'connected' | 'disconnected' | 'error'>,
    updateLastTimestamp: SetterOrUpdater<string>
  ): Promise<void> {
    try {
      const response = await fetch(`${this.apiUrl}/api/failover/status`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Update atoms
      updateAllStatuses(data);
      updateConnectionStatus('connected');
      updateLastTimestamp(new Date().toISOString());
      
      console.log('Failover status updated:', data);
      
    } catch (error) {
      console.error('Error fetching failover status:', error);
      updateConnectionStatus('error');
    }
  }
  
  /**
   * Subscribe to WebSocket updates (alternative to polling)
   */
  subscribeToUpdates(
    updateAllStatuses: SetterOrUpdater<Record<string, FailoverStatus>>,
    updateConnectionStatus: SetterOrUpdater<'connected' | 'disconnected' | 'error'>,
    updateLastTimestamp: SetterOrUpdater<string>
  ): WebSocket {
    const ws = new WebSocket(`${this.apiUrl.replace('http', 'ws')}/ws/failover`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      updateConnectionStatus('connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        updateAllStatuses(data);
        updateLastTimestamp(new Date().toISOString());
        console.log('Received failover update via WebSocket:', data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      updateConnectionStatus('error');
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      updateConnectionStatus('disconnected');
    };
    
    return ws;
  }
}
