/**
 * Example Application 1 - Failover Integration
 * 
 * This example shows how an application subscribes to its failover atom
 * and reacts to failover status changes.
 */

import React, { useEffect } from 'react';
import { RecoilRoot } from 'recoil';
import {
  useAppFailoverStatus,
  useFailoverService,
  useConnectionStatus,
} from '../atom_store/src/hooks/useFailoverStatus';

/**
 * Main App Component
 */
function App1() {
  // Initialize failover service (do this once at app root)
  useFailoverService('http://localhost:3000', 10000);
  
  return (
    <div className="app">
      <Header />
      <FailoverBanner />
      <MainContent />
      <Footer />
    </div>
  );
}

/**
 * Failover Banner Component
 * Shows banner when app is in failover mode
 */
function FailoverBanner() {
  const failoverStatus = useAppFailoverStatus('app1');
  const connectionStatus = useConnectionStatus();
  
  // Don't show banner if not in failover
  if (!failoverStatus || !failoverStatus.failoverActive) {
    return null;
  }
  
  return (
    <div className="failover-banner" style={{
      backgroundColor: '#ff6b6b',
      color: 'white',
      padding: '16px',
      textAlign: 'center',
      fontWeight: 'bold',
    }}>
      <div className="banner-content">
        <span className="icon">⚠️</span>
        <span className="message">
          System is currently in failover mode
        </span>
        <span className="reason">
          {failoverStatus.reason && ` - ${failoverStatus.reason}`}
        </span>
      </div>
      <div className="banner-details" style={{ fontSize: '12px', marginTop: '8px' }}>
        Last updated: {new Date(failoverStatus.lastUpdated).toLocaleString()}
        {connectionStatus === 'connected' && ' • Connected'}
        {connectionStatus === 'error' && ' • Connection Error'}
      </div>
    </div>
  );
}

/**
 * Header Component with Failover Indicator
 */
function Header() {
  const failoverStatus = useAppFailoverStatus('app1');
  
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '16px',
      backgroundColor: '#2c3e50',
      color: 'white',
    }}>
      <h1>Application 1</h1>
      <FailoverIndicator status={failoverStatus} />
    </header>
  );
}

/**
 * Failover Indicator Component
 */
function FailoverIndicator({ status }: { status: any }) {
  if (!status) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: '#95a5a6',
        }} />
        <span>Status Unknown</span>
      </div>
    );
  }
  
  const isFailover = status.failoverActive;
  
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{
        width: '12px',
        height: '12px',
        borderRadius: '50%',
        backgroundColor: isFailover ? '#e74c3c' : '#2ecc71',
        animation: isFailover ? 'pulse 2s infinite' : 'none',
      }} />
      <span>{isFailover ? 'Failover Active' : 'Normal Operation'}</span>
    </div>
  );
}

/**
 * Main Content Component
 * Adjusts behavior based on failover status
 */
function MainContent() {
  const failoverStatus = useAppFailoverStatus('app1');
  
  useEffect(() => {
    if (failoverStatus?.failoverActive) {
      console.log('App is in failover mode - adjusting behavior');
      // Disable certain features
      // Redirect to backup systems
      // Show limited functionality
    } else {
      console.log('App is in normal operation mode');
    }
  }, [failoverStatus]);
  
  return (
    <main style={{ padding: '24px' }}>
      <h2>Main Content</h2>
      {failoverStatus?.failoverActive ? (
        <div className="failover-content">
          <p>Running in limited mode due to failover.</p>
          <p>Some features may be unavailable.</p>
        </div>
      ) : (
        <div className="normal-content">
          <p>All systems operational.</p>
          <p>Full functionality available.</p>
        </div>
      )}
    </main>
  );
}

/**
 * Footer Component
 */
function Footer() {
  return (
    <footer style={{
      padding: '16px',
      backgroundColor: '#34495e',
      color: 'white',
      textAlign: 'center',
    }}>
      <p>Application 1 © 2024</p>
    </footer>
  );
}

/**
 * App wrapped with RecoilRoot
 */
export default function App1Root() {
  return (
    <RecoilRoot>
      <App1 />
    </RecoilRoot>
  );
}
