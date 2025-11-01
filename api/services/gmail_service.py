"""
Gmail Service - Handles Gmail API authentication and email fetching
"""

import os
import base64
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.logger import logger
from utils.env_loader import get_env_loader


class GmailService:
    """Gmail API service for fetching transaction emails"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    TOKEN_FILE = 'token.pickle'
    
    def __init__(self):
        """Initialize Gmail service"""
        self.config = get_env_loader().get_config()
        self.creds: Optional[Credentials] = None
        self.service = None
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load or refresh credentials"""
        token_path = Path(self.TOKEN_FILE)
        
        # Load existing token
        if token_path.exists():
            with open(self.TOKEN_FILE, 'rb') as token:
                self.creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials...")
                self.creds.refresh(Request())
            else:
                logger.info("Initiating OAuth flow for new credentials...")
                self._get_new_credentials()
            
            # Save credentials
            with open(self.TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
            logger.success("Credentials saved")
    
    def _get_new_credentials(self) -> None:
        """Get new credentials via OAuth flow"""
        # Create credentials dict for OAuth flow
        client_config = {
            "installed": {
                "client_id": self.config["gmail_client_id"],
                "client_secret": self.config["gmail_client_secret"],
                "redirect_uris": [self.config["gmail_redirect_uri"]],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        flow = InstalledAppFlow.from_client_config(
            client_config,
            scopes=self.SCOPES
        )
        
        # Run local server for OAuth callback
        self.creds = flow.run_local_server(port=8000)
        logger.success("New credentials obtained via OAuth")
    
    def connect(self) -> bool:
        """
        Connect to Gmail API
        
        Returns:
            True if connection successful
        """
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.success("Successfully connected to Gmail API")
            return True
        except HttpError as error:
            logger.error(f"Failed to connect to Gmail API: {error}")
            return False
    
    def get_unread_emails(
        self,
        sender_email: str = "alerts@hdfcbank.net",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from specific sender
        
        Args:
            sender_email: Email address to filter by
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email data dictionaries
        """
        if not self.service:
            logger.warning("Service not connected. Connecting now...")
            if not self.connect():
                return []
        
        try:
            # Build query
            query = f"from:{sender_email} is:unread"
            logger.info(f"Fetching unread emails: {query}")
            
            # Get message list
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No unread emails found")
                return []
            
            logger.info(f"Found {len(messages)} unread email(s)")
            
            # Fetch full message details
            email_data = []
            for msg in messages:
                email = self._get_message_details(msg['id'])
                if email:
                    email_data.append(email)
            
            return email_data
            
        except HttpError as error:
            logger.error(f"Error fetching emails: {error}")
            return []
    
    def _get_message_details(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed message information
        
        Args:
            msg_id: Message ID
            
        Returns:
            Dictionary with message details
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract body
            body = self._get_message_body(message['payload'])
            
            # Get snippet (preview text)
            snippet = message.get('snippet', '')
            
            email_data = {
                'id': msg_id,
                'thread_id': message.get('threadId'),
                'from': header_dict.get('From', ''),
                'to': header_dict.get('To', ''),
                'subject': header_dict.get('Subject', ''),
                'date': header_dict.get('Date', ''),
                'snippet': snippet,
                'body': body,
                'internal_date': message.get('internalDate'),
            }
            
            logger.debug(f"Fetched email: {email_data['subject']}")
            return email_data
            
        except HttpError as error:
            logger.error(f"Error getting message {msg_id}: {error}")
            return None
    
    def _get_message_body(self, payload: Dict) -> str:
        """
        Extract message body from payload
        
        Args:
            payload: Message payload
            
        Returns:
            Decoded message body
        """
        body = ""
        
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8')
        
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
        
        return body
    
    def mark_as_read(self, msg_id: str) -> bool:
        """
        Mark email as read
        
        Args:
            msg_id: Message ID
            
        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info(f"Marked email {msg_id} as read")
            return True
            
        except HttpError as error:
            logger.error(f"Error marking email as read: {error}")
            return False
    
    def get_all_emails(
        self,
        sender_email: str = "alerts@hdfcbank.net",
        max_results: int = 50,
        include_read: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch all emails (read and unread) from specific sender
        For onboarding new users who want historical data
        
        Args:
            sender_email: Email address to filter by
            max_results: Maximum number of emails to fetch
            include_read: Whether to include read emails
            
        Returns:
            List of email data dictionaries
        """
        if not self.service:
            if not self.connect():
                return []
        
        try:
            # Build query
            query = f"from:{sender_email}"
            if not include_read:
                query += " is:unread"
            
            logger.info(f"Fetching emails: {query}")
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No emails found")
                return []
            
            logger.info(f"Found {len(messages)} email(s)")
            
            email_data = []
            for msg in messages:
                email = self._get_message_details(msg['id'])
                if email:
                    email_data.append(email)
            
            return email_data
            
        except HttpError as error:
            logger.error(f"Error fetching emails: {error}")
            return []


# Singleton instance
_gmail_service: Optional[GmailService] = None


def get_gmail_service() -> GmailService:
    """Get singleton instance of GmailService"""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
    return _gmail_service


if __name__ == "__main__":
    # Quick test
    service = get_gmail_service()
    service.connect()
    emails = service.get_unread_emails(max_results=5)
    print(f"Found {len(emails)} unread emails")
    for email in emails:
        print(f"- {email['subject']}")