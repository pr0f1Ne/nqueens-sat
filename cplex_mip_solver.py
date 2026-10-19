"""Giải N-Queens bằng IBM CPLEX MIP với dependency/runtime tùy chọn."""

from math import isfinite
from time import perf_counter

from sat_encoding import validate_n
from sat_solver import SolveResult
from timeout_runner import run_in_worker
from validator import validate_solution


STOP_CONDITION = "mip.limits.solutions=1"


def solve_n_queens_cplex_mip(
    n: int,
    timeout: float | None = None,
    random_seed: int = 0,
    num_threads: int = 1,
) -> SolveResult:
    """Giải trực tiếp hoặc bằng deadline worker ngoài dùng chung."""

    validate_n(n)
    _validate_parameters(timeout, random_seed, num_threads)
    if timeout is None:
        return _solve_n_queens_cplex_mip_task(n, random_seed, num_threads)

    outcome = run_in_worker(
        _solve_n_queens_cplex_mip_task,
        (n, random_seed, num_threads),
        float(timeout),
    )
    if outcome.status == "COMPLETED":
        result = outcome.value
        if not isinstance(result, SolveResult):
            return _worker_error_result(
                n, random_seed, num_threads, float(timeout),
                outcome.parent_observed_time,
                "Worker trả về dữ liệu không đúng kiểu SolveResult",
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
            message=(
                f"Vượt giới hạn ngoài {float(timeout)} giây tính từ lúc tiến "
                "trình cha bắt đầu spawn; worker đã được thu hồi"
            ),
        )
    return _worker_error_result(
        n, random_seed, num_threads, float(timeout),
        outcome.parent_observed_time,
        outcome.error or "Worker lỗi mà không cung cấp chi tiết",
    )


def _solve_n_queens_cplex_mip_task(
    n: int, random_seed: int = 0, num_threads: int = 1
) -> SolveResult:
    """Dựng MIP nhị phân, dừng ở nghiệm đầu tiên và xác thực."""

    validate_n(n)
    total_start = perf_counter()
    try:
        cplex = _load_cplex()
    except ImportError as error:
        return _base_result(
            n, "UNAVAILABLE", "IMPORT_ERROR", random_seed, num_threads,
            total_time=perf_counter() - total_start, message=str(error),
        )

    build_start = perf_counter()
    try:
        model = cplex.Cplex()
        _silence_streams(model)
        model.parameters.threads.set(num_threads)
        model.parameters.randomseed.set(random_seed)
        model.parameters.mip.limits.solutions.set(1)
        names = [_variable_name(row, col) for row in range(n) for col in range(n)]
        model.variables.add(
            names=names,
            types=[model.variables.type.binary] * (n * n),
        )
        expressions = []
        senses = []
        rhs = []
        for row in range(n):
            expressions.append(cplex.SparsePair(
                ind=[_variable_name(row, col) for col in range(n)],
                val=[1.0] * n,
            ))
            senses.append("E")
            rhs.append(1.0)
        for col in range(n):
            expressions.append(cplex.SparsePair(
                ind=[_variable_name(row, col) for row in range(n)],
                val=[1.0] * n,
            ))
            senses.append("E")
            rhs.append(1.0)
        for groups in (_diagonal_groups(n, difference=True), _diagonal_groups(n, difference=False)):
            for variables in groups:
                expressions.append(cplex.SparsePair(
                    ind=variables, val=[1.0] * len(variables)
                ))
                senses.append("L")
                rhs.append(1.0)
        model.linear_constraints.add(lin_expr=expressions, senses=senses, rhs=rhs)
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
        model.solve()
        solve_time = perf_counter() - solve_start
        status_code = model.solution.get_status()
        status_text = model.solution.get_status_string()
        backend_status = f"{status_code}: {status_text}"
        primal_feasible = model.solution.is_primal_feasible()
    except Exception as error:
        status, backend = _classify_exception(error)
        return _base_result(
            n, status, backend, random_seed, num_threads,
            build_time=build_time, solve_time=perf_counter() - solve_start,
            total_time=perf_counter() - total_start, message=repr(error),
        )

    if primal_feasible:
        values = model.solution.get_values()
        tolerance = model.parameters.mip.tolerances.integrality.get()
        solution, decoding_error = _decode_binary_solution(n, values, tolerance)
        if decoding_error is not None:
            return _base_result(
                n, "ERROR", backend_status, random_seed, num_threads,
                build_time=build_time, solve_time=solve_time,
                total_time=perf_counter() - total_start,
                message=decoding_error,
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

    common_status = _map_status_without_solution(model.solution.status, status_code)
    return _base_result(
        n, common_status, backend_status, random_seed, num_threads,
        build_time=build_time, solve_time=solve_time,
        total_time=perf_counter() - total_start,
    )


def _decode_binary_solution(
    n: int, values: list[float], tolerance: float
) -> tuple[list[tuple[int, int]], str | None]:
    """Kiểm tra tính nguyên trước khi đổi giá trị 1 thành tọa độ."""

    if len(values) != n * n:
        return [], f"CPLEX trả {len(values)} giá trị, cần {n * n}"
    solution: list[tuple[int, int]] = []
    for index, value in enumerate(values):
        nearest = round(value)
        if nearest not in (0, 1) or abs(value - nearest) > tolerance:
            return [], (
                f"Giá trị nhị phân không nguyên trong dung sai {tolerance}: "
                f"biến {index} có giá trị {value}"
            )
        if nearest == 1:
            solution.append((index // n, index % n))
    return solution, None


def _map_status_without_solution(statuses, status_code: int) -> str:
    """Chỉ công nhận vô nghiệm khi CPLEX chứng minh MIP infeasible."""

    if status_code in {statuses.MIP_infeasible, statuses.infeasible}:
        return "UNSAT"
    return "UNKNOWN"


def _classify_exception(error: Exception) -> tuple[str, str]:
    """Chỉ lỗi runtime/license nhận diện được mới là UNAVAILABLE."""

    message = str(error).lower()
    unavailable_markers = (
        "license", "licence", "not licensed", "cplex runtime",
        "failed to initialize cplex", "no such file or directory",
        "the specified module could not be found", "community edition",
        "problem size limits exceeded", "error  1016",
    )
    if any(marker in message for marker in unavailable_markers):
        return "UNAVAILABLE", "RUNTIME_OR_LICENSE_ERROR"
    return "ERROR", "CPLEX_EXCEPTION"


def _base_result(
    n: int, status: str, backend_status: str, random_seed: int,
    num_threads: int, *, solution=None, build_time=None, solve_time=None,
    total_time=None, validated=None, message=None, timeout_seconds=None,
    parent_observed_time=None,
) -> SolveResult:
    return SolveResult(
        n=n, method="CPLEX_MIP", solver="IBM ILOG CPLEX", encoding=None,
        status=status, solution=solution, build_time=build_time,
        load_time=None, solve_time=solve_time, total_time=total_time,
        num_variables=n * n, num_board_variables=n * n,
        num_auxiliary_variables=0, num_clauses=None,
        validated=validated, backend_status=backend_status, message=message,
        timeout_seconds=timeout_seconds,
        parent_observed_time=parent_observed_time,
        solver_seed=random_seed, solver_workers=num_threads,
        internal_timeout_seconds=None, stop_condition=STOP_CONDITION,
    )


def _worker_error_result(
    n: int, random_seed: int, num_threads: int, timeout: float,
    parent_observed_time: float, message: str,
) -> SolveResult:
    return _base_result(
        n, "ERROR", "WORKER_ERROR", random_seed, num_threads,
        timeout_seconds=timeout, parent_observed_time=parent_observed_time,
        message=message,
    )


def _diagonal_groups(n: int, difference: bool) -> list[list[str]]:
    groups: dict[int, list[str]] = {}
    for row in range(n):
        for col in range(n):
            key = row - col if difference else row + col
            groups.setdefault(key, []).append(_variable_name(row, col))
    return list(groups.values())


def _variable_name(row: int, col: int) -> str:
    return f"x_{row}_{col}"


def _silence_streams(model) -> None:
    model.set_log_stream(None)
    model.set_results_stream(None)
    model.set_warning_stream(None)
    model.set_error_stream(None)


def _validate_parameters(timeout, random_seed, num_threads) -> None:
    if timeout is not None and (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout phải là số dương hữu hạn")
    if isinstance(random_seed, bool) or not isinstance(random_seed, int) or random_seed < 0:
        raise ValueError("random_seed phải là số nguyên không âm")
    if isinstance(num_threads, bool) or not isinstance(num_threads, int) or num_threads <= 0:
        raise ValueError("num_threads phải là số nguyên dương")


def _load_cplex():
    """Import muộn để thiếu package không ảnh hưởng SAT/CP-SAT."""

    import cplex

    return cplex
