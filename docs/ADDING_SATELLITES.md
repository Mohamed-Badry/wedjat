# Integrating a New Satellite into Project Wedjat

Project Wedjat is designed to be highly modular. Thanks to a decentralized registry pattern and the underlying schemaless JSONB database architecture, adding a new satellite requires **zero SQL migrations** and **zero frontend updates**. 

When you add a satellite decoder, the SvelteKit frontend dynamically queries the API and builds its ML Analytics charts based strictly on whatever features the decoder outputs!

To add a new satellite, you only need to modify **4 specific files**.

## Step 1: Introspect the Kaitai Struct

We rely on the [satnogs-decoders](https://gitlab.com/librespacefoundation/satnogs/satnogs-decoders) library which parses binary telemetry frames into Python objects. Before integrating, you need to know what physical parameters (temperatures, voltages) are available.

1. Ensure your desired satellite is supported by running a python script to inspect the `satnogsdecoders.decoder` module.
2. Find the telemetry structures and decide which variables you want to feed to the ML Autoencoder.

## Step 2: Define the ML Contract (`src/gr_sat/core/satellite_profiles.py`)

Every satellite has a specific "Profile" that dictates its nominal limits and the exact array of features we want to track.

Open `src/gr_sat/core/satellite_profiles.py` and create a new `SatelliteProfile`.

```python
NEW_SAT_PROFILE = SatelliteProfile(
    norad_id=12345,
    name="NEW-SAT",
    feature_contract=FeatureContract(
        version=1,
        feature_names=("batt_voltage", "temp_sensor_1"),
        diagnosis_feature_names=("batt_voltage", "temp_sensor_1"),
    ),
    pass_gap_seconds=120.0,
    cadence_tolerance_ratio=0.5,
    cadence_min_tolerance_seconds=5.0,
    baseline_filters=(
        # Reject packets where voltage is physically impossible (e.g., 0V)
        BaselineFilter("batt_voltage", "gt", 0.0),
    ),
)
```
Add your new profile to the `_SATELLITE_PROFILES` dictionary at the bottom of the file!

## Step 3: Build the Decoder Adapter (`src/gr_sat/core/decoders/<satellite_name>.py`)

Create a new file in the decoders directory (e.g., `src/gr_sat/core/decoders/newsat.py`).

Your class must inherit from `BaseDecoder` and be decorated with the satellite's NORAD ID.

```python
import math
from loguru import logger
import satnogsdecoders.decoder.newsat as newsat

from gr_sat.core.decoders.base import BaseDecoder, DecoderRegistry

@DecoderRegistry.register(12345)
class NewSatDecoder(BaseDecoder):
    def decode(self, raw_bytes: bytes):
        try:
            return newsat.NewSat.from_bytes(raw_bytes)
        except Exception:
            return None

    def adapt(self, parsed_obj) -> dict[str, float] | None:
        if not parsed_obj:
            return None

        # Map Kaitai properties to your FeatureContract defined in Step 2
        features = {}
        features["batt_voltage"] = float(parsed_obj.payload.voltage)
        features["temp_sensor_1"] = float(parsed_obj.payload.temp)

        # Drop impossible packets and fix ML-crashing NaNs
        for k, v in features.items():
            if math.isnan(v) or math.isinf(v):
                features[k] = 0.0
                
        return features
```

## Step 4: Register the Decoder globally (`src/gr_sat/core/decoders/__init__.py`)

To ensure the `@DecoderRegistry` fires and registers the satellite across the entire system, import your new module in the `__init__.py` file:

```python
from . import uwe4  # noqa: F401
from . import newsat  # noqa: F401
```

---
**Done!** 
Because of the centralized `_SATELLITE_PROFILES` registry, the fetching scripts, edge simulator, database schema, and frontend UI will all automatically inherit your new satellite without any further code changes.

Restart the Docker containers, run `just fetch --norad 12345`, and watch the new telemetry populate straight through to the SvelteKit charts!
