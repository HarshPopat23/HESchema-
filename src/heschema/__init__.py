"""HESchema: validation decisions and reproducible schema-effect experiments."""

__version__ = "0.1.0"

from .contracts import Contract
from .guard import ContractViolationError, guard

__all__ = ["guard", "ContractViolationError", "Contract"]
