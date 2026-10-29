import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


spec = importlib.util.spec_from_file_location(
    "upload_bilibili",
    Path(__file__).resolve().parents[1] / "scripts/upload_bilibili.py",
)
upload = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = upload
spec.loader.exec_module(upload)


def cookie(name, value, domain=".bilibili.com", expires=None):
    return upload.Cookie(name, value, domain, expires)


def session(label):
    return [cookie("SESSDATA", label), cookie("bili_jct", label + "-csrf")]


class BrowserSelectionTests(unittest.TestCase):
    def collect(self, batches, statuses, only=None):
        browsers = [
            upload.Browser(name, "chromium", [])
            for name in ("chrome", "chromium", "edge")
        ]
        with (
            mock.patch.object(upload, "supported_browsers", return_value=browsers),
            mock.patch.object(
                upload.Browser, "existing_db", return_value=Path("Cookies")
            ),
            mock.patch.object(upload, "_read_chromium", side_effect=batches) as read,
            mock.patch.object(
                upload, "_validate_browser_login", side_effect=statuses
            ) as validate,
        ):
            result = upload.collect_browser_cookies(only)
        return result, read, validate

    def test_skips_logged_out_session_without_mixing_cookies(self):
        result, read, validate = self.collect(
            [session("old"), session("valid"), session("unused")], [False, True]
        )
        self.assertEqual(result, {"SESSDATA": "valid", "bili_jct": "valid-csrf"})
        self.assertEqual(read.call_count, 2)
        self.assertEqual(validate.call_args_list[0].args[0]["bili_jct"], "old-csrf")

    def test_incomplete_browsers_are_never_combined(self):
        result, _, validate = self.collect(
            [
                [cookie("SESSDATA", "one")],
                [cookie("bili_jct", "two")],
                session("three"),
            ],
            [True],
        )
        self.assertEqual(result["SESSDATA"], "three")
        self.assertEqual(validate.call_count, 1)

    def test_api_failure_continues_to_next_browser(self):
        result, _, _ = self.collect(
            [session("one"), session("two")], [RuntimeError("API unavailable"), True]
        )
        self.assertEqual(result["SESSDATA"], "two")

    def test_read_failure_continues_to_next_browser(self):
        result, _, _ = self.collect([RuntimeError("locked"), session("two")], [True])
        self.assertEqual(result["SESSDATA"], "two")

    def test_api_failures_are_not_reported_as_logout(self):
        with self.assertRaisesRegex(SystemExit, "login checks failed"):
            self.collect(
                [session("one"), session("two"), session("three")],
                [RuntimeError("offline")] * 3,
            )

    def test_all_logged_out_fails_closed(self):
        with self.assertRaisesRegex(SystemExit, "No logged-in"):
            self.collect([session("one")] * 3, [False] * 3)

    def test_pinned_browser_does_not_switch_accounts(self):
        result, read, _ = self.collect([session("edge")], [True], only="edge")
        self.assertEqual(result["SESSDATA"], "edge")
        self.assertEqual(read.call_args.args[0].name, "edge")
        with self.assertRaisesRegex(SystemExit, "No logged-in"):
            self.collect([session("edge")], [False], only="edge")

    def test_unknown_browser_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "Unsupported browser"):
            self.collect([], [], only="typo")

    def test_root_domain_expiry_and_empty_values(self):
        with mock.patch.object(upload.time, "time", return_value=100):
            selected = upload._select_browser_cookies(
                [
                    cookie("SESSDATA", "root", expires=200),
                    cookie("SESSDATA", "subdomain", "live.bilibili.com", 300),
                    cookie("expired", "bad", expires=100),
                    cookie("empty", ""),
                    cookie("evil", "bad", "evilbilibili.com"),
                    cookie("session", "ok"),
                ]
            )
        self.assertEqual(selected, {"SESSDATA": "root", "session": "ok"})


class LoginValidationTests(unittest.TestCase):
    def test_login_logout_and_api_errors(self):
        self.assertTrue(
            upload._parse_login_status({"code": 0, "data": {"isLogin": True}})
        )
        self.assertFalse(
            upload._parse_login_status({"code": 0, "data": {"isLogin": False}})
        )
        self.assertFalse(upload._parse_login_status({"code": -101}))
        for body in [
            None,
            {},
            {"code": "0"},
            {"code": False},
            {"code": -412},
            {"code": 0, "data": {}},
            {"code": 0, "data": {"isLogin": "true"}},
        ]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                upload._parse_login_status(body)

    def test_request_has_bounded_timeouts_and_no_redirects(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"code": 0, "data": {"isLogin": True}}
        with mock.patch("curl_cffi.requests.get", return_value=response) as get:
            self.assertTrue(upload._validate_browser_login({"SESSDATA": "secret"}))
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 5))
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        with mock.patch("curl_cffi.requests.get", side_effect=RuntimeError("secret")):
            with self.assertRaisesRegex(RuntimeError, "not a logout") as error:
                upload._validate_browser_login({})
        self.assertNotIn("secret", str(error.exception))

    def test_http_and_malformed_json_are_errors(self):
        for response in [
            mock.Mock(status_code=302),
            mock.Mock(status_code=403),
            mock.Mock(status_code=200, json=mock.Mock(side_effect=ValueError())),
        ]:
            with (
                mock.patch("curl_cffi.requests.get", return_value=response),
                self.assertRaises(RuntimeError),
            ):
                upload._validate_browser_login({})


class ChromiumDecryptionTests(unittest.TestCase):
    def encrypt(self, prefix, key, value):
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        return prefix + AES.new(key, AES.MODE_CBC, b" " * 16).encrypt(pad(value, 16))

    def test_legacy_and_host_bound_values(self):
        key = upload._pbkdf2_aes_key(b"test-key", 1)
        old = self.encrypt(b"v11", key, b"session")
        bound = upload.hashlib.sha256(b".bilibili.com").digest() + b"session"
        new = self.encrypt(b"v11", key, bound)
        with mock.patch.object(upload.sys, "platform", "linux"):
            self.assertEqual(
                upload._decrypt_chromium_value(old, key, ".bilibili.com", 23), "session"
            )
            self.assertEqual(
                upload._decrypt_chromium_value(new, key, ".bilibili.com", 24), "session"
            )
            self.assertEqual(
                upload._decrypt_chromium_value(new, key, ".example.com", 24), ""
            )
            self.assertEqual(
                upload._decrypt_chromium_value(new, None, ".bilibili.com", 24), ""
            )
            legacy_key = upload._pbkdf2_aes_key(b"peanuts", 1)
            legacy = self.encrypt(b"v10", legacy_key, b"legacy")
            self.assertEqual(
                upload._decrypt_chromium_value(legacy, key, ".bilibili.com", 23),
                "legacy",
            )

    def test_corrupt_unsupported_and_invalid_utf8_are_rejected(self):
        key = upload._pbkdf2_aes_key(b"test-key", 1)
        for value in [b"v20secret", b"v11bad", self.encrypt(b"v11", key, b"\xff")]:
            self.assertEqual(
                upload._decrypt_chromium_value(value, key, ".bilibili.com", 23), ""
            )

    def test_keyring_lookup_is_bounded_and_does_not_fallback(self):
        with mock.patch.object(
            upload.subprocess,
            "run",
            return_value=mock.Mock(returncode=0, stdout=b"key\n"),
        ) as run:
            self.assertEqual(
                upload._linux_chromium_key("Chrome"), upload._pbkdf2_aes_key(b"key", 1)
            )
        self.assertEqual(
            run.call_args.args[0], ["secret-tool", "lookup", "application", "chrome"]
        )
        self.assertEqual(run.call_args.kwargs["timeout"], 10)
        with mock.patch.object(
            upload.subprocess, "run", return_value=mock.Mock(returncode=1, stdout=b"")
        ):
            with self.assertRaises(RuntimeError):
                upload._linux_chromium_key("Chrome")

    def test_reader_uses_database_version_and_filters_domain(self):
        key = upload._pbkdf2_aes_key(b"peanuts", 1)
        value = self.encrypt(
            b"v10", key, upload.hashlib.sha256(b".bilibili.com").digest() + b"session"
        )
        rows = [
            ("SESSDATA", "", value, ".bilibili.com", 0),
            ("bad", "bad", b"", "evilbilibili.com", 0),
        ]
        with mock.patch.object(
            upload, "_read_sqlite_rows", side_effect=[rows, [("24",)]]
        ):
            result = upload._read_chromium(
                upload.Browser("chrome", "chromium", []),
                Path("Cookies"),
                "bilibili.com",
            )
        self.assertEqual(result, [cookie("SESSDATA", "session")])

    def test_sqlite_copy_stays_private_and_is_cleaned_up(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "Cookies"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE example (value TEXT)")
                conn.execute("INSERT INTO example VALUES ('test')")
            self.assertEqual(
                upload._read_sqlite_rows(db, "SELECT value FROM example"), [("test",)]
            )


if __name__ == "__main__":
    unittest.main()
