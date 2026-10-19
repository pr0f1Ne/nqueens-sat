"""Tổng hợp và vẽ biểu đồ benchmark N-Queens từ dữ liệu JSONL thật."""

import argparse
import csv
import json
import os
from pathlib import Path
from statistics import median, quantiles

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


STATUSES = ("SAT", "UNSAT", "TIMEOUT", "UNKNOWN", "ERROR", "UNAVAILABLE")
TIME_FIELDS = (
    "build_time", "load_time", "solve_time", "total_time", "parent_observed_time"
)


def load_records(run_directory: Path, group: str) -> list[dict]:
    path = run_directory / "raw_results.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for record in records:
        record["group"] = group
        record["configuration"] = configuration_name(record)
        if record["status"] == "SAT" and record["validated"] is not True:
            raise ValueError(f"Nghiệm SAT chưa validated: {record['case_id']} tại {path}")
    return records


def configuration_name(record: dict) -> str:
    if record["method"] == "SAT":
        return f"SAT-{record['encoding']}"
    return record["method"]


def summarize(records: list[dict]) -> list[dict]:
    keys = sorted({(r["group"], r["configuration"], r["n"]) for r in records})
    rows = []
    for group, configuration, n in keys:
        subset = [
            r for r in records
            if (r["group"], r["configuration"], r["n"])
            == (group, configuration, n)
        ]
        successful = [r for r in subset if r["status"] == "SAT" and r["validated"]]
        row = {
            "group": group,
            "configuration": configuration,
            "n": n,
            "repeats_planned": len(subset),
            "successful_time_samples": len(successful),
        }
        for status in STATUSES:
            row[f"count_{status.lower()}"] = sum(r["status"] == status for r in subset)
        for field in TIME_FIELDS:
            values = [r[field] for r in successful if r[field] is not None]
            row[f"{field}_median_seconds"] = median(values) if values else None
            row[f"{field}_iqr_seconds"] = _iqr(values)
            row[f"{field}_min_seconds"] = min(values) if values else None
            row[f"{field}_max_seconds"] = max(values) if values else None
        first = subset[0]
        row.update({
            "num_board_variables": first["num_board_variables"],
            "num_auxiliary_variables": first["num_auxiliary_variables"],
            "num_variables": first["num_variables"],
            "num_clauses": first["num_clauses"],
            "timeout_seconds": first["timeout_seconds"],
            "source_run_id": first["run_id"],
        })
        rows.append(row)
    return rows


def _iqr(values: list[float]) -> float | None:
    if len(values) < 2:
        return 0.0 if values else None
    q1, _, q3 = quantiles(values, n=4, method="inclusive")
    return q3 - q1


def write_summary(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_time(rows: list[dict], output: Path, sources: str) -> None:
    groups = sorted({row["group"] for row in rows})
    figure, axes = plt.subplots(len(groups), 1, figsize=(8, 4.2 * len(groups)), squeeze=False)
    markers = ["o", "s", "^", "D", "P", "X"]
    for axis, group in zip(axes[:, 0], groups):
        group_rows = [row for row in rows if row["group"] == group]
        configurations = sorted({row["configuration"] for row in group_rows})
        for marker, configuration in zip(markers, configurations):
            subset = sorted(
                [row for row in group_rows if row["configuration"] == configuration],
                key=lambda row: row["n"],
            )
            successful = [row for row in subset if row["parent_observed_time_median_seconds"] is not None]
            axis.plot(
                [row["n"] for row in successful],
                [row["parent_observed_time_median_seconds"] for row in successful],
                marker=marker, label=configuration,
            )
            timed_out = [row for row in subset if row["count_timeout"]]
            if timed_out:
                axis.scatter(
                    [row["n"] for row in timed_out],
                    [row["timeout_seconds"] for row in timed_out],
                    marker="x", color="red", s=70,
                    label=f"{configuration} TIMEOUT",
                )
        axis.set_title(f"Nhóm {group}")
        axis.set_xlabel("N (kích thước bàn cờ)")
        axis.set_ylabel("Trung vị thời gian cha quan sát (giây)")
        axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend(fontsize=8)
    figure.suptitle("Thời gian tìm một nghiệm N-Queens (5 phép đo lặp)")
    figure.text(0.01, 0.01, f"Nguồn: {sources}. TIMEOUT là dấu x tại giới hạn, không vào trung vị.", fontsize=8)
    figure.tight_layout(rect=(0, 0.04, 1, 0.95))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_sat_size(rows: list[dict], output: Path, sources: str) -> None:
    sat_rows = {
        (row["configuration"], row["n"]): row
        for row in rows if row["group"] == "A" and row["configuration"].startswith("SAT-")
    }
    configurations = sorted({key[0] for key in sat_rows})
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    for configuration in configurations:
        subset = sorted(
            [row for (config, _), row in sat_rows.items() if config == configuration],
            key=lambda row: row["n"],
        )
        axes[0].plot([r["n"] for r in subset], [r["num_variables"] for r in subset], marker="o", label=configuration)
        axes[1].plot([r["n"] for r in subset], [r["num_clauses"] for r in subset], marker="o", label=configuration)
    axes[0].set_title("Tổng số biến")
    axes[1].set_title("Số clause CNF")
    for axis in axes:
        axis.set_xlabel("N (kích thước bàn cờ)")
        axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend(fontsize=8)
    axes[0].set_ylabel("Số biến")
    axes[1].set_ylabel("Số clause")
    figure.suptitle("Kích thước mô hình SAT theo encoding")
    figure.text(0.01, 0.01, f"Nguồn: {sources}; số đếm lấy trực tiếp từ CNF đã chạy.", fontsize=8)
    figure.tight_layout(rect=(0, 0.04, 1, 0.95))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_phases(rows: list[dict], output: Path, sources: str) -> None:
    group_rows = [
        row for row in rows
        if row["group"] in {"B", "C"} and row["successful_time_samples"] > 0
    ]
    labels = [f"{row['configuration']}\nN={row['n']}" for row in group_rows]
    build = [row["build_time_median_seconds"] or 0.0 for row in group_rows]
    load = [row["load_time_median_seconds"] or 0.0 for row in group_rows]
    solve = [row["solve_time_median_seconds"] or 0.0 for row in group_rows]
    x = list(range(len(labels)))
    figure, axis = plt.subplots(figsize=(16, 7))
    axis.bar(x, build, label="Dựng mô hình")
    axis.bar(x, load, bottom=build, label="Nạp backend")
    bottom = [a + b for a, b in zip(build, load)]
    axis.bar(x, solve, bottom=bottom, label="Giải")
    axis.set_xticks(x, labels, rotation=60, ha="right", fontsize=8)
    axis.set_ylabel("Trung vị thời gian đo được (giây)")
    axis.set_yscale("log")
    axis.set_title("Tách thời gian dựng, nạp và giải - các backend so sánh")
    axis.grid(True, axis="y", which="both", alpha=0.3)
    axis.legend()
    figure.text(
        0.01, 0.01,
        f"Nguồn: {sources}. Thành phần null không được đo và không được diễn giải là thời gian 0.",
        fontsize=8,
    )
    figure.tight_layout(rect=(0, 0.05, 1, 0.96))
    figure.savefig(output, dpi=180)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group-a", type=Path, required=True)
    parser.add_argument("--group-b", type=Path, required=True)
    parser.add_argument("--group-c", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    records = load_records(args.group_a, "A") + load_records(args.group_b, "B")
    if args.group_c is not None:
        records += load_records(args.group_c, "C")
    rows = summarize(records)
    write_summary(args.output / "summary.csv", rows)
    source_paths = [args.group_a, args.group_b]
    if args.group_c is not None:
        source_paths.append(args.group_c)
    sources = ", ".join(path.name for path in source_paths)
    plot_time(rows, args.output / "time_by_n.png", sources)
    plot_sat_size(rows, args.output / "sat_model_size.png", sources)
    plot_phases(rows, args.output / "phase_times.png", sources)
    print(json.dumps({"output": str(args.output), "summary_rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
