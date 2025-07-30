"""Security manager for API keys and authentication secrets only."""
import asyncio
import logging
from typing import Optional, Dict
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError

#from src.utils.log_config import get_logger

# Use standard logger instead of custom one to avoid circular import
logger = logging.getLogger(__name__)

class SecurityManager:
    """Handles ONLY authentication secrets - not configuration."""
    
    def __init__(self, config):
        self.config = config
        self._secret_client: Optional[SecretClient] = None
        self._secret_cache: Dict[str, str] = {}
        self._initialization_error: Optional[Exception] = None  # Track init errors
    
    async def initialize(self) -> None:
        """Initialize Key Vault connection only when secrets are needed."""
        if not self.config.use_azure_key_vault:
            logger.info("Azure Key Vault disabled, skipping initialization")
            return
    
        if not self.config.azure_key_vault_name:
            raise ValueError("Azure Key Vault name not configured")
        
        if not self.config.azure_key_vault_name:
            raise ValueError("Azure Key Vault name not configured")
        
        logger.info(f"Initializing Key Vault connection to: {self.config.azure_key_vault_name}")
            
        # Try to create credential
        credential = DefaultAzureCredential()
        logger.info("DefaultAzureCredential created successfully")
            
        # Build vault URL
        vault_url = f"https://{self.config.azure_key_vault_name}.vault.azure.net/"
        logger.info(f"Connecting to Key Vault URL: {vault_url}")
            
        # Create client
        self._secret_client = SecretClient(vault_url=vault_url, credential=credential)
        logger.info("SecretClient created successfully")
            
        # Test the connection by trying to list secrets (just to verify access)
        # try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: list(self._secret_client.list_properties_of_secrets())
        )
        logger.info(f"✅ Successfully connected to Key Vault: {self.config.azure_key_vault_name}")
  
    async def get_secret(self, secret_name: str) -> str:
        """Get authentication secret from Key Vault."""
        
        if not self._secret_client:
            raise RuntimeError("Key Vault client not initialized - call initialize() first")
        
        # Check cache first
        if secret_name in self._secret_cache:
            logger.info(f"Retrieved cached secret: {secret_name}")
            return self._secret_cache[secret_name]
        
        # try:
        logger.info(f"Retrieving secret '{secret_name}' from Key Vault")
        loop = asyncio.get_event_loop()
        secret = await loop.run_in_executor(
            None,
            lambda: self._secret_client.get_secret(secret_name)
        )
        
        # Cache the secret
        self._secret_cache[secret_name] = secret.value
        logger.info(f"✅ Successfully retrieved secret: {secret_name}")
        return secret.value