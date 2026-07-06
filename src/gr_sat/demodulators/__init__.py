from gr_sat.demodulators.base import BaseDemodulator
from gr_sat.demodulators.registry import DemodulatorRegistry

# Import subclasses here to trigger decoration/registration on module load
import gr_sat.demodulators.uwe4 as _uwe4
import gr_sat.demodulators.cute as _cute

__all__ = ["BaseDemodulator", "DemodulatorRegistry"]
