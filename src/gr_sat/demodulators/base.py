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

    @abstractmethod
    def start_live_stream(self, source_endpoint: str, callback: callable) -> None:
        """Start a real-time GNU Radio flowgraph listening on a ZMQ socket.

        Args:
            source_endpoint: ZMQ connection string (e.g., 'tcp://0.0.0.0:5555')
            callback: Function to invoke with bytes of each decoded valid frame.
        """
        pass

    @abstractmethod
    def stop_live_stream(self) -> None:
        """Stop the currently running live stream flowgraph and clean up resources."""
        pass
