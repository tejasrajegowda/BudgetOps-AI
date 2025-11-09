"""
Transaction Categorization Chain
Uses Gemini to categorize transactions into spending categories
"""

from typing import Dict, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from utils.env_loader import get_env_loader
from utils.logger import logger


class CategoryData(BaseModel):
    """Transaction category data"""
    category: str = Field(description="Transaction category")
    sub_category: Optional[str] = Field(description="Sub-category if applicable", default=None)
    confidence: float = Field(description="Confidence score 0-1", default=1.0)


class TransactionCategorizer:
    """Categorize transactions using AI"""
    
    # Predefined categories
    CATEGORIES = [
        "Food & Dining",
        "Groceries",
        "Transportation",
        "Shopping",
        "Entertainment",
        "Bills & Utilities",
        "Healthcare",
        "Education",
        "Travel",
        "Investment",
        "Transfer",
        "Others"
    ]
    
    def __init__(self):
        """Initialize categorizer with Gemini"""
        config = get_env_loader().get_config()
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=config["google_api_key"],
            temperature=0.1,
        )
        
        self.output_parser = PydanticOutputParser(pydantic_object=CategoryData)
        self.prompt = self._create_prompt_template()
        
        logger.info("Transaction categorizer initialized")
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create prompt for categorization"""
        
        categories_str = "\n".join([f"- {cat}" for cat in self.CATEGORIES])
        
        template = """You are an expert at categorizing financial transactions.

Available categories:
{categories}

Analyze the following transaction and assign it to the most appropriate category.

Transaction Details:
- Amount: {amount} INR
- Type: {transaction_type}
- Merchant: {merchant}
- Description: {description}

Consider:
1. The merchant name (e.g., "Swiggy" → Food & Dining, "Uber" → Transportation)
2. Transaction type (UPI to individuals might be Transfer)
3. Amount patterns (small amounts at food places → Food & Dining)

{format_instructions}

Return the category, optional sub-category, and confidence score (0-1).
"""
        
        return ChatPromptTemplate.from_template(template)
    
    def categorize_transaction(
        self,
        transaction: Dict
    ) -> Optional[Dict]:
        """
        Categorize a single transaction
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Category data or None
        """
        try:
            # Extract merchant name
            merchant = transaction.get('to', transaction.get('to_merchant', 'Unknown'))
            description = transaction.get('description', '')
            
            # Format prompt
            formatted_prompt = self.prompt.format(
                categories="\n".join([f"- {cat}" for cat in self.CATEGORIES]),
                amount=transaction.get('amount', 0),
                transaction_type=transaction.get('transaction_type', 'unknown'),
                merchant=merchant,
                description=description,
                format_instructions=self.output_parser.get_format_instructions()
            )
            
            # Get response
            response = self.llm.invoke(formatted_prompt)
            parsed = self.output_parser.parse(response.content)
            
            result = parsed.model_dump()
            
            logger.info(f"✓ Categorized as: {result['category']} (confidence: {result['confidence']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error categorizing transaction: {e}")
            return None
    
    def categorize_batch(
        self,
        transactions: List[Dict]
    ) -> List[Dict]:
        """
        Categorize multiple transactions
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of transactions with categories added
        """
        categorized = []
        
        for transaction in transactions:
            category_data = self.categorize_transaction(transaction)
            
            if category_data:
                transaction['category'] = category_data['category']
                transaction['sub_category'] = category_data.get('sub_category')
                transaction['category_confidence'] = category_data.get('confidence', 1.0)
            else:
                transaction['category'] = 'Others'
                transaction['sub_category'] = None
                transaction['category_confidence'] = 0.5
            
            categorized.append(transaction)
        
        logger.info(f"✓ Categorized {len(categorized)} transactions")
        return categorized


# Singleton instance
_categorizer: Optional[TransactionCategorizer] = None


def get_categorizer() -> TransactionCategorizer:
    """Get singleton instance of TransactionCategorizer"""
    global _categorizer
    if _categorizer is None:
        _categorizer = TransactionCategorizer()
    return _categorizer


if __name__ == "__main__":
    # Quick test
    categorizer = get_categorizer()
    
    test_transaction = {
        'amount': 250.50,
        'transaction_type': 'debit',
        'to': 'Swiggy (paytm@swiggy)',
        'description': 'Food delivery'
    }
    
    result = categorizer.categorize_transaction(test_transaction)
    print(f"Category: {result}")