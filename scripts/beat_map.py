"""Write a beat map for each music library track (docs/DECISIONS.md ADR-118).

    python scripts/beat_map.py

For every web/assets/audio/<slug>.mp3 listed in TRACKS this writes
web/assets/audio/<slug>.beats.json: the tempo, every beat time, how strong
each beat is, which beats start a bar, and a 10 Hz loudness curve. The music
page reads it to pulse the background video, the cover and the visualizer
exactly on the beat, including after a seek, instead of guessing beats from
live audio.

Offline, run when a track is added or replaced; the JSON files are committed.
Needs ffmpeg on PATH and numpy (not a project dependency: this is an asset
tool like scripts/brand_assets.py).

Method: onset strength is the positive spectral flux of log-compressed
log-spaced bands (bass weighted), the tempo is the autocorrelation peak of
that envelope under a broad prior around 120 BPM, and beats come from
dynamic-programming beat tracking (D. P. W. Ellis, "Beat Tracking by Dynamic
Programming", J. New Music Research 36(1), 2007).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "web" / "assets" / "audio"
TRACKS = ("brawlistan", "urooj", "zarb", "zarb-2", "anthem-full", "bulandiyon-ki-janab")

SR = 22050
N_FFT = 2048
HOP = 512
FPS = SR / HOP  # onset frames per second (~43)
BANDS = 48
ENERGY_RATE = 10  # loudness samples per second


def decode(path: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def spectrogram(signal: np.ndarray) -> np.ndarray:
    frames = 1 + (len(signal) - N_FFT) // HOP
    index = np.arange(N_FFT)[None, :] + HOP * np.arange(frames)[:, None]
    window = np.hanning(N_FFT).astype(np.float32)
    return np.abs(np.fft.rfft(signal[index] * window, axis=1))


def band_energies(spec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Log-spaced bands from 30 Hz to 11 kHz, and a weight per band (bass heavier)."""
    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    edges = np.geomspace(30, SR / 2, BANDS + 1)
    bands = np.stack(
        [
            spec[:, (freqs >= lo) & (freqs < hi)].sum(axis=1)
            for lo, hi in zip(edges[:-1], edges[1:], strict=True)
        ],
        axis=1,
    )
    centres = np.sqrt(edges[:-1] * edges[1:])
    weights = np.where(centres < 200, 1.6, np.where(centres < 2000, 1.0, 0.7))
    return bands, weights


def onset_envelope(bands: np.ndarray, weights: np.ndarray) -> np.ndarray:
    compressed = np.log1p(100 * bands / (bands.max() + 1e-9))
    flux = np.maximum(0, np.diff(compressed, axis=0, prepend=compressed[:1])) * weights
    onset = flux.sum(axis=1)
    # Remove the slow trend so loud passages don't swamp quiet ones, then smooth.
    trend = np.convolve(onset, np.ones(int(FPS)) / int(FPS), mode="same")
    onset = np.maximum(0, onset - trend)
    onset = np.convolve(onset, np.hanning(5) / np.hanning(5).sum(), mode="same")
    return onset / (onset.std() + 1e-9)


def estimate_period(onset: np.ndarray) -> float:
    """Beat period in onset frames: autocorrelation peak, 70-190 BPM, prior at 120."""
    centred = onset - onset.mean()
    spectrum = np.fft.rfft(centred, n=2 * len(centred))
    acf = np.fft.irfft(spectrum * np.conj(spectrum))[: len(centred)]
    lags = np.arange(len(acf), dtype=float)
    bpm = np.where(lags > 0, 60 * FPS / np.maximum(lags, 1), 0)
    prior = np.exp(-0.5 * (np.log2(np.maximum(bpm, 1) / 120) / 0.9) ** 2)
    scored = np.where((bpm >= 70) & (bpm <= 190), acf * prior, -np.inf)
    lag = int(np.argmax(scored))
    # Parabolic refinement of the peak for a sub-frame period.
    a, b, c = acf[lag - 1], acf[lag], acf[lag + 1]
    shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    return lag + float(np.clip(shift, -0.5, 0.5))


def track_beats(onset: np.ndarray, period: float, tightness: float = 100.0) -> np.ndarray:
    """Ellis' dynamic programming: maximise onset strength plus tempo consistency."""
    n = len(onset)
    score = onset.astype(float).copy()
    backlink = np.full(n, -1)
    window = np.arange(-int(round(2 * period)), -int(round(period / 2)) + 1)
    penalty = -tightness * np.log(-window / period) ** 2
    for t in range(n):
        prev = t + window
        valid = prev >= 0
        if not valid.any():
            continue
        candidates = score[prev[valid]] + penalty[valid]
        best = int(np.argmax(candidates))
        if candidates[best] > 0:
            score[t] = onset[t] + candidates[best]
            backlink[t] = prev[valid][best]
    # Start from the best-scoring frame within the last beat period.
    tail = np.arange(max(0, n - int(round(period))), n)
    t = int(tail[np.argmax(score[tail])])
    beats = [t]
    while backlink[t] >= 0:
        t = int(backlink[t])
        beats.append(t)
    return np.array(beats[::-1])


def downbeat_phase(beats: np.ndarray, bass: np.ndarray) -> int:
    """Which of four beat phases carries the most bass: the bar's first beat."""
    weight = bass[np.clip(beats, 0, len(bass) - 1)]
    sums = [weight[phase::4].mean() if len(weight[phase::4]) else 0 for phase in range(4)]
    return int(np.argmax(sums))


def loudness(signal: np.ndarray) -> list[int]:
    step = SR // ENERGY_RATE
    blocks = signal[: len(signal) // step * step].reshape(-1, step)
    rms = np.sqrt((blocks**2).mean(axis=1))
    db = 20 * np.log10(rms + 1e-6)
    lo, hi = np.percentile(db, 5), np.percentile(db, 99)
    return [int(v) for v in np.clip((db - lo) / max(hi - lo, 1e-6) * 99, 0, 99).round()]


def analyse(path: Path) -> dict[str, object]:
    signal = decode(path)
    spec = spectrogram(signal)
    bands, weights = band_energies(spec)
    onset = onset_envelope(bands, weights)
    period = estimate_period(onset)
    beats = track_beats(onset, period)
    bass = bands[:, :8].sum(axis=1)
    strength = onset[beats] / (np.percentile(onset[beats], 95) + 1e-9)
    times = beats / FPS
    # Report the tempo the beat grid actually follows (median inter-beat interval).
    bpm = 60 / float(np.median(np.diff(times)))
    return {
        "duration": round(len(signal) / SR, 2),
        "bpm": round(bpm, 1),
        "beats": [round(float(t), 3) for t in times],
        "strength": [int(v) for v in np.clip(strength * 9, 0, 9).round()],
        "downbeat_phase": downbeat_phase(beats, bass),
        "energy": {"rate": ENERGY_RATE, "values": loudness(signal)},
    }


def main() -> None:
    for slug in TRACKS:
        source = AUDIO / f"{slug}.mp3"
        if not source.exists():
            print(f"{slug}: no {source.name}, skipped")
            continue
        result = analyse(source)
        out = AUDIO / f"{slug}.beats.json"
        out.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
        intervals = np.diff(result["beats"])  # type: ignore[arg-type]
        print(
            f"{slug}: {result['bpm']} BPM, {len(result['beats'])} beats, "  # type: ignore[arg-type]
            f"interval spread {np.std(intervals) * 1000:.0f} ms, {out.stat().st_size // 1024} KB"
        )


if __name__ == "__main__":
    main()
