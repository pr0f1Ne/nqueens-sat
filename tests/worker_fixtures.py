"""Các tác vụ cấp module dùng để kiểm thử worker với chế độ spawn."""

from time import sleep


def slow_worker(delay: float) -> str:
    """Cố ý chạy chậm để kiểm tra timeout mà không phụ thuộc kích thước N."""

    sleep(delay)
    return "finished"


def fast_worker(value: int) -> int:
    """Hoàn thành trước hạn và trả một giá trị có thể kiểm tra."""

    return value * 2


def failing_worker() -> None:
    """Cố ý phát sinh lỗi để kiểm tra trạng thái lỗi worker."""

    raise RuntimeError("intentional worker failure")
