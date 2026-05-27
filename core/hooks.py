"""Hook System - Extension points for pipeline"""
import asyncio
import logging
from typing import Callable, Any, List

logger = logging.getLogger(__name__)


class HookManager:
    """Manages lifecycle hooks for the pipeline"""
    
    def __init__(self):
        self._hooks: dict = {}
        
    def register(self, hook_point: str) -> Callable:
        """Decorator to register a hook function"""
        def decorator(func: Callable) -> Callable:
            if hook_point not in self._hooks:
                self._hooks[hook_point] = []
            self._hooks[hook_point].append(func)
            logger.debug(f"Registered hook '{func.__name__}' for '{hook_point}'")
            return func
        return decorator
        
    def unregister(self, hook_point: str, func: Callable) -> bool:
        """Unregister a hook function"""
        if hook_point in self._hooks and func in self._hooks[hook_point]:
            self._hooks[hook_point].remove(func)
            return True
        return False
        
    async def execute(self, hook_point: str, context: Any) -> Any:
        """Execute all hooks for a given point"""
        hooks = self._hooks.get(hook_point, [])
        if not hooks:
            return context
            
        logger.debug(f"Executing {len(hooks)} hooks for '{hook_point}'")
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(context)
                else:
                    result = hook(context)
                # Allow hooks to modify context
                if result is not None:
                    context = result
            except Exception as e:
                logger.error(f"Hook '{hook.__name__}' for '{hook_point}' failed: {e}")
                # Continue with other hooks even if one fails
        return context
        
    def list_hooks(self, hook_point: str = None) -> List[str]:
        """List registered hooks"""
        if hook_point:
            hooks = self._hooks.get(hook_point, [])
            return [h.__name__ for h in hooks]
        return list(self._hooks.keys())


# Global hook manager instance
hook_manager = HookManager()