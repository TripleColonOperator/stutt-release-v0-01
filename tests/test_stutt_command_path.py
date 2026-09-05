"""Offline regression tests for the public command path.

Fixtures live in a temporary project. Network calls are blocked, and the process
environment is cleared while each test runs so developer credentials are unused.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import stutt_command_path as command_path
import stutt_model_adapter as model_adapter


class CommandPathTests(unittest.TestCase):
    def start_patch(self, patcher):
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def setUp(self) -> None:
        fixture = tempfile.TemporaryDirectory(prefix="stutt-command-tests-")
        self.addCleanup(fixture.cleanup)
        self.project = Path(fixture.name) / "project"
        self.project.mkdir()
        self.outside = Path(fixture.name) / "outside"
        self.outside.mkdir()
        self.start_patch(
            mock.patch.object(command_path, "__file__", str(self.project / "stutt_command_path.py"))
        )
        self.start_patch(mock.patch.dict(command_path.os.environ, {}, clear=True))
        self.start_patch(
            mock.patch.object(
                model_adapter.request,
                "urlopen",
                side_effect=AssertionError("Command tests must not contact model servers"),
            )
        )
        opener = mock.Mock()
        opener.open.side_effect = AssertionError("Command tests must not contact model servers")
        self.start_patch(mock.patch.object(model_adapter.request, "build_opener", return_value=opener))
        (self.project / "README.md").write_text("Release README fixture\n", encoding="utf-8")
        (self.project / "REUBARB_STUTT_ROADMAP.md").write_text(
            "Release roadmap fixture\n", encoding="utf-8"
        )
        (self.project / "stutt_model_backends.example.json").write_text(
            '{"openai_compatible": []}', encoding="utf-8"
        )
        self.start_patch(
            mock.patch.object(
                command_path, "DEFAULT_CONFIG_PATH", self.project / "stutt_model_backends.example.json"
            )
        )

    def model_decision(self, response: str):
        gateway = mock.Mock()
        gateway.infer.return_value = model_adapter.ModelResult(
            content=response, model="offline-fixture", backend="mock", status=200
        )
        return command_path.infer_model_decision("An ordinary request", gateway)

    def assert_bounded_failure(self, outcome) -> None:
        self.assertIsInstance(outcome, command_path.CommandOutcome)
        self.assertTrue(outcome.error or "denied" in outcome.result.lower())

    def test_payload_case_unicode_and_whitespace_are_preserved(self) -> None:
        cases = (
            ("echo MiXeD Καλημέρα 世界  ", "MiXeD Καλημέρα 世界  "),
            ("echo   Two spaces remain", "  Two spaces remain"),
            ("echo\t\tSecond tab remains\t", "\tSecond tab remains\t"),
            ("echo\nFirst\nSecond\n", "First\nSecond\n"),
            ("echo \n\t", "\n\t"),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                decision = command_path.parse_local_intent(source)
                self.assertEqual(decision.action, "echo")
                self.assertEqual(decision.payload, expected)
                self.assertEqual(command_path.run_one(source).result, expected)

    def test_case_insensitive_aliases_and_optional_slash(self) -> None:
        cases = (
            ("EcHo MiXeD", "echo", "MiXeD"),
            ("/EcHo MiXeD", "echo", "MiXeD"),
            ("  /EcHo MiXeD", "echo", "MiXeD"),
            ("CoMmAnDs", "commands", None),
            ("StAtS MiXeD", "count", "MiXeD"),
            ("LIST-FILES SubDir", "list_files", "SubDir"),
        )
        for source, action, payload in cases:
            with self.subTest(source=source):
                decision = command_path.parse_local_intent(source)
                self.assertEqual(decision.action, action)
                self.assertEqual(decision.payload, payload)

    def test_text_operations_use_original_payload(self) -> None:
        cases = (
            ("echo AbC", "AbC"),
            ("trim   AbC  ", "AbC"),
            ("reverse AbC", "CbA"),
            ("upper Abç", "ABÇ"),
            ("lower AbÇ", "abç"),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(command_path.run_one(source).result, expected)

    def test_count_keeps_newlines_and_trailing_spaces(self) -> None:
        payload = "MiXeD\n世界  "
        result = json.loads(command_path.run_one("count " + payload).result)
        self.assertEqual(result["characters"], len(payload))
        self.assertEqual(result["words"], 2)
        self.assertEqual(result["lines"], 2)
        self.assertEqual(result["text_preview"], payload)

    def test_count_recognizes_cr_lf_and_crlf_without_double_counting(self) -> None:
        for payload, expected in (("A\rB", 2), ("A\nB", 2), ("A\r\nB", 2), ("A\r", 2), ("", 1)):
            with self.subTest(payload=payload):
                result = json.loads(command_path.run_one("count " + payload).result)
                self.assertEqual(result["lines"], expected)
                self.assertEqual(result["text_preview"], payload)

    def test_json_preserves_key_and_value_case(self) -> None:
        result = command_path.run_one('json {"CaseSensitive": "MiXeD 世界"}')
        self.assertIsNone(result.error)
        self.assertEqual(json.loads(result.result), {"CaseSensitive": "MiXeD 世界"})

    def test_unknown_and_empty_input_stay_local(self) -> None:
        with mock.patch.object(command_path, "build_gateway_from_config") as build_gateway:
            for source in ("", "  \t\n", "unregistered-command"):
                with self.subTest(source=source):
                    result = command_path.run_one(source)
                    self.assertEqual(result.action, "status")
                    self.assertTrue(result.result)
                    self.assertIsNone(result.error)
            command_path.run_one("  \t\n", use_model=True)
            build_gateway.assert_not_called()

    def test_registered_commands_run_with_absent_optional_assets(self) -> None:
        self.assertEqual(len(command_path.ALLOWED_ACTIONS), 19)
        text_actions = {"echo", "count", "trim", "reverse", "upper", "lower"}
        for action in command_path.ALLOWED_ACTIONS:
            with self.subTest(action=action):
                payload = "MiXeD" if action in text_actions else None
                if action == "json":
                    payload = '{"Case": "Value"}'
                outcome = command_path.execute_command(
                    command_path.CommandDecision(action=action, payload=payload)
                )
                self.assertEqual(outcome.action, action)
                self.assertTrue(outcome.allowed)
                self.assertIsNone(outcome.error)

    def test_readme_and_roadmap_read_their_release_documents(self) -> None:
        self.assertIn("Release README fixture", command_path.run_one("readme").result)
        self.assertIn("Release roadmap fixture", command_path.run_one("roadmap").result)

    def test_list_files_defaults_to_project_and_accepts_subdirectory(self) -> None:
        (self.project / "SubDir").mkdir()
        (self.project / "SubDir" / "MixedCase.txt").write_text("fixture", encoding="utf-8")
        self.assertIn("SubDir/", command_path.run_one("list-files").result)
        self.assertIn("MixedCase.txt", command_path.run_one("list-files SubDir").result)

    def test_list_files_denies_parent_traversal_and_absolute_outside_path(self) -> None:
        for path in ("..", "../outside", str(self.outside)):
            with self.subTest(path=path):
                outcome = command_path.run_one("list-files " + path)
                self.assert_bounded_failure(outcome)

    def test_list_files_denies_a_resolved_symlink_outside_project(self) -> None:
        link = self.project / "external-link"
        original_resolve = Path.resolve

        def resolve_with_link(path, *args, **kwargs):
            if path == link:
                return self.outside
            return original_resolve(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", autospec=True, side_effect=resolve_with_link):
            outcome = command_path.run_one("list-files external-link")
        self.assert_bounded_failure(outcome)

    def test_list_files_denies_real_symlink_when_supported(self) -> None:
        link = self.project / "external-link"
        try:
            link.symlink_to(self.outside, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Directory symlinks are unavailable: {type(exc).__name__}")
        self.assert_bounded_failure(command_path.run_one("list-files external-link"))

    def test_fixed_document_and_asset_paths_cannot_resolve_outside_project(self) -> None:
        command_paths = (
            ("readme", self.project / "README.md"),
            ("roadmap", self.project / "REUBARB_STUTT_ROADMAP.md"),
            ("font", self.project / "fonts" / "v0_1" / "ReubarbPiSymbols-Regular.ttf"),
            ("glyphs", self.project / "glyphs" / "v0_1"),
        )
        original_resolve = Path.resolve
        for command, linked_path in command_paths:
            with self.subTest(command=command):
                def resolve_with_link(path, *args, **kwargs):
                    if path == linked_path:
                        return self.outside
                    return original_resolve(path, *args, **kwargs)

                with mock.patch.object(Path, "resolve", autospec=True, side_effect=resolve_with_link):
                    self.assert_bounded_failure(command_path.run_one(command))

    def test_disallowed_action_never_executes(self) -> None:
        outcome = command_path.execute_command(command_path.CommandDecision("delete", "file"))
        self.assertFalse(outcome.allowed)
        self.assertTrue(outcome.error)

    def test_model_accepts_complete_object_and_json_fence(self) -> None:
        source = '{"action":"echo","payload":"MiXeD 世界  "}'
        for response in (source, "```json\n" + source + "\n```"):
            with self.subTest(response=response):
                decision = self.model_decision(response)
                self.assertEqual(decision.action, "echo")
                self.assertEqual(decision.payload, "MiXeD 世界  ")

    def test_model_accepts_explicit_empty_text_and_default_directory(self) -> None:
        for action in ("echo", "count", "trim", "reverse", "upper", "lower", "json"):
            with self.subTest(action=action):
                decision = self.model_decision(json.dumps({"action": action, "payload": ""}))
                self.assertEqual(decision.action, action)
                self.assertEqual(decision.payload, "")
        for response in ('{"action":"list_files"}', '{"action":"list_files","payload":null}'):
            with self.subTest(response=response):
                decision = self.model_decision(response)
                self.assertEqual(decision.action, "list_files")
                self.assertFalse(decision.payload)

    def test_model_rejects_missing_or_nonstring_text_payload(self) -> None:
        for action in ("echo", "count", "trim", "reverse", "upper", "lower", "json"):
            responses = [{"action": action}]
            responses.extend({"action": action, "payload": value} for value in (None, 12, False, [], {}))
            for response in responses:
                with self.subTest(response=response):
                    decision = self.model_decision(json.dumps(response))
                    self.assertTrue(decision is None or decision.action == "status")

    def test_model_rejects_malformed_actions_and_directory_payloads(self) -> None:
        responses = [
            {},
            {"action": None},
            {"action": False},
            {"action": 7},
            {"action": []},
            {"action": {}},
            {"action": "delete", "payload": "anything"},
            {"action": "echo", "payload": "text", "extra": "field"},
            {"action": "list_files", "payload": []},
            {"action": "list_files", "payload": 7},
            {"action": "status", "payload": {}},
        ]
        for response in responses:
            with self.subTest(response=response):
                decision = self.model_decision(json.dumps(response))
                self.assertTrue(decision is None or decision.action == "status")

    def test_model_rejects_prose_array_duplicate_keys_and_incomplete_json(self) -> None:
        responses = (
            'Explanation: {"action":"echo","payload":"text"}',
            '[{"action":"echo","payload":"text"}]',
            '{"action":"status","action":"echo","payload":"text"}',
            '{"action":"echo","payload":"first","payload":"second"}',
            '{"action":"echo","payload":"text"} trailing prose',
            '```json\n{"action":"echo","payload":"text"}\n```\nExplanation',
            '{"action":"echo",',
            'null',
            '"text"',
        )
        for response in responses:
            with self.subTest(response=response):
                decision = self.model_decision(response)
                self.assertTrue(decision is None or decision.action == "status")

    def test_model_backend_failure_does_not_execute_a_data_action(self) -> None:
        gateway = mock.Mock()
        gateway.infer.side_effect = model_adapter.ModelBackendError("Offline fixture unavailable")
        with mock.patch.object(command_path, "build_gateway_from_config", return_value=gateway):
            outcome = command_path.run_one("Please normalize this", use_model=True)
        self.assertEqual(outcome.action, "status")

    def test_default_model_config_is_anchored_to_adapter_location(self) -> None:
        gateway = mock.Mock()
        gateway.infer.return_value = model_adapter.ModelResult(
            content='{"action":"status"}', model="fixture", backend="mock", status=200
        )
        with mock.patch.object(command_path, "DEFAULT_CONFIG_PATH", model_adapter.DEFAULT_CONFIG_PATH):
            with mock.patch.object(command_path, "build_gateway_from_config", return_value=gateway) as build:
                command_path.run_one("Please normalize this", use_model=True)
        configured_path = Path(build.call_args.kwargs["config_path"])
        self.assertTrue(configured_path.is_absolute())
        self.assertEqual(configured_path, model_adapter.DEFAULT_CONFIG_PATH)

    def test_explicit_relative_config_is_not_rebased(self) -> None:
        gateway = mock.Mock()
        gateway.infer.return_value = model_adapter.ModelResult(
            content='{"action":"status"}', model="fixture", backend="mock", status=200
        )
        with mock.patch.object(command_path, "build_gateway_from_config", return_value=gateway) as build:
            command_path.run_one("Please normalize this", use_model=True, config="custom.json")
        self.assertEqual(Path(build.call_args.kwargs["config_path"]), Path("custom.json"))

    def test_model_fallback_requires_explicit_opt_in(self) -> None:
        gateway = mock.Mock()
        gateway.infer.return_value = model_adapter.ModelResult(
            content='{"action":"status"}', model="fixture", backend="mock", status=200
        )
        for allow_fallback in (False, True):
            with self.subTest(allow_fallback=allow_fallback):
                with mock.patch.object(
                    command_path, "build_gateway_from_config", return_value=gateway
                ) as build:
                    command_path.run_one(
                        "Please normalize this", use_model=True, model_fallback=allow_fallback
                    )
                self.assertIs(build.call_args.kwargs["allow_fallback"], allow_fallback)
        self.assertFalse(command_path.parse_args([]).model_fallback)
        self.assertTrue(command_path.parse_args(["--model", "--model-fallback"]).model_fallback)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                command_path.parse_args(["--model-fallback"])
        self.assertEqual(stopped.exception.code, 2)

    def test_malformed_model_config_is_a_structured_failure(self) -> None:
        config = self.project / "broken.json"
        for content in ("{", "[]", '{"openai_compatible":42}', '{"openai_compatible":[null]}'):
            with self.subTest(content=content):
                config.write_text(content, encoding="utf-8")
                outcome = command_path.run_one("Please normalize this", use_model=True, config=str(config))
                self.assertEqual(outcome.action, "status")
                self.assertTrue(outcome.error)

    def test_backend_inspector_handles_malformed_config(self) -> None:
        config = self.project / "stutt_model_backends.example.json"
        for content in ("{", "[]", '{"openai_compatible":42}', '{"openai_compatible":[null]}'):
            with self.subTest(content=content):
                config.write_text(content, encoding="utf-8")
                outcome = command_path.run_one("model-backends")
                self.assertTrue(outcome.error)

    def test_manifest_inspector_handles_invalid_json_and_wrong_shape(self) -> None:
        directory = self.project / "fonts" / "v0_1"
        directory.mkdir(parents=True)
        for content in ("{", "[]", "null"):
            with self.subTest(content=content):
                (directory / "font-manifest.json").write_text(content, encoding="utf-8")
                outcome = command_path.run_one("check-glyph-map")
                self.assertTrue(outcome.error)

    def test_file_read_and_directory_permission_errors_are_structured(self) -> None:
        with mock.patch.object(Path, "open", side_effect=PermissionError("Fixture access denied")):
            for command in ("readme", "roadmap", "model-backends"):
                with self.subTest(command=command):
                    outcome = command_path.run_one(command)
                    self.assertTrue(outcome.error)
        with mock.patch.object(Path, "iterdir", side_effect=PermissionError("Fixture access denied")):
            self.assertTrue(command_path.run_one("list-files").error)
        with mock.patch.object(Path, "resolve", side_effect=PermissionError("Fixture access denied")):
            self.assertTrue(command_path.run_one("list-files").error)

    def test_document_read_accepts_utf8_bom_and_rejects_invalid_encoding(self) -> None:
        readme = self.project / "README.md"
        readme.write_bytes(b"\xef\xbb\xbfA readable UTF-8 document\n")
        outcome = command_path.run_one("readme")
        self.assertIsNone(outcome.error)
        self.assertEqual(outcome.result, "A readable UTF-8 document")
        readme.write_bytes(b"\xff\xfe\x00Invalid UTF-8\n")
        self.assertTrue(command_path.run_one("readme").error)

    def test_document_read_rejects_oversized_files(self) -> None:
        (self.project / "README.md").write_bytes(b"x" * (1024 * 1024 + 1))
        self.assertTrue(command_path.run_one("readme").error)

    def test_malformed_json_command_returns_structured_failure(self) -> None:
        self.assertTrue(command_path.run_one('json {"Incomplete":').error)

    def test_json_rejects_nonfinite_values_and_duplicate_keys(self) -> None:
        for source in (
            'NaN',
            'Infinity',
            '-Infinity',
            '{"Value":NaN}',
            '{"Same":1,"Same":2}',
        ):
            with self.subTest(source=source):
                self.assertTrue(command_path.run_one("json " + source).error)

    def test_json_and_model_json_handle_excessive_nesting(self) -> None:
        nested = "[" * 1500 + "0" + "]" * 1500
        self.assertTrue(command_path.run_one("json " + nested).error)
        decision = self.model_decision('{"action":"echo","payload":' + nested + '}')
        self.assertTrue(decision is None or decision.action == "status")

    def test_json_nesting_limit_ignores_escaped_quotes_and_string_brackets(self) -> None:
        payload = {"Text": '[{\\"' * 300 + "}]" * 300}
        outcome = command_path.run_one("json " + json.dumps(payload))
        self.assertIsNone(outcome.error)
        self.assertEqual(json.loads(outcome.result), payload)
        nested = "[" * 128 + "0" + "]" * 128
        self.assertIsNone(command_path.run_one("json " + nested).error)
        self.assertTrue(command_path.run_one("json [" + nested + "]").error)

    def test_json_rejects_float_overflow(self) -> None:
        self.assertTrue(command_path.run_one('json {"Value": 1e999}').error)

    def test_input_limit_accepts_boundary_and_rejects_oversize(self) -> None:
        source = "echo " + "x" * (command_path.MAX_INPUT_CHARACTERS - 5)
        self.assertIsNone(command_path.run_one(source).error)
        self.assertTrue(command_path.run_one(source + "x").error)
        self.assertTrue(command_path.execute_command(
            command_path.CommandDecision("echo", "x" * (command_path.MAX_INPUT_CHARACTERS + 1))
        ).error)

    def test_model_proposals_execute_only_after_validation(self) -> None:
        gateway = mock.Mock()
        for response, expected in ((json.dumps({"action": "echo", "payload": "MiXeD  "}), "MiXeD  "),
                                   ('{"action":"delete","payload":"README.md"}', None)):
            with self.subTest(response=response):
                gateway.infer.return_value = model_adapter.ModelResult(
                    content=response, model="fixture", backend="mock", status=200
                )
                with mock.patch.object(command_path, "build_gateway_from_config", return_value=gateway):
                    outcome = command_path.run_one("a free form request", use_model=True)
                if expected is None:
                    self.assertFalse(outcome.allowed)
                    self.assertTrue(outcome.error)
                else:
                    self.assertEqual(outcome.result, expected)
                    self.assertIsNone(outcome.error)

    def test_glyph_inventory_marks_counts_and_lists_as_truncated(self) -> None:
        glyphs = self.project / "glyphs" / "v0_1"
        glyphs.mkdir(parents=True)
        for number in range(3):
            (glyphs / f"rp_g{number}.svg").write_text("fixture", encoding="utf-8")
        with mock.patch.object(command_path, "MAX_DIRECTORY_ENTRIES", 2):
            report = command_path.run_one("check-glyph-map")
            self.assertIsNone(report.error)
            self.assertIn("glyph_dir_file_count: at least 3 (listing truncated)", report.result)
            report = command_path.run_one("glyphs")
            self.assertIsNone(report.error)
            self.assertIn("glyph listing truncated", report.result)

    def test_cli_returns_nonzero_for_structured_error(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                command_path.main(["--input", 'json {"Incomplete":'])
        self.assertEqual(stopped.exception.code, 1)

    def test_interactive_eof_exits_cleanly(self) -> None:
        with mock.patch("builtins.input", side_effect=EOFError):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    command_path.main([])
                except SystemExit as stopped:
                    self.assertIn(stopped.code, (None, 0))

    def test_interactive_ctrl_c_exits_with_130(self) -> None:
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    command_path.main([])
        self.assertEqual(stopped.exception.code, 130)


if __name__ == "__main__":
    unittest.main()
