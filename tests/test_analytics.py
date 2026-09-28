import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from api.analytics import DEFAULT_POSTHOG_HOST, handle_get
from api.index import route


def handler(path="/api/analytics/config"):
    return SimpleNamespace(
        path=path,
        headers={},
        wfile=io.BytesIO(),
        send_response=Mock(),
        send_header=Mock(),
        end_headers=Mock(),
    )


class AnalyticsConfigTests(unittest.TestCase):
    def test_route_supports_direct_and_rewritten_paths(self):
        self.assertEqual(route(handler()), "analytics-config")
        self.assertEqual(route(handler("/api/index?route=analytics-config")), "analytics-config")

    def test_disabled_config_is_safe_and_cacheable(self):
        with patch.dict(os.environ, {}, clear=True):
            target = handler()
            handle_get(target)
        payload = json.loads(target.wfile.getvalue())
        self.assertEqual(payload, {
            "ok": True,
            "enabled": False,
            "project_key": "",
            "host": DEFAULT_POSTHOG_HOST,
        })
        headers = dict(call.args for call in target.send_header.call_args_list)
        self.assertIn("max-age=300", headers["Cache-Control"])

    def test_config_exposes_public_key_and_rejects_unsafe_host(self):
        with patch.dict(os.environ, {
            "POSTHOG_PROJECT_KEY": "phc_public",
            "POSTHOG_HOST": "http://not-secure.example",
        }, clear=True):
            target = handler()
            handle_get(target)
        payload = json.loads(target.wfile.getvalue())
        self.assertTrue(payload["enabled"])
        self.assertEqual(payload["project_key"], "phc_public")
        self.assertEqual(payload["host"], DEFAULT_POSTHOG_HOST)


if __name__ == "__main__":
    unittest.main()
