"""Audio format helpers. Internal format: 16 kHz mono int16, frames of 1280 samples (80 ms)."""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import resample_poly

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280
FRAME_SECONDS = FRAME_SAMPLES / SAMPLE_RATE


def resample(samples: np.ndarray, src_rate: int, dst_rate: int = SAMPLE_RATE) -> np.ndarray:
    samples = np.asarray(samples)
    if src_rate == dst_rate:
        return samples
    divisor = math.gcd(src_rate, dst_rate)
    return resample_poly(samples.astype(np.float32), dst_rate // divisor, src_rate // divisor).astype(np.float32)


def to_float32(samples: np.ndarray) -> np.ndarray:
    array = np.asarray(samples)
    if array.dtype == np.int16:
        return array.astype(np.float32) / 32768.0
    return array.astype(np.float32)


def to_int16(samples: np.ndarray) -> np.ndarray:
    array = np.asarray(samples)
    if array.dtype == np.int16:
        return array
    return (np.clip(array, -1.0, 1.0) * 32767.0).astype(np.int16)


def chunk_frames(samples: np.ndarray, frame_samples: int = FRAME_SAMPLES) -> list[np.ndarray]:
    array = to_int16(samples)
    remainder = len(array) % frame_samples
    if remainder:
        array = np.concatenate([array, np.zeros(frame_samples - remainder, dtype=np.int16)])
    return [array[i:i + frame_samples] for i in range(0, len(array), frame_samples)]


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(round(seconds * SAMPLE_RATE)), dtype=np.int16)
