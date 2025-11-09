"""
Email Parser Chain
Uses LangChain + Gemini to parse transaction emails into structured data
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from utils.env_loader import get_env_loader
from utils.logger import logger


class TransactionData(BaseModel):
    """Structured transaction data model"""
    amount: float = Field(description="Transaction amount in INR")
    transaction_type: str = Field(description="Either 'credit' or 'debit'")
    card: Optional[str] = Field(description="Card name and number", default=None)
    to: Optional[str] = Field(description="Merchant or recipient name with UPI ID if present", default=None)
    transaction_reference_number: Optional[str] = Field(description="Transaction reference or ID", default=None)
    date: str = Field(description="Transaction date in YYYY-MM-DD format")
    timestamp: str = Field(description="Current timestamp in YYYY-MM-DD HH:MM:SS format")
    description: Optional[str] = Field(description="Additional transaction details", default=None)


class EmailParser:
    """Parse transaction emails using LangChain + Gemini"""
    
    def __init__(self):
        """Initialize parser with Gemini model"""
        config = get_env_loader().get_config()
        
        # Initialize Gemini model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=config["google_api_key"],
            temperature=0.1,  # Low temperature for consistent parsing
        )
        
        # Initialize output parser
        self.output_parser = PydanticOutputParser(pydantic_object=TransactionData)
        
        # Create prompt template
        self.prompt = self._create_prompt_template()
        
        logger.info("Email parser initialized with Gemini")
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create prompt template for email parsing"""
        
        template = """You are an expert at extracting structured transaction data from bank alert messages.

Extract the following information from the transaction message:
- amount: Numeric value in INR (e.g., 30 for Rs.30.00)
- transaction_type: Either "credit" or "debit" based on the message wording
- card: Full card name and number (e.g., 'HDFC Bank RuPay Credit Card XX7276')
- to: Merchant or recipient name, include UPI ID if present (e.g., 'Deccan spice (paytmqr6j4s3b@ptys)')
- transaction_reference_number: Alphanumeric transaction reference or ID
- date: Date in YYYY-MM-DD format (convert from DD-MM-YY if needed)
- timestamp: Use the provided current timestamp
- description: Any additional relevant details

Rules:
1. Clean up spaces and punctuation
2. Ensure consistent capitalization
3. If a field is not found in the message, set it to null
4. For dates: Convert DD-MM-YY format to YYYY-MM-DD (e.g., 30-10-25 → 2025-10-30)
5. Extract amount as a number without currency symbols

Current timestamp: {current_timestamp}

Transaction message:
{transaction_message}

{format_instructions}

Return only valid JSON with the extracted data.
"""
        
        return ChatPromptTemplate.from_template(template)
    
    def parse_email(
        self,
        email_text: str,
        current_timestamp: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Parse email text to extract transaction data
        
        Args:
            email_text: Raw email text (snippet or body)
            current_timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Dictionary with parsed transaction data, or None if parsing fails
        """
        if not current_timestamp:
            # Use Asia/Kolkata timezone
            from datetime import datetime
            import pytz
            tz = pytz.timezone('Asia/Kolkata')
            current_timestamp = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Format prompt
            formatted_prompt = self.prompt.format(
                transaction_message=email_text,
                current_timestamp=current_timestamp,
                format_instructions=self.output_parser.get_format_instructions()
            )
            
            # Get LLM response
            logger.debug(f"Parsing email: {email_text[:100]}...")
            response = self.llm.invoke(formatted_prompt)
            
            # Parse response
            parsed_data = self.output_parser.parse(response.content)
            
            # Convert to dict
            result = parsed_data.model_dump()
            
            logger.success(f"Parsed transaction: {result['amount']} INR, {result['transaction_type']}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            logger.debug(f"Email text was: {email_text[:200]}...")
            return None
    
    def parse_email_batch(
        self,
        emails: list,
        use_snippet: bool = True
    ) -> list:
        """
        Parse multiple emails in batch
        
        Args:
            emails: List of email dictionaries from GmailService
            use_snippet: Whether to use snippet or full body
        
        Returns:
            List of parsed transaction data
        """
        results = []
        
        for email in emails:
            # Choose text source
            text = email['snippet'] if use_snippet else email['body']
            
            # Parse email
            parsed = self.parse_email(text)
            
            if parsed:
                # Add original email metadata
                parsed['email_id'] = email['id']
                parsed['email_subject'] = email['subject']
                parsed['email_date'] = email['date']
                results.append(parsed)
        
        logger.info(f"Parsed {len(results)}/{len(emails)} emails successfully")
        return results


# Singleton instance
_parser: Optional[EmailParser] = None


def get_email_parser() -> EmailParser:
    """Get singleton instance of EmailParser"""
    global _parser
    if _parser is None:
        _parser = EmailParser()
    return _parser


if __name__ == "__main__":
    # Quick test
    parser = get_email_parser()
    
    sample_text = """Dear Customer, Rs.30.00 has been debited from your HDFC Bank RuPay Credit Card XX7276 to paytmqr6j4s3b@ptys Deccan spice on 30-10-25. Your UPI transaction reference number is 235232."""
    
    result = parser.parse_email(sample_text)
    print("Parsed Result:")
    print(json.dumps(result, indent=2))