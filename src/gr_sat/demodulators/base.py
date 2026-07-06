from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

class BaseDemodulator(ABC):
    @abstractmethod
    def demodulate(self, iq_path: Path) -> List[bytes]:
        """Demodulate raw IQ file and return decoded AX.25 frame bytes.

        Args:
            iq_path: Path to the raw IQ file (interleaved int16).

        Returns:
            List of decoded unique, valid AX.25 frame bytes.
        """
        pass
