"""Gọi Glucose3, giải mã mô hình SAT và xác thực nghiệm."""

from dataclasses import dataclass
from math import isfinite
from time import perf_counter

from sat_encoding import board_var, encode_n_queens, validate_encoding, validate_n
from validator import validate_solution
from timeout_runner import run_in_worker


@dataclass(frozen=True)
class SolveResult:
    """Cấu trúc kết quả thống nhất cho mọi encoding SAT được hỗ trợ."""

    n: int
    method: str
    solver: str
    encoding: str | None
    status: str
    solution: list[tuple[int, int]] | None
    build_time: float | None
    load_time: float | None
    solve_time: float | None
    total_time: float | None
    num_variables: int | None
    num_board_variables: int | None
    num_auxiliary_variables: int | None
    num_clauses: int | None
    validated: bool | None
    backend_status: str
    message: str | None = None
    timeout_seconds: float | None = None
    parent_observed_time: float | None = None
    solver_seed: int | None = None
    solver_workers: int | None = None
    internal_timeout_seconds: float | None = None
    stop_condition: str | None = None


def decode_model(n: int, model: list[int]) -> list[tuple[int, int]]:
    """Chỉ lấy literal dương của biến bàn cờ 1..N² rồi đổi thành tọa độ."""

    validate_n(n)
    positive_board_variables = {
        literal for literal in model if 1 <= literal <= n * n
    }
    return [
        (row, col)
        for row in range(n)
        for col in range(n)
        if board_var(n, row, col) in positive_board_variables
    ]


def solve_n_queens(
    n: int, timeout: float | None = None, encoding: str = "pairwise"
) -> SolveResult:
    """Giải trực tiếp, hoặc giới hạn toàn tác vụ bằng một worker process."""

    validate_n(n)
    validate_encoding(encoding)
    if timeout is None:
        return _solve_n_queens_task(n, encoding)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout phải là số dương")

    outcome = run_in_worker(_solve_n_queens_task, (n, encoding), float(timeout))
    if outcome.status == "COMPLETED":
        result = outcome.value
        if not isinstance(result, SolveResult):
            return _worker_error_result(
                n, encoding, float(timeout), outcome.parent_observed_time,
                "Worker trả về dữ liệu không đúng kiểu SolveResult",
            )
        return _with_parent_timing(result, float(timeout), outcome.parent_observed_time)
    if outcome.status == "TIMEOUT":
        return SolveResult(
            n=n, method="SAT", solver="Glucose3", encoding=encoding,
            status="TIMEOUT", solution=None, build_time=None, load_time=None,
            solve_time=None, total_time=None, num_variables=None,
            num_board_variables=None, num_auxiliary_variables=None,
            num_clauses=None, validated=None, backend_status="TIMEOUT",
            message=(
                f"Vượt giới hạn {float(timeout)} giây tính từ lúc tiến trình "
                "cha bắt đầu khởi động worker; worker đã được thu hồi"
            ),
            timeout_seconds=float(timeout),
            parent_observed_time=outcome.parent_observed_time,
        )
    return _worker_error_result(
        n, encoding, float(timeout), outcome.parent_observed_time,
        outcome.error or "Worker lỗi mà không cung cấp chi tiết",
    )


def _solve_n_queens_task(n: int, encoding: str = "pairwise") -> SolveResult:
    """Toàn tác vụ trong worker: dựng CNF, nạp, giải, giải mã, xác thực."""

    validate_n(n)
    total_start = perf_counter()

    build_start = perf_counter()
    formula = encode_n_queens(n, encoding)
    build_time = perf_counter() - build_start

    try:
        Glucose3 = _load_glucose3()
    except ImportError as error:
        return _unavailable_result(n, formula, build_time, total_start, error)

    load_start = perf_counter()
    try:
        solver = Glucose3(bootstrap_with=formula.clauses)
    except Exception as error:
        return SolveResult(
            n=n, method="SAT", solver="Glucose3", encoding=encoding,
            status="ERROR", solution=None, build_time=build_time,
            load_time=None, solve_time=None,
            total_time=perf_counter() - total_start,
            num_variables=formula.num_variables,
            num_board_variables=formula.num_board_variables,
            num_auxiliary_variables=formula.num_auxiliary_variables,
            num_clauses=len(formula.clauses), validated=None,
            backend_status="LOAD_ERROR", message=repr(error),
        )
    load_time = perf_counter() - load_start

    try:
        solve_start = perf_counter()
        try:
            is_sat = solver.solve()
        except Exception as error:
            return SolveResult(
                n=n, method="SAT", solver="Glucose3", encoding=encoding,
                status="ERROR", solution=None, build_time=build_time,
                load_time=load_time, solve_time=None,
                total_time=perf_counter() - total_start,
                num_variables=formula.num_variables,
                num_board_variables=formula.num_board_variables,
                num_auxiliary_variables=formula.num_auxiliary_variables,
                num_clauses=len(formula.clauses), validated=None,
                backend_status="SOLVE_ERROR", message=repr(error),
            )
        solve_time = perf_counter() - solve_start

        if is_sat is False:
            return SolveResult(
                n=n, method="SAT", solver="Glucose3", encoding=encoding,
                status="UNSAT", solution=None, build_time=build_time,
                load_time=load_time, solve_time=solve_time,
                total_time=perf_counter() - total_start,
                num_variables=formula.num_variables,
                num_board_variables=formula.num_board_variables,
                num_auxiliary_variables=formula.num_auxiliary_variables,
                num_clauses=len(formula.clauses), validated=None,
                backend_status="UNSAT",
            )

        if is_sat is not True:
            return SolveResult(
                n=n, method="SAT", solver="Glucose3", encoding=encoding,
                status="UNKNOWN", solution=None, build_time=build_time,
                load_time=load_time, solve_time=solve_time,
                total_time=perf_counter() - total_start,
                num_variables=formula.num_variables,
                num_board_variables=formula.num_board_variables,
                num_auxiliary_variables=formula.num_auxiliary_variables,
                num_clauses=len(formula.clauses), validated=None,
                backend_status="UNKNOWN",
                message="Backend không trả về SAT hoặc UNSAT",
            )

        solution = decode_model(n, solver.get_model() or [])
        validation = validate_solution(n, solution)
        status = "SAT" if validation.is_valid else "ERROR"
        return SolveResult(
            n=n, method="SAT", solver="Glucose3", encoding=encoding,
            status=status, solution=solution, build_time=build_time,
            load_time=load_time, solve_time=solve_time,
            total_time=perf_counter() - total_start,
            num_variables=formula.num_variables,
            num_board_variables=formula.num_board_variables,
            num_auxiliary_variables=formula.num_auxiliary_variables,
            num_clauses=len(formula.clauses), validated=validation.is_valid,
            backend_status="SAT",
            message=None if validation.is_valid else "; ".join(validation.errors),
        )
    finally:
        solver.delete()


def _unavailable_result(n, formula, build_time, total_start, error):
    """Tạo kết quả UNAVAILABLE khi môi trường thiếu python-sat."""

    return SolveResult(
        n=n, method="SAT", solver="Glucose3", encoding=formula.encoding,
        status="UNAVAILABLE", solution=None, build_time=build_time,
        load_time=None, solve_time=None,
        total_time=perf_counter() - total_start, num_variables=formula.num_variables,
        num_board_variables=formula.num_board_variables,
        num_auxiliary_variables=formula.num_auxiliary_variables,
        num_clauses=len(formula.clauses), validated=None, backend_status="IMPORT_ERROR",
        message=str(error),
    )


def _load_glucose3():
    """Điểm nạp backend tách riêng để kiểm thử UNAVAILABLE bằng mock."""

    from pysat.solvers import Glucose3

    return Glucose3


def _with_parent_timing(
    result: SolveResult,
    timeout: float,
    parent_observed_time: float,
) -> SolveResult:
    """Gắn thời gian tiến trình cha mà không thay số đo bên trong worker."""

    values = result.__dict__ | {
        "timeout_seconds": timeout,
        "parent_observed_time": parent_observed_time,
    }
    return SolveResult(**values)


def _worker_error_result(
    n: int,
    encoding: str,
    timeout: float,
    parent_observed_time: float,
    message: str,
) -> SolveResult:
    """Biểu diễn lỗi hạ tầng worker, không giả lập thời gian chưa đo."""

    return SolveResult(
        n=n, method="SAT", solver="Glucose3", encoding=encoding,
        status="ERROR", solution=None, build_time=None, load_time=None,
        solve_time=None, total_time=None, num_variables=None,
        num_board_variables=None, num_auxiliary_variables=None,
        num_clauses=None, validated=None, backend_status="WORKER_ERROR",
        message=message, timeout_seconds=timeout,
        parent_observed_time=parent_observed_time,
    )
