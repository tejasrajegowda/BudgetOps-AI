"""
Gmail API Routes
Endpoints for Gmail integration
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.gmail_service import get_gmail_service
from utils.logger import logger


router = APIRouter()


class EmailResponse(BaseModel):
    """Email response model"""
    id: str
    thread_id: str
    from_email: str = Field(alias="from")
    to: str
    subject: str
    date: str
    snippet: str
    body: str
    internal_date: str
    
    class Config:
        populate_by_name = True


class EmailListResponse(BaseModel):
    """Email list response"""
    count: int
    emails: List[EmailResponse]


@router.get("/connect")
async def connect_gmail():
    """
    Test Gmail API connection
    """
    try:
        service = get_gmail_service()
        success = service.connect()
        
        if success:
            return {
                "status": "success",
                "message": "Successfully connected to Gmail API"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to Gmail API"
            )
    
    except Exception as e:
        logger.error(f"Error connecting to Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread", response_model=EmailListResponse)
async def get_unread_emails(
    sender: str = Query(
        default="alerts@hdfcbank.net",
        description="Email address to filter by"
    ),
    max_results: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of emails to fetch"
    )
):
    """
    Fetch unread emails from specific sender
    
    Args:
        sender: Email address to filter by
        max_results: Maximum number of emails to fetch (1-50)
    
    Returns:
        List of unread emails
    """
    try:
        service = get_gmail_service()
        emails = service.get_unread_emails(
            sender_email=sender,
            max_results=max_results
        )
        
        return {
            "count": len(emails),
            "emails": emails
        }
    
    except Exception as e:
        logger.error(f"Error fetching unread emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=EmailListResponse)
async def get_all_emails(
    sender: str = Query(
        default="alerts@hdfcbank.net",
        description="Email address to filter by"
    ),
    max_results: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of emails to fetch"
    ),
    include_read: bool = Query(
        default=True,
        description="Include read emails"
    )
):
    """
    Fetch all emails (for historical data import)
    
    Args:
        sender: Email address to filter by
        max_results: Maximum number of emails to fetch (1-100)
        include_read: Whether to include read emails
    
    Returns:
        List of all emails
    """
    try:
        service = get_gmail_service()
        emails = service.get_all_emails(
            sender_email=sender,
            max_results=max_results,
            include_read=include_read
        )
        
        return {
            "count": len(emails),
            "emails": emails
        }
    
    except Exception as e:
        logger.error(f"Error fetching all emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-read/{email_id}")
async def mark_email_as_read(email_id: str):
    """
    Mark email as read
    
    Args:
        email_id: Gmail message ID
    
    Returns:
        Success status
    """
    try:
        service = get_gmail_service()
        success = service.mark_as_read(email_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Email {email_id} marked as read"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to mark email as read"
            )
    
    except Exception as e:
        logger.error(f"Error marking email as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))