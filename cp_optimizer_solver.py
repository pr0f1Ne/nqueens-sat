"""Giải N-Queens bằng IBM CP Optimizer thông qua DOcplex.CP."""

from math import isfinite
from pathlib import Path
import sys
from time import perf_counter

from sat_encoding import validate_n
from sat_solver import SolveResult
from timeout_runner import run_in_worker
from validator import validate_solution


STOP_CONDITION = "first feasible satisfaction solution; no objective"


def solve_n_queens_cp_optimizer(
    n: int, timeout: float | None = None, random_seed: int = 0,
    num_workers: int = 1,
) -> SolveResult:
    validate_n(n)
    _validate_parameters(timeout, random_seed, num_workers)
    if timeout is None:
        return _solve_task(n, random_seed, num_workers)
    outcome = run_in_worker(_solve_task, (n, random_seed, num_workers), float(timeout))
    if outcome.status == "COMPLETED":
        result = outcome.value
        if not isinstance(result, SolveResult):
            return _base_result(
                n, "ERROR", "WORKER_ERROR", random_seed, num_workers,
                timeout_seconds=float(timeout),
                parent_observed_time=outcome.parent_observed_time,
                message="Worker trả về dữ liệu không đúng kiểu SolveResult",
            )
        return SolveResult(**(result.__dict__ | {
            "timeout_seconds": float(timeout),
            "parent_observed_time": outcome.parent_observed_time,
        }))
    if outcome.status == "TIMEOUT":
        return _base_result(
            n, "TIMEOUT", "OUTER_TIMEOUT", random_seed, num_workers,
            timeout_seconds=float(timeout),
            parent_observed_time=outcome.parent_observed_time,
            message=f"Vượt deadline ngoài {float(timeout)} giây; worker đã được thu hồi",
        )
    return _base_result(
        n, "ERROR", "WORKER_ERROR", random_seed, num_workers,
        timeout_seconds=float(timeout),
        parent_observed_time=outcome.parent_observed_time,
        message=outcome.error or "Worker lỗi mà không cung cấp chi tiết",
    )


def _solve_task(n: int, random_seed: int, num_workers: int) -> SolveResult:
    total_start = perf_counter()
    try:
        CpoModel, execfile = _load_cp_optimizer()
    except (ImportError, FileNotFoundError) as error:
        return _base_result(
            n, "UNAVAILABLE", "IMPORT_OR_RUNTIME_ERROR", random_seed, num_workers,
            total_time=perf_counter() - total_start, message=str(error),
        )

    build_start = perf_counter()
    try:
        model = CpoModel(name="nqueens")
        queens = [model.integer_var(0, n - 1, f"q_{row}") for row in range(n)]
        model.add(model.all_diff(queens))
        model.add(model.all_diff([queens[row] + row for row in range(n)]))
        model.add(model.all_diff([queens[row] - row for row in range(n)]))
    except Exception as error:
        return _base_result(
            n, "ERROR", "MODEL_BUILD_ERROR", random_seed, num_workers,
            build_time=perf_counter() - build_start,
            total_time=perf_counter() - total_start, message=repr(error),
        )
    build_time = perf_counter() - build_start

    solve_start = perf_counter()
    try:
        result = model.solve(
            Workers=num_workers, RandomSeed=random_seed, LogVerbosity="Quiet",
            execfile=str(execfile),
        )
        solve_time = perf_counter() - solve_start
        solve_status = str(result.get_solve_status())
        infos = result.get_solver_infos()
        search_status = infos.get("SearchStatus")
        stop_cause = infos.get("SearchStopCause")
        backend_status = f"{solve_status}; {search_status}; {stop_cause}"
    except Exception as error:
        status, backend = _classify_exception(error)
        return _base_result(
            n, status, backend, random_seed, num_workers,
            build_time=build_time, solve_time=perf_counter() - solve_start,
            total_time=perf_counter() - total_start, message=repr(error),
        )

    if solve_status in {"Feasible", "Optimal"}:
        solution = [(row, int(result[queens[row]])) for row in range(n)]
        validation = validate_solution(n, solution)
        return _base_result(
            n, "SAT" if validation.is_valid else "ERROR", backend_status,
            random_seed, num_workers, solution=solution, build_time=build_time,
            solve_time=solve_time, total_time=perf_counter() - total_start,
            validated=validation.is_valid,
            message=None if validation.is_valid else "; ".join(validation.errors),
        )
    status = "UNSAT" if solve_status == "Infeasible" else "UNKNOWN"
    return _base_result(
        n, status, backend_status, random_seed, num_workers,
        build_time=build_time, solve_time=solve_time,
        total_time=perf_counter() - total_start,
    )


def _classify_exception(error: Exception) -> tuple[str, str]:
    message = str(error).lower()
    markers = (
        "executable file", "does not exists", "not found", "license",
        "licence", "problem size limit", "community edition",
    )
    return (
        ("UNAVAILABLE", "RUNTIME_OR_LICENSE_ERROR")
        if any(marker in message for marker in markers)
        else ("ERROR", "CP_OPTIMIZER_EXCEPTION")
    )


def _base_result(
    n, status, backend_status, random_seed, num_workers, *, solution=None,
    build_time=None, solve_time=None, total_time=None, validated=None,
    message=None, timeout_seconds=None, parent_observed_time=None,
):
    return SolveResult(
        n=n, method="CP_OPTIMIZER", solver="IBM ILOG CP Optimizer",
        encoding=None, status=status, solution=solution, build_time=build_time,
        load_time=None, solve_time=solve_time, total_time=total_time,
        num_variables=n, num_board_variables=None,
        num_auxiliary_variables=None, num_clauses=None, validated=validated,
        backend_status=backend_status, message=message,
        timeout_seconds=timeout_seconds,
        parent_observed_time=parent_observed_time, solver_seed=random_seed,
        solver_workers=num_workers, internal_timeout_seconds=None,
        stop_condition=STOP_CONDITION,
    )


def _load_cp_optimizer():
    from docplex.cp.model import CpoModel

    executable = Path(sys.executable).resolve().parent / "cpoptimizer.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Không tìm thấy CP Optimizer runtime: {executable}")
    return CpoModel, executable


def _validate_parameters(timeout, random_seed, num_workers):
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, (int, float))
        or not isfinite(timeout) or timeout <= 0
    ):
        raise ValueError("timeout phải là số dương hữu hạn")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
        raise ValueError("random_seed phải là số nguyên không âm")
    if isinstance(num_workers, bool) or not isinstance(num_workers, int) or num_workers <= 0:
        raise ValueError("num_workers phải là số nguyên dương")
