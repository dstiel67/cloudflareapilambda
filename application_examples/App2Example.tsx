/**
 * Example Application 2 - Failover Integration with Redirect
 * 
 * This example shows an app that redirects users to a backup system
 * when failover is active.
 */

import React, { useEffect } from 'react';
import { RecoilRoot } from 'recoil';
import {
  useAppFailoverStatus,
  useFailoverService,
} from '../atom_store/src/hooks/useFailoverStatus';

/**
 * Main App Component
 */
function App2() {
  // Initialize failover service
  useFailoverService('http://localhost:3000', 10000);
  
  return (
    <div className="app">
      <FailoverRedirect />
      <Header />
      <MainContent />
    </div>
  );
}

/**
 * Failover Redirect Component
 * Automatically redirects to backup system when failover is active
 */
function FailoverRedirect() {
  const failoverStatus = useAppFailoverStatus('app2');
  
  useEffect(() => {
    if (failoverStatus?.failoverActive) {
      console.log('Failover active - redirecting to backup system');
      
      // Show countdown before redirect
      let countdown = 5;
      const countdownInterval = setInterval(() => {
        countdown--;
        if (countdown <= 0) {
          clearInterval(countdownInterval);
          // Redirect to backup system
          window.location.href = 'https://backup.example.com/app2';
        }
      }, 1000);
      
      return () => clearInterval(countdownInterval);
    }
  }, [failoverStatus]);
  
  if (!failoverStatus?.failoverActive) {
    return null;
  }
  
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      color: 'white',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,
    }}>
      <h1>System Failover Active</h1>
      <p style={{ fontSize: '18px', marginTop: '16px' }}>
        {failoverStatus.reason}
      </p>
      <p style={{ fontSize: '16px', marginTop: '24px' }}>
        Redirecting to backup system in 5 seconds...
      </p>
      <div style={{
        marginTop: '32px',
        width: '200px',
        height: '4px',
        backgroundColor: '#333',
        borderRadius: '2px',
        overflow: 'hidden',
      }}>
        <div style={{
          width: '100%',
          height: '100%',
          backgroundColor: '#3498db',
          animation: 'progress 5s linear',
        }} />
      </div>
    </div>
  );
}

/**
 * Header Component
 */
function Header() {
  return (
    <header style={{
      padding: '16px',
      backgroundColor: '#16a085',
      color: 'white',
    }}>
      <h1>Application 2</h1>
    </header>
  );
}

/**
 * Main Content Component
 */
function MainContent() {
  const failoverStatus = useAppFailoverStatus('app2');
  
  return (
    <main style={{ padding: '24px' }}>
      <h2>Welcome to Application 2</h2>
      <p>This application automatically redirects to a backup system during failover.</p>
      
      {failoverStatus && (
        <div style={{
          marginTop: '24px',
          padding: '16px',
          backgroundColor: '#ecf0f1',
          borderRadius: '8px',
        }}>
          <h3>Current Status</h3>
          <p>
            <strong>Failover Active:</strong>{' '}
            {failoverStatus.failoverActive ? 'Yes' : 'No'}
          </p>
          <p>
            <strong>Last Updated:</strong>{' '}
            {new Date(failoverStatus.lastUpdated).toLocaleString()}
          </p>
        </div>
      )}
    </main>
  );
}

/**
 * App wrapped with RecoilRoot
 */
export default function App2Root() {
  return (
    <RecoilRoot>
      <App2 />
      <style>{`
        @keyframes progress {
          from { transform: translateX(-100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </RecoilRoot>
  );
}
