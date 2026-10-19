"""Kiểm thử backend OR-Tools CP-SAT và ánh xạ trạng thái."""

import unittest
from unittest.mock import patch

from cpsat_solver import _map_status, solve_n_queens_cpsat
from validator import validate_solution


class FakeStatuses:
    UNKNOWN = 0
    MODEL_INVALID = 1
    FEASIBLE = 2
    INFEASIBLE = 3
    OPTIMAL = 4


class CpSatSolverTests(unittest.TestCase):
    def test_required_cases_and_validator(self):
        expected = {1: "SAT", 2: "UNSAT", 3: "UNSAT", 4: "SAT", 8: "SAT"}
        for n, status in expected.items():
            with self.subTest(n=n):
                result = solve_n_queens_cpsat(n)
                self.assertEqual(result.status, status)
                self.assertEqual(result.method, "CP-SAT")
                self.assertIsNone(result.encoding)
                self.assertIsNone(result.load_time)
                self.assertIsNone(result.num_clauses)
                self.assertEqual(result.solver_workers, 1)
                self.assertEqual(result.solver_seed, 0)
                if status == "SAT":
                    self.assertTrue(result.validated)
                    self.assertTrue(validate_solution(n, result.solution or []).is_valid)

    def test_missing_dependency_is_unavailable(self):
        with patch("cpsat_solver._load_cp_model", side_effect=ImportError("mock missing ortools")):
            result = solve_n_queens_cpsat(4)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.backend_status, "IMPORT_ERROR")
        self.assertIn("mock missing ortools", result.message or "")

    def test_backend_status_mapping(self):
        expected = {
            FakeStatuses.OPTIMAL: "SAT",
            FakeStatuses.FEASIBLE: "SAT",
            FakeStatuses.INFEASIBLE: "UNSAT",
            FakeStatuses.MODEL_INVALID: "ERROR",
            FakeStatuses.UNKNOWN: "UNKNOWN",
            99: "UNKNOWN",
        }
        for backend_status, status in expected.items():
            with self.subTest(backend_status=backend_status):
                self.assertEqual(_map_status(FakeStatuses, backend_status), status)

    def test_outer_timeout_path_preserves_configuration(self):
        result = solve_n_queens_cpsat(8, timeout=5.0, random_seed=7, num_workers=1)
        self.assertEqual(result.status, "SAT")
        self.assertTrue(result.validated)
        self.assertEqual(result.solver_seed, 7)
        self.assertEqual(result.solver_workers, 1)
        self.assertIsNone(result.internal_timeout_seconds)
        self.assertIsNotNone(result.parent_observed_time)


if __name__ == "__main__":
    unittest.main()
