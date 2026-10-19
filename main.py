"""Giao diện dòng lệnh cho các phương pháp giải N-Queens."""

import argparse
import json
import sys
from dataclasses import asdict

from cplex_mip_solver import solve_n_queens_cplex_mip
from cp_optimizer_solver import solve_n_queens_cp_optimizer
from gurobi_mip_solver import solve_n_queens_gurobi_mip
from sat_encoding import SUPPORTED_ENCODINGS
from cpsat_solver import solve_n_queens_cpsat
from sat_solver import solve_n_queens


def parse_args() -> argparse.Namespace:
    """Đọc N, phương pháp, encoding SAT và giới hạn thời gian."""

    parser = argparse.ArgumentParser(description="Giải N-Queens bằng SAT, CP hoặc MIP")
    parser.add_argument("n", type=int, help="Kích thước bàn cờ (số nguyên dương)")
    parser.add_argument(
        "--method", choices=("sat", "cpsat", "cplex_mip", "gurobi_mip", "cp_optimizer"), default="sat",
        help="Phương pháp giải (mặc định: sat)",
    )
    parser.add_argument(
        "--encoding",
        choices=SUPPORTED_ENCODINGS,
        default=None,
        help="Encoding AMO chỉ dành cho SAT (SAT mặc định: pairwise)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        help="Giới hạn toàn tác vụ bằng worker process, đơn vị giây",
    )
    parser.add_argument(
        "--solver-seed", type=_non_negative_int, default=0,
        help="Seed backend CP/MIP; không áp dụng cho SAT (mặc định: 0)",
    )
    args = parser.parse_args()
    if args.method != "sat" and args.encoding is not None:
        parser.error("--encoding chỉ áp dụng cho method sat")
    if args.method == "sat" and args.solver_seed != 0:
        parser.error("--solver-seed chỉ áp dụng cho backend CP/MIP")
    return args


def _positive_float(value: str) -> float:
    """Chuyển timeout CLI và từ chối số không, số âm hoặc không hữu hạn."""

    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timeout phải là số dương") from error
    if number <= 0 or number == float("inf") or number != number:
        raise argparse.ArgumentTypeError("timeout phải là số dương hữu hạn")
    return number


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("solver seed phải là số nguyên không âm") from error
    if number < 0:
        raise argparse.ArgumentTypeError("solver seed phải là số nguyên không âm")
    return number


def main() -> int:
    """Chạy bộ giải, in JSON có thể đọc bằng máy và trả mã thoát phù hợp."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        if args.method == "sat":
            result = solve_n_queens(
                args.n, timeout=args.timeout, encoding=args.encoding or "pairwise"
            )
        elif args.method == "cpsat":
            result = solve_n_queens_cpsat(
                args.n, timeout=args.timeout, random_seed=args.solver_seed,
                num_workers=1,
            )
        elif args.method == "cplex_mip":
            result = solve_n_queens_cplex_mip(
                args.n, timeout=args.timeout, random_seed=args.solver_seed,
                num_threads=1,
            )
        elif args.method == "gurobi_mip":
            result = solve_n_queens_gurobi_mip(
                args.n, timeout=args.timeout, random_seed=args.solver_seed,
                num_threads=1,
            )
        else:
            result = solve_n_queens_cp_optimizer(
                args.n, timeout=args.timeout, random_seed=args.solver_seed,
                num_workers=1,
            )
    except ValueError as error:
        print(json.dumps({"status": "ERROR", "message": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status in {"SAT", "UNSAT"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
