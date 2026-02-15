"""
Read Flags Service - Polls DynamoDB for failover flag changes.

This service:
1. Periodically polls DynamoDB for current failover flags
2. Detects changes in failover status
3. Publishes updates to Atom Store via API or WebSocket
"""

import boto3
import json
import time
import logging
import os
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReadFlagsService:
    """Service for polling DynamoDB and updating Atom Store."""
    
    def __init__(
        self,
        table_name: str,
        atom_store_url: str,
        polling_interval: int = 10
    ):
        """
        Initialize Read Flags Service.
        
        Args:
            table_name: DynamoDB table name
            atom_store_url: URL of Atom Store API
            polling_interval: Seconds between polls
        """
        self.table_name = table_name
        self.atom_store_url = atom_store_url
        self.polling_interval = polling_interval
        
        # Initialize DynamoDB client
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        
        # Track previous state to detect changes
        self.previous_state: Optional[Dict[str, Any]] = None
        
        logger.info(f"Read Flags Service initialized")
        logger.info(f"Table: {table_name}")
        logger.info(f"Atom Store URL: {atom_store_url}")
        logger.info(f"Polling interval: {polling_interval}s")
    
    def start(self):
        """Start the polling loop."""
        logger.info("Starting Read Flags Service...")
        
        try:
            while True:
                self.poll_and_update()
                time.sleep(self.polling_interval)
                
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error(f"Service error: {str(e)}")
            raise
    
    def poll_and_update(self):
        """Poll DynamoDB and update Atom Store if changes detected."""
        try:
            # Read current flags from DynamoDB
            current_state = self.read_flags()
            
            if current_state is None:
                logger.warning("No failover status found in DynamoDB")
                return
            
            # Check for changes
            if self.has_changes(current_state):
                logger.info("Changes detected, updating Atom Store")
                self.update_atom_store(current_state)
                self.previous_state = current_state
            else:
                logger.debug("No changes detected")
                
        except Exception as e:
            logger.error(f"Error in poll_and_update: {str(e)}")
    
    def read_flags(self) -> Optional[Dict[str, Any]]:
        """
        Read current failover flags from DynamoDB.
        
        Returns:
            Dict with current flags or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'pk': 'FAILOVER_STATUS',
                    'sk': 'CURRENT'
                }
            )
            
            item = response.get('Item')
            
            if item:
                logger.debug(f"Read flags: {item}")
                return item
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error reading flags from DynamoDB: {str(e)}")
            return None
    
    def has_changes(self, current_state: Dict[str, Any]) -> bool:
        """
        Check if current state differs from previous state.
        
        Args:
            current_state: Current flags from DynamoDB
            
        Returns:
            True if changes detected, False otherwise
        """
        if self.previous_state is None:
            return True
        
        # Extract failover flags (keys ending with _Failover)
        current_flags = {
            k: v for k, v in current_state.items()
            if k.endswith('_Failover')
        }
        
        previous_flags = {
            k: v for k, v in self.previous_state.items()
            if k.endswith('_Failover')
        }
        
        return current_flags != previous_flags
    
    def update_atom_store(self, state: Dict[str, Any]):
        """
        Update Atom Store with new failover flags.
        
        Args:
            state: Current state from DynamoDB
        """
        try:
            # Extract failover data
            failover_updates = self.extract_failover_data(state)
            
            # Send to Atom Store API
            response = requests.post(
                f"{self.atom_store_url}/api/failover/update",
                json=failover_updates,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated Atom Store with {len(failover_updates)} flags")
            else:
                logger.error(f"Failed to update Atom Store: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Atom Store: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating Atom Store: {str(e)}")
    
    def extract_failover_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract failover data from DynamoDB state.
        
        Args:
            state: DynamoDB item
            
        Returns:
            Dict with failover data for each app
        """
        failover_data = {}
        
        # Find all failover flags
        for key, value in state.items():
            if key.endswith('_Failover'):
                # Extract app ID
                app_id = key.replace('_Failover', '')
                
                # Get related fields
                timestamp_key = f"{app_id}_LastUpdated"
                reason_key = f"{app_id}_Reason"
                
                failover_data[app_id] = {
                    'appId': app_id,
                    'failoverActive': value == 'Y',
                    'lastUpdated': state.get(timestamp_key, ''),
                    'reason': state.get(reason_key, ''),
                    'updatedBy': state.get('LastUpdatedBy', 'unknown')
                }
        
        return failover_data


def main():
    """Main entry point for the service."""
    # Get configuration from environment
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'failover-status')
    atom_store_url = os.environ.get('ATOM_STORE_URL', 'http://localhost:3000')
    polling_interval = int(os.environ.get('POLLING_INTERVAL', '10'))
    
    # Create and start service
    service = ReadFlagsService(
        table_name=table_name,
        atom_store_url=atom_store_url,
        polling_interval=polling_interval
    )
    
    service.start()


if __name__ == '__main__':
    main()
