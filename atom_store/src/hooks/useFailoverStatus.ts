/**
 * React hooks for accessing failover status
 */

import { useEffect } from 'react';
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil';
import {
  failoverAtomFamily,
  allFailoverStatusesAtom,
  appsInFailoverSelector,
  anyAppInFailoverSelector,
  failoverCountSelector,
  connectionStatusAtom,
  lastUpdateTimestampAtom,
  FailoverStatus,
} from '../atoms/failoverAtoms';
import { FailoverService } from '../services/FailoverService';

/**
 * Hook to get failover status for a specific app
 */
export function useAppFailoverStatus(appId: string): FailoverStatus | null {
  return useRecoilValue(failoverAtomFamily(appId));
}

/**
 * Hook to get all failover statuses
 */
export function useAllFailoverStatuses(): Record<string, FailoverStatus> {
  return useRecoilValue(allFailoverStatusesAtom);
}

/**
 * Hook to get list of apps currently in failover
 */
export function useAppsInFailover(): FailoverStatus[] {
  return useRecoilValue(appsInFailoverSelector);
}

/**
 * Hook to check if any app is in failover
 */
export function useAnyAppInFailover(): boolean {
  return useRecoilValue(anyAppInFailoverSelector);
}

/**
 * Hook to get count of apps in failover
 */
export function useFailoverCount(): number {
  return useRecoilValue(failoverCountSelector);
}

/**
 * Hook to get connection status
 */
export function useConnectionStatus(): 'connected' | 'disconnected' | 'error' {
  return useRecoilValue(connectionStatusAtom);
}

/**
 * Hook to get last update timestamp
 */
export function useLastUpdateTimestamp(): string {
  return useRecoilValue(lastUpdateTimestampAtom);
}

/**
 * Hook to initialize failover service and start polling
 */
export function useFailoverService(apiUrl: string, pollingInterval: number = 10000) {
  const setAllStatuses = useSetRecoilState(allFailoverStatusesAtom);
  const setConnectionStatus = useSetRecoilState(connectionStatusAtom);
  const setLastTimestamp = useSetRecoilState(lastUpdateTimestampAtom);
  
  useEffect(() => {
    const service = new FailoverService(apiUrl, pollingInterval);
    
    // Start polling
    service.startPolling(setAllStatuses, setConnectionStatus, setLastTimestamp);
    
    // Cleanup on unmount
    return () => {
      service.stopPolling();
    };
  }, [apiUrl, pollingInterval, setAllStatuses, setConnectionStatus, setLastTimestamp]);
}

/**
 * Hook to subscribe to WebSocket updates (alternative to polling)
 */
export function useFailoverWebSocket(apiUrl: string) {
  const setAllStatuses = useSetRecoilState(allFailoverStatusesAtom);
  const setConnectionStatus = useSetRecoilState(connectionStatusAtom);
  const setLastTimestamp = useSetRecoilState(lastUpdateTimestampAtom);
  
  useEffect(() => {
    const service = new FailoverService(apiUrl);
    
    // Subscribe to WebSocket
    const ws = service.subscribeToUpdates(setAllStatuses, setConnectionStatus, setLastTimestamp);
    
    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [apiUrl, setAllStatuses, setConnectionStatus, setLastTimestamp]);
}
