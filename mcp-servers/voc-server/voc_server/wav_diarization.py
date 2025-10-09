"""Simple diarization utilities for two-channel WAV files."""

from __future__ import annotations

import contextlib
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# Default parameters tuned for telephony-style stereo captures.
_DEFAULT_FRAME_SECONDS = 0.5
_DEFAULT_SILENCE_THRESHOLD = 0.01  # Normalised RMS energy threshold for silence.
_DEFAULT_OVERLAP_MARGIN = 0.2  # When channels differ less than this ratio, treat as overlap.
_DEFAULT_MIN_SEGMENT_SECONDS = 0.3


def diarize_stereo_wav(
    file_path: str,
    frame_seconds: float | None = None,
    silence_threshold: float | None = None,
    overlap_margin: float | None = None,
    min_segment_seconds: float | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """
    Heuristically diarize a two-channel PCM WAV file by energy comparison.

    For each analysis frame, compare the per-channel RMS energy. The louder
    channel is considered active. When both channels show similar energy (within
    ``overlap_margin``) the frame is marked as ``overlap``. Frames whose overall
    RMS energy drop below ``silence_threshold`` are labelled ``silence``.

    Args:
        file_path: Absolute or relative path to the WAV file to analyse.
        frame_seconds: Length of analysis window in seconds. Defaults to
            ``_DEFAULT_FRAME_SECONDS``.
        silence_threshold: Minimum RMS energy (0-1 range) to consider the frame
            non-silent. Defaults to ``_DEFAULT_SILENCE_THRESHOLD``.
        overlap_margin: Maximum relative RMS difference between channels to
            treat the frame as overlapping speech.
        min_segment_seconds: Duration threshold used when merging consecutive
            segments; segments shorter than this that immediately neighbour an
            identical speaker are merged into that speaker's segment.

    Returns:
        A dictionary with the diarization result. On success, the dictionary has
        the following schema::

            {
              "status": "ok",
              "sample_rate": <int>,
              "frame_seconds": <float>,
              "segments": [
                {
                  "speaker": "speaker_1" | "speaker_2" | "overlap" | "silence",
                  "start": <float>,
                  "end": <float>,
                  "avg_level": <float>,
                  "confidence": <float>,
                  "channel_level": [<float>, <float>],
                },
                ...
              ]
            }

        On failure, the dictionary has ``{"status": "error", "error": str}``.

        When diarization succeeds, mono WAV tracks for the left/right channels
        are emitted under ``output_dir`` (defaults to
        ``./downloads/diarization/<input-stem>``) and their paths added to the
        response under ``audio_files`` using the keys ``left`` and ``right``.
    """

    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "error": f"file not found: {file_path}"}

    frame_seconds = _coalesce_positive(frame_seconds, _DEFAULT_FRAME_SECONDS)
    silence_threshold = _clamp01(_coalesce_positive(silence_threshold, _DEFAULT_SILENCE_THRESHOLD))
    overlap_margin = _clamp01(_coalesce_positive(overlap_margin, _DEFAULT_OVERLAP_MARGIN))
    min_segment_seconds = _coalesce_positive(min_segment_seconds, _DEFAULT_MIN_SEGMENT_SECONDS)

    load_result = _read_stereo_wav(path)
    if load_result["status"] == "error":
        return {"status": "error", "error": load_result["error"]}

    samples = load_result["samples"]
    sample_rate = load_result["sample_rate"]
    sample_width = load_result["sample_width"]

    if samples.size == 0:
        return {"status": "ok", "sample_rate": sample_rate, "frame_seconds": frame_seconds, "segments": []}

    segments = _analyse_frames(
        samples,
        sample_rate,
        frame_seconds,
        silence_threshold,
        overlap_margin,
        min_segment_seconds,
    )

    saved_files = _emit_speaker_tracks(
        samples,
        segments,
        sample_rate,
        sample_width,
        path,
        output_dir,
    )

    return {
        "status": "ok",
        "sample_rate": sample_rate,
        "frame_seconds": frame_seconds,
        "segments": segments,
        "audio_files": saved_files,
    }


def _read_stereo_wav(path: Path) -> dict[str, Any]:
    """Load a stereo WAV file into normalised float32 samples."""

    try:
        with contextlib.closing(wave.open(str(path), "rb")) as wav_reader:
            n_channels = wav_reader.getnchannels()
            if n_channels != 2:
                return {
                    "status": "error",
                    "error": f"expected 2 channels, found {n_channels}",
                }

            sample_width = wav_reader.getsampwidth()
            sample_rate = wav_reader.getframerate()
            n_frames = wav_reader.getnframes()
            raw_pcm = wav_reader.readframes(n_frames)
    except (wave.Error, OSError) as exc:
        return {"status": "error", "error": f"failed to read wav: {exc}"}

    dtype = _dtype_for_sample_width(sample_width)
    if dtype is None:
        return {
            "status": "error",
            "error": f"unsupported sample width: {sample_width * 8} bits",
        }

    try:
        samples = np.frombuffer(raw_pcm, dtype=dtype)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid PCM payload: {exc}"}

    if samples.size == 0:
        empty = np.empty((0, 2), dtype=np.float32)
        return {
            "status": "ok",
            "samples": empty,
            "sample_rate": sample_rate,
            "sample_width": sample_width,
        }

    try:
        samples = samples.reshape(-1, 2)
    except ValueError:
        return {"status": "error", "error": "stereo PCM data is malformed"}

    max_int = float(np.iinfo(dtype).max)
    scale = max_int if max_int > 0 else 1.0
    normalised = samples.astype(np.float32) / scale

    return {
        "status": "ok",
        "samples": normalised,
        "sample_rate": sample_rate,
        "sample_width": sample_width,
    }


def _analyse_frames(
    samples: np.ndarray,
    sample_rate: int,
    frame_seconds: float,
    silence_threshold: float,
    overlap_margin: float,
    min_segment_seconds: float,
) -> list[dict[str, Any]]:
    """Slice the audio into frames and derive diarization segments."""

    frame_samples = max(1, int(round(frame_seconds * sample_rate)))
    total_samples = samples.shape[0]
    segments: list[dict[str, Any]] = []
    state = _SegmentAccumulator(min_segment_seconds=min_segment_seconds)

    for frame_start in range(0, total_samples, frame_samples):
        frame_end = min(frame_start + frame_samples, total_samples)
        frame = samples[frame_start:frame_end]
        if frame.size == 0:
            continue

        duration, channel_rms, overall_rms = _compute_frame_metrics(frame, sample_rate)
        speaker, confidence = _classify_frame(channel_rms, overall_rms, silence_threshold, overlap_margin)

        if speaker != state.current_speaker:
            state.flush(segments, frame_start, sample_rate)
            state.reset(speaker, frame_start)

        state.accumulate(duration, overall_rms, confidence, channel_rms)

    state.flush(segments, total_samples, sample_rate)
    return segments


@dataclass
class _SegmentAccumulator:
    """Mutable container that aggregates frame statistics for a segment."""

    min_segment_seconds: float
    current_speaker: str | None = None
    segment_start_idx: int = 0
    energy_sum: float = 0.0
    confidence_sum: float = 0.0
    channel_energy_sum: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float64))
    segment_duration: float = 0.0

    def reset(self, speaker: str, start_idx: int) -> None:
        self.current_speaker = speaker
        self.segment_start_idx = start_idx
        self.energy_sum = 0.0
        self.confidence_sum = 0.0
        self.channel_energy_sum = np.zeros(2, dtype=np.float64)
        self.segment_duration = 0.0

    def accumulate(
        self,
        duration: float,
        overall_rms: float,
        confidence: float,
        channel_rms: np.ndarray,
    ) -> None:
        vector = np.asarray(channel_rms, dtype=np.float64)
        self.energy_sum += overall_rms * duration
        self.confidence_sum += confidence * duration
        self.channel_energy_sum += vector * duration
        self.segment_duration += duration

    def flush(self, segments: list[dict[str, Any]], end_idx: int, sample_rate: int) -> None:
        if self.current_speaker is None:
            return

        _flush_segment(
            segments,
            self.current_speaker,
            self.segment_start_idx,
            end_idx,
            sample_rate,
            self.energy_sum,
            self.confidence_sum,
            self.channel_energy_sum,
            self.segment_duration,
            self.min_segment_seconds,
        )
        self.current_speaker = None


def _compute_frame_metrics(frame: np.ndarray, sample_rate: int) -> tuple[float, np.ndarray, float]:
    duration = frame.shape[0] / sample_rate if sample_rate else 0.0
    channel_rms = np.sqrt(np.mean(np.square(frame), axis=0))
    overall_rms = float(np.sqrt(np.mean(np.square(frame))))
    return duration, channel_rms, overall_rms


def _classify_frame(
    channel_rms: np.ndarray,
    overall_rms: float,
    silence_threshold: float,
    overlap_margin: float,
) -> tuple[str, float]:
    if overall_rms < silence_threshold:
        return "silence", 0.0

    diff = float(abs(channel_rms[0] - channel_rms[1]))
    max_channel = float(max(channel_rms[0], channel_rms[1]))
    ratio = diff / (max_channel + 1e-9)

    if ratio < overlap_margin:
        return "overlap", 1.0 - ratio

    speaker = "speaker_1" if channel_rms[0] > channel_rms[1] else "speaker_2"
    return speaker, ratio


def _flush_segment(
    segments: list[dict[str, Any]],
    speaker: str,
    start_idx: int,
    end_idx: int,
    sample_rate: int,
    energy_sum: float,
    confidence_sum: float,
    channel_energy_sum: np.ndarray,
    segment_duration: float,
    min_segment_seconds: float,
) -> None:
    """Append a completed segment, merging with the previous one when possible."""

    if segment_duration <= 0.0:
        return

    start_time = start_idx / sample_rate
    end_time = end_idx / sample_rate
    avg_level = energy_sum / segment_duration
    confidence = confidence_sum / segment_duration
    channel_level = (channel_energy_sum / segment_duration).tolist()

    current_duration = end_time - start_time
    new_segment = {
        "speaker": speaker,
        "start": start_time,
        "end": end_time,
        "avg_level": float(avg_level),
        "confidence": float(_clamp01(confidence)),
        "channel_level": [float(x) for x in channel_level],
    }

    if segments:
        prev = segments[-1]
        prev_duration = prev["end"] - prev["start"]
        if prev["speaker"] == speaker or (speaker == "silence" and prev["speaker"] == "silence"):
            # Merge consecutive segments for the same label.
            combined_duration = prev_duration + current_duration
            if combined_duration > 0:
                prev["avg_level"] = (
                    prev["avg_level"] * prev_duration + avg_level * current_duration
                ) / combined_duration
                prev["confidence"] = (
                    prev["confidence"] * prev_duration + confidence * current_duration
                ) / combined_duration
                for i in range(2):
                    prev["channel_level"][i] = (
                        prev["channel_level"][i] * prev_duration + channel_level[i] * current_duration
                    ) / combined_duration
            prev["end"] = end_time
            return

        if current_duration < min_segment_seconds and prev["speaker"] == speaker:
            # Very short duplicate segment; extend the previous one instead of
            # adding a separate entry.
            prev["end"] = end_time
            return

    segments.append(new_segment)


def _dtype_for_sample_width(sample_width: int) -> type[np.signedinteger] | None:
    """Return a numpy dtype that matches the given sample width."""

    if sample_width == 1:
        return np.int8
    if sample_width == 2:
        return np.int16
    if sample_width == 4:
        return np.int32
    return None


def _coalesce_positive(value: float | None, default: float) -> float:
    if value is None or not math.isfinite(value) or value <= 0:
        return default
    return value


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _emit_speaker_tracks(
    samples: np.ndarray,
    segments: list[dict[str, Any]],
    sample_rate: int,
    sample_width: int,
    source_path: Path,
    output_dir: str | None,
) -> dict[str, str]:
    """Write mono WAV files per speaker and return their paths."""

    if not segments:
        return {}

    speaker_tracks = {
        "left": np.zeros(samples.shape[0], dtype=np.float32),
        "right": np.zeros(samples.shape[0], dtype=np.float32),
    }

    for segment in segments:
        speaker = segment.get("speaker")
        if speaker not in ("speaker_1", "speaker_2", "overlap"):
            continue

        start_idx = int(round(float(segment.get("start", 0.0)) * sample_rate))
        end_idx = int(round(float(segment.get("end", 0.0)) * sample_rate))
        start_idx = max(0, min(start_idx, samples.shape[0]))
        end_idx = max(0, min(end_idx, samples.shape[0]))
        if end_idx <= start_idx:
            continue

        if speaker in ("speaker_1", "overlap"):
            speaker_tracks["left"][start_idx:end_idx] = samples[start_idx:end_idx, 0]
        if speaker in ("speaker_2", "overlap"):
            speaker_tracks["right"][start_idx:end_idx] = samples[start_idx:end_idx, 1]

    base_output = Path(output_dir) if output_dir else Path.cwd() / "downloads" / "diarization"
    diarized_dir = base_output / source_path.stem
    diarized_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[str, str] = {}
    for channel, track in speaker_tracks.items():
        if not np.any(np.abs(track) > 1e-6):
            continue

        pcm_bytes = _float_to_pcm_bytes(track, sample_width)
        file_path = diarized_dir / f"{channel}.wav"
        with contextlib.closing(wave.open(str(file_path), "wb")) as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        saved[channel] = str(file_path)

    return saved


def _float_to_pcm_bytes(track: np.ndarray, sample_width: int) -> bytes:
    """Convert mono float samples in [-1, 1] to PCM bytes."""

    clipped = np.clip(track, -1.0, 1.0)

    if sample_width == 1:
        # 8-bit PCM is unsigned.
        pcm = ((clipped + 1.0) * 127.5).astype(np.uint8)
        return pcm.tobytes()

    if sample_width == 2:
        pcm = (clipped * np.iinfo(np.int16).max).astype(np.int16)
        return pcm.tobytes()

    if sample_width == 4:
        pcm = (clipped * np.iinfo(np.int32).max).astype(np.int32)
        return pcm.tobytes()

    raise ValueError(f"unsupported sample width for output: {sample_width * 8} bits")
