import unittest
from pathlib import Path
from gr_sat.demodulators.base import BaseDemodulator
from gr_sat.demodulators.registry import DemodulatorRegistry

# Ensure demodulators are registered
import gr_sat.demodulators  # noqa: F401

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_IQ_PATH = (
    PROJECT_ROOT / "other_components" / "FSKCODE" / "iq_14011420_435599000_57600.raw"
)


class TestDemodulatorRegistry(unittest.TestCase):
    def test_registry_registration(self):
        """Verify that UWE-4 and CUTE demodulators are correctly registered."""
        # UWE-4 (43880)
        demod_cls = DemodulatorRegistry.get(43880)
        self.assertIsNotNone(demod_cls)
        self.assertTrue(issubclass(demod_cls, BaseDemodulator))

        # CUTE (49263)
        cute_cls = DemodulatorRegistry.get(49263)
        self.assertIsNotNone(cute_cls)
        self.assertTrue(issubclass(cute_cls, BaseDemodulator))

    def test_demodulate_sample_file(self):
        """Verify that UWE4Demodulator decodes valid frames from the sample IQ file."""
        demod_cls = DemodulatorRegistry.get(43880)
        self.assertIsNotNone(demod_cls)

        demodulator = demod_cls()

        # Check file exists before running test
        self.assertTrue(
            SAMPLE_IQ_PATH.exists(), f"Sample IQ file not found: {SAMPLE_IQ_PATH}"
        )

        # Run demodulation flowgraph
        frames = demodulator.demodulate(SAMPLE_IQ_PATH)

        # We expect at least one valid AX.25 frame to be decoded
        self.assertGreater(len(frames), 0)
        for frame in frames:
            self.assertIsInstance(frame, bytes)
            # Verify basic AX.25 header structure (at least 17 bytes)
            self.assertGreaterEqual(len(frame), 17)
            # Control byte is UI (0x03), PID is no layer 3 (0xF0)
            self.assertEqual(frame[14], 0x03)
            self.assertEqual(frame[15], 0xF0)


if __name__ == "__main__":
    unittest.main()
