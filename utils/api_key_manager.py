"""
API Key Manager - Handles automatic rotation of API keys when rate limits are hit
"""
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages multiple API keys with automatic rotation on rate limit"""
    
    def __init__(self):
        # Load all API keys from Streamlit secrets or environment
        self.api_keys = []
        
        # Try Streamlit secrets first (for cloud deployment)
        try:
            import streamlit as st
            
            if hasattr(st, 'secrets') and len(st.secrets) > 0:
                logger.info("🔍 Checking Streamlit secrets for API keys...")
                
                # Try direct access to GROQ_API_KEY_1, GROQ_API_KEY_2, etc.
                for i in range(1, 10):
                    key_name = f"GROQ_API_KEY_{i}"
                    try:
                        key = st.secrets[key_name]
                        if key and key != "your_first_api_key_here":
                            self.api_keys.append(key)
                            logger.info(f"✅ Loaded {key_name} from Streamlit secrets")
                    except KeyError:
                        pass  # Key doesn't exist
                
                if not self.api_keys:
                    logger.warning("⚠️ No API keys found in Streamlit secrets")
            else:
                logger.info("Streamlit secrets not available, using environment variables")
                
        except ImportError:
            logger.info("Streamlit not imported, using environment variables")
        except Exception as e:
            logger.warning(f"Error accessing Streamlit secrets: {e}")
        
        # Fallback to environment variables (for local development)
        if not self.api_keys:
            logger.info("🔍 Checking environment variables for API keys...")
            for i in range(1, 10):
                key = os.getenv(f"GROQ_API_KEY_{i}")
                if key:
                    self.api_keys.append(key)
                    logger.info(f"✅ Loaded API key #{i} from environment")
        
        # Last resort: single key
        if not self.api_keys:
            single_key = os.getenv("GROQ_API_KEY")
            if single_key:
                self.api_keys.append(single_key)
                logger.info("✅ Loaded single API key from GROQ_API_KEY")
        
        self.current_index = 0
        
        if self.api_keys:
            logger.info(f"🎉 Successfully loaded {len(self.api_keys)} API key(s) for rotation")
        else:
            logger.error("❌ NO API KEYS FOUND!")
            logger.error("For Streamlit Cloud: Add GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in Settings → Secrets")
            logger.error("For local: Add them to .env file")
    
    def get_current_key(self):
        """Get the current API key"""
        if not self.api_keys:
            raise ValueError("No API keys configured!")
        return self.api_keys[self.current_index]
    
    def rotate_to_next(self):
        """Rotate to the next API key in circular fashion"""
        if len(self.api_keys) <= 1:
            logger.warning("⚠️ Only 1 API key available, cannot rotate")
            return self.api_keys[0] if self.api_keys else None
        
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        logger.info(f"🔄 Rotating API key: Key #{old_index + 1} → Key #{self.current_index + 1}")
        return self.api_keys[self.current_index]
    
    def get_key_number(self):
        """Get current key number (1-indexed)"""
        return self.current_index + 1
    
    def get_total_keys(self):
        """Get total number of keys"""
        return len(self.api_keys)


# Global instance
_api_key_manager = None

def get_api_key_manager():
    """Get or create the global API key manager"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
