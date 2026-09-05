"""Offline regression checks for model configuration and HTTP boundaries."""

import io
import json
import stat
import traceback
import unittest
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from unittest import mock
from urllib import error, request

import stutt_model_adapter as adapter


class Body(io.BytesIO):
    def __init__(self, value, status=200):
        super().__init__(value)
        self.status = status
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


def spec(**changes):
    values = {"name": "local", "model": "test-model", "base_url": "http://localhost:8000"}
    values.update(changes)
    return adapter.OpenAICompatibleSpec(**values)


def config_item(**changes):
    values = {"name": "local", "model": "test-model", "base_url": "http://localhost:8000"}
    values.update(changes)
    return values


class ConfigurationTests(unittest.TestCase):
    def load(self, value):
        body = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
        self.body = Body(body)
        with (mock.patch.object(Path, "stat", return_value=mock.Mock(st_mode=stat.S_IFREG)),
              mock.patch.object(Path, "open", autospec=True, return_value=self.body) as opened):
            result = adapter.load_backends_from_file(Path("test-model-config.json"))
            opened.assert_called_once_with(Path("test-model-config.json"), "rb")
        return result

    def test_valid_config_defaults_and_disabled_entries(self):
        backends = self.load({"openai_compatible": [config_item(), config_item(name="cloud", enabled=False)]})
        self.assertEqual([b.name for b in backends], ["local"])
        self.assertEqual(backends[0].spec.timeout_seconds, 30)
        self.assertEqual(self.body.read_sizes, [adapter.MAX_CONFIG_BYTES + 1])
        self.assertTrue(self.body.closed)

    def test_utf8_bom_and_explicit_values(self):
        item = config_item(name="test unicode \u00e9", timeout_seconds=61, temperature=0,
                           max_tokens=17, api_key_env="TEST_MODEL_KEY", request_path="chat")
        body = json.dumps({"openai_compatible": [item]}).encode("utf-8-sig")
        backend = self.load(body)[0]
        self.assertEqual(backend.name, "test unicode \u00e9")
        self.assertEqual(backend.spec.endpoint(), "http://localhost:8000/chat")
        self.assertEqual(backend.spec.max_tokens, 17)

    def test_invalid_json_and_unicode_are_backend_errors(self):
        for body in (b"{", b"\xff", b'{"openai_compatible":NaN}',
                     b'{"openai_compatible": [], "openai_compatible": []}',
                     b"[" * 1500 + b"]" * 1500):
            with self.subTest(body=body[:60]), self.assertRaises(adapter.ModelBackendError):
                self.load(body)

    def test_json_depth_limit_is_deterministic_and_includes_objects(self):
        limit = adapter.MAX_JSON_DEPTH
        self.assertEqual(limit, 128)
        self.assertIsInstance(adapter._decode_json(b"[" * limit + b"0" + b"]" * limit, "test"), list)
        for body in (b"[" * (limit + 1) + b"0" + b"]" * (limit + 1),
                     b'{"nested":' * (limit + 1) + b"0" + b"}" * (limit + 1)):
            with self.subTest(body=body[:40]), self.assertRaisesRegex(adapter.ModelBackendError, "JSON nesting exceeds 128"):
                self.load(body)

    def test_config_brackets_and_escaped_quotes_in_strings_do_not_count(self):
        name = '[{\\\"' * 150 + ']}"'
        backends = self.load({"openai_compatible": [config_item(name=name)]})
        self.assertEqual(backends[0].name, name)

    def test_wrong_schema_shapes(self):
        cases = [None, [], 0, "text", {}, {"openai_compatible": None},
                 {"openai_compatible": {}}, {"openai_compatible": [None]},
                 {"openai_compatible": [[]]}, {"openai_compatible": [{}]},
                 {"openai_compatible": [], "unknown": 1}]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(adapter.ModelBackendError):
                self.load(case)

    def test_bad_fields_are_rejected_without_coercion(self):
        changes = [dict(name=1), dict(model=None), dict(base_url=[]), dict(enabled="false"),
                   dict(enabled=1), dict(enabled=None), dict(timeout_seconds="30"),
                   dict(timeout_seconds=0), dict(timeout_seconds=-1), dict(timeout_seconds=True),
                   dict(timeout_seconds=None), dict(timeout_seconds=float("inf")),
                   dict(temperature=-1), dict(temperature=3), dict(temperature=True),
                   dict(max_tokens=0), dict(max_tokens=2.5), dict(max_tokens=True),
                   dict(api_key_env=4), dict(api_key_env="BAD=NAME"), dict(api_key={}),
                   dict(api_key="key\r\nInjected: header"), dict(api_key=""),
                   dict(name="line\nbreak"), dict(request_path=None), dict(enabld=False)]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(adapter.ModelBackendError):
                self.load({"openai_compatible": [config_item(**change)]})

    def test_duplicate_names_even_when_disabled_are_rejected(self):
        with self.assertRaisesRegex(adapter.ModelBackendError, "duplicate backend name"):
            self.load({"openai_compatible": [config_item(), config_item(enabled=False)]})

    def test_config_read_errors_are_normalized(self):
        for exc in (FileNotFoundError("private path"), PermissionError("private path"),
                    IsADirectoryError(), OSError("private path")):
            with (self.subTest(exc=type(exc)),
                  mock.patch.object(Path, "stat", return_value=mock.Mock(st_mode=stat.S_IFREG)),
                  mock.patch.object(Path, "open", side_effect=exc)):
                with self.assertRaises(adapter.ModelBackendError) as caught:
                    adapter.load_backends_from_file("anything.json")
                self.assertNotIn("private path", str(caught.exception))
        with self.assertRaises(adapter.ModelBackendError):
            adapter.load_backends_from_file(None)

    def test_special_config_files_are_rejected_before_open(self):
        for mode in (stat.S_IFDIR, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK):
            with (self.subTest(mode=mode),
                  mock.patch.object(Path, "stat", return_value=mock.Mock(st_mode=mode)),
                  mock.patch.object(Path, "open") as opened):
                with self.assertRaisesRegex(adapter.ModelBackendError, "regular file"):
                    adapter.load_backends_from_file("special-config")
                opened.assert_not_called()

    def test_config_size_limit(self):
        with mock.patch.object(adapter, "MAX_CONFIG_BYTES", 20):
            with self.assertRaisesRegex(adapter.ModelBackendError, "exceeds 20"):
                self.load(b" " * 21)
            self.assertEqual(self.body.read_sizes, [21])

    def test_default_config_is_anchored_beside_module(self):
        expected = Path(adapter.__file__).resolve().with_name("stutt_model_backends.example.json")
        self.assertEqual(adapter.DEFAULT_CONFIG_PATH, expected)
        with mock.patch.object(Path, "open", autospec=True, return_value=Body(b'{"openai_compatible": []}')) as opened:
            self.assertEqual(adapter.load_backends_from_file(), [])
            opened.assert_called_once_with(expected, "rb")

    def test_example_enables_only_local_and_keeps_cloud_inactive(self):
        backends = adapter.load_backends_from_file()
        self.assertEqual([b.name for b in backends], ["nvidia-local-stack"])
        self.assertIsNone(backends[0].spec.api_key_env)
        example = json.loads(adapter.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8-sig"))
        cloud = next(item for item in example["openai_compatible"] if item["name"] == "nvidia-cloud-nim")
        self.assertIs(cloud["enabled"], False)
        self.assertEqual(cloud["base_url"] + cloud["request_path"],
                         "https://integrate.api.nvidia.com/v1/chat/completions")


class EndpointAndRequestTests(unittest.TestCase):
    def test_endpoint_joins_base_path_and_relative_request_path(self):
        self.assertEqual(spec(base_url="https://example.test/v1/", request_path="chat/completions").endpoint(),
                         "https://example.test/v1/chat/completions")

    def test_plaintext_http_is_restricted_to_loopback(self):
        for host in ("example.test", "192.168.1.2", "10.0.0.2", "localhost.example.test"):
            with self.subTest(host=host), self.assertRaisesRegex(adapter.ModelBackendError, "must use HTTPS"):
                spec(base_url=f"http://{host}")
        self.assertEqual(spec(base_url="https://192.168.1.2").endpoint(), "https://192.168.1.2/v1/chat/completions")

    def test_bad_endpoints_are_model_errors(self):
        urls = ["localhost:8000", "file:///private", "ftp://example.test", "http://",
                "http://user:secret@example.test", "http://localhost:bad", "http://localhost:70000",
                "http://localhost:0", "http://[", "http://localhost?key=secret", "http://localhost#fragment",
                "http://localhost?", "http://localhost#", " http://localhost", "http://local host",
                "http://localhost\n", "http://localhost\\remote", "http://local%68ost"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(adapter.ModelBackendError):
                spec(base_url=url)
        for path in ("//remote/chat", "http://remote/chat", "http://[", "/chat?key=secret", "/chat#fragment", " /chat", ""):
            with self.subTest(path=path), self.assertRaises(adapter.ModelBackendError):
                spec(request_path=path)

    def test_bad_request_fields_fail_before_http(self):
        fields = [dict(prompt=None), dict(prompt=4), dict(prompt="\ud800"), dict(context={}),
                  dict(max_tokens=-2), dict(max_tokens=True), dict(temperature=float("nan")),
                  dict(temperature=3), dict(top_p=-0.1), dict(top_p=2), dict(top_p=False),
                  dict(timeout_seconds=0), dict(timeout_seconds=-1), dict(timeout_seconds="30"),
                  dict(timeout_seconds=float("inf")), dict(timeout_seconds=10 ** 400)]
        for field in fields:
            values = {"prompt": "hello", **field}
            with self.subTest(field=field), self.assertRaises(adapter.ModelBackendError):
                adapter.ModelRequest(**values)


class InferenceTests(unittest.TestCase):
    def start_patch(self, patcher):
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def setUp(self):
        self.openers = self.start_patch(mock.patch.object(adapter.request, "build_opener"))
        self.opener = self.openers.return_value
        self.start_patch(mock.patch.object(adapter.ssl, "create_default_context", return_value=mock.sentinel.tls))
        self.start_patch(mock.patch.dict(adapter.os.environ, {}, clear=True))

    def infer(self, body, *, backend_spec=None, payload=None, status=200):
        encoded = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.response = Body(encoded, status=status)
        self.opener.open.return_value = self.response
        return adapter.OpenAICompatibleBackend(backend_spec or spec()).infer(payload or adapter.ModelRequest("hello"))

    def test_chat_happy_path_and_default_backend_timeout(self):
        raw = {"choices": [{"message": {"content": "reply \u00e9"}}]}
        result = self.infer(raw, backend_spec=spec(timeout_seconds=47, temperature=0.2, max_tokens=123),
                            payload=adapter.ModelRequest("hello \u00e9", context="context"))
        self.assertEqual(result.content, "reply \u00e9")
        self.assertEqual((result.backend, result.model, result.status), ("local", "test-model", 200))
        self.assertEqual(result.raw, raw)
        req = self.opener.open.call_args.args[0]
        self.assertEqual(req.full_url, "http://localhost:8000/v1/chat/completions")
        self.assertEqual(req.get_method(), "POST")
        self.assertIsNone(req.get_header("Authorization"))
        self.assertEqual(self.opener.open.call_args.kwargs["timeout"], 47)
        self.assertEqual(json.loads(req.data), {"model": "test-model", "messages": [
            {"role": "system", "content": "context"}, {"role": "user", "content": "hello \u00e9"}],
            "stream": False, "temperature": 0.2, "max_tokens": 123})
        self.assertEqual(self.response.read_sizes, [adapter.MAX_RESPONSE_BYTES + 1])
        self.assertTrue(self.response.closed)

    def test_request_overrides_and_legacy_text_response(self):
        result = self.infer({"choices": [{"text": "legacy"}]},
                            backend_spec=spec(timeout_seconds=60, max_tokens=900, temperature=1),
                            payload=adapter.ModelRequest("hello", timeout_seconds=3, max_tokens=7, temperature=0, top_p=0))
        self.assertEqual(result.content, "legacy")
        self.assertEqual(self.opener.open.call_args.kwargs["timeout"], 3)
        sent = json.loads(self.opener.open.call_args.args[0].data)
        self.assertEqual((sent["max_tokens"], sent["temperature"], sent["top_p"]), (7, 0, 0))

    def test_unconfigured_optional_fields_are_omitted(self):
        self.infer({"choices": [{"message": {"content": ""}}]})
        sent = json.loads(self.opener.open.call_args.args[0].data)
        self.assertEqual(set(sent), {"model", "messages", "stream"})

    def test_loopback_auth_optional_and_environment_proxies_disabled(self):
        for host in ("localhost", "LOCALHOST.", "127.0.0.1", "127.0.0.2", "[::1]"):
            with self.subTest(host=host):
                self.infer({"choices": [{"text": "ok"}]}, backend_spec=spec(base_url=f"http://{host}:8000"))
                self.assertIsNone(self.opener.open.call_args.args[0].get_header("Authorization"))
                proxies = [h for h in self.openers.call_args.args if isinstance(h, request.ProxyHandler)]
                self.assertEqual(len(proxies), 1)
                self.assertEqual(proxies[0].proxies, {})

    def test_remote_and_lookalike_hosts_require_key_before_connection(self):
        for host in ("example.test", "localhost.example.test", "127.0.0.1.example.test"):
            with self.subTest(host=host), self.assertRaisesRegex(adapter.ModelBackendError, "no API key"):
                adapter.OpenAICompatibleBackend(spec(base_url=f"https://{host}")).infer(adapter.ModelRequest("private"))
        self.opener.open.assert_not_called()

    def test_remote_environment_key_and_explicit_local_key(self):
        with mock.patch.dict(adapter.os.environ, {"TEST_MODEL_KEY": "fake-key"}):
            self.infer({"choices": [{"text": "ok"}]}, backend_spec=spec(base_url="https://example.test", api_key_env="TEST_MODEL_KEY"))
        self.assertEqual(self.opener.open.call_args.args[0].get_header("Authorization"), "Bearer fake-key")
        self.infer({"choices": [{"text": "ok"}]}, backend_spec=spec(api_key="explicit-fake-key"))
        self.assertEqual(self.opener.open.call_args.args[0].get_header("Authorization"), "Bearer explicit-fake-key")

    def test_invalid_environment_key_is_sanitized_before_http(self):
        with mock.patch.dict(adapter.os.environ, {"TEST_MODEL_KEY": "fake-secret\nInjected"}):
            with self.assertRaises(adapter.ModelBackendError) as caught:
                adapter.OpenAICompatibleBackend(spec(api_key_env="TEST_MODEL_KEY")).infer(adapter.ModelRequest("hello"))
        self.assertNotIn("fake-secret", str(caught.exception))
        self.opener.open.assert_not_called()

    def test_empty_environment_key_is_absent_for_optional_local_auth(self):
        with mock.patch.dict(adapter.os.environ, {"TEST_MODEL_KEY": ""}):
            self.infer({"choices": [{"text": "ok"}]}, backend_spec=spec(api_key_env="TEST_MODEL_KEY"))
        self.assertIsNone(self.opener.open.call_args.args[0].get_header("Authorization"))

    def test_direct_api_key_takes_precedence(self):
        with mock.patch.dict(adapter.os.environ, {"TEST_MODEL_KEY": "environment-fake-key"}):
            self.assertEqual(spec(api_key="explicit-fake-key", api_key_env="TEST_MODEL_KEY").api_key_value(), "explicit-fake-key")

    def test_redirects_are_not_followed(self):
        self.infer({"choices": [{"text": "ok"}]})
        handlers = [h for h in self.openers.call_args.args if isinstance(h, request.HTTPRedirectHandler)]
        self.assertEqual(len(handlers), 1)
        req = request.Request("http://localhost:8000", data=b"private", headers={"Authorization": "Bearer fake-key"})
        self.assertIsNone(handlers[0].redirect_request(req, None, 302, "Found", {}, "https://elsewhere.test"))

    def test_wrong_response_shapes_are_model_errors(self):
        bodies = [None, [], "text", 1, True, {}, {"choices": None}, {"choices": {}},
                  {"choices": []}, {"choices": [None]}, {"choices": ["text"]},
                  {"choices": [{"message": []}]}, {"choices": [{"message": {"content": []}}]},
                  {"choices": [{"text": 3}]}, {"choices": [{"message": {"content": "\ud800"}}]}]
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(adapter.ModelBackendError):
                self.infer(body)

    def test_invalid_response_json_and_utf8_do_not_echo_body(self):
        for body in (b"fake-secret", b"\xfffake-secret", b'{"choices":NaN}',
                     b"[" * 1500 + b"]" * 1500):
            with self.subTest(body=body[:30]), self.assertRaises(adapter.ModelBackendError) as caught:
                self.infer(body)
            self.assertNotIn("fake-secret", str(caught.exception))

    def test_response_json_nesting_is_capped(self):
        body = b'{"choices":[{"text":"ok"}],"extra":' + b"[" * 128 + b"0" + b"]" * 128 + b"}"
        with self.assertRaisesRegex(adapter.ModelBackendError, "JSON nesting exceeds 128"):
            self.infer(body)

    def test_response_brackets_and_escaped_quotes_in_content_do_not_count(self):
        content = '[{\\\"' * 150 + ']}"'
        result = self.infer({"choices": [{"message": {"content": content}}]})
        self.assertEqual(result.content, content)

    def test_overflowing_response_numbers_are_rejected(self):
        for number in (b"1e999", b"-1e999", b"NaN", b"Infinity"):
            with self.subTest(number=number), self.assertRaisesRegex(adapter.ModelBackendError, "invalid UTF-8 JSON"):
                self.infer(b'{"choices":[{"text":"ok"}],"usage":' + number + b"}")

    def test_response_utf8_bom_is_accepted(self):
        result = self.infer(b'\xef\xbb\xbf{"choices":[{"text":"ok"}]}')
        self.assertEqual(result.content, "ok")

    def test_oversized_response_is_bounded_and_closed(self):
        with mock.patch.object(adapter, "MAX_RESPONSE_BYTES", 32):
            with self.assertRaisesRegex(adapter.ModelBackendError, "exceeds 32"):
                self.infer(b"x" * 100)
        self.assertEqual(self.response.read_sizes, [33])
        self.assertTrue(self.response.closed)

    def test_http_errors_do_not_read_or_echo_secret_body_reason_or_url(self):
        for status in (302, 401, 429, 500):
            body = Body(b"private-body-with-fake-key")
            exc = error.HTTPError("https://example.test/private-url", status, "private-reason", {}, body)
            self.opener.open.side_effect = exc
            with self.subTest(status=status), self.assertRaises(adapter.ModelBackendError) as caught:
                adapter.OpenAICompatibleBackend(spec()).infer(adapter.ModelRequest("private-prompt"))
            self.assertEqual(str(caught.exception), f"local: HTTP {status}")
            formatted = "".join(traceback.format_exception(caught.exception))
            self.assertNotIn("private-", formatted)
            self.assertEqual(body.read_sizes, [])
            self.assertTrue(body.closed)

    def test_network_timeout_and_transport_failures_are_sanitized(self):
        failures = [TimeoutError("fake-secret"), error.URLError("fake-secret"),
                    OSError("fake-secret"), RemoteDisconnected("fake-secret"),
                    IncompleteRead(b"fake-secret"), ValueError("fake-secret"), OverflowError("fake-secret")]
        for failure in failures:
            self.opener.open.side_effect = failure
            with self.subTest(failure=type(failure)), self.assertRaises(adapter.ModelBackendError) as caught:
                adapter.OpenAICompatibleBackend(spec()).infer(adapter.ModelRequest("hello"))
            self.assertNotIn("fake-secret", str(caught.exception))

    def test_read_timeout_is_normalized_and_response_closed(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.side_effect = TimeoutError("secret")
        self.opener.open.return_value = response
        with self.assertRaisesRegex(adapter.ModelBackendError, "timed out"):
            adapter.OpenAICompatibleBackend(spec()).infer(adapter.ModelRequest("hello"))
        response.__exit__.assert_called_once()

    def test_non_success_status_and_wrong_payload_object_are_rejected(self):
        with self.assertRaises(adapter.ModelBackendError):
            self.infer({"choices": [{"text": "ok"}]}, status=500)
        with self.assertRaises(adapter.ModelBackendError):
            adapter.OpenAICompatibleBackend(spec()).infer({"prompt": "hello"})


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.first = mock.Mock(spec=adapter.ModelBackend)
        self.first.name = "first"
        self.second = mock.Mock(spec=adapter.ModelBackend)
        self.second.name = "second"
        self.payload = adapter.ModelRequest("private prompt")
        self.first.infer.side_effect = adapter.ModelBackendError("first unavailable")
        self.result = adapter.ModelResult("ok", "test-model", "second", 200)
        self.second.infer.return_value = self.result

    def test_default_gateway_never_falls_back(self):
        with self.assertRaisesRegex(adapter.ModelBackendError, "first unavailable"):
            adapter.STUTTModelGateway((self.first, self.second)).infer(self.payload)
        self.second.infer.assert_not_called()

    def test_explicit_fallback_tries_second_backend(self):
        self.assertIs(adapter.STUTTModelGateway((self.first, self.second), allow_fallback=True).infer(self.payload), self.result)
        self.second.infer.assert_called_once_with(self.payload)

    def test_final_backend_failure_is_returned(self):
        self.second.infer.side_effect = adapter.ModelBackendError("second unavailable")
        with self.assertRaisesRegex(adapter.ModelBackendError, "second unavailable"):
            adapter.STUTTModelGateway((self.first, self.second), allow_fallback=True).infer(self.payload)

    def test_no_backend_and_non_boolean_fallback_fail(self):
        with self.assertRaisesRegex(adapter.ModelBackendError, "No backend"):
            adapter.STUTTModelGateway(()).infer(self.payload)
        for value in ("false", 0, 1, None):
            with self.subTest(value=value), self.assertRaises(adapter.ModelBackendError):
                adapter.STUTTModelGateway((self.first,), allow_fallback=value)

    def test_named_backend_is_first_without_enabling_fallback(self):
        with mock.patch.object(adapter, "load_backends_from_file", return_value=[self.first, self.second]):
            gateway = adapter.build_gateway_from_config(backend_name="second")
        self.assertEqual(gateway.backends, (self.second, self.first))
        self.assertFalse(gateway.allow_fallback)
        self.assertIs(gateway.infer(self.payload), self.result)
        self.first.infer.assert_not_called()

    def test_build_gateway_preserves_explicit_fallback_and_config_path(self):
        with mock.patch.object(adapter, "load_backends_from_file", return_value=[self.first]) as loader:
            gateway = adapter.build_gateway_from_config(config_path=Path("chosen.json"), allow_fallback=True)
        loader.assert_called_once_with(Path("chosen.json"))
        self.assertTrue(gateway.allow_fallback)

    def test_missing_backend_or_empty_config_are_model_errors(self):
        with mock.patch.object(adapter, "load_backends_from_file", return_value=[self.first]):
            with self.assertRaisesRegex(adapter.ModelBackendError, "not found"):
                adapter.build_gateway_from_config(backend_name="unknown")
        with mock.patch.object(adapter, "load_backends_from_file", return_value=[]):
            with self.assertRaisesRegex(adapter.ModelBackendError, "No enabled backends"):
                adapter.build_gateway_from_config()

    def test_simple_infer_passes_prompt_context_and_backend(self):
        with mock.patch.object(adapter, "build_gateway_from_config") as build:
            build.return_value.infer.return_value = self.result
            self.assertEqual(adapter.simple_infer("hello", context="system", backend="chosen"), "ok")
        build.assert_called_once_with(backend_name="chosen")
        build.return_value.infer.assert_called_once_with(adapter.ModelRequest("hello", context="system"))


if __name__ == "__main__":
    unittest.main()
