import unittest
from unittest.mock import patch

from cp_optimizer_solver import _classify_exception, solve_n_queens_cp_optimizer
from validator import validate_solution


class CpOptimizerSolverTests(unittest.TestCase):
    def test_required_cases_run_on_real_backend(self):
        expected = {1: "SAT", 2: "UNSAT", 3: "UNSAT", 4: "SAT", 8: "SAT"}
        for n, status in expected.items():
            with self.subTest(n=n):
                result = solve_n_queens_cp_optimizer(n, timeout=10)
                self.assertEqual(result.status, status)
                self.assertEqual(result.method, "CP_OPTIMIZER")
                if status == "SAT":
                    self.assertTrue(result.validated)
                    self.assertTrue(validate_solution(n, result.solution or []).is_valid)

    def test_missing_runtime_is_unavailable(self):
        with patch("cp_optimizer_solver._load_cp_optimizer", side_effect=FileNotFoundError("missing")):
            result = solve_n_queens_cp_optimizer(4)
        self.assertEqual(result.status, "UNAVAILABLE")

    def test_exception_classification(self):
        self.assertEqual(_classify_exception(RuntimeError("license missing"))[0], "UNAVAILABLE")
        self.assertEqual(_classify_exception(ValueError("bug"))[0], "ERROR")


if __name__ == "__main__":
    unittest.main()
