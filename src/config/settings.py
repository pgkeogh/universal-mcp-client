"""Universal MCP Client configuration with enterprise security."""
import os
import sys
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Add src to Python path for absolute imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load .env for non-sensitive configuration
load_dotenv()

@dataclass
class UniversalMCPConfig:
    """Universal MCP Client configuration - secrets always from Key Vault."""
    
    # OpenAI Configuration
    openai_model: str = "gpt-4o-mini"
    max_tokens: int = 5000
    temperature: float = 0.7
    
    # Connection Configuration
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Universal Client Configuration
    auto_discover_servers: bool = True
    max_concurrent_servers: int = 5
    server_profile_cache_ttl: int = 3600  # 1 hour
    
    # Application Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Azure Key Vault Configuration
    azure_key_vault_name: Optional[str] = None
    use_azure_key_vault: bool = False
    
    # Lazy-loaded security manager
    _security_manager: Optional['SecurityManager'] = None
    
    @classmethod
    def create(cls) -> 'UniversalMCPConfig':
        """Create configuration for universal MCP client."""
        config = cls()
        
        # Load configuration from environment
        config.openai_model = os.getenv('OPENAI_MODEL', config.openai_model)
        config.max_tokens = int(os.getenv('MAX_TOKENS', str(config.max_tokens)))
        config.temperature = float(os.getenv('TEMPERATURE', str(config.temperature)))
        
        config.connection_timeout = int(os.getenv('CONNECTION_TIMEOUT', str(config.connection_timeout)))
        config.retry_attempts = int(os.getenv('RETRY_ATTEMPTS', str(config.retry_attempts)))
        config.log_level = os.getenv('LOG_LEVEL', config.log_level)
        
        # Universal client settings
        config.auto_discover_servers = os.getenv('AUTO_DISCOVER_SERVERS', 'true').lower() == 'true'
        config.max_concurrent_servers = int(os.getenv('MAX_CONCURRENT_SERVERS', str(config.max_concurrent_servers)))
        
        # Azure Key Vault setup
        config.azure_key_vault_name = os.getenv('AZURE_KEY_VAULT_NAME')
        config.use_azure_key_vault = bool(config.azure_key_vault_name)
        
        return config
    
    async def get_openai_api_key(self) -> str:
        """Get OpenAI API key from Key Vault."""
        if not self._security_manager:
            from src.config.security import SecurityManager
            self._security_manager = SecurityManager(self)
            await self._security_manager.initialize()
        
        return await self._security_manager.get_secret('openai-api-key')
    
    def validate(self) -> None:
        """Validate configuration."""
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        
        if not (0 <= self.temperature <= 2):
            raise ValueError("temperature must be between 0 and 2")
        
        if not self.azure_key_vault_name:
            raise ValueError("AZURE_KEY_VAULT_NAME is required for enterprise security")