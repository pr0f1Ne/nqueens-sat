"""Kiểm thử điều phối và lưu trữ benchmark SAT."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from benchmark import BenchmarkConfig, create_run_directory, run_benchmark
from sat_solver import SolveResult


TEST_DIRECTORY = Path(__file__).resolve().parent


def fake_sat(n: int, timeout: float, encoding: str) -> SolveResult:
    solution = [(0, 1), (1, 3), (2, 0), (3, 2)] if n == 4 else None
    return SolveResult(
        n=n, method="SAT", solver="Glucose3", encoding=encoding,
        status="SAT", solution=solution, build_time=0.1, load_time=0.2,
        solve_time=0.3, total_time=0.6, num_variables=n * n,
        num_board_variables=n * n, num_auxiliary_variables=0,
        num_clauses=84, validated=True, backend_status="SAT",
        timeout_seconds=timeout, parent_observed_time=0.7,
    )


def fake_cpsat(
    n: int, timeout: float, random_seed: int, num_workers: int
) -> SolveResult:
    return SolveResult(
        n=n, method="CP-SAT", solver="OR-Tools CP-SAT", encoding=None,
        status="SAT", solution=[(0, 1), (1, 3), (2, 0), (3, 2)],
        build_time=0.1, load_time=None, solve_time=0.2, total_time=0.3,
        num_variables=n, num_board_variables=None,
        num_auxiliary_variables=None, num_clauses=None, validated=True,
        backend_status="OPTIMAL", timeout_seconds=timeout,
        parent_observed_time=0.4, solver_seed=random_seed,
        solver_workers=num_workers, internal_timeout_seconds=None,
    )


def fake_cplex(
    n: int, timeout: float, random_seed: int, num_threads: int
) -> SolveResult:
    return SolveResult(
        n=n, method="CPLEX_MIP", solver="IBM ILOG CPLEX", encoding=None,
        status="SAT", solution=[(0, 1), (1, 3), (2, 0), (3, 2)],
        build_time=0.1, load_time=None, solve_time=0.2, total_time=0.3,
        num_variables=n * n, num_board_variables=n * n,
        num_auxiliary_variables=0, num_clauses=None, validated=True,
        backend_status="101: integer optimal solution", timeout_seconds=timeout,
        parent_observed_time=0.4, solver_seed=random_seed,
        solver_workers=num_threads, internal_timeout_seconds=None,
        stop_condition="mip.limits.solutions=1",
    )


class BenchmarkStorageTests(unittest.TestCase):
    def test_cplex_case_has_mip_metadata_and_no_sat_encoding(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as temporary:
            config = BenchmarkConfig(
                n_values=[4], encodings=["pairwise"], repeats=1,
                timeout_seconds=10.0, output_directory=temporary,
                methods=["cplex_mip"], cplex_seed=13, cplex_threads=1,
            )
            run_directory = run_benchmark(config, solve_cplex=fake_cplex)
            record = json.loads(
                (run_directory / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )
            self.assertEqual(record["method"], "CPLEX_MIP")
            self.assertIsNone(record["encoding"])
            self.assertEqual(record["solver_seed"], 13)
            self.assertEqual(record["solver_workers"], 1)
            self.assertEqual(record["stop_condition"], "mip.limits.solutions=1")

    def test_sat_and_cpsat_cases_share_schema_without_fake_encoding(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as temporary:
            config = BenchmarkConfig(
                n_values=[4], encodings=["pairwise", "bitwise"], repeats=1,
                timeout_seconds=10.0, output_directory=temporary,
                methods=["sat", "cpsat"], cpsat_seed=11, cpsat_workers=1,
            )
            run_directory = run_benchmark(
                config, solve=fake_sat, solve_cpsat=fake_cpsat
            )
            records = [
                json.loads(line)
                for line in (run_directory / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 3)
            cp_record = next(record for record in records if record["method"] == "CP-SAT")
            self.assertIsNone(cp_record["encoding"])
            self.assertIsNone(cp_record["num_clauses"])
            self.assertIsNone(cp_record["load_time"])
            self.assertEqual(cp_record["solver_seed"], 11)
            self.assertEqual(cp_record["solver_workers"], 1)

    def test_run_ids_are_unique_and_existing_runs_are_preserved(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as temporary:
            root = Path(temporary)
            fixed = datetime(2026, 10, 17, tzinfo=timezone.utc)
            first_id, first_path = create_run_directory(root, fixed)
            marker = first_path / "keep.txt"
            marker.write_text("old", encoding="utf-8")
            second_id, second_path = create_run_directory(root, fixed)
            self.assertNotEqual(first_id, second_id)
            self.assertTrue(first_path.is_dir())
            self.assertTrue(second_path.is_dir())
            self.assertEqual(marker.read_text(encoding="utf-8"), "old")

    def test_results_can_be_read_from_jsonl_and_csv(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as temporary:
            config = BenchmarkConfig(
                n_values=[4], encodings=["pairwise", "sequential"],
                repeats=2, timeout_seconds=10.0,
                output_directory=temporary,
            )
            run_directory = run_benchmark(config, solve=fake_sat)
            records = [
                json.loads(line)
                for line in (run_directory / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            with (run_directory / "results.csv").open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            solutions = [
                json.loads(line)
                for line in (run_directory / "solutions.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 4)
            self.assertEqual(len(rows), 4)
            self.assertEqual(len(solutions), 4)
            self.assertTrue(all(record["solution_id"] for record in records))
            self.assertEqual({record["repeat_index"] for record in records}, {0, 1})
            self.assertTrue((run_directory / "config.json").is_file())
            environment = json.loads((run_directory / "environment.json").read_text(encoding="utf-8"))
            self.assertIn("source_hashes", environment)
            self.assertNotIn("environment_variables", environment)

    def test_case_exception_is_recorded_and_later_cases_continue(self):
        calls = 0

        def sometimes_fails(n: int, timeout: float, encoding: str) -> SolveResult:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("deliberate case failure")
            return fake_sat(n, timeout, encoding)

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as temporary:
            config = BenchmarkConfig(
                n_values=[4], encodings=["pairwise"], repeats=2,
                timeout_seconds=10.0, output_directory=temporary,
            )
            run_directory = run_benchmark(config, solve=sometimes_fails)
            records = [
                json.loads(line)
                for line in (run_directory / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["status"] for record in records], ["ERROR", "SAT"])
            self.assertIn("deliberate case failure", records[0]["message"])

    def test_backend_unavailable_is_not_called_repeatedly(self):
        calls = 0

        def unavailable(n: int, timeout: float, encoding: str) -> SolveResult:
            nonlocal calls
            calls += 1
            return SolveResult(
                n=n, method="SAT", solver="Glucose3", encoding=encoding,
                status="UNAVAILABLE", solution=None, build_time=None,
                load_time=None, solve_time=None, total_time=None,
                num_variables=None, num_board_variables=None,
                num_auxiliary_variables=None, num_clauses=None,
                validated=None, backend_status="IMPORT_ERROR",
                message="mock backend missing", timeout_seconds=timeout,
            )

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as temporary:
            config = BenchmarkConfig(
                n_values=[4, 8], encodings=["pairwise"], repeats=2,
                timeout_seconds=10.0, output_directory=temporary,
            )
            run_directory = run_benchmark(config, solve=unavailable)
            records = [
                json.loads(line)
                for line in (run_directory / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(calls, 1)
            self.assertEqual(len(records), 4)
            self.assertTrue(all(record["status"] == "UNAVAILABLE" for record in records))


if __name__ == "__main__":
    unittest.main()
