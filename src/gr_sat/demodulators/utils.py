from typing import List

try:
    from gnuradio import gr
    import pmt
except ImportError:
    # Mock for non-GNU Radio hosts
    class gr:
        class basic_block:
            def __init__(self, *args, **kwargs): pass
    pmt = None

class FrameCollector(gr.basic_block):
    """Collects decoded HDLC/AX.25 PDU frames from message port."""

    def __init__(self, callback=None):
        gr.basic_block.__init__(self, name="Frame Collector", in_sig=[], out_sig=[])
        self.frames = []
        self.callback = callback
        if pmt:
            self.message_port_register_in(pmt.intern("in"))
            self.set_msg_handler(pmt.intern("in"), self._handle_msg)

    def _handle_msg(self, msg):
        try:
            data = bytes(pmt.u8vector_elements(pmt.cdr(msg)))
            self.frames.append(data)
            print(f"FrameCollector: Got raw frame of len {len(data)}")
            if self.callback and is_valid_ax25(data):
                self.callback(data)
        except Exception:
            pass


def is_valid_ax25(frame: bytes) -> bool:
    """Validate that a frame is a proper AX.25 UI frame."""
    if len(frame) < 17:
        return False

    # Validate callsign bytes: each byte >> 1 should be printable ASCII (0x20-0x7E)
    for b in frame[0:6] + frame[7:13]:
        ch = b >> 1
        if ch < 0x20 or ch > 0x7E:
            return False

    # Control = 0x03 (UI frame), PID = 0xF0 (no layer 3)
    if frame[14] != 0x03 or frame[15] != 0xF0:
        return False

    return True


def deduplicate_frames(frames: List[bytes]) -> List[bytes]:
    """Remove duplicate frames, preserving order."""
    seen = set()
    unique = []
    for f in frames:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique
