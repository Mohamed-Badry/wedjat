import unittest
from datetime import datetime, timezone
import pandas as pd

from gr_sat.decoders.uwe4 import UWE4Decoder
from gr_sat.telemetry import process_frame_result, TelemetryFrame

# Kaitai Struct dummy payload for UWE4 for testing decode success
# UWE4 payload needs to be long enough and structured to pass the Kaitai parser.
# We will mock the decoder's adapt/decode methods or just use a known good payload if available.
# Since we want to test the Pipeline rule, we can mock the decoder itself to isolate the pipeline logic.
from unittest.mock import patch, MagicMock

class TelemetryPipelineSpecTests(unittest.TestCase):
    """
    Tests derived from docs/spec/telemetry_pipeline.allium obligations.
    Fills the gap in testing the successful ProcessFrame rule.
    """

    @patch("gr_sat.telemetry.DecoderRegistry.get_decoder")
    def test_rule_success_ProcessFrame_produces_ProcessedTelemetry(self, mock_get_decoder):
        """
        Obligation: rule-success.ProcessFrame
        Obligation: rule-entity-creation.ProcessFrame.2
        """
        # Create a mock decoder that succeeds in both stages
        mock_decoder = MagicMock()
        mock_get_decoder.return_value = mock_decoder
        
        # Stage 1: Decode returns some interim fields
        from gr_sat.telemetry import StageOutcome
        mock_decoder.decode_with_diagnostics.return_value = StageOutcome(
            data={"raw_voltage": 4000, "raw_temp": 12}
        )
        
        # Stage 2: Adapt returns Golden Features map
        mock_decoder.adapt_with_diagnostics.return_value = StageOutcome(
            data={
                "batt_voltage": 4.0,
                "temp_obc": 12.0,
                "uptime": 100
            }
        )

        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = process_frame_result(
            norad_id=43880,
            payload=b"dummy_payload",
            source="satnogs",
            timestamp=timestamp
        )

        # Verify the pipeline successfully processed the frame (status: valid)
        self.assertTrue(result.ok)
        
        # Verify TelemetryFrame (ProcessedTelemetry) entity fields
        self.assertIsInstance(result.frame, TelemetryFrame)
        self.assertEqual(result.frame.norad_id, 43880)
        self.assertEqual(result.frame.batt_voltage, 4.0)
        self.assertEqual(result.frame.temp_obc, 12.0)
        self.assertEqual(result.frame.uptime, 100)
        self.assertEqual(result.frame.source, "satnogs")
        
        # Verify the pipeline logic called both stages with the correct data passing
        mock_decoder.decode_with_diagnostics.assert_called_once_with(b"dummy_payload")
        mock_decoder.adapt_with_diagnostics.assert_called_once_with({"raw_voltage": 4000, "raw_temp": 12})


if __name__ == "__main__":
    unittest.main()
