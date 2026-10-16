"""Synthesises the explainer's sound effects (no third-party samples, so no
licensing questions). Run: python3 video/explainer/scripts/make_sfx.py"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parents[1] / "public" / "sfx"
rng = np.random.default_rng(7)


def t(seconds: float) -> np.ndarray:
    return np.arange(int(SR * seconds)) / SR


def lowpass(x: np.ndarray, alpha: np.ndarray | float) -> np.ndarray:
    """One-pole low-pass; alpha may vary per sample (0..1, higher = brighter)."""
    a = np.broadcast_to(np.asarray(alpha, dtype=float), x.shape)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def reverb(x: np.ndarray, decay: float = 0.35, taps: int = 6) -> np.ndarray:
    d_max = int(SR * 0.037 * taps * (1 + 0.13 * taps))
    y = np.concatenate([x, np.zeros(d_max + 1)])
    for k in range(1, taps + 1):
        d = int(SR * 0.037 * k * (1 + 0.13 * k))
        y[d : d + len(x)] += x * (decay**k)
    return y


def save(name: str, x: np.ndarray, gain: float = 0.9) -> None:
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    stereo = np.stack([x, x], axis=1)
    data = (stereo * 32767).astype("<i2").tobytes()
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def whoosh(seconds: float = 0.5) -> np.ndarray:
    tt = t(seconds)
    env = np.sin(np.pi * (tt / seconds) ** 0.7) ** 2
    sweep = 0.03 + 0.5 * (tt / seconds) ** 1.5
    n = lowpass(rng.standard_normal(len(tt)), sweep)
    return n * env


def impact(seconds: float = 1.4, freq: float = 52.0) -> np.ndarray:
    tt = t(seconds)
    pitch = freq * (1 + 2.2 * np.exp(-tt * 28))
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    body = np.sin(phase) * np.exp(-tt * 4.2)
    crack = lowpass(rng.standard_normal(len(tt)), 0.35) * np.exp(-tt * 38) * 0.9
    return reverb(np.tanh(1.6 * (body + crack)), 0.28)


def hit(seconds: float = 0.35) -> np.ndarray:
    tt = t(seconds)
    body = np.sin(2 * np.pi * 95 * tt * (1 + np.exp(-tt * 40))) * np.exp(-tt * 14)
    snap = lowpass(rng.standard_normal(len(tt)), 0.6) * np.exp(-tt * 60)
    return np.tanh(1.4 * (body + 0.8 * snap))


def click(seconds: float = 0.06) -> np.ndarray:
    tt = t(seconds)
    return (np.sin(2 * np.pi * 2400 * tt) * 0.6 + rng.standard_normal(len(tt)) * 0.25) * np.exp(-tt * 140)


def sweep_up(seconds: float = 0.45) -> np.ndarray:
    tt = t(seconds)
    f = 300 + 2600 * (tt / seconds) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = np.sin(np.pi * tt / seconds) ** 1.5
    return reverb(tone * env * 0.5 + whoosh(seconds) * 0.4, 0.2, 3)


def tick(seconds: float = 0.04) -> np.ndarray:
    tt = t(seconds)
    return np.sin(2 * np.pi * 1600 * tt) * np.exp(-tt * 180)


def success(seconds: float = 0.7) -> np.ndarray:
    tt = t(seconds)
    out = np.zeros(len(tt))
    for i, f in enumerate((880, 1318.5)):
        start = int(i * 0.09 * SR)
        seg = tt[: len(tt) - start]
        out[start:] += np.sin(2 * np.pi * f * seg) * np.exp(-seg * 7)
    return reverb(out, 0.25, 4)


def boom(seconds: float = 3.0) -> np.ndarray:
    tt = t(seconds)
    sub = np.sin(2 * np.pi * 42 * tt * (1 + 1.5 * np.exp(-tt * 18))) * np.exp(-tt * 1.6)
    crack = lowpass(rng.standard_normal(len(tt)), 0.5) * np.exp(-tt * 22)
    tail = lowpass(rng.standard_normal(len(tt)), 0.05) * np.exp(-tt * 2.2) * 0.6
    return reverb(np.tanh(1.8 * (sub + crack + tail)), 0.4, 8)


def type_key(seconds: float = 0.035) -> np.ndarray:
    tt = t(seconds)
    return lowpass(rng.standard_normal(len(tt)), 0.4) * np.exp(-tt * 220)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    save("whoosh", whoosh(0.5), 0.8)
    save("whoosh-long", whoosh(0.9), 0.8)
    save("impact", impact(), 0.95)
    save("hit", hit(), 0.85)
    save("click", click(), 0.7)
    save("sweep", sweep_up(), 0.7)
    save("tick", tick(), 0.5)
    save("success", success(), 0.6)
    save("boom", boom(), 0.98)
    save("key", type_key(), 0.5)
    print("sfx written to", OUT)


if __name__ == "__main__":
    main()
