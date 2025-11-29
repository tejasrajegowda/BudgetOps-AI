"""
Insights Generation Chain
Generates AI-powered daily spending insights
"""

from typing import Dict, List, Optional
from datetime import date, datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

from utils.env_loader import get_env_loader
from utils.logger import logger


class InsightGenerator:
    """Generate spending insights using AI"""
    
    def __init__(self):
        """Initialize insight generator with Gemini"""
        config = get_env_loader().get_config()
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=config["google_api_key"],
            temperature=0.7,  # Higher temperature for creative insights
        )
        
        self.daily_prompt = self._create_daily_prompt()
        self.monthly_prompt = self._create_monthly_prompt()
        
        logger.info("Insight generator initialized")
    
    def _create_daily_prompt(self) -> ChatPromptTemplate:
        """Create prompt for daily insights"""
        
        template = """You are a friendly personal finance assistant. Generate a concise daily spending summary.

Date: {date}

Spending Summary:
- Total Spent: ₹{total_spent}
- Total Earned: ₹{total_earned}
- Net: ₹{net}
- Number of Transactions: {transaction_count}

Top Spending Categories:
{category_breakdown}

Transaction Details:
{transactions_summary}

Generate a friendly 2-3 sentence daily insight that:
1. Summarizes today's spending in a conversational tone
2. Highlights the main spending category
3. Gives a quick tip or observation

Keep it brief, positive, and actionable."""
        
        return ChatPromptTemplate.from_template(template)
    
    def _create_monthly_prompt(self) -> ChatPromptTemplate:
        """Create prompt for monthly insights"""
        
        template = """You are a personal finance advisor. Generate a monthly spending analysis.

Month: {month} {year}

Monthly Summary:
- Total Spent: ₹{total_spent}
- Total Earned: ₹{total_earned}
- Net: ₹{net}
- Average Daily Spend: ₹{avg_daily}
- Number of Transactions: {transaction_count}

Category Breakdown:
{category_breakdown}

Generate a comprehensive 4-5 sentence monthly insight that:
1. Summarizes overall spending patterns
2. Highlights top spending categories
3. Identifies any concerning trends
4. Provides actionable recommendations for next month

Be specific with numbers and constructive with feedback."""
        
        return ChatPromptTemplate.from_template(template)
    
    def generate_daily_insight(
        self,
        summary: Dict,
        transactions: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate daily spending insight
        
        Args:
            summary: Daily summary dict from Supabase
            transactions: Optional list of transactions
            
        Returns:
            AI-generated insight text
        """
        try:
            # Calculate category breakdown
            if transactions:
                category_totals = {}
                for t in transactions:
                    if t.get('transaction_type') == 'debit':
                        cat = t.get('category', 'Others')
                        category_totals[cat] = category_totals.get(cat, 0) + t.get('amount', 0)
                
                category_breakdown = "\n".join([
                    f"- {cat}: ₹{amount:.2f}"
                    for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
                ])
                
                # Create transaction summary
                trans_summary = "\n".join([
                    f"- ₹{t.get('amount', 0)} to {t.get('to_merchant', 'Unknown')[:30]}"
                    for t in transactions[:5]  # Top 5 transactions
                    if t.get('transaction_type') == 'debit'
                ])
            else:
                category_breakdown = "No category data available"
                trans_summary = "No transactions available"
            
            # Format prompt
            formatted_prompt = self.daily_prompt.format(
                date=summary.get('date', date.today().isoformat()),
                total_spent=summary.get('total_spent', 0),
                total_earned=summary.get('total_earned', 0),
                net=summary.get('net', 0),
                transaction_count=summary.get('transaction_count', 0),
                category_breakdown=category_breakdown,
                transactions_summary=trans_summary
            )
            
            # Generate insight
            response = self.llm.invoke(formatted_prompt)
            insight = response.content.strip()
            
            logger.success(f"✓ Generated daily insight ({len(insight)} chars)")
            return insight
            
        except Exception as e:
            logger.error(f"Error generating daily insight: {e}")
            return f"Today you spent ₹{summary.get('total_spent', 0)} across {summary.get('transaction_count', 0)} transactions."
    
    def generate_monthly_insight(
        self,
        summary: Dict,
        category_breakdown: Optional[Dict] = None
    ) -> str:
        """
        Generate monthly spending insight
        
        Args:
            summary: Monthly summary dict
            category_breakdown: Category-wise spending
            
        Returns:
            AI-generated insight text
        """
        try:
            # Format category breakdown
            if category_breakdown:
                cat_text = "\n".join([
                    f"- {cat}: ₹{amount:.2f}"
                    for cat, amount in sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
                ])
            else:
                cat_text = "No category data available"
            
            # Format prompt
            formatted_prompt = self.monthly_prompt.format(
                month=summary.get('month', date.today().month),
                year=summary.get('year', date.today().year),
                total_spent=summary.get('total_spent', 0),
                total_earned=summary.get('total_earned', 0),
                net=summary.get('net', 0),
                avg_daily=summary.get('average_daily_spend', 0),
                transaction_count=summary.get('transaction_count', 0),
                category_breakdown=cat_text
            )
            
            # Generate insight
            response = self.llm.invoke(formatted_prompt)
            insight = response.content.strip()
            
            logger.success(f"✓ Generated monthly insight ({len(insight)} chars)")
            return insight
            
        except Exception as e:
            logger.error(f"Error generating monthly insight: {e}")
            return f"This month you spent ₹{summary.get('total_spent', 0)}."


# Singleton
_insight_generator: Optional[InsightGenerator] = None


def get_insight_generator() -> InsightGenerator:
    """Get singleton instance"""
    global _insight_generator
    if _insight_generator is None:
        _insight_generator = InsightGenerator()
    return _insight_generator


if __name__ == "__main__":
    generator = get_insight_generator()
    
    test_summary = {
        'date': '2025-10-30',
        'total_spent': 500,
        'total_earned': 0,
        'net': -500,
        'transaction_count': 3
    }
    
    insight = generator.generate_daily_insight(test_summary)
    print(f"Daily Insight:\n{insight}")