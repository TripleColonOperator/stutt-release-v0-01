"""I-18 checks for inert exact-anchor same-occurrence continuity."""
from __future__ import annotations

import ast
import contextlib
from dataclasses import FrozenInstanceError, fields
import inspect
import io
from itertools import product
from pathlib import Path
import unittest

import core_0_1_occurrence_continuity as i18


def _evidence(
    entity: i18.AnchorObservation = i18.AnchorObservation.UNCHANGED,
    need: i18.AnchorObservation = i18.AnchorObservation.UNCHANGED,
    boundary: i18.AnchorObservation = i18.AnchorObservation.UNCHANGED,
    fulfillment: i18.EndObservation = i18.EndObservation.ABSENT,
    closure: i18.EndObservation = i18.EndObservation.ABSENT,
) -> i18.SameOccurrenceEvidence:
    return i18.SameOccurrenceEvidence(
        entity,
        need,
        boundary,
        fulfillment,
        closure,
    )


class OccurrenceContinuityTests(unittest.TestCase):
    def test_01_profile_and_outcome_identifiers_are_fixed(self):
        self.assertEqual(i18.PROFILE_ID, "gart-occurrence-continuity-i18-0.1")
        self.assertEqual(i18.SAME_OCCURRENCE, "same-occurrence")
        self.assertEqual(i18.CLASSIFICATION_STOPPED, "classification-stopped")
        self.assertNotEqual(i18.SAME_OCCURRENCE, i18.CLASSIFICATION_STOPPED)

    def test_02_all_exact_anchors_unchanged_and_unterminated_is_same(self):
        result = i18.assess_same_occurrence(_evidence())
        self.assertEqual(result.outcome, i18.SAME_OCCURRENCE)
        self.assertEqual(result.issues, ())

    def test_03_each_different_anchor_stops_with_its_exact_reason(self):
        cases = (
            (
                _evidence(entity=i18.AnchorObservation.DIFFERENT),
                i18.ENTITY_ANCHOR_DIFFERENT,
            ),
            (
                _evidence(need=i18.AnchorObservation.DIFFERENT),
                i18.NEED_ANCHOR_DIFFERENT,
            ),
            (
                _evidence(boundary=i18.AnchorObservation.DIFFERENT),
                i18.BOUNDARY_ANCHOR_DIFFERENT,
            ),
        )
        for evidence, reason in cases:
            with self.subTest(reason=reason):
                result = i18.assess_same_occurrence(evidence)
                self.assertEqual(result.outcome, i18.CLASSIFICATION_STOPPED)
                self.assertEqual(tuple(issue.code for issue in result.issues), (reason,))

    def test_04_each_unavailable_anchor_stops_with_its_exact_reason(self):
        cases = (
            (
                _evidence(entity=i18.AnchorObservation.UNAVAILABLE),
                i18.ENTITY_ANCHOR_UNAVAILABLE,
            ),
            (
                _evidence(need=i18.AnchorObservation.UNAVAILABLE),
                i18.NEED_ANCHOR_UNAVAILABLE,
            ),
            (
                _evidence(boundary=i18.AnchorObservation.UNAVAILABLE),
                i18.BOUNDARY_ANCHOR_UNAVAILABLE,
            ),
        )
        for evidence, reason in cases:
            with self.subTest(reason=reason):
                result = i18.assess_same_occurrence(evidence)
                self.assertEqual(result.outcome, i18.CLASSIFICATION_STOPPED)
                self.assertEqual(tuple(issue.code for issue in result.issues), (reason,))

    def test_05_all_two_hundred_forty_three_observation_combinations_are_exhaustive(self):
        anchor_observations = tuple(i18.AnchorObservation)
        end_observations = tuple(i18.EndObservation)
        anchor_reasons = (
            {
                i18.AnchorObservation.UNCHANGED: None,
                i18.AnchorObservation.DIFFERENT: i18.ENTITY_ANCHOR_DIFFERENT,
                i18.AnchorObservation.UNAVAILABLE: i18.ENTITY_ANCHOR_UNAVAILABLE,
            },
            {
                i18.AnchorObservation.UNCHANGED: None,
                i18.AnchorObservation.DIFFERENT: i18.NEED_ANCHOR_DIFFERENT,
                i18.AnchorObservation.UNAVAILABLE: i18.NEED_ANCHOR_UNAVAILABLE,
            },
            {
                i18.AnchorObservation.UNCHANGED: None,
                i18.AnchorObservation.DIFFERENT: i18.BOUNDARY_ANCHOR_DIFFERENT,
                i18.AnchorObservation.UNAVAILABLE: i18.BOUNDARY_ANCHOR_UNAVAILABLE,
            },
        )
        fulfillment_reasons = {
            i18.EndObservation.ABSENT: None,
            i18.EndObservation.PRESENT: i18.INTERVENING_FULFILLMENT_PRESENT,
            i18.EndObservation.UNAVAILABLE: i18.INTERVENING_FULFILLMENT_UNAVAILABLE,
        }
        closure_reasons = {
            i18.EndObservation.ABSENT: None,
            i18.EndObservation.PRESENT: i18.EXPLICIT_CLOSURE_PRESENT,
            i18.EndObservation.UNAVAILABLE: i18.EXPLICIT_CLOSURE_UNAVAILABLE,
        }
        same_count = 0
        stopped_count = 0
        combinations = product(
            product(anchor_observations, repeat=3),
            product(end_observations, repeat=2),
        )
        for anchors, endings in combinations:
            entity, need, boundary = anchors
            fulfillment, closure = endings
            with self.subTest(
                entity=entity,
                need=need,
                boundary=boundary,
                fulfillment=fulfillment,
                closure=closure,
            ):
                result = i18.assess_same_occurrence(
                    _evidence(
                        entity=entity,
                        need=need,
                        boundary=boundary,
                        fulfillment=fulfillment,
                        closure=closure,
                    )
                )
                expected_codes = tuple(
                    code
                    for code in (
                        anchor_reasons[0][entity],
                        anchor_reasons[1][need],
                        anchor_reasons[2][boundary],
                        fulfillment_reasons[fulfillment],
                        closure_reasons[closure],
                    )
                    if code is not None
                )
                self.assertEqual(
                    tuple(issue.code for issue in result.issues), expected_codes
                )
                if expected_codes:
                    self.assertEqual(result.outcome, i18.CLASSIFICATION_STOPPED)
                    stopped_count += 1
                else:
                    self.assertEqual(result.outcome, i18.SAME_OCCURRENCE)
                    same_count += 1
        self.assertEqual((same_count, stopped_count), (1, 242))

    def test_06_intervening_fulfillment_stops_classification(self):
        result = i18.assess_same_occurrence(
            _evidence(fulfillment=i18.EndObservation.PRESENT)
        )
        self.assertEqual(result.outcome, i18.CLASSIFICATION_STOPPED)
        self.assertEqual(
            tuple(issue.code for issue in result.issues),
            (i18.INTERVENING_FULFILLMENT_PRESENT,),
        )

    def test_07_explicit_closure_stops_classification(self):
        result = i18.assess_same_occurrence(
            _evidence(closure=i18.EndObservation.PRESENT)
        )
        self.assertEqual(result.outcome, i18.CLASSIFICATION_STOPPED)
        self.assertEqual(
            tuple(issue.code for issue in result.issues),
            (i18.EXPLICIT_CLOSURE_PRESENT,),
        )

    def test_08_both_end_conditions_stop_in_fixed_order(self):
        result = i18.assess_same_occurrence(
            _evidence(
                fulfillment=i18.EndObservation.PRESENT,
                closure=i18.EndObservation.PRESENT,
            )
        )
        self.assertEqual(
            tuple(issue.code for issue in result.issues),
            (
                i18.INTERVENING_FULFILLMENT_PRESENT,
                i18.EXPLICIT_CLOSURE_PRESENT,
            ),
        )

    def test_09_unavailable_end_observations_stop_classification(self):
        result = i18.assess_same_occurrence(
            _evidence(
                fulfillment=i18.EndObservation.UNAVAILABLE,
                closure=i18.EndObservation.UNAVAILABLE,
            )
        )
        self.assertEqual(result.outcome, i18.CLASSIFICATION_STOPPED)
        self.assertEqual(
            tuple(issue.code for issue in result.issues),
            (
                i18.INTERVENING_FULFILLMENT_UNAVAILABLE,
                i18.EXPLICIT_CLOSURE_UNAVAILABLE,
            ),
        )

    def test_10_mixed_stopping_reasons_use_one_deterministic_order(self):
        result = i18.assess_same_occurrence(
            _evidence(
                entity=i18.AnchorObservation.UNAVAILABLE,
                need=i18.AnchorObservation.DIFFERENT,
                boundary=i18.AnchorObservation.UNAVAILABLE,
                fulfillment=i18.EndObservation.PRESENT,
                closure=i18.EndObservation.UNAVAILABLE,
            )
        )
        self.assertEqual(
            tuple(issue.code for issue in result.issues),
            (
                i18.ENTITY_ANCHOR_UNAVAILABLE,
                i18.NEED_ANCHOR_DIFFERENT,
                i18.BOUNDARY_ANCHOR_UNAVAILABLE,
                i18.INTERVENING_FULFILLMENT_PRESENT,
                i18.EXPLICIT_CLOSURE_UNAVAILABLE,
            ),
        )

    def test_11_evidence_requires_all_five_exact_enum_observations(self):
        with self.assertRaises(TypeError):
            i18.SameOccurrenceEvidence()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            i18.SameOccurrenceEvidence(  # type: ignore[call-arg]
                i18.AnchorObservation.UNCHANGED,
                i18.AnchorObservation.UNCHANGED,
                i18.AnchorObservation.UNCHANGED,
                i18.EndObservation.ABSENT,
            )

        class HostileObservation:
            def __eq__(self, other):
                raise AssertionError("target equality hook was invoked")

        malformed = ("UNCHANGED", 1, None, True, HostileObservation())
        for field_index, value in enumerate(malformed):
            values = [
                i18.AnchorObservation.UNCHANGED,
                i18.AnchorObservation.UNCHANGED,
                i18.AnchorObservation.UNCHANGED,
                i18.EndObservation.ABSENT,
                i18.EndObservation.ABSENT,
            ]
            values[field_index] = value
            with self.subTest(field_index=field_index, host_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    i18.SameOccurrenceEvidence(*values)
        with self.assertRaises(TypeError):
            i18.assess_same_occurrence(object())

    def test_12_records_are_frozen_slotted_and_have_no_target_equality(self):
        evidence = _evidence()
        assessment = i18.assess_same_occurrence(evidence)
        issue = i18.ContinuityIssue(i18.ENTITY_ANCHOR_DIFFERENT)
        for value, field_name, replacement in (
            (evidence, "entity_anchor", i18.AnchorObservation.DIFFERENT),
            (assessment, "outcome", i18.CLASSIFICATION_STOPPED),
            (issue, "code", i18.NEED_ANCHOR_DIFFERENT),
        ):
            with self.subTest(host_type=type(value).__name__):
                self.assertFalse(hasattr(value, "__dict__"))
                with self.assertRaises(FrozenInstanceError):
                    setattr(value, field_name, replacement)
        self.assertIs(i18.SameOccurrenceEvidence.__eq__, object.__eq__)
        self.assertIs(i18.SameOccurrenceAssessment.__eq__, object.__eq__)
        self.assertIs(i18.ContinuityIssue.__eq__, object.__eq__)

    def test_13_issue_and_assessment_invariants_reject_malformed_results(self):
        issue = i18.ContinuityIssue(i18.ENTITY_ANCHOR_DIFFERENT)
        later_issue = i18.ContinuityIssue(i18.NEED_ANCHOR_DIFFERENT)
        with self.assertRaises(ValueError):
            i18.ContinuityIssue("unregistered")
        with self.assertRaises(ValueError):
            i18.SameOccurrenceAssessment(i18.SAME_OCCURRENCE, (issue,))
        with self.assertRaises(ValueError):
            i18.SameOccurrenceAssessment(i18.CLASSIFICATION_STOPPED, ())
        with self.assertRaises(ValueError):
            i18.SameOccurrenceAssessment("new-occurrence", (issue,))
        with self.assertRaises(ValueError):
            i18.SameOccurrenceAssessment(
                i18.CLASSIFICATION_STOPPED, (issue, issue)
            )
        with self.assertRaises(ValueError):
            i18.SameOccurrenceAssessment(
                i18.CLASSIFICATION_STOPPED, (later_issue, issue)
            )
        contradictory_pairs = (
            (i18.ENTITY_ANCHOR_DIFFERENT, i18.ENTITY_ANCHOR_UNAVAILABLE),
            (i18.NEED_ANCHOR_DIFFERENT, i18.NEED_ANCHOR_UNAVAILABLE),
            (i18.BOUNDARY_ANCHOR_DIFFERENT, i18.BOUNDARY_ANCHOR_UNAVAILABLE),
            (
                i18.INTERVENING_FULFILLMENT_PRESENT,
                i18.INTERVENING_FULFILLMENT_UNAVAILABLE,
            ),
            (i18.EXPLICIT_CLOSURE_PRESENT, i18.EXPLICIT_CLOSURE_UNAVAILABLE),
        )
        for first_code, second_code in contradictory_pairs:
            with self.subTest(first_code=first_code, second_code=second_code):
                with self.assertRaises(ValueError):
                    i18.SameOccurrenceAssessment(
                        i18.CLASSIFICATION_STOPPED,
                        (
                            i18.ContinuityIssue(first_code),
                            i18.ContinuityIssue(second_code),
                        ),
                    )
        with self.assertRaises(ValueError):
            i18.SameOccurrenceAssessment(
                i18.CLASSIFICATION_STOPPED, [issue]  # type: ignore[arg-type]
            )

    def test_14_repeated_assessment_is_deterministic_and_stateless(self):
        evidence = _evidence(
            entity=i18.AnchorObservation.DIFFERENT,
            closure=i18.EndObservation.UNAVAILABLE,
        )
        public_before = tuple(sorted(i18.__all__))
        first = i18.assess_same_occurrence(evidence)
        second = i18.assess_same_occurrence(evidence)
        self.assertEqual(first.outcome, second.outcome)
        self.assertEqual(
            tuple(issue.code for issue in first.issues),
            tuple(issue.code for issue in second.issues),
        )
        self.assertEqual(tuple(sorted(i18.__all__)), public_before)

    def test_15_assessment_does_not_mutate_its_input(self):
        evidence = _evidence(
            need=i18.AnchorObservation.UNAVAILABLE,
            fulfillment=i18.EndObservation.PRESENT,
        )
        before = tuple(getattr(evidence, field.name) for field in fields(evidence))
        i18.assess_same_occurrence(evidence)
        after = tuple(getattr(evidence, field.name) for field in fields(evidence))
        self.assertEqual(after, before)

    def test_16_calls_are_silent_and_representations_omit_premises(self):
        evidence = _evidence(
            entity=i18.AnchorObservation.DIFFERENT,
            need=i18.AnchorObservation.UNAVAILABLE,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = i18.assess_same_occurrence(evidence)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        evidence_repr = repr(evidence)
        self.assertNotIn("DIFFERENT", evidence_repr)
        self.assertNotIn("UNAVAILABLE", evidence_repr)
        self.assertNotIn("entity_anchor", evidence_repr)
        self.assertNotIn(i18.ENTITY_ANCHOR_DIFFERENT, repr(result.issues[0]))
        self.assertNotIn("entity_anchor", repr(result))

    def test_17_public_surface_is_classification_only(self):
        signature = inspect.signature(i18.assess_same_occurrence)
        parameters = tuple(signature.parameters.values())
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0].name, "evidence")
        self.assertIs(parameters[0].default, inspect.Parameter.empty)
        self.assertEqual(
            tuple(field.name for field in fields(i18.SameOccurrenceEvidence)),
            (
                "entity_anchor",
                "unresolved_need_anchor",
                "authorized_boundary_anchor",
                "intervening_fulfillment",
                "explicit_closure",
            ),
        )
        self.assertEqual(
            tuple(field.name for field in fields(i18.SameOccurrenceAssessment)),
            ("outcome", "issues"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(i18.ContinuityIssue)),
            ("code",),
        )
        exported_functions = tuple(
            name for name in i18.__all__ if inspect.isfunction(getattr(i18, name))
        )
        self.assertEqual(exported_functions, ("assess_same_occurrence",))
        forbidden_action_fragments = (
            "create", "invoke", "new_occurrence", "transition", "retry",
            "authorize", "perform_fulfillment", "perform_closure", "persist",
            "record", "execute", "schedule", "queue",
        )
        for record_type in (
            i18.SameOccurrenceEvidence,
            i18.SameOccurrenceAssessment,
            i18.ContinuityIssue,
        ):
            callable_names = tuple(
                name
                for name in dir(record_type)
                if not name.startswith("__") and callable(getattr(record_type, name))
            )
            for callable_name in callable_names:
                folded = callable_name.casefold()
                for fragment in forbidden_action_fragments:
                    self.assertNotIn(fragment, folded)

    def test_18_module_has_no_identity_creation_or_operational_path(self):
        source_path = Path(i18.__file__).resolve()
        self.assertEqual(source_path.name, "core_0_1_occurrence_continuity.py")
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        called_names: set[str] = set()
        attribute_calls: set[str] = set()
        defined_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    attribute_calls.add(node.func.attr)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)

        forbidden_imports = {
            "asyncio", "hashlib", "http", "logging", "multiprocessing", "os",
            "pathlib", "pickle", "random", "requests", "shutil", "socket",
            "sqlite3", "subprocess", "sys", "tempfile", "threading", "time",
            "urllib", "uuid", "webbrowser",
        }
        forbidden_calls = {
            "__import__", "compile", "connect", "eval", "exec", "hash", "id",
            "input", "open", "popen", "print", "remove", "run", "send",
            "sendall", "system", "unlink", "uuid4", "write_bytes", "write_text",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden_imports))
        self.assertTrue(called_names.isdisjoint(forbidden_calls))
        self.assertTrue(attribute_calls.isdisjoint(forbidden_calls))
        for forbidden_name in (
            "create_occurrence", "new_occurrence", "retry", "record_attempt",
            "invoke_source", "authorize", "transition", "fulfill", "close",
        ):
            self.assertNotIn(forbidden_name, defined_names)


if __name__ == "__main__":
    unittest.main()
