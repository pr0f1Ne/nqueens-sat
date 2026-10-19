"""Giải N-Queens bằng Gurobi MIP với dependency/license tùy chọn."""

from math import isfinite
from time import perf_counter

from sat_encoding import validate_n
from sat_solver import SolveResult
from timeout_runner import run_in_worker
from validator import validate_solution


STOP_CONDITION = "SolutionLimit=1"


def solve_n_queens_gurobi_mip(
    n: int, timeout: float | None = None, random_seed: int = 0,
    num_threads: int = 1,
) -> SolveResult:
    validate_n(n)
    _validate_parameters(timeout, random_seed, num_threads)
    if timeout is None:
        return _solve_task(n, random_seed, num_threads)
    outcome = run_in_worker(_solve_task, (n, random_seed, num_threads), float(timeout))
    if outcome.status == "COMPLETED":
        result = outcome.value
        if not isinstance(result, SolveResult):
            return _base_result(
                n, "ERROR", "WORKER_ERROR", random_seed, num_threads,
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
            n, "TIMEOUT", "OUTER_TIMEOUT", random_seed, num_threads,
            timeout_seconds=float(timeout),
            parent_observed_time=outcome.parent_observed_time,
            message=f"Vượt deadline ngoài {float(timeout)} giây; worker đã được thu hồi",
        )
    return _base_result(
        n, "ERROR", "WORKER_ERROR", random_seed, num_threads,
        timeout_seconds=float(timeout),
        parent_observed_time=outcome.parent_observed_time,
        message=outcome.error or "Worker lỗi mà không cung cấp chi tiết",
    )


def _solve_task(n: int, random_seed: int, num_threads: int) -> SolveResult:
    total_start = perf_counter()
    try:
        gp = _load_gurobi()
    except ImportError as error:
        return _base_result(
            n, "UNAVAILABLE", "IMPORT_ERROR", random_seed, num_threads,
            total_time=perf_counter() - total_start, message=str(error),
        )

    build_start = perf_counter()
    try:
        model = gp.Model("nqueens")
        model.Params.OutputFlag = 0
        model.Params.Threads = num_threads
        model.Params.Seed = random_seed
        model.Params.SolutionLimit = 1
        variables = model.addVars(n, n, vtype=gp.GRB.BINARY, name="x")
        for row in range(n):
            model.addConstr(gp.quicksum(variables[row, col] for col in range(n)) == 1)
        for col in range(n):
            model.addConstr(gp.quicksum(variables[row, col] for row in range(n)) == 1)
        for groups in (_diagonal_groups(n, True), _diagonal_groups(n, False)):
            for group in groups:
                model.addConstr(gp.quicksum(variables[row, col] for row, col in group) <= 1)
        model.update()
    except Exception as error:
        status, backend = _classify_exception(error)
        return _base_result(
            n, status, backend, random_seed, num_threads,
            build_time=perf_counter() - build_start,
            total_time=perf_counter() - total_start, message=repr(error),
        )
    build_time = perf_counter() - build_start

    solve_start = perf_counter()
    try:
        model.optimize()
        solve_time = perf_counter() - solve_start
        backend_status = f"{model.Status}: {_status_name(gp.GRB, model.Status)}"
    except Exception as error:
        status, backend = _classify_exception(error)
        return _base_result(
            n, status, backend, random_seed, num_threads,
            build_time=build_time, solve_time=perf_counter() - solve_start,
            total_time=perf_counter() - total_start, message=repr(error),
        )

    if model.SolCount > 0:
        tolerance = float(model.Params.IntFeasTol)
        values = [variables[row, col].X for row in range(n) for col in range(n)]
        solution, error = _decode_binary_solution(n, values, tolerance)
        if error:
            return _base_result(
                n, "ERROR", backend_status, random_seed, num_threads,
                build_time=build_time, solve_time=solve_time,
                total_time=perf_counter() - total_start, message=error,
            )
        validation = validate_solution(n, solution)
        return _base_result(
            n, "SAT" if validation.is_valid else "ERROR", backend_status,
            random_seed, num_threads, solution=solution,
            build_time=build_time, solve_time=solve_time,
            total_time=perf_counter() - total_start,
            validated=validation.is_valid,
            message=None if validation.is_valid else "; ".join(validation.errors),
        )
    status = "UNSAT" if model.Status == gp.GRB.INFEASIBLE else "UNKNOWN"
    return _base_result(
        n, status, backend_status, random_seed, num_threads,
        build_time=build_time, solve_time=solve_time,
        total_time=perf_counter() - total_start,
    )


def _decode_binary_solution(n, values, tolerance):
    if len(values) != n * n:
        return [], f"Gurobi trả {len(values)} giá trị, cần {n * n}"
    solution = []
    for index, value in enumerate(values):
        nearest = round(value)
        if nearest not in (0, 1) or abs(value - nearest) > tolerance:
            return [], f"Giá trị biến {index}={value} nằm ngoài dung sai tích phân {tolerance}"
        if nearest == 1:
            solution.append((index // n, index % n))
    return solution, None


def _classify_exception(error: Exception) -> tuple[str, str]:
    message = str(error).lower()
    markers = (
        "license", "licence", "model too large", "size-limited",
        "not found", "could not be loaded", "failed to create environment",
    )
    return (
        ("UNAVAILABLE", "RUNTIME_OR_LICENSE_ERROR")
        if any(marker in message for marker in markers)
        else ("ERROR", "GUROBI_EXCEPTION")
    )


def _status_name(grb, code: int) -> str:
    names = {
        grb.LOADED: "LOADED", grb.OPTIMAL: "OPTIMAL",
        grb.INFEASIBLE: "INFEASIBLE", grb.INF_OR_UNBD: "INF_OR_UNBD",
        grb.TIME_LIMIT: "TIME_LIMIT", grb.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        grb.INTERRUPTED: "INTERRUPTED",
    }
    return names.get(code, "STATUS_UNKNOWN")


def _base_result(
    n, status, backend_status, random_seed, num_threads, *, solution=None,
    build_time=None, solve_time=None, total_time=None, validated=None,
    message=None, timeout_seconds=None, parent_observed_time=None,
):
    return SolveResult(
        n=n, method="GUROBI_MIP", solver="Gurobi Optimizer", encoding=None,
        status=status, solution=solution, build_time=build_time, load_time=None,
        solve_time=solve_time, total_time=total_time, num_variables=n * n,
        num_board_variables=n * n, num_auxiliary_variables=0,
        num_clauses=None, validated=validated, backend_status=backend_status,
        message=message, timeout_seconds=timeout_seconds,
        parent_observed_time=parent_observed_time, solver_seed=random_seed,
        solver_workers=num_threads, internal_timeout_seconds=None,
        stop_condition=STOP_CONDITION,
    )


def _diagonal_groups(n, difference):
    groups = {}
    for row in range(n):
        for col in range(n):
            groups.setdefault(row - col if difference else row + col, []).append((row, col))
    return list(groups.values())


def _validate_parameters(timeout, random_seed, num_threads):
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, (int, float))
        or not isfinite(timeout) or timeout <= 0
    ):
        raise ValueError("timeout phải là số dương hữu hạn")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
        raise ValueError("random_seed phải là số nguyên không âm")
    if isinstance(num_threads, bool) or not isinstance(num_threads, int) or num_threads <= 0:
        raise ValueError("num_threads phải là số nguyên dương")


def _load_gurobi():
    import gurobipy
    return gurobipy
