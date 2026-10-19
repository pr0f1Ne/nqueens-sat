"""Kiểm thử chung cho pairwise, sequential counter và bitwise."""

from itertools import product
import unittest

from pysat.card import IDPool
from pysat.solvers import Glucose3

from sat_encoding import (
    SUPPORTED_ENCODINGS,
    add_at_least_one,
    add_at_most_one,
    add_exactly_one,
    encode_n_queens,
)
from sat_solver import solve_n_queens
from validator import validate_solution


class CardinalityEncodingTests(unittest.TestCase):
    def _assert_truth_table(self, encoding: str, exactly_one: bool) -> None:
        variables = [1, 2, 3, 4]
        clauses: list[list[int]] = []
        pool = IDPool(start_from=5)
        if exactly_one:
            add_exactly_one(clauses, variables, encoding, pool)
        else:
            add_at_most_one(clauses, variables, encoding, pool)

        with Glucose3(bootstrap_with=clauses) as solver:
            for values in product((False, True), repeat=len(variables)):
                assumptions = [variable if value else -variable for variable, value in zip(variables, values)]
                expected = sum(values) == 1 if exactly_one else sum(values) <= 1
                self.assertEqual(
                    solver.solve(assumptions=assumptions),
                    expected,
                    msg=f"{encoding=}, {exactly_one=}, {values=}",
                )

    def test_amo_truth_tables_allow_auxiliary_extensions(self):
        for encoding in SUPPORTED_ENCODINGS:
            with self.subTest(encoding=encoding):
                self._assert_truth_table(encoding, exactly_one=False)

    def test_eo_truth_tables_allow_auxiliary_extensions(self):
        for encoding in SUPPORTED_ENCODINGS:
            with self.subTest(encoding=encoding):
                self._assert_truth_table(encoding, exactly_one=True)

    def test_shared_pool_allocates_disjoint_auxiliary_ranges(self):
        for encoding in ("sequential", "bitwise"):
            with self.subTest(encoding=encoding):
                clauses: list[list[int]] = []
                pool = IDPool(start_from=9)
                add_at_most_one(clauses, [1, 2, 3, 4], encoding, pool)
                first_ids = set(range(9, pool.top + 1))
                first_top = pool.top
                add_at_most_one(clauses, [5, 6, 7, 8], encoding, pool)
                second_ids = set(range(first_top + 1, pool.top + 1))
                self.assertTrue(first_ids)
                self.assertTrue(second_ids)
                self.assertTrue(first_ids.isdisjoint(second_ids))
                self.assertTrue(all(variable > 8 for variable in first_ids | second_ids))

    def test_empty_and_singleton_group_policy(self):
        for encoding in SUPPORTED_ENCODINGS:
            with self.subTest(encoding=encoding):
                clauses: list[list[int]] = []
                pool = IDPool(start_from=2)
                add_at_most_one(clauses, [], encoding, pool)
                add_at_most_one(clauses, [1], encoding, pool)
                self.assertEqual(clauses, [])
                with self.assertRaises(ValueError):
                    add_at_least_one(clauses, [])
                with self.assertRaises(ValueError):
                    add_exactly_one(clauses, [], encoding, pool)


class NQueensEncodingTests(unittest.TestCase):
    def test_required_cases_for_every_encoding(self):
        expected = {1: "SAT", 2: "UNSAT", 3: "UNSAT", 4: "SAT", 8: "SAT"}
        for encoding in SUPPORTED_ENCODINGS:
            for n, status in expected.items():
                with self.subTest(encoding=encoding, n=n):
                    result = solve_n_queens(n, encoding=encoding)
                    self.assertEqual(result.encoding, encoding)
                    self.assertEqual(result.status, status)
                    if status == "SAT":
                        self.assertTrue(result.validated)
                        self.assertTrue(validate_solution(n, result.solution or []).is_valid)

    def test_timeout_worker_preserves_selected_encoding(self):
        result = solve_n_queens(8, timeout=5.0, encoding="sequential")
        self.assertEqual(result.status, "SAT")
        self.assertEqual(result.encoding, "sequential")
        self.assertTrue(result.validated)

    def test_variable_counts_are_explicit_and_reserved(self):
        for encoding in SUPPORTED_ENCODINGS:
            with self.subTest(encoding=encoding):
                formula = encode_n_queens(4, encoding)
                self.assertEqual(formula.num_board_variables, 16)
                self.assertEqual(
                    formula.num_variables,
                    formula.num_board_variables + formula.num_auxiliary_variables,
                )
                auxiliary_literals = {
                    abs(literal)
                    for clause in formula.clauses
                    for literal in clause
                    if abs(literal) > 16
                }
                self.assertEqual(len(auxiliary_literals), formula.num_auxiliary_variables)

    def test_pairwise_baseline_size_is_unchanged(self):
        formula = encode_n_queens(4, "pairwise")
        self.assertEqual(formula.num_variables, 16)
        self.assertEqual(formula.num_auxiliary_variables, 0)
        self.assertEqual(len(formula.clauses), 84)

    def test_invalid_encoding_is_rejected(self):
        with self.assertRaises(ValueError):
            encode_n_queens(4, "unknown")


if __name__ == "__main__":
    unittest.main()
