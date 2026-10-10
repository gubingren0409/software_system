from __future__ import annotations

import json
import signal
import tempfile
import unittest
from pathlib import Path

from autotuner.core import (
    BuildArtifact,
    BuildFailure,
    Config,
    ConfigSpace,
    ConfigurationError,
    EvaluationContext,
    Evaluator,
    ReferenceArtifact,
    TargetAdapter,
    classify_execution,
    strict_json_line,
)


def valid_result() -> dict[str, object]:
    return {
        "schema": "matrix-multiplication-result-v1",
        "status": "ok",
        "n": 17,
        "block_size": 8,
        "seed": 1,
        "input": "random",
        "input_generator": "splitmix64-interleaved-v1",
        "elapsed_seconds": 0.1,
        "validation_seconds": 0.001,
        "checksum": 1.0,
        "reference_checksum": 1.0,
        "max_abs_error": 0.0,
        "max_rel_error": 0.0,
        "abs_tol": 1e-12,
        "rel_tol": 1e-12,
        "checked_entries": 289,
        "mismatch_count": 0,
        "nonfinite_result_count": 0,
        "nonfinite_reference_count": 0,
        "nonfinite_error_count": 0,
        "finite_elapsed": True,
        "finite_checksum": True,
        "finite_reference_checksum": True,
        "finite_error_summary": True,
        "validation": True,
        "fault_injection": 0,
    }


def isolated_target_config(root: Path, directory: Path) -> Path:
    data = json.loads((root / "configs/target.json").read_text(encoding="utf-8"))
    data["candidate_source"] = str((root / "code/working/matrix_multiplication.c").resolve())
    data["reference_source"] = str((root / "code/working/reference_generator.c").resolve())
    data["shared_sources"] = [str((root / "code/working/matrix_input.h").resolve())]
    data["cache_root"] = str((directory / "cache").resolve())
    if "timing_protocol" in data:
        data["timing_protocol"]["file"] = str((root / 'configs' / data['timing_protocol']['file']).resolve())
    path = directory / "target.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class StrictJsonTests(unittest.TestCase):
    def test_rejects_nan_constant(self) -> None:
        with self.assertRaises(ValueError):
            strict_json_line('{"value":NaN}')

    def test_rejects_duplicate_key(self) -> None:
        with self.assertRaises(ValueError):
            strict_json_line('{"value":1,"value":2}')

    def test_rejects_multiple_lines(self) -> None:
        with self.assertRaises(ValueError):
            strict_json_line('{}\n{}\n')


class ClassificationTests(unittest.TestCase):
    def test_success_json_with_nonzero_exit_is_never_success(self) -> None:
        for code in (64, 65):
            self.assertNotEqual(classify_execution(code, False, json.dumps(valid_result()))[0], "success")

    def test_error_classification_requires_schema(self) -> None:
        for code, status in ((64, "parameter_error"), (65, "validation_failed")):
            self.assertEqual(classify_execution(code, False, json.dumps(
                {"schema": "wrong", "status": status}))[0], "output_parse_failure")

    def test_request_identity_and_tolerance_are_required(self) -> None:
        expected = {key: valid_result()[key] for key in
                    ("n", "block_size", "seed", "input", "input_generator", "abs_tol", "rel_tol")}
        for field, value in (("n", 18), ("block_size", 16), ("seed", 2), ("input", "zero"),
                             ("input_generator", "other"), ("checked_entries", 0),
                             ("abs_tol", 0.01), ("rel_tol", 0.01), ("abs_tol", -1),
                             ("rel_tol", None), ("max_abs_error", -0.1), ("max_rel_error", -0.1),
                             ("block_size", 0), ("seed", -1), ("seed", 1 << 64)):
            result = valid_result()
            result[field] = value
            with self.subTest(field=field, value=value):
                self.assertNotEqual(classify_execution(0, False, json.dumps(result), expected=expected)[0], "success")
    def test_success(self) -> None:
        classification, _, _ = classify_execution(0, False, json.dumps(valid_result()))
        self.assertEqual(classification, "success")

    def test_parameter_rejection_requires_contract(self) -> None:
        output = json.dumps(
            {
                "schema": "matrix-multiplication-result-v1",
                "status": "parameter_error",
                "error": "INVALID_ARGUMENT",
            }
        )
        self.assertEqual(classify_execution(64, False, output)[0], "parameter_rejected")
        self.assertEqual(classify_execution(1, False, output)[0], "crash")

    def test_validation_failure(self) -> None:
        output = json.dumps(
            {"schema": "matrix-multiplication-result-v1", "status": "validation_failed"}
        )
        self.assertEqual(classify_execution(65, False, output)[0], "validation_failure")

    def test_crash_timeout_and_parse_failure_are_distinct(self) -> None:
        self.assertEqual(classify_execution(-signal.SIGSEGV, False, "")[0], "crash")
        self.assertEqual(classify_execution(137, False, "")[0], "crash")
        self.assertEqual(classify_execution(0, True, "")[0], "timeout")
        self.assertEqual(classify_execution(0, False, "not-json")[0], "output_parse_failure")

    def test_nonfinite_success_cannot_score(self) -> None:
        output = json.dumps(valid_result()).replace('"elapsed_seconds": 0.1', '"elapsed_seconds": NaN')
        self.assertEqual(classify_execution(0, False, output)[0], "output_parse_failure")
        result = valid_result()
        result["checksum"] = None
        self.assertEqual(classify_execution(0, False, json.dumps(result))[0], "validation_failure")


class ConfigSpaceTests(unittest.TestCase):
    def test_external_space_has_twenty_unique_configs_in_canonical_order(self) -> None:
        root = Path(__file__).resolve().parents[1]
        space = ConfigSpace.load(root / "configs/config_space.json")
        configs = space.all()
        self.assertEqual(len(configs), 20)
        self.assertEqual(len(set(configs)), 20)
        self.assertEqual(configs[0], Config("O0", 8))
        self.assertEqual(configs[-1], Config("O3", 128))

    def test_search_protocol_is_frozen_with_requested_budgets_and_seeds(self) -> None:
        root = Path(__file__).resolve().parents[1]
        protocol = json.loads((root / "configs/search_protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["schema_version"], 2)
        self.assertEqual(protocol["status"], "revised-p1-r1-before-formal-grid")
        self.assertEqual(protocol["budgets"], [4, 8, 12])
        self.assertEqual(len(protocol["search_seeds"]), 5)
        self.assertFalse(protocol["grid"]["early_stop"])
        self.assertIn("seven unique neighbors", protocol["random_restart_greedy"]["neighbors"])
        self.assertIn("order-dependent", protocol["grid"]["limited_budget_comparison"])


class BuildCacheTests(unittest.TestCase):
    def test_reference_request_rejects_seed_above_uint64(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            target = TargetAdapter.load(
                isolated_target_config(root, directory), evidence_root=directory / "evidence"
            )
            with self.assertRaises(ConfigurationError):
                target.get_reference(17, 1 << 64, "random", 30.0)

    def test_build_key_covers_size_optimization_and_fault_mode(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            target = TargetAdapter.load(
                isolated_target_config(root, directory), evidence_root=directory / "evidence"
            )
            first = target.build_candidate(17, "O0")
            repeated = target.build_candidate(17, "O0")
            different_size = target.build_candidate(18, "O0")
            different_optimization = target.build_candidate(17, "O1")
            fault_build = target.build_candidate(17, "O0", fault_injection=1)
            self.assertEqual(first.build_key, repeated.build_key)
            self.assertEqual(first.binary_sha256, repeated.binary_sha256)
            self.assertEqual(
                len(
                    {
                        first.build_key,
                        different_size.build_key,
                        different_optimization.build_key,
                        fault_build.build_key,
                    }
                ),
                4,
            )

    def test_performance_cache_requires_explicit_reuse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            target = TargetAdapter.load(
                isolated_target_config(root, directory), evidence_root=directory / "evidence"
            )
            evaluator = Evaluator(target)
            fresh = evaluator.evaluate(
                Config("O2", 8),
                EvaluationContext(
                    17,
                    424242,
                    "random",
                    30.0,
                    "fresh",
                    force_remeasure=True,
                    protocol_hash="unit-cache-test-v1",
                ),
            )
            cached = evaluator.evaluate(
                Config("O2", 8),
                EvaluationContext(
                    17,
                    424242,
                    "random",
                    30.0,
                    "cached",
                    force_remeasure=False,
                    protocol_hash="unit-cache-test-v1",
                ),
            )
            self.assertEqual(fresh["source"], "fresh_measurement")
            self.assertEqual(cached["source"], "performance_cache")
            self.assertEqual(fresh["score_seconds"], cached["score_seconds"])

    def test_actual_gcc_failure_is_classified_without_score(self) -> None:
        root = Path(__file__).resolve().parents[1]
        base_config = json.loads((root / "configs/target.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            base_config["candidate_source"] = str(
                (root / "code/working/matrix_multiplication.c").resolve()
            )
            base_config["reference_source"] = str(
                (root / "code/working/reference_generator.c").resolve()
            )
            base_config["shared_sources"] = [
                str((root / "code/working/matrix_input.h").resolve())
            ]
            base_config["fixed_flags"] = ["-fdefinitely-not-a-real-p1-option"]
            base_config["cache_root"] = str((directory / "cache").resolve())
            if "timing_protocol" in base_config:
                base_config["timing_protocol"]["file"] = str((root / 'configs' / base_config['timing_protocol']['file']).resolve())
            config_path = directory / "target.json"
            config_path.write_text(json.dumps(base_config), encoding="utf-8")
            target = TargetAdapter.load(config_path, evidence_root=directory / "evidence")
            record = Evaluator(target).evaluate(
                Config("O0", 8),
                EvaluationContext(17, 1, "random", 30.0, "compile-failure"),
            )
            self.assertEqual(record["classification"], "compile_failure")
            self.assertIsNone(record["score_seconds"])


class FakeTarget:
    def __init__(self, executable: Path, evidence_root: Path, mode: str):
        self.executable = executable
        self.evidence_root = evidence_root
        self.mode = mode
        self.cache_root = evidence_root / "cache"
        self.config = {"result_schema": "matrix-multiplication-result-v1"}

    def build_candidate(self, matrix_n: int, optimization: str, fault_injection: int) -> BuildArtifact:
        if self.mode == "compile_failure":
            raise BuildFailure("injected", ["false"], "", "injected compile failure")
        return BuildArtifact(
            binary=self.executable,
            build_key="build",
            binary_sha256="binary",
            command=(str(self.executable),),
            optimization=optimization,
            matrix_n=matrix_n,
            fault_injection=fault_injection,
        )

    def get_reference(
        self, matrix_n: int, seed: int, input_pattern: str, timeout_seconds: float
    ) -> ReferenceArtifact:
        reference = self.evidence_root / "reference.bin"
        reference.write_bytes(b"reference")
        metadata = self.evidence_root / "reference.json"
        metadata.write_text("{}", encoding="utf-8")
        return ReferenceArtifact(reference, metadata, "reference", "hash", {})


class EvaluatorFailurePathTests(unittest.TestCase):
    def test_evaluator_binds_success_output_to_request(self) -> None:
        for field, value in (("n", 18), ("block_size", 16), ("seed", 2), ("input", "zero"),
                             ("checked_entries", 0), ("abs_tol", 1.0)):
            result = valid_result()
            result[field] = value
            record = self.run_fake(f"print({json.dumps(result)!r})\n")
            self.assertNotEqual(record["classification"], "success")
            self.assertIsNone(record["score_seconds"])

    def test_evaluator_never_scores_success_json_on_exit_64_65(self) -> None:
        for code in (64, 65):
            record = self.run_fake(f"import sys\nprint({json.dumps(valid_result())!r})\nsys.exit({code})\n")
            self.assertIsNone(record["score_seconds"])

    def run_fake(self, body: str, mode: str = "run", timeout: float = 1.0) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory_text:
            directory = Path(directory_text)
            executable = directory / "fake.py"
            executable.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
            executable.chmod(0o755)
            target = FakeTarget(executable, directory / "evidence", mode)
            evaluator = Evaluator(target)  # type: ignore[arg-type]
            return evaluator.evaluate(
                Config("O0", 8),
                EvaluationContext(17, 1, "random", timeout, "fixture"),
            )

    def test_compile_failure_has_no_score(self) -> None:
        record = self.run_fake("print('unused')\n", mode="compile_failure")
        self.assertEqual(record["classification"], "compile_failure")
        self.assertIsNone(record["score_seconds"])

    def test_actual_crash_has_no_score(self) -> None:
        record = self.run_fake("import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)\n")
        self.assertEqual(record["classification"], "crash")
        self.assertIsNone(record["score_seconds"])

    def test_actual_timeout_has_no_score(self) -> None:
        record = self.run_fake("import time\ntime.sleep(10)\n", timeout=0.05)
        self.assertEqual(record["classification"], "timeout")
        self.assertIsNone(record["score_seconds"])

    def test_actual_output_parse_failure_has_no_score(self) -> None:
        record = self.run_fake("print('not-json')\n")
        self.assertEqual(record["classification"], "output_parse_failure")
        self.assertIsNone(record["score_seconds"])


if __name__ == "__main__":
    unittest.main()
