"""Chạy một tác vụ trong worker process với giới hạn thời gian thực sự."""

from dataclasses import dataclass
from math import isfinite
import multiprocessing
from multiprocessing.connection import Connection
from time import perf_counter
import traceback
from typing import Any, Callable


@dataclass(frozen=True)
class WorkerOutcome:
    """Kết quả quan sát từ tiến trình cha sau khi đã thu hồi worker."""

    status: str
    value: Any
    parent_observed_time: float
    worker_pid: int | None
    worker_alive_after_cleanup: bool
    error: str | None = None


def _worker_entry(
    connection: Connection,
    target: Callable[..., Any],
    args: tuple[Any, ...],
) -> None:
    """Thực thi target và gửi về payload hoặc lỗi có traceback."""

    try:
        connection.send(("COMPLETED", target(*args), None))
    except BaseException:
        connection.send(("ERROR", None, traceback.format_exc()))
    finally:
        connection.close()


def run_in_worker(
    target: Callable[..., Any],
    args: tuple[Any, ...],
    timeout_seconds: float,
) -> WorkerOutcome:
    """Chạy target bằng spawn; timeout thì dừng và thu hồi worker hữu hạn."""

    if not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout phải là số dương")

    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker_entry,
        args=(send_connection, target, args),
        name="nqueens-worker",
    )
    observed_start = perf_counter()
    try:
        process.start()
    except Exception:
        receive_connection.close()
        send_connection.close()
        process.close()
        return WorkerOutcome(
            status="ERROR",
            value=None,
            parent_observed_time=perf_counter() - observed_start,
            worker_pid=None,
            worker_alive_after_cleanup=False,
            error=traceback.format_exc(),
        )
    worker_pid = process.pid
    send_connection.close()

    status = "ERROR"
    value: Any = None
    error: str | None = None
    try:
        remaining = max(
            0.0,
            timeout_seconds - (perf_counter() - observed_start),
        )
        if receive_connection.poll(remaining):
            try:
                status, value, error = receive_connection.recv()
            except EOFError:
                error = "Worker kết thúc mà không gửi kết quả"
        else:
            status = "TIMEOUT"
            error = f"Worker vượt quá giới hạn {timeout_seconds} giây"
    finally:
        receive_connection.close()
        _stop_and_reap(process, force=status == "TIMEOUT")

    observed_time = perf_counter() - observed_start
    alive_after_cleanup = process.is_alive()
    if not alive_after_cleanup:
        process.close()
    return WorkerOutcome(
        status=status,
        value=value,
        parent_observed_time=observed_time,
        worker_pid=worker_pid,
        worker_alive_after_cleanup=alive_after_cleanup,
        error=error,
    )


def _stop_and_reap(process: multiprocessing.Process, force: bool = False) -> None:
    """Thu hồi worker mà không có bất kỳ join vô hạn nào."""

    if force and process.is_alive():
        process.terminate()
    process.join(timeout=0.25 if not force else 1.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=1.0)
    if process.is_alive():
        process.kill()
        process.join(timeout=1.0)
