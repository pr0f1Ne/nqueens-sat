"""Kiểm thử backend IBM CPLEX MIP."""

import unittest
from unittest.mock import patch

from cplex_mip_solver import (
    _classify_exception,
    _decode_binary_solution,
    _map_status_without_solution,
    solve_n_queens_cplex_mip,
)
from validator import validate_solution


class FakeStatuses:
    MIP_infeasible = 103
    infeasible = 3


class CplexMipSolverTests(unittest.TestCase):
    def test_required_cases_run_on_real_backend(self):
        expected = {1: "SAT", 2: "UNSAT", 3: "UNSAT", 4: "SAT", 8: "SAT"}
        for n, status in expected.items():
            with self.subTest(n=n):
                result = solve_n_queens_cplex_mip(n)
                self.assertEqual(result.status, status)
                self.assertEqual(result.method, "CPLEX_MIP")
                self.assertIsNone(result.encoding)
                self.assertIsNone(result.num_clauses)
                self.assertEqual(result.solver_workers, 1)
                self.assertEqual(result.stop_condition, "mip.limits.solutions=1")
                if status == "SAT":
                    self.assertTrue(result.validated)
                    self.assertTrue(validate_solution(n, result.solution or []).is_valid)

    def test_missing_dependency_is_unavailable(self):
        with patch("cplex_mip_solver._load_cplex", side_effect=ImportError("mock missing cplex")):
            result = solve_n_queens_cplex_mip(4)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.backend_status, "IMPORT_ERROR")

    def test_status_without_incumbent_only_proves_exact_infeasible(self):
        self.assertEqual(_map_status_without_solution(FakeStatuses, 103), "UNSAT")
        self.assertEqual(_map_status_without_solution(FakeStatuses, 3), "UNSAT")
        for status in (0, 104, 108, 114, 119):
            with self.subTest(status=status):
                self.assertEqual(_map_status_without_solution(FakeStatuses, status), "UNKNOWN")

    def test_integrality_tolerance_is_checked_before_decoding(self):
        solution, error = _decode_binary_solution(2, [1.0, 0.0, 0.0, 1.0], 1e-5)
        self.assertEqual(solution, [(0, 0), (1, 1)])
        self.assertIsNone(error)
        solution, error = _decode_binary_solution(2, [0.9, 0.1, 0.0, 1.0], 1e-5)
        self.assertEqual(solution, [])
        self.assertIn("không nguyên", error or "")

    def test_only_runtime_or_license_errors_are_unavailable(self):
        self.assertEqual(_classify_exception(RuntimeError("No license available"))[0], "UNAVAILABLE")
        self.assertEqual(
            _classify_exception(RuntimeError("CPLEX Error 1016: Community Edition. Problem size limits exceeded"))[0],
            "UNAVAILABLE",
        )
        self.assertEqual(_classify_exception(ValueError("programming bug"))[0], "ERROR")

    def test_outer_timeout_configuration_is_recorded(self):
        result = solve_n_queens_cplex_mip(8, timeout=5.0, random_seed=17, num_threads=1)
        self.assertEqual(result.status, "SAT")
        self.assertTrue(result.validated)
        self.assertEqual(result.solver_seed, 17)
        self.assertEqual(result.solver_workers, 1)
        self.assertIsNotNone(result.parent_observed_time)


if __name__ == "__main__":
    unittest.main()
