"""Stage Registry - Self-registration system for pipeline stages"""
from typing import Dict, Type, Callable, Any, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class StageRegistry:
    """Central registry for pipeline stages"""
    
    def __init__(self):
        self._stages: Dict[str, Type] = {}
        self._hooks: Dict[str, list] = {}
        
    def register(self, name: str):
        """Decorator to register a stage class"""
        def decorator(cls: Type) -> Type:
            self._stages[name] = cls
            logger.debug(f"Registered stage: {name}")
            return cls
        return decorator
        
    def get(self, name: str) -> Optional[Type]:
        """Get a registered stage by name"""
        return self._stages.get(name)
        
    def list_stages(self) -> list:
        """List all registered stage names"""
        return list(self._stages.keys())
        
    def create(self, name: str, *args, **kwargs) -> Any:
        """Create an instance of a registered stage"""
        stage_class = self.get(name)
        if stage_class is None:
            raise KeyError(f"Stage '{name}' not found in registry")
        return stage_class(*args, **kwargs)


class HookRegistry:
    """Registry for pipeline hooks"""
    
    def __init__(self):
        self._hooks: Dict[str, list] = {}
        
    def register(self, hook_point: str):
        """Decorator to register a hook function"""
        def decorator(func: Callable) -> Callable:
            if hook_point not in self._hooks:
                self._hooks[hook_point] = []
            self._hooks[hook_point].append(func)
            logger.debug(f"Registered hook for '{hook_point}': {func.__name__}")
            return func
        return decorator
        
    async def execute(self, hook_point: str, context: Any) -> Any:
        """Execute all hooks for a given point"""
        hooks = self._hooks.get(hook_point, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    context = await hook(context)
                else:
                    context = hook(context)
            except Exception as e:
                logger.error(f"Hook '{hook.__name__}' failed: {e}")
        return context
        
    def list_hooks(self, hook_point: Optional[str] = None) -> list:
        """List registered hooks"""
        if hook_point:
            return self._hooks.get(hook_point, [])
        return list(self._hooks.keys())


# Global registries
stage_registry = StageRegistry()
hook_registry = HookRegistry()