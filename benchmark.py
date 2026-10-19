"""Benchmark tuần tự các encoding SAT N-Queens và lưu dữ liệu tăng dần."""

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from math import isfinite
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import uuid
from typing import Callable

from cplex_mip_solver import solve_n_queens_cplex_mip
from cp_optimizer_solver import solve_n_queens_cp_optimizer
from cpsat_solver import solve_n_queens_cpsat
from gurobi_mip_solver import solve_n_queens_gurobi_mip
from sat_encoding import SUPPORTED_ENCODINGS, validate_encoding, validate_n
from sat_solver import SolveResult, solve_n_queens


TIMEOUT_SCOPE = (
    "Mỗi lần chạy: từ trước khi tiến trình cha spawn worker đến sau khi nhận "
    "kết quả và thu hồi worker; gồm build, load, solve, decode và validate."
)
SOURCE_FILES = (
    "benchmark.py",
    "cplex_mip_solver.py",
    "cp_optimizer_solver.py",
    "cpsat_solver.py",
    "gurobi_mip_solver.py",
    "sat_encoding.py",
    "sat_solver.py",
    "timeout_runner.py",
    "validator.py",
    "requirements.txt",
)
CSV_FIELDS = (
    "run_id", "case_id", "repeat_index", "timestamp", "n", "method",
    "solver", "encoding", "status", "backend_status", "validated",
    "build_time", "load_time", "solve_time", "total_time",
    "parent_observed_time", "timeout_seconds", "timeout_scope",
    "num_board_variables", "num_auxiliary_variables", "num_variables",
    "num_clauses", "benchmark_order_seed", "shuffle",
    "solver_seed", "solver_seed_control", "solver_workers",
    "solver_workers_control", "internal_timeout_seconds", "stop_condition",
    "message", "solution_id",
)


@dataclass(frozen=True)
class BenchmarkConfig:
    """Cấu hình đầy đủ của một phiên benchmark SAT."""

    n_values: list[int]
    encodings: list[str]
    repeats: int
    timeout_seconds: float
    output_directory: str
    seed: int = 0
    shuffle: bool = False
    methods: list[str] | None = None
    cpsat_seed: int = 0
    cpsat_workers: int = 1
    cplex_seed: int = 0
    cplex_threads: int = 1
    gurobi_seed: int = 0
    gurobi_threads: int = 1
    cp_optimizer_seed: int = 0
    cp_optimizer_workers: int = 1


def create_run_directory(output_directory: Path, now: datetime | None = None) -> tuple[str, Path]:
    """Tạo thư mục run mới; hậu tố ngẫu nhiên ngăn ghi đè phiên cũ."""

    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%S.%fZ")
    for _ in range(100):
        run_id = f"nqueens-{timestamp}-{uuid.uuid4().hex[:8]}"
        run_directory = output_directory / run_id
        try:
            run_directory.mkdir()
        except FileExistsError:
            continue
        return run_id, run_directory
    raise RuntimeError("Không thể tạo run ID duy nhất sau 100 lần thử")


def collect_environment(project_root: Path) -> dict[str, object]:
    """Thu metadata tái lập cần thiết, không đọc biến môi trường người dùng."""

    git_commit, git_dirty = _git_metadata(project_root)
    return {
        "captured_at": _utc_now(),
        "os": platform.platform(),
        "cpu": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "ram_bytes": _physical_memory_bytes(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "dependencies": {
            "python-sat": _package_version("python-sat"),
            "ortools": _package_version("ortools"),
            "cplex": _package_version("cplex"),
            "docplex": _package_version("docplex"),
            "gurobipy": _package_version("gurobipy"),
        },
        "solvers": [
            {
                "method": "SAT", "name": "Glucose3",
                "class": "pysat.solvers.Glucose3", "seed": None,
                "seed_control": "not_exposed_by_current_api",
                "workers": None,
                "workers_control": "not_configurable_by_current_api",
            },
            {
                "method": "CP-SAT", "name": "OR-Tools CP-SAT",
                "class": "ortools.sat.python.cp_model.CpSolver",
                "dependency_version": _package_version("ortools"),
            },
            {
                "method": "CPLEX_MIP", "name": "IBM ILOG CPLEX",
                "class": "cplex.Cplex",
                "dependency_version": _package_version("cplex"),
                "distribution": "Community Edition",
            },
            {
                "method": "GUROBI_MIP", "name": "Gurobi Optimizer",
                "class": "gurobipy.Model",
                "dependency_version": _package_version("gurobipy"),
                "license": "restricted non-production license (runtime verified)",
            },
            {
                "method": "CP_OPTIMIZER", "name": "IBM ILOG CP Optimizer",
                "class": "docplex.cp.model.CpoModel",
                "dependency_version": _package_version("docplex"),
                "runtime": "cpoptimizer.exe (runtime verified)",
            },
        ],
        "git_commit": git_commit,
        "git_worktree_dirty": git_dirty,
        "source_hash_algorithm": "sha256",
        "source_hashes": _source_hashes(project_root),
    }


def run_benchmark(
    config: BenchmarkConfig,
    solve: Callable[..., SolveResult] = solve_n_queens,
    solve_cpsat: Callable[..., SolveResult] = solve_n_queens_cpsat,
    solve_cplex: Callable[..., SolveResult] = solve_n_queens_cplex_mip,
    solve_gurobi: Callable[..., SolveResult] = solve_n_queens_gurobi_mip,
    solve_cp_optimizer: Callable[..., SolveResult] = solve_n_queens_cp_optimizer,
) -> Path:
    """Chạy tuần tự, khởi tạo solver mới từng case và ghi ngay từng kết quả."""

    _validate_config(config)
    project_root = Path(__file__).resolve().parent
    run_id, run_directory = create_run_directory(Path(config.output_directory))
    methods = config.methods or ["sat"]
    expected_case_count = len(config.n_values) * config.repeats * (
        (len(config.encodings) if "sat" in methods else 0)
        + (1 if "cpsat" in methods else 0)
        + (1 if "cplex_mip" in methods else 0)
        + (1 if "gurobi_mip" in methods else 0)
        + (1 if "cp_optimizer" in methods else 0)
    )
    config_payload = asdict(config) | {
        "run_id": run_id,
        "created_at": _utc_now(),
        "methods": methods,
        "solvers": {
            "sat": "Glucose3", "cpsat": "OR-Tools CP-SAT",
            "cplex_mip": "IBM ILOG CPLEX",
            "gurobi_mip": "Gurobi Optimizer",
            "cp_optimizer": "IBM ILOG CP Optimizer",
        },
        "benchmark_order_seed_scope": (
            "Chỉ điều khiển thứ tự case khi shuffle=true; không phải solver seed."
        ),
        "execution": "sequential",
        "expected_case_count": expected_case_count,
        "timeout_scope": TIMEOUT_SCOPE,
        "internal_timeout_seconds": None,
        "cpsat_timeout_relation": (
            "Không đặt giới hạn nội bộ; chỉ deadline ngoài worker áp dụng cho toàn case."
        ),
        "cplex_timeout_relation": (
            "Không đặt giới hạn nội bộ; chỉ deadline ngoài worker áp dụng cho toàn case."
        ),
        "gurobi_timeout_relation": "Không đặt giới hạn nội bộ; deadline ngoài bao phủ toàn case.",
        "cp_optimizer_timeout_relation": "Không đặt giới hạn nội bộ; deadline ngoài bao phủ toàn case.",
    }
    _write_json(run_directory / "config.json", config_payload)
    _write_json(run_directory / "environment.json", collect_environment(project_root))

    cases: list[tuple[int, str, str | None, int]] = []
    for n in config.n_values:
        if "sat" in methods:
            cases.extend(
                (n, "sat", encoding, repeat_index)
                for encoding in config.encodings
                for repeat_index in range(config.repeats)
            )
        if "cpsat" in methods:
            cases.extend(
                (n, "cpsat", None, repeat_index)
                for repeat_index in range(config.repeats)
            )
        if "cplex_mip" in methods:
            cases.extend(
                (n, "cplex_mip", None, repeat_index)
                for repeat_index in range(config.repeats)
            )
        if "gurobi_mip" in methods:
            cases.extend((n, "gurobi_mip", None, repeat_index) for repeat_index in range(config.repeats))
        if "cp_optimizer" in methods:
            cases.extend((n, "cp_optimizer", None, repeat_index) for repeat_index in range(config.repeats))
    if config.shuffle:
        random.Random(config.seed).shuffle(cases)

    raw_path = run_directory / "raw_results.jsonl"
    csv_path = run_directory / "results.csv"
    solutions_path = run_directory / "solutions.jsonl"
    unavailable_backends: dict[str, str] = {}
    with (
        raw_path.open("x", encoding="utf-8", newline="") as raw_file,
        csv_path.open("x", encoding="utf-8", newline="") as csv_file,
        solutions_path.open("x", encoding="utf-8", newline="") as solutions_file,
    ):
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        csv_file.flush()
        for index, (n, method, encoding, repeat_index) in enumerate(cases, start=1):
            case_id = f"case-{index:04d}"
            timestamp = _utc_now()
            if method not in unavailable_backends:
                try:
                    if method == "sat":
                        result = solve(n, timeout=config.timeout_seconds, encoding=encoding)
                    elif method == "cpsat":
                        result = solve_cpsat(
                            n, timeout=config.timeout_seconds,
                            random_seed=config.cpsat_seed,
                            num_workers=config.cpsat_workers,
                        )
                    elif method == "cplex_mip":
                        result = solve_cplex(
                            n, timeout=config.timeout_seconds,
                            random_seed=config.cplex_seed,
                            num_threads=config.cplex_threads,
                        )
                    elif method == "gurobi_mip":
                        result = solve_gurobi(
                            n, timeout=config.timeout_seconds,
                            random_seed=config.gurobi_seed,
                            num_threads=config.gurobi_threads,
                        )
                    else:
                        result = solve_cp_optimizer(
                            n, timeout=config.timeout_seconds,
                            random_seed=config.cp_optimizer_seed,
                            num_workers=config.cp_optimizer_workers,
                        )
                except Exception as error:
                    result = _error_result(
                        n, method, encoding, config.timeout_seconds, error
                    )
            else:
                result = _skipped_unavailable_result(
                    n, method, encoding, config.timeout_seconds,
                    unavailable_backends[method], config,
                )
            if result.status == "UNAVAILABLE" and method not in unavailable_backends:
                unavailable_backends[method] = (
                    result.message or f"Backend {method} không khả dụng"
                )

            solution_id = None
            if result.solution is not None:
                solution_id = f"solution-{case_id}"
                _append_json_line(
                    solutions_file,
                    {
                        "run_id": run_id,
                        "solution_id": solution_id,
                        "case_id": case_id,
                        "n": result.n,
                        "method": result.method,
                        "encoding": result.encoding,
                        "solution": result.solution,
                    },
                )
            record = _result_record(
                run_id, case_id, repeat_index, timestamp, config, result, solution_id
            )
            _append_json_line(raw_file, record)
            writer.writerow({field: record.get(field) for field in CSV_FIELDS})
            csv_file.flush()
    return run_directory


def _result_record(
    run_id: str,
    case_id: str,
    repeat_index: int,
    timestamp: str,
    config: BenchmarkConfig,
    result: SolveResult,
    solution_id: str | None,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "case_id": case_id,
        "repeat_index": repeat_index,
        "timestamp": timestamp,
        "n": result.n,
        "method": result.method,
        "solver": result.solver,
        "encoding": result.encoding,
        "status": result.status,
        "backend_status": result.backend_status,
        "validated": result.validated,
        "build_time": result.build_time,
        "load_time": result.load_time,
        "solve_time": result.solve_time,
        "total_time": result.total_time,
        "parent_observed_time": result.parent_observed_time,
        "timeout_seconds": config.timeout_seconds,
        "timeout_scope": TIMEOUT_SCOPE,
        "num_board_variables": result.num_board_variables,
        "num_auxiliary_variables": result.num_auxiliary_variables,
        "num_variables": result.num_variables,
        "num_clauses": result.num_clauses,
        "benchmark_order_seed": config.seed if config.shuffle else None,
        "shuffle": config.shuffle,
        "solver_seed": result.solver_seed,
        "solver_seed_control": (
            "configured" if result.solver_seed is not None
            else "not_exposed_by_current_api"
        ),
        "solver_workers": result.solver_workers,
        "solver_workers_control": (
            "configured" if result.solver_workers is not None
            else "not_configurable_by_current_api"
        ),
        "internal_timeout_seconds": result.internal_timeout_seconds,
        "stop_condition": result.stop_condition,
        "message": result.message,
        "solution_id": solution_id,
    }


def _error_result(
    n: int, method: str, encoding: str | None, timeout: float, error: Exception
) -> SolveResult:
    result_method, solver = _method_identity(method)
    return SolveResult(
        n=n, method=result_method, solver=solver, encoding=encoding,
        status="ERROR", solution=None, build_time=None, load_time=None,
        solve_time=None, total_time=None, num_variables=None,
        num_board_variables=None, num_auxiliary_variables=None,
        num_clauses=None, validated=None, backend_status="BENCHMARK_EXCEPTION",
        message=f"{type(error).__name__}: {error}", timeout_seconds=timeout,
        parent_observed_time=None,
    )


def _skipped_unavailable_result(
    n: int, method: str, encoding: str | None, timeout: float, reason: str,
    config: BenchmarkConfig,
) -> SolveResult:
    result_method, solver = _method_identity(method)
    return SolveResult(
        n=n, method=result_method, solver=solver, encoding=encoding,
        status="UNAVAILABLE", solution=None, build_time=None, load_time=None,
        solve_time=None, total_time=None, num_variables=None,
        num_board_variables=None, num_auxiliary_variables=None,
        num_clauses=None, validated=None, backend_status="BACKEND_UNAVAILABLE",
        message=f"Không gọi lại backend sau lỗi không khả dụng: {reason}",
        timeout_seconds=timeout, parent_observed_time=None,
        solver_seed=_configured_seed(config, method),
        solver_workers=_configured_workers(config, method),
        stop_condition=(
            "mip.limits.solutions=1" if method == "cplex_mip" else
            "SolutionLimit=1" if method == "gurobi_mip" else
            "first feasible satisfaction solution; no objective" if method == "cp_optimizer" else None
        ),
    )


def _method_identity(method: str) -> tuple[str, str]:
    if method == "sat":
        return "SAT", "Glucose3"
    if method == "cpsat":
        return "CP-SAT", "OR-Tools CP-SAT"
    if method == "cplex_mip":
        return "CPLEX_MIP", "IBM ILOG CPLEX"
    if method == "gurobi_mip":
        return "GUROBI_MIP", "Gurobi Optimizer"
    return "CP_OPTIMIZER", "IBM ILOG CP Optimizer"


def _configured_seed(config: BenchmarkConfig, method: str) -> int | None:
    return {
        "sat": None, "cpsat": config.cpsat_seed, "cplex_mip": config.cplex_seed,
        "gurobi_mip": config.gurobi_seed, "cp_optimizer": config.cp_optimizer_seed,
    }[method]


def _configured_workers(config: BenchmarkConfig, method: str) -> int | None:
    return {
        "sat": None, "cpsat": config.cpsat_workers, "cplex_mip": config.cplex_threads,
        "gurobi_mip": config.gurobi_threads,
        "cp_optimizer": config.cp_optimizer_workers,
    }[method]


def _validate_config(config: BenchmarkConfig) -> None:
    for n in config.n_values:
        validate_n(n)
    if not config.n_values:
        raise ValueError("Danh sách N không được rỗng")
    for encoding in config.encodings:
        validate_encoding(encoding)
    if not config.encodings:
        raise ValueError("Danh sách encoding không được rỗng")
    methods = config.methods or ["sat"]
    if not methods or any(
        method not in {"sat", "cpsat", "cplex_mip", "gurobi_mip", "cp_optimizer"} for method in methods
    ):
        raise ValueError("Method benchmark không được hỗ trợ")
    if len(set(methods)) != len(methods):
        raise ValueError("Danh sách methods không được trùng")
    if (
        isinstance(config.cpsat_seed, bool)
        or not isinstance(config.cpsat_seed, int)
        or config.cpsat_seed < 0
    ):
        raise ValueError("CP-SAT seed phải là số nguyên không âm")
    if config.cpsat_workers != 1:
        raise ValueError("Benchmark so sánh ban đầu yêu cầu CP-SAT workers=1")
    if (
        isinstance(config.cplex_seed, bool)
        or not isinstance(config.cplex_seed, int)
        or config.cplex_seed < 0
    ):
        raise ValueError("CPLEX seed phải là số nguyên không âm")
    if config.cplex_threads != 1:
        raise ValueError("Benchmark so sánh ban đầu yêu cầu CPLEX threads=1")
    if config.gurobi_threads != 1:
        raise ValueError("Benchmark so sánh yêu cầu Gurobi threads=1")
    if config.cp_optimizer_workers != 1:
        raise ValueError("Benchmark so sánh yêu cầu CP Optimizer workers=1")
    for name, value in (("Gurobi", config.gurobi_seed), ("CP Optimizer", config.cp_optimizer_seed)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} seed phải là số nguyên không âm")
    if (
        isinstance(config.repeats, bool)
        or not isinstance(config.repeats, int)
        or config.repeats <= 0
    ):
        raise ValueError("Số lần lặp phải là số nguyên dương")
    if (
        isinstance(config.timeout_seconds, bool)
        or not isinstance(config.timeout_seconds, (int, float))
        or not isfinite(config.timeout_seconds)
        or config.timeout_seconds <= 0
    ):
        raise ValueError("Timeout phải là số dương")


def _git_metadata(project_root: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=project_root, check=True,
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=project_root, check=True,
            capture_output=True, text=True, timeout=5,
        ).stdout
        return commit or None, bool(status.strip())
    except (FileNotFoundError, subprocess.SubprocessError):
        return None, None


def _source_hashes(project_root: Path) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for relative_name in SOURCE_FILES:
        path = project_root / relative_name
        hashes[relative_name] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )
    return hashes


def _physical_memory_bytes() -> int | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical)
    except (AttributeError, OSError):
        pass
    return None


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: object) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")


def _append_json_line(output, payload: object) -> None:
    output.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    output.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark tuần tự SAT và CP-SAT N-Queens")
    parser.add_argument("--n", dest="n_values", nargs="+", type=int, required=True)
    parser.add_argument(
        "--methods", nargs="+", choices=("sat", "cpsat", "cplex_mip", "gurobi_mip", "cp_optimizer"),
        default=["sat"],
    )
    parser.add_argument(
        "--encodings", nargs="+", choices=SUPPORTED_ENCODINGS,
        default=list(SUPPORTED_ENCODINGS),
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--shuffle", action="store_true")
    parser.add_argument("--cpsat-seed", type=int, default=0)
    parser.add_argument("--cplex-seed", type=int, default=0)
    parser.add_argument("--gurobi-seed", type=int, default=0)
    parser.add_argument("--cp-optimizer-seed", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        run_directory = run_benchmark(BenchmarkConfig(
            n_values=args.n_values,
            encodings=args.encodings,
            repeats=args.repeats,
            timeout_seconds=args.timeout,
            output_directory=str(args.output),
            seed=args.seed,
            shuffle=args.shuffle,
            methods=args.methods,
            cpsat_seed=args.cpsat_seed,
            cpsat_workers=1,
            cplex_seed=args.cplex_seed,
            cplex_threads=1,
            gurobi_seed=args.gurobi_seed,
            gurobi_threads=1,
            cp_optimizer_seed=args.cp_optimizer_seed,
            cp_optimizer_workers=1,
        ))
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "ERROR", "message": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "COMPLETED", "run_directory": str(run_directory)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
