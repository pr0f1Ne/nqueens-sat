"""Mã hóa bài toán N-Queens thành CNF với nhiều encoding AMO."""

from dataclasses import dataclass
from itertools import combinations

from pysat.card import CardEnc, EncType, IDPool


SUPPORTED_ENCODINGS = ("pairwise", "sequential", "bitwise")
_PYSAT_ENCODINGS = {"sequential": EncType.seqcounter, "bitwise": EncType.bitwise}


@dataclass(frozen=True)
class CNFFormula:
    """CNF N-Queens cùng các số đếm biến được định nghĩa tường minh."""

    n: int
    clauses: list[list[int]]
    num_board_variables: int
    num_auxiliary_variables: int
    num_variables: int
    encoding: str = "pairwise"


def validate_n(n: int) -> None:
    """Báo lỗi nếu N không phải số nguyên dương (bool không được xem là int)."""

    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("N phải là số nguyên dương")


def validate_encoding(encoding: str) -> None:
    """Yêu cầu tên encoding thuộc tập được CLI và thư viện hỗ trợ."""

    if encoding not in SUPPORTED_ENCODINGS:
        choices = ", ".join(SUPPORTED_ENCODINGS)
        raise ValueError(f"Encoding phải là một trong: {choices}")


def board_var(n: int, row: int, col: int) -> int:
    """Trả ID SAT của ô (row, col) theo công thức row * N + col + 1."""

    validate_n(n)
    if not (0 <= row < n and 0 <= col < n):
        raise ValueError("Tọa độ phải nằm trong bàn cờ")
    return row * n + col + 1


def add_at_least_one(clauses: list[list[int]], variables: list[int]) -> None:
    """Thêm một clause ALO; nhóm rỗng bị từ chối vì ALO rỗng là bất khả thi."""

    if not variables:
        raise ValueError("Nhóm ALO không được rỗng")
    clauses.append(list(variables))


def add_pairwise_at_most_one(
    clauses: list[list[int]], variables: list[int]
) -> None:
    """Wrapper public cũ: thêm AMO pairwise, không cần biến phụ."""

    for first, second in combinations(variables, 2):
        clauses.append([-first, -second])


def add_at_most_one(
    clauses: list[list[int]],
    variables: list[int],
    encoding: str = "pairwise",
    vpool: IDPool | None = None,
) -> None:
    """Thêm AMO tại điểm chọn chung; nhóm rỗng/một biến không sinh clause."""

    validate_encoding(encoding)
    if len(variables) <= 1:
        return
    if encoding == "pairwise":
        add_pairwise_at_most_one(clauses, variables)
        return
    if vpool is None:
        raise ValueError("Encoding có biến phụ yêu cầu một IDPool dùng chung")
    encoded = CardEnc.atmost(
        lits=variables,
        bound=1,
        vpool=vpool,
        encoding=_PYSAT_ENCODINGS[encoding],
    )
    clauses.extend(encoded.clauses)


def add_exactly_one(
    clauses: list[list[int]],
    variables: list[int],
    encoding: str = "pairwise",
    vpool: IDPool | None = None,
) -> None:
    """Thêm EO dưới dạng một clause ALO trực tiếp cộng AMO đã chọn."""

    add_at_least_one(clauses, variables)
    add_at_most_one(clauses, variables, encoding=encoding, vpool=vpool)


def encode_n_queens(n: int, encoding: str = "pairwise") -> CNFFormula:
    """Tạo CNF N-Queens; chỉ chiến lược mã hóa AMO thay đổi."""

    validate_n(n)
    validate_encoding(encoding)
    board_variables = n * n
    vpool = IDPool(start_from=board_variables + 1)
    clauses: list[list[int]] = []

    for row in range(n):
        add_exactly_one(clauses, [board_var(n, row, col) for col in range(n)], encoding, vpool)
    for col in range(n):
        add_exactly_one(clauses, [board_var(n, row, col) for row in range(n)], encoding, vpool)

    descending: dict[int, list[int]] = {}
    ascending: dict[int, list[int]] = {}
    for row in range(n):
        for col in range(n):
            variable = board_var(n, row, col)
            descending.setdefault(row - col, []).append(variable)
            ascending.setdefault(row + col, []).append(variable)

    for diagonal in (*descending.values(), *ascending.values()):
        add_at_most_one(clauses, diagonal, encoding, vpool)

    # IDPool cấp liên tiếp từ N²+1. Đếm theo miền ID đã cấp, không suy ra từ
    # max literal xuất hiện (cách đó sai nếu một cơ chế cấp ID có khoảng trống).
    auxiliary_variables = vpool.top - board_variables
    total_variables = board_variables + auxiliary_variables
    return CNFFormula(
        n=n,
        clauses=clauses,
        num_board_variables=board_variables,
        num_auxiliary_variables=auxiliary_variables,
        num_variables=total_variables,
        encoding=encoding,
    )


def encode_n_queens_pairwise(n: int) -> CNFFormula:
    """Wrapper tương thích API cũ cho baseline pairwise."""

    return encode_n_queens(n, encoding="pairwise")
