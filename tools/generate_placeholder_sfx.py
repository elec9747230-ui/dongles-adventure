"""Generate placeholder SFX as 8-bit WAV files."""
from __future__ import annotations

import math
import os
import struct
import wave


def write_tone(path: str, freq: float, duration: float, volume: float = 0.6, sample_rate: int = 22050) -> None:
    n_frames = int(sample_rate * duration)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)  # 8-bit
        w.setframerate(sample_rate)
        for i in range(n_frames):
            env = max(0.0, 1.0 - i / n_frames)
            v = math.sin(2 * math.pi * freq * i / sample_rate) * env * volume
            byte = int((v + 1.0) * 127.5)
            w.writeframes(struct.pack("B", byte))


def main() -> None:
    out = "assets/sounds"
    os.makedirs(out, exist_ok=True)
    write_tone(f"{out}/jump.wav", 660, 0.10)
    write_tone(f"{out}/land.wav", 220, 0.08)
    write_tone(f"{out}/pickup.wav", 880, 0.10)
    write_tone(f"{out}/hit.wav", 110, 0.20)
    write_tone(f"{out}/gameover.wav", 80, 0.50)
    print("Wrote placeholder SFX to", out)


if __name__ == "__main__":
    main()
