from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RESULT_SCHEMA = "matrix-multiplication-result-v1"
REFERENCE_SCHEMA = "matrix-reference-v1"
RUNNER_SCHEMA = "matrix-autotuner-evaluation-v1"
VALID_OPTIMIZATIONS = ("O0", "O1", "O2", "O3")
VALID_INPUTS = ("random", "zero", "identity")


class ConfigurationError(ValueError):
    pass


class BuildFailure(RuntimeError):
    def __init__(self, message: str, command: list[str], stdout: str, stderr: str):
        super().__init__(message)
        self.command = command
        self.stdout = stdout
        self.stderr = stderr


class ReferenceFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    optimization: str
    block_size: int


@dataclass(frozen=True)
class BuildArtifact:
    binary: Path
    build_key: str
    binary_sha256: str
    command: tuple[str, ...]
    optimization: str
    matrix_n: int
    fault_injection: int


@dataclass(frozen=True)
class ReferenceArtifact:
    data_path: Path
    metadata_path: Path
    reference_key: str
    data_sha256: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EvaluationContext:
    matrix_n: int
    seed: int
    input_pattern: str
    timeout_seconds: float
    evidence_label: str
    min_wsl_available_bytes: int = 0
    fault_injection: int = 0
    force_remeasure: bool = True
    protocol_hash: str = "p1-diagnostic-v1"


class ConfigSpace:
    def __init__(self, optimization_levels: Iterable[str], block_sizes: Iterable[int]):
        optimizations = tuple(optimization_levels)
        blocks = tuple(block_sizes)
        if not optimizations or not blocks:
            raise ConfigurationError("configuration space cannot be empty")
        if len(set(optimizations)) != len(optimizations):
            raise ConfigurationError("duplicate optimization level")
        if len(set(blocks)) != len(blocks):
            raise ConfigurationError("duplicate block size")
        if any(opt not in VALID_OPTIMIZATIONS for opt in optimizations):
            raise ConfigurationError("unsupported optimization level")
        if any(type(block) is not int or block < 1 for block in blocks):
            raise ConfigurationError("block sizes must be positive integers")
        self.optimization_levels = optimizations
        self.block_sizes = blocks

    @classmethod
    def load(cls, path: Path) -> "ConfigSpace":
        data = _load_json_file(path)
        if set(data) != {"schema_version", "optimization_levels", "block_sizes"}:
            raise ConfigurationError("unexpected config-space fields")
        if data["schema_version"] != 1:
            raise ConfigurationError("unsupported config-space schema")
        return cls(data["optimization_levels"], data["block_sizes"])

    def all(self) -> tuple[Config, ...]:
        return tuple(
            Config(optimization=optimization, block_size=block)
            for optimization in self.optimization_levels
            for block in self.block_sizes
        )

    def validate(self, config: Config, matrix_n: int) -> None:
        if config.optimization not in self.optimization_levels:
            raise ConfigurationError("optimization is outside the space")
        if config.block_size not in self.block_sizes:
            raise ConfigurationError("block size is outside the space")
        if config.block_size > matrix_n:
            raise ConfigurationError("block size exceeds matrix dimension")


class TargetAdapter:
    REQUIRED_FIELDS = {
        "schema_version",
        "name",
        "candidate_source",
        "reference_source",
        "shared_sources",
        "compiler",
        "language_standard",
        "warning_flags",
        "fixed_flags",
        "link_flags",
        "matrix_size_macro",
        "default_matrix_size",
        "default_seed",
        "default_input",
        "result_schema",
        "cache_root",
        "small_reference_max_n",
        "abs_tolerance",
        "rel_tolerance",
    }

    def __init__(self, config_path: Path, evidence_root: Path | None = None):
        config_path = config_path.resolve()
        data = _load_json_file(config_path)
        if set(data) != self.REQUIRED_FIELDS:
            missing = sorted(self.REQUIRED_FIELDS - set(data))
            extra = sorted(set(data) - self.REQUIRED_FIELDS)
            raise ConfigurationError(f"target fields differ: missing={missing}, extra={extra}")
        if data["schema_version"] != 1 or data["result_schema"] != RESULT_SCHEMA:
            raise ConfigurationError("unsupported target schema")
        if data["default_input"] not in VALID_INPUTS:
            raise ConfigurationError("unsupported default input")
        self.config_path = config_path
        self.config = data
        self.base_dir = config_path.parent
        self.candidate_source = (self.base_dir / data["candidate_source"]).resolve()
        self.reference_source = (self.base_dir / data["reference_source"]).resolve()
        self.shared_sources = tuple(
            (self.base_dir / item).resolve() for item in data["shared_sources"]
        )
        self.compiler = Path(data["compiler"]).resolve()
        if not self.compiler.is_file():
            raise ConfigurationError(f"compiler not found: {self.compiler}")
        for source in (self.candidate_source, self.reference_source, *self.shared_sources):
            if not source.is_file():
                raise ConfigurationError(f"source not found: {source}")
        self.cache_root = Path(data["cache_root"])
        if not self.cache_root.is_absolute():
            raise ConfigurationError("cache_root must be absolute and outside the repository")
        self.evidence_root = evidence_root.resolve() if evidence_root else None
        self._compiler_version = _run_checked(
            [str(self.compiler), "--version"]
        ).stdout.strip()

    @classmethod
    def load(cls, path: Path, evidence_root: Path | None = None) -> "TargetAdapter":
        return cls(path, evidence_root=evidence_root)

    def _source_hashes(self, primary: Path) -> dict[str, str]:
        paths = (primary, *self.shared_sources)
        return {str(path): sha256_file(path) for path in paths}

    def _compile_command(
        self,
        source: Path,
        output: Path,
        matrix_n: int,
        optimization: str,
        fault_injection: int = 0,
    ) -> list[str]:
        if optimization not in VALID_OPTIMIZATIONS:
            raise ConfigurationError(f"invalid optimization: {optimization}")
        if matrix_n < 1:
            raise ConfigurationError("matrix_n must be positive")
        if fault_injection not in range(0, 8):
            raise ConfigurationError("unsupported fault injection")
        command = [
            str(self.compiler),
            self.config["language_standard"],
            *self.config["warning_flags"],
            *self.config["fixed_flags"],
            f"-D{self.config['matrix_size_macro']}={matrix_n}",
            f"-DABS_TOL={self.config['abs_tolerance']:.17g}L",
            f"-DREL_TOL={self.config['rel_tolerance']:.17g}L",
        ]
        if source == self.candidate_source:
            command.append(f"-DMM_TEST_FAULT={fault_injection}")
        command.extend([f"-{optimization}", str(source), *self.config["link_flags"], "-o", str(output)])
        return command

    def build_candidate(
        self, matrix_n: int, optimization: str, fault_injection: int = 0
    ) -> BuildArtifact:
        placeholder = Path("candidate")
        key_command = self._compile_command(
            self.candidate_source, placeholder, matrix_n, optimization, fault_injection
        )
        payload = {
            "schema": "candidate-build-v1",
            "source_hashes": self._source_hashes(self.candidate_source),
            "compiler": str(self.compiler),
            "compiler_version": self._compiler_version,
            "command_without_output_path": key_command[:-2] + ["-o", "candidate"],
            "matrix_n": matrix_n,
            "optimization": optimization,
            "fault_injection": fault_injection,
        }
        build_key = sha256_json(payload)
        directory = self.cache_root / "build" / build_key
        binary = directory / "candidate"
        manifest = directory / "manifest.json"
        if binary.is_file() and manifest.is_file():
            metadata = _load_json_file(manifest)
            binary_hash = sha256_file(binary)
            if metadata.get("binary_sha256") == binary_hash:
                return BuildArtifact(
                    binary=binary,
                    build_key=build_key,
                    binary_sha256=binary_hash,
                    command=tuple(metadata["command"]),
                    optimization=optimization,
                    matrix_n=matrix_n,
                    fault_injection=fault_injection,
                )
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f"candidate.{uuid.uuid4().hex}.tmp"
        command = self._compile_command(
            self.candidate_source, temporary, matrix_n, optimization, fault_injection
        )
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise BuildFailure("candidate compilation failed", command, completed.stdout, completed.stderr)
        os.replace(temporary, binary)
        binary_hash = sha256_file(binary)
        metadata = {
            **payload,
            "build_key": build_key,
            "command": [*command[:-1], str(binary)],
            "binary_sha256": binary_hash,
            "created_at": utc_now(),
        }
        atomic_write_json(manifest, metadata)
        return BuildArtifact(
            binary=binary,
            build_key=build_key,
            binary_sha256=binary_hash,
            command=tuple(metadata["command"]),
            optimization=optimization,
            matrix_n=matrix_n,
            fault_injection=fault_injection,
        )

    def build_reference_generator(self, matrix_n: int) -> BuildArtifact:
        optimization = "O3"
        placeholder = Path("reference_generator")
        key_command = self._compile_command(
            self.reference_source, placeholder, matrix_n, optimization
        )
        payload = {
            "schema": "reference-build-v1",
            "source_hashes": self._source_hashes(self.reference_source),
            "compiler": str(self.compiler),
            "compiler_version": self._compiler_version,
            "command_without_output_path": key_command[:-2] + ["-o", "reference_generator"],
            "matrix_n": matrix_n,
            "optimization": optimization,
        }
        build_key = sha256_json(payload)
        directory = self.cache_root / "build" / build_key
        binary = directory / "reference_generator"
        manifest = directory / "manifest.json"
        if binary.is_file() and manifest.is_file():
            metadata = _load_json_file(manifest)
            binary_hash = sha256_file(binary)
            if metadata.get("binary_sha256") == binary_hash:
                return BuildArtifact(
                    binary=binary,
                    build_key=build_key,
                    binary_sha256=binary_hash,
                    command=tuple(metadata["command"]),
                    optimization=optimization,
                    matrix_n=matrix_n,
                    fault_injection=0,
                )
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f"reference_generator.{uuid.uuid4().hex}.tmp"
        command = self._compile_command(
            self.reference_source, temporary, matrix_n, optimization
        )
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise BuildFailure("reference compilation failed", command, completed.stdout, completed.stderr)
        os.replace(temporary, binary)
        binary_hash = sha256_file(binary)
        metadata = {
            **payload,
            "build_key": build_key,
            "command": [*command[:-1], str(binary)],
            "binary_sha256": binary_hash,
            "created_at": utc_now(),
        }
        atomic_write_json(manifest, metadata)
        return BuildArtifact(
            binary=binary,
            build_key=build_key,
            binary_sha256=binary_hash,
            command=tuple(metadata["command"]),
            optimization=optimization,
            matrix_n=matrix_n,
            fault_injection=0,
        )

    def get_reference(
        self,
        matrix_n: int,
        seed: int,
        input_pattern: str,
        timeout_seconds: float,
    ) -> ReferenceArtifact:
        if input_pattern not in VALID_INPUTS or seed < 0 or seed > (1 << 64) - 1:
            raise ConfigurationError("invalid reference request")
        generator = self.build_reference_generator(matrix_n)
        accumulator = (
            "long-double"
            if matrix_n <= int(self.config["small_reference_max_n"])
            else "double"
        )
        payload = {
            "schema": "reference-cache-key-v1",
            "reference_build_key": generator.build_key,
            "reference_binary_sha256": generator.binary_sha256,
            "matrix_n": matrix_n,
            "seed": seed,
            "input": input_pattern,
            "input_generator": "splitmix64-interleaved-v1",
            "accumulator": accumulator,
            "element_type": "float64-native-le",
        }
        reference_key = sha256_json(payload)
        directory = self.cache_root / "reference" / reference_key
        data_path = directory / "reference.bin"
        metadata_path = directory / "manifest.json"
        if data_path.is_file() and metadata_path.is_file():
            metadata = _load_json_file(metadata_path)
            expected_bytes = matrix_n * matrix_n * 8
            if (
                metadata.get("complete") is True
                and metadata.get("reference_key") == reference_key
                and data_path.stat().st_size == expected_bytes
                and metadata.get("data_sha256") == sha256_file(data_path)
            ):
                self._write_reference_evidence(metadata)
                return ReferenceArtifact(
                    data_path=data_path,
                    metadata_path=metadata_path,
                    reference_key=reference_key,
                    data_sha256=metadata["data_sha256"],
                    metadata=metadata,
                )
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f"reference.{uuid.uuid4().hex}.tmp"
        command = [
            str(generator.binary),
            "--seed",
            str(seed),
            "--input",
            input_pattern,
            "--output",
            str(temporary),
            "--accumulator",
            accumulator,
        ]
        before = resource_snapshot()
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            temporary.unlink(missing_ok=True)
            raise ReferenceFailure(f"reference generation timed out: {error}") from error
        wall_seconds = time.monotonic() - started
        after = resource_snapshot()
        if completed.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise ReferenceFailure(
                f"reference generation failed rc={completed.returncode}: {completed.stderr}"
            )
        try:
            parsed = strict_json_line(completed.stdout)
        except ValueError as error:
            temporary.unlink(missing_ok=True)
            raise ReferenceFailure(f"reference output parse failed: {error}") from error
        expected_bytes = matrix_n * matrix_n * 8
        if (
            parsed.get("schema") != REFERENCE_SCHEMA
            or parsed.get("status") != "ok"
            or parsed.get("n") != matrix_n
            or parsed.get("seed") != seed
            or parsed.get("input") != input_pattern
            or parsed.get("accumulator") != accumulator
            or parsed.get("byte_count") != expected_bytes
            or parsed.get("sample_mismatch_count") != 0
            or not temporary.is_file()
            or temporary.stat().st_size != expected_bytes
        ):
            temporary.unlink(missing_ok=True)
            raise ReferenceFailure("reference metadata or file length validation failed")
        for field in (
            "generation_seconds",
            "checksum",
            "sample_max_abs_error",
            "sample_max_rel_error",
        ):
            if not is_finite_number(parsed.get(field)):
                temporary.unlink(missing_ok=True)
                raise ReferenceFailure(f"non-finite reference field: {field}")
        with temporary.open("rb+") as stream:
            os.fsync(stream.fileno())
        data_hash = sha256_file(temporary)
        os.replace(temporary, data_path)
        metadata = {
            **payload,
            **parsed,
            "complete": True,
            "reference_key": reference_key,
            "data_sha256": data_hash,
            "generator_command": command,
            "generator_stdout": completed.stdout,
            "generator_stderr": completed.stderr,
            "generator_returncode": completed.returncode,
            "process_wall_seconds": wall_seconds,
            "resource_before": before,
            "resource_after": after,
            "created_at": utc_now(),
        }
        atomic_write_json(metadata_path, metadata)
        self._write_reference_evidence(metadata)
        return ReferenceArtifact(
            data_path=data_path,
            metadata_path=metadata_path,
            reference_key=reference_key,
            data_sha256=data_hash,
            metadata=metadata,
        )

    def _write_reference_evidence(self, metadata: dict[str, Any]) -> None:
        if self.evidence_root is None:
            return
        destination = self.evidence_root / "references" / f"{metadata['reference_key']}.json"
        atomic_write_json(destination, metadata)


class Evaluator:
    def __init__(self, target: TargetAdapter):
        self.target = target

    def evaluate(self, config: Config, context: EvaluationContext) -> dict[str, Any]:
        label = sanitize_label(context.evidence_label)
        if not label:
            label = uuid.uuid4().hex
        run_directory = (
            self.target.evidence_root / "runs" / label
            if self.target.evidence_root
            else Path(tempfile.mkdtemp(prefix="mm-evaluation-"))
        )
        run_directory.mkdir(parents=True, exist_ok=True)

        try:
            artifact = self.target.build_candidate(
                context.matrix_n, config.optimization, context.fault_injection
            )
        except BuildFailure as error:
            record = self._base_record(config, context)
            record.update(
                {
                    "classification": "compile_failure",
                    "score_seconds": None,
                    "command": error.command,
                    "stdout": error.stdout,
                    "stderr": error.stderr,
                }
            )
            self._write_record(run_directory, record, error.stdout, error.stderr, "")
            return record

        try:
            reference = self.target.get_reference(
                context.matrix_n,
                context.seed,
                context.input_pattern,
                max(context.timeout_seconds, 30.0),
            )
        except (BuildFailure, ReferenceFailure, ConfigurationError) as error:
            record = self._base_record(config, context)
            record.update(
                {
                    "classification": "reference_failure",
                    "score_seconds": None,
                    "command": [],
                    "stdout": "",
                    "stderr": str(error),
                    "build_key": artifact.build_key,
                }
            )
            self._write_record(run_directory, record, "", str(error), "")
            return record

        performance_key = sha256_json(
            {
                "schema": "performance-cache-key-v1",
                "build_key": artifact.build_key,
                "reference_key": reference.reference_key,
                "block_size": config.block_size,
                "seed": context.seed,
                "input": context.input_pattern,
                "protocol_hash": context.protocol_hash,
            }
        )
        performance_path = self.target.cache_root / "performance" / f"{performance_key}.json"
        if (
            not context.force_remeasure
            and context.fault_injection == 0
            and performance_path.is_file()
        ):
            cached = _load_json_file(performance_path)
            if cached.get("classification") == "success" and is_finite_number(
                cached.get("score_seconds")
            ):
                record = dict(cached)
                record["source"] = "performance_cache"
                record["cache_reused_at"] = utc_now()
                self._write_record(run_directory, record, "", "", "")
                return record

        before = resource_snapshot()
        if before["mem_available_bytes"] < context.min_wsl_available_bytes:
            record = self._base_record(config, context)
            record.update(
                {
                    "classification": "resource_rejected",
                    "score_seconds": None,
                    "command": [],
                    "stdout": "",
                    "stderr": "WSL MemAvailable is below the configured threshold",
                    "build_key": artifact.build_key,
                    "reference_key": reference.reference_key,
                    "resource_before": before,
                }
            )
            self._write_record(run_directory, record, "", record["stderr"], "")
            return record

        command = [
            str(artifact.binary),
            "--block-size",
            str(config.block_size),
            "--seed",
            str(context.seed),
            "--input",
            context.input_pattern,
            "--reference",
            str(reference.data_path),
        ]
        time_output = run_directory / "resource.txt"
        timed_command = ["/usr/bin/time", "-v", "-o", str(time_output), *command]
        started = time.monotonic()
        process = subprocess.Popen(
            timed_command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=context.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        process_wall_seconds = time.monotonic() - started
        after = resource_snapshot()
        resource_text = time_output.read_text(encoding="utf-8") if time_output.exists() else ""
        classification, parsed, detail = classify_execution(
            process.returncode, timed_out, stdout, self.target.config["result_schema"]
        )
        score = parsed.get("elapsed_seconds") if classification == "success" else None
        record = self._base_record(config, context)
        record.update(
            {
                "classification": classification,
                "classification_detail": detail,
                "score_seconds": score,
                "command": command,
                "timed_command": timed_command,
                "returncode": process.returncode,
                "signal": -process.returncode if process.returncode < 0 else None,
                "timed_out": timed_out,
                "process_wall_seconds": process_wall_seconds,
                "stdout_sha256": sha256_text(stdout),
                "stderr_sha256": sha256_text(stderr),
                "build_key": artifact.build_key,
                "binary_sha256": artifact.binary_sha256,
                "reference_key": reference.reference_key,
                "reference_sha256": reference.data_sha256,
                "resource_before": before,
                "resource_after": after,
                "target_result": parsed,
                "source": "fresh_measurement",
            }
        )
        self._write_record(run_directory, record, stdout, stderr, resource_text)
        if classification == "success" and context.fault_injection == 0:
            atomic_write_json(performance_path, record)
        return record

    @staticmethod
    def _base_record(config: Config, context: EvaluationContext) -> dict[str, Any]:
        return {
            "schema": RUNNER_SCHEMA,
            "created_at": utc_now(),
            "config": asdict(config),
            "context": asdict(context),
        }

    @staticmethod
    def _write_record(
        directory: Path,
        record: dict[str, Any],
        stdout: str,
        stderr: str,
        resource_text: str,
    ) -> None:
        atomic_write_text(directory / "stdout.txt", stdout)
        atomic_write_text(directory / "stderr.txt", stderr)
        if resource_text:
            atomic_write_text(directory / "resource.txt", resource_text)
        atomic_write_json(directory / "result.json", record)


def classify_execution(
    returncode: int, timed_out: bool, stdout: str, expected_schema: str = RESULT_SCHEMA
) -> tuple[str, dict[str, Any], str]:
    if timed_out:
        return "timeout", {}, "deadline exceeded and process group was terminated"
    if returncode < 0:
        return "crash", {}, f"terminated by signal {-returncode}"
    if returncode not in (0, 64, 65):
        return "crash", {}, f"unexpected nonzero exit code {returncode}"
    try:
        parsed = strict_json_line(stdout)
    except ValueError as error:
        return "output_parse_failure", {}, str(error)
    if returncode == 64 and parsed.get("status") == "parameter_error":
        return "parameter_rejected", parsed, "target reported invalid arguments"
    if returncode == 65 and parsed.get("status") == "validation_failed":
        return "validation_failure", parsed, "target correctness gate rejected the result"
    if parsed.get("schema") != expected_schema or parsed.get("status") != "ok":
        return "output_parse_failure", parsed, "unexpected schema or status"
    required_integer_fields = (
        "n",
        "block_size",
        "seed",
        "checked_entries",
        "mismatch_count",
        "nonfinite_result_count",
        "nonfinite_reference_count",
        "nonfinite_error_count",
        "fault_injection",
    )
    if any(type(parsed.get(field)) is not int for field in required_integer_fields):
        return "output_parse_failure", parsed, "missing or non-integer result field"
    required_boolean_fields = (
        "finite_elapsed",
        "finite_checksum",
        "finite_reference_checksum",
        "finite_error_summary",
        "validation",
    )
    if any(type(parsed.get(field)) is not bool for field in required_boolean_fields):
        return "output_parse_failure", parsed, "missing or non-boolean result field"
    finite_fields = (
        "elapsed_seconds",
        "checksum",
        "reference_checksum",
        "max_abs_error",
        "max_rel_error",
        "abs_tol",
        "rel_tol",
    )
    if any(not is_finite_number(parsed.get(field)) for field in finite_fields):
        return "validation_failure", parsed, "non-finite or missing numeric result field"
    if parsed["elapsed_seconds"] <= 0:
        return "validation_failure", parsed, "non-positive compute time"
    if (
        not all(parsed[field] for field in required_boolean_fields)
        or parsed["mismatch_count"] != 0
        or parsed["nonfinite_result_count"] != 0
        or parsed["nonfinite_reference_count"] != 0
        or parsed["nonfinite_error_count"] != 0
        or parsed["fault_injection"] != 0
    ):
        return "validation_failure", parsed, "success output violates correctness invariants"
    return "success", parsed, "validated result"


def strict_json_line(text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError(f"expected exactly one non-empty JSON line, got {len(lines)}")

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    parsed = json.loads(
        lines[0], parse_constant=reject_constant, object_pairs_hook=reject_duplicates
    )
    if type(parsed) is not dict:
        raise ValueError("top-level JSON value must be an object")
    return parsed


def resource_snapshot() -> dict[str, Any]:
    mem_available = 0
    mem_total = 0
    with Path("/proc/meminfo").open(encoding="utf-8") as stream:
        for line in stream:
            name, value = line.split(":", 1)
            kib = int(value.strip().split()[0])
            if name == "MemAvailable":
                mem_available = kib * 1024
            elif name == "MemTotal":
                mem_total = kib * 1024
    load_average = Path("/proc/loadavg").read_text(encoding="utf-8").strip()
    allowed = "unknown"
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("Cpus_allowed_list:"):
            allowed = line.split(":", 1)[1].strip()
            break
    disk = shutil.disk_usage("/")
    return {
        "captured_at": utc_now(),
        "mem_total_bytes": mem_total,
        "mem_available_bytes": mem_available,
        "loadavg": load_average,
        "cpus_allowed_list": allowed,
        "root_disk_free_bytes": disk.free,
    }


def is_finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_text(encoded)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )


def sanitize_label(label: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in label)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if type(data) is not dict:
        raise ConfigurationError(f"expected JSON object: {path}")
    return data


def _run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=True)
