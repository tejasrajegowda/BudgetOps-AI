"""
Supabase Client
Wrapper for Supabase database operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from supabase import create_client, Client
from utils.env_loader import get_env_loader
from utils.logger import logger


class SupabaseClient:
    """Wrapper for Supabase database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        config = get_env_loader().get_config()
        
        self.url = config["supabase_url"]
        self.key = config["supabase_key"]
        
        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase client initialized")
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection successful
        """
        try:
            # Try a simple query
            result = self.client.table('users').select('id').limit(1).execute()
            logger.success("✓ Supabase connection successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection failed: {e}")
            return False
    
    # ============= TRANSACTIONS =============
    
    def insert_transaction(self, transaction_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Insert a transaction record
        
        Args:
            transaction_data: Transaction data dictionary
            
        Returns:
            Inserted record or None if failed
        """
        try:
            # Prepare data
            data = {
                'amount': transaction_data.get('amount'),
                'transaction_type': transaction_data.get('transaction_type'),
                'card': transaction_data.get('card'),
                'to_merchant': transaction_data.get('to'),
                'transaction_reference_number': transaction_data.get('transaction_reference_number'),
                'description': transaction_data.get('description'),
                'transaction_date': transaction_data.get('date'),
                'transaction_timestamp': transaction_data.get('timestamp'),
                'email_id': transaction_data.get('email_id'),
                'email_subject': transaction_data.get('email_subject'),
                'email_date': transaction_data.get('email_date'),
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Insert
            result = self.client.table('transactions').insert(data).execute()
            
            if result.data:
                logger.success(f"✓ Inserted transaction: {data.get('amount')} {data.get('transaction_type')}")
                return result.data[0]
            else:
                logger.error("Failed to insert transaction")
                return None
                
        except Exception as e:
            logger.error(f"Error inserting transaction: {e}")
            return None
    
    def insert_transactions_batch(self, transactions: List[Dict[str, Any]]) -> List[Dict]:
        """
        Insert multiple transactions
        
        Args:
            transactions: List of transaction data dictionaries
            
        Returns:
            List of inserted records
        """
        inserted = []
        
        for transaction in transactions:
            result = self.insert_transaction(transaction)
            if result:
                inserted.append(result)
        
        logger.info(f"✓ Inserted {len(inserted)}/{len(transactions)} transactions")
        return inserted
    
    def get_transactions(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get transactions with filters
        
        Args:
            user_id: Filter by user ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            transaction_type: Filter by 'credit' or 'debit'
            limit: Maximum number of records
            
        Returns:
            List of transaction records
        """
        try:
            query = self.client.table('transactions').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            if start_date:
                query = query.gte('transaction_date', start_date)
            
            if end_date:
                query = query.lte('transaction_date', end_date)
            
            if transaction_type:
                query = query.eq('transaction_type', transaction_type)
            
            query = query.order('transaction_date', desc=True).limit(limit)
            
            result = query.execute()
            
            logger.info(f"✓ Retrieved {len(result.data)} transactions")
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def get_transaction_by_email_id(self, email_id: str) -> Optional[Dict]:
        """
        Get transaction by email ID (to avoid duplicates)
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            Transaction record or None
        """
        try:
            result = self.client.table('transactions')\
                .select('*')\
                .eq('email_id', email_id)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting transaction by email_id: {e}")
            return None
    
    def update_transaction(self, transaction_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update transaction record
        
        Args:
            transaction_id: Transaction UUID
            updates: Fields to update
            
        Returns:
            True if successful
        """
        try:
            result = self.client.table('transactions')\
                .update(updates)\
                .eq('id', transaction_id)\
                .execute()
            
            if result.data:
                logger.info(f"✓ Updated transaction {transaction_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    def delete_transaction(self, transaction_id: str) -> bool:
        """
        Delete transaction
        
        Args:
            transaction_id: Transaction UUID
            
        Returns:
            True if successful
        """
        try:
            result = self.client.table('transactions')\
                .delete()\
                .eq('id', transaction_id)\
                .execute()
            
            logger.info(f"✓ Deleted transaction {transaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False
    
    # ============= ANALYTICS =============
    
    def get_daily_summary(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get daily spending summary
        
        Args:
            target_date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Summary dictionary with totals
        """
        if not target_date:
            target_date = date.today().isoformat()
        
        try:
            transactions = self.get_transactions(
                start_date=target_date,
                end_date=target_date
            )
            
            total_debit = sum(
                t['amount'] for t in transactions 
                if t['transaction_type'] == 'debit'
            )
            
            total_credit = sum(
                t['amount'] for t in transactions 
                if t['transaction_type'] == 'credit'
            )
            
            summary = {
                'date': target_date,
                'total_spent': total_debit,
                'total_earned': total_credit,
                'net': total_credit - total_debit,
                'transaction_count': len(transactions),
                'transactions': transactions
            }
            
            logger.info(f"✓ Daily summary for {target_date}: Spent {total_debit}, Earned {total_credit}")
            return summary
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {}
    
    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly spending summary
        
        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            
        Returns:
            Summary dictionary
        """
        try:
            # Calculate date range
            start_date = f"{year}-{month:02d}-01"
            
            # Get last day of month
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day}"
            
            transactions = self.get_transactions(
                start_date=start_date,
                end_date=end_date,
                limit=1000
            )
            
            total_debit = sum(
                t['amount'] for t in transactions 
                if t['transaction_type'] == 'debit'
            )
            
            total_credit = sum(
                t['amount'] for t in transactions 
                if t['transaction_type'] == 'credit'
            )
            
            summary = {
                'year': year,
                'month': month,
                'total_spent': total_debit,
                'total_earned': total_credit,
                'net': total_credit - total_debit,
                'transaction_count': len(transactions),
                'average_daily_spend': total_debit / last_day if last_day else 0
            }
            
            logger.info(f"✓ Monthly summary for {year}-{month}: Spent {total_debit}")
            return summary
            
        except Exception as e:
            logger.error(f"Error getting monthly summary: {e}")
            return {}
    
    # ============= USERS =============
    
    def get_or_create_user(self, email: str) -> Optional[Dict]:
        """
        Get user or create if doesn't exist
        
        Args:
            email: User email
            
        Returns:
            User record
        """
        try:
            # Try to get existing user
            result = self.client.table('users')\
                .select('*')\
                .eq('email', email)\
                .execute()
            
            if result.data:
                return result.data[0]
            
            # Create new user
            result = self.client.table('users')\
                .insert({'email': email, 'gmail_connected': True})\
                .execute()
            
            if result.data:
                logger.info(f"✓ Created new user: {email}")
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error with user operations: {e}")
            return None


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get singleton instance of SupabaseClient"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client


if __name__ == "__main__":
    # Quick test
    client = get_supabase_client()
    client.test_connection()
    
    # Get today's summary
    summary = client.get_daily_summary()
    print(f"Today's spending: {summary.get('total_spent', 0)} INR")