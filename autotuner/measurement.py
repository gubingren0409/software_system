from __future__ import annotations

import json
import math
import os
import statistics
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .core import Config, EvaluationContext, Evaluator, atomic_write_json, utc_now
from .timing import measurement_timing, execution_clock


def statistics_for(values: list[float]) -> dict[str, float]:
    median = statistics.median(values)
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    mad = statistics.median(abs(value - median) for value in values)
    return {
        "median_seconds": median, "mean_seconds": mean,
        "minimum_seconds": min(values), "maximum_seconds": max(values),
        "sample_stdev_seconds": stdev, "coefficient_of_variation": stdev / mean,
        "median_absolute_deviation_seconds": mad, "relative_mad": mad / median,
    }


def summarize_group(config: Config, attempt_id: str, samples: list[dict[str, Any]],
                    measured_runs: int, total_seconds: float) -> dict[str, Any]:
    valid = len(samples) == measured_runs + 1 and all(
        item.get("classification") == "success" and item.get("source") == "fresh_measurement"
        and item.get("context", {}).get("force_remeasure") is True
        and type(item.get("score_seconds")) in (int, float)
        and math.isfinite(item["score_seconds"]) and item["score_seconds"] > 0
        for item in samples
    ) and len({item.get("run_id") for item in samples}) == len(samples)
    values = [item["score_seconds"] for item in samples[1:]] if valid else []
    return {
        "schema": "configuration-evaluation-v1", "config": asdict(config),
        "attempt_id": attempt_id, "classification": "success" if valid else "invalid",
        "score_seconds": statistics.median(values) if valid else None,
        "statistics": statistics_for(values) if valid else None,
        "measured_compute_seconds": values, "samples": samples,
        "process_wall_seconds": sum(item.get("process_wall_seconds", 0) for item in samples),
        "compute_total_seconds": sum(item.get("target_result", {}).get("elapsed_seconds") or 0
                                     for item in samples),
        "validation_total_seconds": sum(item.get("target_result", {}).get("validation_seconds") or 0
                                        for item in samples),
        "evaluation_wall_seconds": total_seconds,
    }


class ConfigurationEvaluator:
    """The sole configuration measurement interface used by every search strategy."""

    def __init__(self, executor: Evaluator, protocol: dict[str, Any], protocol_hash: str,
                 output: Path, on_sample: Callable[[dict[str, Any]], None] | None = None,
                 on_before_sample: Callable[[int], None] | None = None):
        self.executor, self.protocol, self.protocol_hash = executor, protocol, protocol_hash
        self.output, self.on_sample = output, on_sample
        self.on_before_sample = on_before_sample
        if protocol["measurement"]["warmup_runs"] != 1:
            raise ValueError("this protocol requires one warmup")
        timing = measurement_timing(protocol, Path(__file__).resolve().parents[1])
        self.raw_timing = timing is not None
        if timing is not None and getattr(executor.target, "timing_protocol", None) != timing:
            raise ValueError("configuration evaluator/target timing protocols differ")

    def evaluate(self, config: Config, *, attempt_id: str | None = None,
                 purpose: str = "search") -> dict[str, Any]:
        attempt_id = attempt_id or uuid.uuid4().hex
        samples: list[dict[str, Any]] = []
        clock = lambda: execution_clock(self.raw_timing)
        started = clock()
        destination = self.output / "configurations" / f"{purpose}_{attempt_id}.json"
        for index in range(1 + self.protocol["measurement"]["measured_runs"]):
            if self.on_before_sample:
                self.on_before_sample(index)
            record = self.executor.evaluate(config, EvaluationContext(
                matrix_n=self.protocol["target_matrix_n"],
                seed=self.protocol["matrix_input_seed"],
                input_pattern=self.protocol["input_pattern"],
                timeout_seconds=self.protocol["formal_timeout_seconds"][config.optimization],
                evidence_label=f"{purpose}_{attempt_id}_{index}", force_remeasure=True,
                min_wsl_available_bytes=self.protocol["resource_gate"]["formal_wsl_minimum_available_bytes"],
                protocol_hash=self.protocol_hash,
            ))
            record["attempt_id"] = attempt_id
            record["sample_index"] = index
            record["role"] = "warmup" if index == 0 else "measurement"
            record["purpose"] = purpose
            samples.append(record)
            self.output.mkdir(parents=True, exist_ok=True)
            with (self.output / "samples.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            partial = {"config": asdict(config), "attempt_id": attempt_id,
                       "status": "in_progress", "samples": samples, "updated_at": utc_now()}
            atomic_write_json(destination, partial)
            if self.on_sample:
                self.on_sample(record)
            if record["classification"] != "success":
                break
        result = summarize_group(config, attempt_id, samples,
                                 self.protocol["measurement"]["measured_runs"], clock() - started)
        result["purpose"] = purpose
        result['evaluation_wall_clock'] = 'CLOCK_MONOTONIC_RAW' if self.raw_timing else 'Python time.monotonic (legacy uncalibrated)'
        atomic_write_json(destination, result)
        return result
