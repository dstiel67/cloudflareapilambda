/**
 * Failover Atom Store
 * 
 * Provides reactive state management for failover flags across applications.
 * Uses Recoil for atom-based state management.
 */

import { atom, selector, atomFamily } from 'recoil';

/**
 * Interface for failover status
 */
export interface FailoverStatus {
  appId: string;
  failoverActive: boolean;
  lastUpdated: string;
  reason: string;
  updatedBy: string;
}

/**
 * Atom family for individual app failover status
 * Each app gets its own atom that can be subscribed to independently
 */
export const failoverAtomFamily = atomFamily<FailoverStatus | null, string>({
  key: 'failoverStatus',
  default: null,
});

/**
 * Atom for all failover statuses (for bulk updates)
 */
export const allFailoverStatusesAtom = atom<Record<string, FailoverStatus>>({
  key: 'allFailoverStatuses',
  default: {},
});

/**
 * Selector to get list of all apps in failover
 */
export const appsInFailoverSelector = selector({
  key: 'appsInFailover',
  get: ({ get }) => {
    const allStatuses = get(allFailoverStatusesAtom);
    return Object.values(allStatuses).filter(status => status.failoverActive);
  },
});

/**
 * Selector to check if any app is in failover
 */
export const anyAppInFailoverSelector = selector({
  key: 'anyAppInFailover',
  get: ({ get }) => {
    const appsInFailover = get(appsInFailoverSelector);
    return appsInFailover.length > 0;
  },
});

/**
 * Selector to get failover count
 */
export const failoverCountSelector = selector({
  key: 'failoverCount',
  get: ({ get }) => {
    const appsInFailover = get(appsInFailoverSelector);
    return appsInFailover.length;
  },
});

/**
 * Atom for connection status to Read Flags Service
 */
export const connectionStatusAtom = atom<'connected' | 'disconnected' | 'error'>({
  key: 'connectionStatus',
  default: 'disconnected',
});

/**
 * Atom for last update timestamp
 */
export const lastUpdateTimestampAtom = atom<string>({
  key: 'lastUpdateTimestamp',
  default: '',
});
