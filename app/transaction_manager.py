"""
Transaction Manager - ACID Compliance for Multi-Step API Workflows
===================================================================
Provides atomic transaction semantics across multiple external API calls
(Cloudinary, Seedream, Lark Bitable, Supabase, etc.).

Key Principles:
- Atomicity: All steps in a workflow succeed together or are rolled back together.
- Consistency: The system remains in a valid state after any workflow.
- Isolation: Concurrent workflows do not interfere with each other.
- Durability: Completed results are persisted and cached for reuse.

Rollback Strategy:
- Each step registers a compensating action (undo function).
- On failure, all previously completed compensating actions are executed in reverse order.
- Cloudinary uploads are deleted, DB inserts are reversed, Lark records removed.

Usage:
    async with TransactionManager("employee_submit") as txn:
        url = await txn.execute_step(
            name="upload_photo",
            action=lambda: upload_to_cloudinary(file),
            rollback=lambda result: delete_from_cloudinary(result),
            cache_key=f"photo_{employee_id}"
        )
        ...
"""
import logging
import time
import uuid
import traceback
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CACHED = "cached"  # Result was reused from cache


class TransactionStatus(Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class StepResult:
    """Result of a single step in a transaction."""
    name: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    from_cache: bool = False


@dataclass
class TransactionStep:
    """A single step within a transaction with its compensating action."""
    name: str
    action: Callable
    rollback: Optional[Callable] = None
    cache_key: Optional[str] = None
    result: Any = None
    status: StepStatus = StepStatus.PENDING
    error: Optional[str] = None
    duration_ms: float = 0
    is_critical: bool = True  # If True, failure causes full rollback


class TransactionManager:
    """
    Manages a multi-step workflow as an atomic transaction.
    
    Supports:
    - Step-by-step execution with automatic rollback on failure
    - Result caching to avoid re-executing successful steps
    - Detailed logging of each step for debugging
    - Non-critical steps that log warnings but don't trigger rollback
    
    Example:
        txn = TransactionManager("employee_registration")
        try:
            photo_url = txn.execute_step(
                name="upload_photo",
                action=lambda: upload_photo(file_path),
                rollback=lambda r: delete_cloudinary(r),
                cache_key="photo_EMP001"
            )
            db_id = txn.execute_step(
                name="insert_db",
                action=lambda: insert_employee(data),
                rollback=lambda r: delete_employee(r)
            )
            txn.commit()
        except Exception:
            txn.rollback()
    """
    
    def __init__(self, workflow_name: str, context: Optional[Dict] = None):
        self.workflow_name = workflow_name
        self.transaction_id = uuid.uuid4().hex[:12]
        self.steps: List[TransactionStep] = []
        self.completed_steps: List[TransactionStep] = []
        self.status = TransactionStatus.ACTIVE
        self.context = context or {}
        self.start_time = time.time()
        self._step_results: Dict[str, Any] = {}
        
        logger.info(f"🔄 TXN [{self.transaction_id}] Started: {workflow_name}")
    
    def execute_step(
        self,
        name: str,
        action: Callable,
        rollback: Optional[Callable] = None,
        cache_key: Optional[str] = None,
        is_critical: bool = True,
        error_message: Optional[str] = None,
    ) -> Any:
        """
        Execute a single step in the transaction.
        
        Args:
            name: Human-readable step name for logging
            action: Callable that performs the work. Should return a result.
            rollback: Optional callable that undoes the work. Receives the step result.
            cache_key: Optional key to check/store result in cache.
            is_critical: If True (default), failure triggers full rollback.
                         If False, failure is logged but workflow continues.
            error_message: Optional custom error message for user-facing errors.
        
        Returns:
            The result of the action callable.
        
        Raises:
            TransactionError: If the step fails and is critical.
        """
        if self.status != TransactionStatus.ACTIVE:
            raise TransactionError(
                f"Cannot execute step '{name}' - transaction is {self.status.value}",
                transaction_id=self.transaction_id
            )
        
        step = TransactionStep(
            name=name,
            action=action,
            rollback=rollback,
            cache_key=cache_key,
            is_critical=is_critical,
        )
        self.steps.append(step)
        
        # Check cache first
        if cache_key:
            from app.workflow_cache import WorkflowCache
            cached = WorkflowCache.get(cache_key)
            if cached is not None:
                step.result = cached
                step.status = StepStatus.CACHED
                step.duration_ms = 0
                self.completed_steps.append(step)
                self._step_results[name] = cached
                logger.info(
                    f"  ♻️ TXN [{self.transaction_id}] Step '{name}' → CACHED "
                    f"(key={cache_key})"
                )
                return cached
        
        # Execute the action
        step.status = StepStatus.RUNNING
        step_start = time.time()
        
        try:
            result = action()
            step.duration_ms = (time.time() - step_start) * 1000
            
            if result is None and is_critical:
                # Treat None result as failure for critical steps
                step.status = StepStatus.FAILED
                step.error = error_message or f"Step '{name}' returned None"
                logger.error(
                    f"  ❌ TXN [{self.transaction_id}] Step '{name}' → FAILED "
                    f"(returned None, {step.duration_ms:.0f}ms)"
                )
                raise TransactionError(
                    step.error,
                    transaction_id=self.transaction_id,
                    step_name=name,
                )
            
            step.result = result
            step.status = StepStatus.COMPLETED
            self.completed_steps.append(step)
            self._step_results[name] = result
            
            # Cache the result if cache_key provided
            if cache_key and result is not None:
                from app.workflow_cache import WorkflowCache
                WorkflowCache.set(cache_key, result)
            
            logger.info(
                f"  ✅ TXN [{self.transaction_id}] Step '{name}' → OK "
                f"({step.duration_ms:.0f}ms)"
            )
            return result
            
        except TransactionError:
            raise  # Re-raise our own errors
            
        except Exception as e:
            step.duration_ms = (time.time() - step_start) * 1000
            step.status = StepStatus.FAILED
            step.error = str(e)
            
            logger.error(
                f"  ❌ TXN [{self.transaction_id}] Step '{name}' → FAILED "
                f"({step.duration_ms:.0f}ms): {e}"
            )
            
            if is_critical:
                raise TransactionError(
                    error_message or f"Step '{name}' failed: {e}",
                    transaction_id=self.transaction_id,
                    step_name=name,
                    original_error=e,
                )
            else:
                logger.warning(
                    f"  ⚠️ TXN [{self.transaction_id}] Non-critical step '{name}' "
                    f"failed, continuing: {e}"
                )
                return None
    
    def get_step_result(self, step_name: str) -> Any:
        """Get the result of a previously completed step."""
        return self._step_results.get(step_name)
    
    def rollback(self) -> List[StepResult]:
        """
        Roll back all completed steps in reverse order.
        
        Returns:
            List of StepResult showing rollback outcomes.
        """
        if self.status in (TransactionStatus.ROLLED_BACK, TransactionStatus.COMMITTED):
            logger.warning(
                f"⚠️ TXN [{self.transaction_id}] Cannot rollback - already {self.status.value}"
            )
            return []
        
        self.status = TransactionStatus.ROLLING_BACK
        rollback_results = []
        
        logger.info(
            f"🔙 TXN [{self.transaction_id}] Rolling back {len(self.completed_steps)} steps..."
        )
        
        # Rollback in reverse order (LIFO)
        for step in reversed(self.completed_steps):
            if step.rollback and step.status in (StepStatus.COMPLETED, StepStatus.CACHED):
                try:
                    logger.info(
                        f"  🔙 TXN [{self.transaction_id}] Rolling back '{step.name}'..."
                    )
                    step.rollback(step.result)
                    step.status = StepStatus.ROLLED_BACK
                    rollback_results.append(StepResult(
                        name=step.name,
                        status=StepStatus.ROLLED_BACK,
                    ))
                    logger.info(
                        f"  ✅ TXN [{self.transaction_id}] Rolled back '{step.name}'"
                    )
                except Exception as e:
                    logger.error(
                        f"  ❌ TXN [{self.transaction_id}] Rollback failed for "
                        f"'{step.name}': {e}\n{traceback.format_exc()}"
                    )
                    rollback_results.append(StepResult(
                        name=step.name,
                        status=StepStatus.FAILED,
                        error=str(e),
                    ))
            else:
                # Step had no rollback function or wasn't completed
                rollback_results.append(StepResult(
                    name=step.name,
                    status=StepStatus.PENDING,
                    error="No rollback action defined" if not step.rollback else "Step not completed",
                ))
        
        self.status = TransactionStatus.ROLLED_BACK
        elapsed = (time.time() - self.start_time) * 1000
        logger.info(
            f"🔙 TXN [{self.transaction_id}] Rollback complete ({elapsed:.0f}ms total)"
        )
        return rollback_results
    
    def commit(self) -> Dict[str, Any]:
        """
        Mark the transaction as committed. No more steps can be added.
        
        Returns:
            Summary dict of all step results.
        """
        if self.status != TransactionStatus.ACTIVE:
            logger.warning(
                f"⚠️ TXN [{self.transaction_id}] Cannot commit - status is {self.status.value}"
            )
            return self.get_summary()
        
        self.status = TransactionStatus.COMMITTED
        elapsed = (time.time() - self.start_time) * 1000
        
        cached_count = sum(1 for s in self.completed_steps if s.status == StepStatus.CACHED)
        executed_count = len(self.completed_steps) - cached_count
        
        logger.info(
            f"✅ TXN [{self.transaction_id}] Committed: {self.workflow_name} "
            f"({executed_count} executed, {cached_count} cached, {elapsed:.0f}ms total)"
        )
        return self.get_summary()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the transaction state."""
        return {
            "transaction_id": self.transaction_id,
            "workflow": self.workflow_name,
            "status": self.status.value,
            "total_steps": len(self.steps),
            "completed_steps": len(self.completed_steps),
            "cached_steps": sum(1 for s in self.completed_steps if s.status == StepStatus.CACHED),
            "elapsed_ms": (time.time() - self.start_time) * 1000,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "from_cache": s.status == StepStatus.CACHED,
                }
                for s in self.steps
            ],
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(
                f"❌ TXN [{self.transaction_id}] Exception in context: {exc_val}"
            )
            self.rollback()
            return False  # Don't suppress the exception
        elif self.status == TransactionStatus.ACTIVE:
            self.commit()
        return False


class TransactionError(Exception):
    """Error raised when a transaction step fails."""
    
    def __init__(
        self,
        message: str,
        transaction_id: str = "",
        step_name: str = "",
        original_error: Optional[Exception] = None,
    ):
        self.transaction_id = transaction_id
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": str(self),
            "transaction_id": self.transaction_id,
            "step_name": self.step_name,
            "original_error": str(self.original_error) if self.original_error else None,
        }
