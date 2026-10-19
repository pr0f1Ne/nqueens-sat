"""Giải N-Queens bằng OR-Tools CP-SAT với dependency tùy chọn."""

from math import isfinite
from time import perf_counter

from sat_encoding import validate_n
from sat_solver import SolveResult
from timeout_runner import run_in_worker
from validator import validate_solution


def solve_n_queens_cpsat(
    n: int,
    timeout: float | None = None,
    random_seed: int = 0,
    num_workers: int = 1,
) -> SolveResult:
    """Giải trực tiếp hoặc dùng deadline ngoài worker giống backend SAT."""

    validate_n(n)
    _validate_parameters(timeout, random_seed, num_workers)
    if timeout is None:
        return _solve_n_queens_cpsat_task(n, random_seed, num_workers)

    outcome = run_in_worker(
        _solve_n_queens_cpsat_task, (n, random_seed, num_workers), float(timeout)
    )
    if outcome.status == "COMPLETED":
        result = outcome.value
        if not isinstance(result, SolveResult):
            return _worker_error_result(
                n, random_seed, num_workers, float(timeout),
                outcome.parent_observed_time,
                "Worker trả về dữ liệu không đúng kiểu SolveResult",
            )
        return SolveResult(**(result.__dict__ | {
            "timeout_seconds": float(timeout),
            "parent_observed_time": outcome.parent_observed_time,
        }))
    if outcome.status == "TIMEOUT":
        return SolveResult(
            n=n, method="CP-SAT", solver="OR-Tools CP-SAT", encoding=None,
            status="TIMEOUT", solution=None, build_time=None, load_time=None,
            solve_time=None, total_time=None, num_variables=None,
            num_board_variables=None, num_auxiliary_variables=None,
            num_clauses=None, validated=None, backend_status="OUTER_TIMEOUT",
            message=(
                f"Vượt giới hạn ngoài {float(timeout)} giây tính từ lúc tiến "
                "trình cha bắt đầu spawn; worker đã được thu hồi"
            ),
            timeout_seconds=float(timeout),
            parent_observed_time=outcome.parent_observed_time,
            solver_seed=random_seed, solver_workers=num_workers,
            internal_timeout_seconds=None,
        )
    return _worker_error_result(
        n, random_seed, num_workers, float(timeout),
        outcome.parent_observed_time,
        outcome.error or "Worker lỗi mà không cung cấp chi tiết",
    )


def _solve_n_queens_cpsat_task(
    n: int, random_seed: int = 0, num_workers: int = 1
) -> SolveResult:
    """Dựng mô hình q[r], giải một nghiệm và xác thực độc lập."""

    validate_n(n)
    total_start = perf_counter()
    try:
        cp_model = _load_cp_model()
    except ImportError as error:
        return _base_result(
            n, "UNAVAILABLE", "IMPORT_ERROR", random_seed, num_workers,
            total_time=perf_counter() - total_start, message=str(error),
        )

    build_start = perf_counter()
    try:
        model = cp_model.CpModel()
        queens = [model.new_int_var(0, n - 1, f"q[{row}]") for row in range(n)]
        model.add_all_different(queens)
        model.add_all_different([queens[row] + row for row in range(n)])
        model.add_all_different([queens[row] - row for row in range(n)])
    except Exception as error:
        return _base_result(
            n, "ERROR", "MODEL_BUILD_ERROR", random_seed, num_workers,
            build_time=perf_counter() - build_start,
            total_time=perf_counter() - total_start, message=repr(error),
        )
    build_time = perf_counter() - build_start

    try:
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = num_workers
        solver.parameters.random_seed = random_seed
        solve_start = perf_counter()
        status_code = solver.solve(model)
        solve_time = perf_counter() - solve_start
        backend_status = solver.status_name(status_code)
    except Exception as error:
        return _base_result(
            n, "ERROR", "SOLVE_ERROR", random_seed, num_workers,
            build_time=build_time, total_time=perf_counter() - total_start,
            message=repr(error),
        )

    status = _map_status(cp_model, status_code)
    if status == "SAT":
        solution = [(row, solver.value(queens[row])) for row in range(n)]
        validation = validate_solution(n, solution)
        return _base_result(
            n, "SAT" if validation.is_valid else "ERROR", backend_status,
            random_seed, num_workers, solution=solution,
            build_time=build_time, solve_time=solve_time,
            total_time=perf_counter() - total_start,
            validated=validation.is_valid,
            message=None if validation.is_valid else "; ".join(validation.errors),
        )
    return _base_result(
        n, status, backend_status, random_seed, num_workers,
        build_time=build_time, solve_time=solve_time,
        total_time=perf_counter() - total_start,
    )


def _map_status(cp_model, status_code) -> str:
    """Ánh xạ trạng thái CP-SAT mà không biến UNKNOWN thành UNSAT."""

    if status_code in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return "SAT"
    if status_code == cp_model.INFEASIBLE:
        return "UNSAT"
    if status_code == cp_model.MODEL_INVALID:
        return "ERROR"
    return "UNKNOWN"


def _base_result(
    n: int, status: str, backend_status: str, random_seed: int,
    num_workers: int, *, solution=None, build_time=None, solve_time=None,
    total_time=None, validated=None, message=None,
) -> SolveResult:
    """Tạo schema chung; CP-SAT không có encoding AMO hoặc số clause CNF."""

    return SolveResult(
        n=n, method="CP-SAT", solver="OR-Tools CP-SAT", encoding=None,
        status=status, solution=solution, build_time=build_time,
        load_time=None, solve_time=solve_time, total_time=total_time,
        num_variables=n, num_board_variables=None,
        num_auxiliary_variables=None, num_clauses=None,
        validated=validated, backend_status=backend_status, message=message,
        solver_seed=random_seed, solver_workers=num_workers,
        internal_timeout_seconds=None,
    )


def _worker_error_result(
    n: int, random_seed: int, num_workers: int, timeout: float,
    parent_observed_time: float, message: str,
) -> SolveResult:
    return SolveResult(
        n=n, method="CP-SAT", solver="OR-Tools CP-SAT", encoding=None,
        status="ERROR", solution=None, build_time=None, load_time=None,
        solve_time=None, total_time=None, num_variables=None,
        num_board_variables=None, num_auxiliary_variables=None,
        num_clauses=None, validated=None, backend_status="WORKER_ERROR",
        message=message, timeout_seconds=timeout,
        parent_observed_time=parent_observed_time,
        solver_seed=random_seed, solver_workers=num_workers,
        internal_timeout_seconds=None,
    )


def _validate_parameters(timeout, random_seed, num_workers) -> None:
    if timeout is not None and (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout phải là số dương hữu hạn")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
        raise ValueError("random_seed phải là số nguyên không âm")
    if isinstance(num_workers, bool) or not isinstance(num_workers, int) or num_workers <= 0:
        raise ValueError("num_workers phải là số nguyên dương")


def _load_cp_model():
    """Import muộn để thiếu OR-Tools chỉ làm backend CP-SAT UNAVAILABLE."""

    from ortools.sat.python import cp_model

    return cp_model
