"""Kiểm tra nghiệm N-Queens trực tiếp, độc lập với mô hình SAT."""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ValidationResult:
    """Kết quả kiểm tra cùng danh sách lý do khi nghiệm không hợp lệ."""

    is_valid: bool
    errors: list[str]


def validate_solution(n: int, queens: Iterable[tuple[int, int]]) -> ValidationResult:
    """Kiểm tra số hậu, biên, hàng, cột và cả hai hướng đường chéo."""

    errors: list[str] = []
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        return ValidationResult(False, ["N phải là số nguyên dương"])

    positions = list(queens)
    if len(positions) != n:
        errors.append(f"Cần đúng {n} quân hậu, nhận được {len(positions)}")

    malformed = [position for position in positions if not _is_coordinate(position)]
    if malformed:
        errors.append("Mỗi vị trí phải là một cặp số nguyên (row, col)")
        return ValidationResult(False, errors)

    out_of_bounds = [
        (row, col)
        for row, col in positions
        if not (0 <= row < n and 0 <= col < n)
    ]
    if out_of_bounds:
        errors.append(f"Tọa độ ngoài bàn cờ: {out_of_bounds}")

    if len({row for row, _ in positions}) != len(positions):
        errors.append("Có hai quân hậu cùng hàng")
    if len({col for _, col in positions}) != len(positions):
        errors.append("Có hai quân hậu cùng cột")
    if len({row - col for row, col in positions}) != len(positions):
        errors.append("Có hai quân hậu cùng đường chéo r-c")
    if len({row + col for row, col in positions}) != len(positions):
        errors.append("Có hai quân hậu cùng đường chéo r+c")

    return ValidationResult(not errors, errors)


def _is_coordinate(position: object) -> bool:
    """Nhận diện một cặp tọa độ nguyên và loại bool một cách tường minh."""

    return (
        isinstance(position, (tuple, list))
        and len(position) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) for value in position)
    )
