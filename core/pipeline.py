"""Pipeline Engine - Orchestrates the execution of stages"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StageContext:
    """Context object passed between stages"""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    skipped: bool = False
    
    def get(self, key: str, default=None) -> Any:
        """Get data by key"""
        return self.data.get(key, default)
        
    def set(self, key: str, value: Any) -> "StageContext":
        """Set data by key"""
        self.data[key] = value
        return self
        
    def get_metadata(self, key: str, default=None) -> Any:
        """Get metadata by key"""
        return self.metadata.get(key, default)
        
    def set_metadata(self, key: str, value: Any) -> "StageContext":
        """Set metadata by key"""
        self.metadata[key] = value
        return self
        
    def add_error(self, error: str) -> "StageContext":
        """Add error message"""
        self.errors.append(error)
        return self
        
    def copy(self) -> "StageContext":
        """Create a copy of the context"""
        return StageContext(
            data=self.data.copy(),
            metadata=self.metadata.copy(),
            errors=self.errors.copy(),
            skipped=self.skipped
        )


class Stage:
    """Base class for pipeline stages"""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        
    async def execute(self, context: StageContext) -> StageContext:
        """Execute the stage - must be implemented by subclasses"""
        raise NotImplementedError(f"Stage {self.name} must implement execute()")
        
    async def run(self, context: StageContext) -> StageContext:
        """Run the stage with error handling"""
        if not self.enabled:
            logger.info(f"Stage '{self.name}' is disabled, skipping")
            context.skipped = True
            return context
            
        logger.info(f"Executing stage: {self.name}")
        try:
            result = await self.execute(context)
            logger.info(f"Stage '{self.name}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"Stage '{self.name}' failed: {e}")
            context.add_error(f"{self.name}: {str(e)}")
            raise


class Pipeline:
    """Pipeline orchestrator"""
    
    def __init__(self, state_manager=None):
        self.stages: List[Stage] = []
        self.state_manager = state_manager
        self._context = StageContext()
        
    def add_stage(self, stage: Stage) -> "Pipeline":
        """Add a stage to the pipeline"""
        self.stages.append(stage)
        return self
        
    async def execute(self, initial_data: Optional[Dict] = None) -> StageContext:
        """Execute all stages in sequence"""
        context = StageContext()
        if initial_data:
            context.data.update(initial_data)
            
        for stage in self.stages:
            try:
                context = await stage.run(context)
            except Exception as e:
                logger.error(f"Pipeline stopped at stage '{stage.name}': {e}")
                # Try to execute error hooks
                try:
                    from .registry import hook_manager
                    context = await hook_manager.execute("on_error", context)
                except Exception as hook_error:
                    logger.error(f"Error hook failed: {hook_error}")
                raise PipelineError(f"Pipeline failed at stage '{stage.name}': {e}")
                
        return context
        
    async def execute_parallel(self, items: List[Dict], 
                              max_concurrency: int = 5) -> List[StageContext]:
        """Execute pipeline for multiple items in parallel with concurrency limit"""
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_item(item: Dict) -> StageContext:
            async with semaphore:
                context = StageContext(data=item)
                for stage in self.stages:
                    try:
                        context = await stage.run(context)
                    except Exception as e:
                        logger.error(f"Item failed at stage '{stage.name}': {e}")
                        context.add_error(f"{stage.name}: {str(e)}")
                        break
                return context
                
        tasks = [process_item(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    def get_stage(self, name: str) -> Optional[Stage]:
        """Get a stage by name"""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None


class PipelineError(Exception):
    """Pipeline execution error"""
    pass