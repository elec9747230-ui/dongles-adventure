"""Generate an original 16-bit chiptune-style BGM loop.

Writes `assets/music/bgm_loop.wav` — a simple, happy 4-chord progression
(I - IV - ii - V) in C major with a saw-ish lead and pulse bass, evoking
the feel of MSX-era platformer music while being 100% original material.

Run from the project root:
    python tools/generate_placeholder_bgm.py
"""
from __future__ import annotations

import math
import os
import struct
import wave

SAMPLE_RATE = 22050
TEMPO_BPM = 138

# Eighth-note duration in seconds (8 per bar at 4/4)
EIGHTH = 60.0 / TEMPO_BPM / 2

# C major scale MIDI numbers
C4, D4, E4, F4, G4, A4, B4 = 60, 62, 64, 65, 67, 69, 71
C5, D5, E5, F5, G5, A5, B5 = 72, 74, 76, 77, 79, 81, 83
C6 = 84
REST = -1


def midi_to_freq(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12))


# Lead melody: 8 bars, 8 eighth notes per bar = 64 notes.
# Climbing motif over a I - IV - ii - V - I - IV - V - I cadence.
LEAD: list[int] = [
    # Bar 1: C major (I) — rising arpeggio + figure
    C5, E5, G5, C6,  G5, E5, C5, REST,
    # Bar 2: F major (IV)
    F5, A5, C6, F5,  C6, A5, F5, REST,
    # Bar 3: D minor (ii)
    D5, F5, A5, D5,  A5, F5, D5, REST,
    # Bar 4: G major (V)
    G5, B5, D5, G5,  D5, B5, G5, REST,
    # Bar 5: I again, slight variation
    C5, G5, E5, C5,  E5, G5, C6, REST,
    # Bar 6: IV
    F5, C6, A5, F5,  A5, C6, F5, REST,
    # Bar 7: V (drive home)
    G5, B5, D5, G5,  F5, D5, B5, REST,
    # Bar 8: cadence to I, end with sustained C
    C5, E5, G5, C6,  G5, E5, G5, C5,
]

# Bass: one note per beat (quarter notes) = 4 per bar = 32 total
BASS: list[int] = [
    C4, C4, C4, C4,   # I
    F4, F4, F4, F4,   # IV
    D4, D4, D4, D4,   # ii
    G4, G4, G4, G4,   # V
    C4, C4, C4, C4,   # I
    F4, F4, F4, F4,   # IV
    G4, G4, G4, G4,   # V
    C4, C4, C4, C4,   # I
]


def synth_lead(freq: float, samples: int) -> list[float]:
    """Saw-ish lead using fundamental + 3rd harmonic."""
    if freq <= 0:
        return [0.0] * samples
    out = []
    for i in range(samples):
        t = i / SAMPLE_RATE
        v = (
            math.sin(2 * math.pi * freq * t) * 0.6
            + math.sin(2 * math.pi * freq * 3 * t) * 0.2
            + math.sin(2 * math.pi * freq * 5 * t) * 0.1
        )
        # ADSR-like envelope: quick attack, gentle decay
        env = min(1.0, i / 200) * max(0.0, 1.0 - i / samples) ** 0.4
        out.append(v * env)
    return out


def synth_bass(freq: float, samples: int) -> list[float]:
    """Pulse-style bass — square wave with envelope."""
    if freq <= 0:
        return [0.0] * samples
    out = []
    period = SAMPLE_RATE / freq
    for i in range(samples):
        v = 1.0 if (i % period) < (period * 0.5) else -1.0
        env = min(1.0, i / 100) * max(0.0, 1.0 - i / samples) ** 0.3
        out.append(v * env * 0.6)
    return out


def render_track(notes: list[int], note_dur: float, synth) -> list[float]:
    samples_per_note = int(SAMPLE_RATE * note_dur)
    track: list[float] = []
    for n in notes:
        if n == REST:
            track.extend([0.0] * samples_per_note)
        else:
            track.extend(synth(midi_to_freq(n), samples_per_note))
    return track


def main() -> None:
    out_dir = "assets/music"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "bgm_loop.wav")

    lead = render_track(LEAD, EIGHTH, synth_lead)
    bass = render_track(BASS, EIGHTH * 2, synth_bass)  # quarter notes

    # Pad/truncate so both are the same length
    n = min(len(lead), len(bass))
    lead = lead[:n]
    bass = bass[:n]

    # Mix and clip
    mix = [max(-1.0, min(1.0, lead[i] * 0.55 + bass[i] * 0.45)) for i in range(n)]

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit signed
        w.setframerate(SAMPLE_RATE)
        for v in mix:
            w.writeframes(struct.pack("<h", int(v * 32000)))
    print(f"Wrote {out_path} ({n / SAMPLE_RATE:.2f}s, 16-bit mono @ {SAMPLE_RATE}Hz)")


if __name__ == "__main__":
    main()
