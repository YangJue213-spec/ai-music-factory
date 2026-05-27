"""Base Stage - Base class for all pipeline stages"""
from core.pipeline import Stage, StageContext
from typing import Dict, Any, Optional


class BaseStage(Stage):
    """Base class for all pipeline stages with common functionality"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        super().__init__(name, config)
        self.config = config or {}
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default"""
        return self.config.get(key, default)
        
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
        
    def is_enabled(self) -> bool:
        """Check if stage is enabled"""
        return self.config.get("enabled", True)