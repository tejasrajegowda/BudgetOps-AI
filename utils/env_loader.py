"""
Environment Configuration Loader
Loads and validates environment variables from .env file
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from loguru import logger


class EnvLoader:
    """Loads and validates environment variables"""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize environment loader
        
        Args:
            env_file: Path to .env file (default: ".env")
        """
        self.env_file = env_file
        self.config: Dict[str, Any] = {}
        self._load_env()
    
    def _load_env(self) -> None:
        """Load environment variables from .env file"""
        env_path = Path(self.env_file)
        
        if not env_path.exists():
            raise FileNotFoundError(
                f"Environment file '{self.env_file}' not found. "
                f"Please create it from .env.example"
            )
        
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded environment variables from {self.env_file}")
    
    def validate_credentials(self) -> Dict[str, bool]:
        """
        Validate all required credentials are present
        
        Returns:
            Dictionary with validation status for each service
        """
        validation_results = {
            "gmail": self._validate_gmail(),
            "supabase": self._validate_supabase(),
            "gemini": self._validate_gemini(),
            "app_config": self._validate_app_config()
        }
        
        return validation_results
    
    def _validate_gmail(self) -> bool:
        """Validate Gmail API credentials"""
        required = [
            "GMAIL_CLIENT_ID",
            "GMAIL_CLIENT_SECRET",
            "GMAIL_REDIRECT_URI",
            "GMAIL_SCOPES"
        ]
        
        missing = [key for key in required if not os.getenv(key)]
        
        if missing:
            logger.error(f"Missing Gmail credentials: {', '.join(missing)}")
            return False
        
        logger.success("✓ Gmail credentials validated")
        return True
    
    def _validate_supabase(self) -> bool:
        """Validate Supabase credentials"""
        required = ["SUPABASE_URL", "SUPABASE_KEY"]
        
        missing = [key for key in required if not os.getenv(key)]
        
        if missing:
            logger.error(f"Missing Supabase credentials: {', '.join(missing)}")
            return False
        
        logger.success("✓ Supabase credentials validated")
        return True
    
    def _validate_gemini(self) -> bool:
        """Validate Google Gemini API credentials"""
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            logger.error("Missing GOOGLE_API_KEY")
            return False
        
        logger.success("✓ Gemini API credentials validated")
        return True
    
    def _validate_app_config(self) -> bool:
        """Validate general application configuration"""
        required = ["APP_NAME", "TIMEZONE", "DAILY_INSIGHT_TIME"]
        
        missing = [key for key in required if not os.getenv(key)]
        
        if missing:
            logger.warning(f"Missing app config (using defaults): {', '.join(missing)}")
            return False
        
        logger.success("✓ Application config validated")
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get all configuration as a dictionary
        
        Returns:
            Dictionary containing all environment variables
        """
        return {
            # Gmail
            "gmail_client_id": os.getenv("GMAIL_CLIENT_ID"),
            "gmail_client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
            "gmail_redirect_uri": os.getenv("GMAIL_REDIRECT_URI"),
            "gmail_scopes": os.getenv("GMAIL_SCOPES", "").split(","),
            
            # Supabase
            "supabase_url": os.getenv("SUPABASE_URL"),
            "supabase_key": os.getenv("SUPABASE_KEY"),
            
            # Gemini
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            
            # App Settings
            "app_name": os.getenv("APP_NAME", "BudgetOps AI"),
            "app_version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": int(os.getenv("API_PORT", "8000")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "timezone": os.getenv("TIMEZONE", "Asia/Kolkata"),
            "daily_insight_time": os.getenv("DAILY_INSIGHT_TIME", "23:59"),
        }
    
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Get a specific configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self.config:
            self.config = self.get_config()
        
        return self.config.get(key, default)
    
    def print_summary(self) -> None:
        """Print a summary of loaded configuration (without sensitive data)"""
        logger.info("=" * 50)
        logger.info("Environment Configuration Summary")
        logger.info("=" * 50)
        
        validation = self.validate_credentials()
        
        for service, is_valid in validation.items():
            status = "✓ VALID" if is_valid else "✗ INVALID"
            logger.info(f"{service.upper():15} : {status}")
        
        config = self.get_config()
        logger.info(f"{'App Name':15} : {config['app_name']}")
        logger.info(f"{'Environment':15} : {config['environment']}")
        logger.info(f"{'API Port':15} : {config['api_port']}")
        logger.info(f"{'Timezone':15} : {config['timezone']}")
        logger.info("=" * 50)
        
        all_valid = all(validation.values())
        if all_valid:
            logger.success("All credentials are valid! ✓")
        else:
            logger.error("Some credentials are missing or invalid!")
        
        return all_valid


# Singleton instance
_env_loader: Optional[EnvLoader] = None


def get_env_loader() -> EnvLoader:
    """Get singleton instance of EnvLoader"""
    global _env_loader
    if _env_loader is None:
        _env_loader = EnvLoader()
    return _env_loader


# Convenience function
def load_and_validate() -> bool:
    """
    Load environment and validate all credentials
    
    Returns:
        True if all credentials are valid, False otherwise
    """
    loader = get_env_loader()
    return loader.print_summary()


if __name__ == "__main__":
    # Quick test
    load_and_validate()