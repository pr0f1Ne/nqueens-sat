import unittest
from unittest.mock import patch

from gurobi_mip_solver import _classify_exception, _decode_binary_solution, solve_n_queens_gurobi_mip
from validator import validate_solution


class GurobiMipSolverTests(unittest.TestCase):
    def test_required_cases_run_on_real_backend(self):
        expected = {1: "SAT", 2: "UNSAT", 3: "UNSAT", 4: "SAT", 8: "SAT"}
        for n, status in expected.items():
            with self.subTest(n=n):
                result = solve_n_queens_gurobi_mip(n, timeout=10)
                self.assertEqual(result.status, status)
                self.assertEqual(result.method, "GUROBI_MIP")
                if status == "SAT":
                    self.assertTrue(result.validated)
                    self.assertTrue(validate_solution(n, result.solution or []).is_valid)

    def test_missing_dependency_is_unavailable(self):
        with patch("gurobi_mip_solver._load_gurobi", side_effect=ImportError("missing")):
            result = solve_n_queens_gurobi_mip(4)
        self.assertEqual(result.status, "UNAVAILABLE")

    def test_integrality_and_exception_classification(self):
        solution, error = _decode_binary_solution(2, [1.0, 0.0, 0.0, 1.0], 1e-5)
        self.assertEqual(solution, [(0, 0), (1, 1)])
        self.assertIsNone(error)
        self.assertEqual(_classify_exception(RuntimeError("license missing"))[0], "UNAVAILABLE")
        self.assertEqual(_classify_exception(ValueError("bug"))[0], "ERROR")


if __name__ == "__main__":
    unittest.main()
