import time
import logging
from typing import Dict, Callable, Any

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Thread-safe, lightweight Circuit Breaker implementation for managing 
    external dependencies (LLMs, Job APIs, database connections).
    """
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failure_count = 0
        self.last_state_change = time.time()

    def allow_request(self) -> bool:
        """Determines if the request should be allowed or failed-fast."""
        now = time.time()
        
        if self.state == "OPEN":
            # Check if cooldown recovery timeout has elapsed
            if now - self.last_state_change > self.recovery_timeout:
                logger.info(f"[CIRCUIT BREAKER] {self.name} cooldown elapsed. Transitioning OPEN -> HALF-OPEN.")
                self.state = "HALF-OPEN"
                self.last_state_change = now
                return True
            return False
            
        return True

    def record_success(self):
        """Records a successful operation, resetting the breaker."""
        self.failure_count = 0
        if self.state != "CLOSED":
            logger.info(f"[CIRCUIT BREAKER] {self.name} call succeeded. Closing circuit breaker.")
            self.state = "CLOSED"
            self.last_state_change = time.time()

    def record_failure(self):
        """Records a failed operation, potentially opening the breaker."""
        self.failure_count += 1
        now = time.time()
        logger.warning(f"[CIRCUIT BREAKER] {self.name} failed (count: {self.failure_count}/{self.failure_threshold})")
        
        if self.state in ["CLOSED", "HALF-OPEN"] and self.failure_count >= self.failure_threshold:
            logger.error(f"[CIRCUIT BREAKER] {self.name} exceeded failure threshold. Opening circuit breaker.")
            self.state = "OPEN"
            self.last_state_change = now

# Registry for all application circuit breakers
CIRCUIT_REGISTRY: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Helper to fetch or register a circuit breaker."""
    if name not in CIRCUIT_REGISTRY:
        CIRCUIT_REGISTRY[name] = CircuitBreaker(name, **kwargs)
    return CIRCUIT_REGISTRY[name]
