"""Kiểm thử tính đúng đắn của mốc SAT pairwise."""

import unittest
from unittest.mock import patch

from sat_encoding import board_var, encode_n_queens_pairwise
from sat_solver import decode_model, solve_n_queens
from validator import validate_solution
from timeout_runner import WorkerOutcome, run_in_worker
from tests.worker_fixtures import failing_worker, fast_worker, slow_worker


class PairwiseEncodingTests(unittest.TestCase):
    def test_board_variable_mapping(self):
        self.assertEqual(board_var(4, 0, 0), 1)
        self.assertEqual(board_var(4, 3, 3), 16)

    def test_n4_formula_size_and_no_auxiliary_variables(self):
        formula = encode_n_queens_pairwise(4)
        self.assertEqual(formula.num_variables, 16)
        self.assertEqual(len(formula.clauses), 84)
        self.assertTrue(all(abs(literal) <= 16 for clause in formula.clauses for literal in clause))

    def test_invalid_n_is_rejected(self):
        for value in (0, -1, True, 2.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                encode_n_queens_pairwise(value)

    def test_decoder_ignores_negative_and_non_board_literals(self):
        self.assertEqual(decode_model(2, [1, -2, 4, 5]), [(0, 0), (1, 1)])

    def test_exhaustive_assignments_match_independent_validator(self):
        for n in (1, 2, 3):
            formula = encode_n_queens_pairwise(n)
            for mask in range(1 << (n * n)):
                assignment = {
                    variable: bool(mask & (1 << (variable - 1)))
                    for variable in range(1, n * n + 1)
                }
                satisfies_cnf = all(
                    any(
                        assignment[abs(literal)] if literal > 0
                        else not assignment[abs(literal)]
                        for literal in clause
                    )
                    for clause in formula.clauses
                )
                queens = [
                    ((variable - 1) // n, (variable - 1) % n)
                    for variable, is_true in assignment.items()
                    if is_true
                ]
                self.assertEqual(
                    satisfies_cnf,
                    validate_solution(n, queens).is_valid,
                    msg=f"Sai khác tại N={n}, mask={mask}",
                )


class ValidatorTests(unittest.TestCase):
    def test_valid_n4_solution(self):
        self.assertTrue(validate_solution(4, [(0, 1), (1, 3), (2, 0), (3, 2)]).is_valid)

    def test_rejects_wrong_count_and_attacks(self):
        self.assertFalse(validate_solution(4, [(0, 0), (1, 1), (2, 2)]).is_valid)
        self.assertFalse(validate_solution(4, [(0, 1), (0, 3), (2, 0), (3, 2)]).is_valid)
        self.assertFalse(validate_solution(4, [(0, 0), (1, 2), (2, 0), (3, 3)]).is_valid)

    def test_rejects_out_of_bounds(self):
        self.assertFalse(validate_solution(1, [(1, 0)]).is_valid)


class RequiredNQueensCases(unittest.TestCase):
    def test_required_statuses_and_solutions(self):
        expected = {1: "SAT", 2: "UNSAT", 3: "UNSAT", 4: "SAT", 8: "SAT"}
        for n, status in expected.items():
            with self.subTest(n=n):
                result = solve_n_queens(n)
                self.assertEqual(result.status, status)
                if status == "SAT":
                    self.assertTrue(result.validated)
                    self.assertTrue(validate_solution(n, result.solution or []).is_valid)
                else:
                    self.assertIsNone(result.solution)

    def test_missing_backend_is_unavailable_without_uninstalling_it(self):
        with patch("sat_solver._load_glucose3", side_effect=ImportError("mock missing backend")):
            result = solve_n_queens(4)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.backend_status, "IMPORT_ERROR")
        self.assertIsNone(result.load_time)
        self.assertIsNone(result.solve_time)


class WorkerTimeoutTests(unittest.TestCase):
    def test_timeout_must_be_positive_and_finite(self):
        for timeout in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                solve_n_queens(4, timeout=timeout)

    def test_worker_finishes_before_deadline(self):
        outcome = run_in_worker(fast_worker, (21,), 2.0)
        self.assertEqual(outcome.status, "COMPLETED")
        self.assertEqual(outcome.value, 42)
        self.assertFalse(outcome.worker_alive_after_cleanup)

    def test_slow_worker_is_stopped_and_reaped(self):
        outcome = run_in_worker(slow_worker, (2.0,), 0.1)
        self.assertEqual(outcome.status, "TIMEOUT")
        self.assertFalse(outcome.worker_alive_after_cleanup)
        self.assertLess(outcome.parent_observed_time, 2.0)

    def test_timeout_result_uses_null_for_unmeasured_stages(self):
        timeout_outcome = WorkerOutcome(
            status="TIMEOUT",
            value=None,
            parent_observed_time=0.12,
            worker_pid=123,
            worker_alive_after_cleanup=False,
            error="deliberate timeout",
        )
        with patch("sat_solver.run_in_worker", return_value=timeout_outcome):
            result = solve_n_queens(8, timeout=0.1)
        self.assertEqual(result.status, "TIMEOUT")
        self.assertEqual(result.backend_status, "TIMEOUT")
        self.assertIsNone(result.build_time)
        self.assertIsNone(result.load_time)
        self.assertIsNone(result.solve_time)
        self.assertIsNone(result.total_time)
        self.assertEqual(result.parent_observed_time, 0.12)

    def test_worker_error_is_not_reported_as_unsat(self):
        outcome = run_in_worker(failing_worker, (), 2.0)
        self.assertEqual(outcome.status, "ERROR")
        self.assertIn("intentional worker failure", outcome.error or "")
        self.assertFalse(outcome.worker_alive_after_cleanup)

    def test_solver_can_complete_inside_worker(self):
        result = solve_n_queens(8, timeout=5.0)
        self.assertEqual(result.status, "SAT")
        self.assertTrue(result.validated)
        self.assertIsNotNone(result.parent_observed_time)
        self.assertEqual(result.timeout_seconds, 5.0)


if __name__ == "__main__":
    unittest.main()
