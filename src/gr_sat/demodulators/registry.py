from typing import Dict, Type, Optional
from gr_sat.demodulators.base import BaseDemodulator

class DemodulatorRegistry:
    _registry: Dict[int, Type[BaseDemodulator]] = {}

    @classmethod
    def register(cls, norad_id: int):
        """Decorator to register a demodulator class for a specific satellite."""
        def decorator(subclass: Type[BaseDemodulator]):
            cls._registry[norad_id] = subclass
            return subclass
        return decorator

    @classmethod
    def get(cls, norad_id: int) -> Optional[Type[BaseDemodulator]]:
        """Get the registered demodulator class for a satellite."""
        return cls._registry.get(norad_id)

    @classmethod
    def list_registered(cls) -> Dict[int, Type[BaseDemodulator]]:
        """List all registered demodulator classes."""
        return cls._registry.copy()
