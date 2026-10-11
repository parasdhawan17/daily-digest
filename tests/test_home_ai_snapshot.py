from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_home_ai_snapshot as build


def payload(hours=0):
    item = {'heading': 'Growth', 'text': 'Reported growth.', 'tone': 'positive',
            'evidence_ids': ['S1'], 'facts': [{'label': 'Revenue', 'value': '+10%'}]}
    data = {k: [] for k in build.CATEGORIES}
    data.update(summary=item, encouraging=[item], sources=[{'id': 'S1'}],
                generated_at=(datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat())
    return {'ok': True, 'stock': {'name': 'Example', 'symbol': 'IN:EXAMPLE',
            'price': 100, 'percent_change': 2, 'market_cap_crore': 1000},
            'core': {}, 'overview': {'ok': True, 'data': data}}


class SnapshotTests(unittest.TestCase):
    def test_validation_and_boundary(self):
        self.assertIsNotNone(build.validate(payload(47), 48))
        self.assertIsNone(build.validate(payload(48), 48))
        self.assertIsNone(build.validate(payload(-1), 48))
        for value in (None, {}, {'ok': True}):
            self.assertIsNone(build.validate(value, 48))
        value = payload(); value['overview']['data']['summary'] = None
        self.assertIsNone(build.validate(value, 48))

    def test_production_reuse_and_fallback(self):
        with patch.dict(build.os.environ, {'VERCEL_ENV': 'production', 'INDIANAPI_API_KEY': 'test', 'OPENROUTER_API_KEY': 'test'}, clear=True):
            with patch.object(build, 'read_previous', return_value=payload()) as read, patch.object(build, 'generate') as generate:
                value, source = build.prepare()
                self.assertEqual(source, 'production API'); generate.assert_not_called()
                read.assert_called_once_with('/api/home-ai-signal?selection=market-cap-v1', 10, 24)
            with patch.object(build, 'read_previous', side_effect=[None, payload(30)]), patch.object(build, 'generate', return_value=None):
                self.assertEqual(build.prepare()[1], 'previous snapshot')
            with patch.object(build, 'read_previous', return_value=None), patch.object(build, 'generate', return_value=payload()):
                self.assertEqual(build.prepare()[1], 'fresh generation')

    def test_preview_and_missing_credentials(self):
        with patch.dict(build.os.environ, {'VERCEL_ENV': 'preview'}, clear=True), patch.object(build, 'read_previous') as read:
            self.assertIsNone(build.prepare()[0]); read.assert_not_called()
        with patch.dict(build.os.environ, {'VERCEL_ENV': 'production'}, clear=True), patch.object(build, 'read_previous', return_value=None), patch.object(build, 'generate') as generate:
            self.assertIsNone(build.prepare()[0]); generate.assert_not_called()

    def test_subprocess_timeout_and_invalid_output(self):
        for error in (subprocess.TimeoutExpired('python', 120), ValueError('bad')):
            with patch.object(build.subprocess, 'run', side_effect=error):
                self.assertIsNone(build.generate())

    def test_artifacts_and_safe_embedding(self):
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory)
            public.joinpath('index.html').write_text(build.MARKER + 'null</script>')
            value = payload(); value['stock']['name'] = '</script><script>alert(1)</script>'
            build.write_artifacts(public, value)
            html = public.joinpath('index.html').read_text()
            self.assertEqual(html.count('</script>'), 1)
            self.assertNotIn('<script>alert', html)
            embedded = json.loads(html[len(build.MARKER):-len('</script>')])
            self.assertEqual(embedded, json.loads(public.joinpath('home-ai-snapshot.json').read_text()))
            build.write_artifacts(public, None)
            self.assertIsNone(json.loads(public.joinpath('home-ai-snapshot.json').read_text())['payload'])
