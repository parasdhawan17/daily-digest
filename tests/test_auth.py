import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from api.auth import handle_auth
from api.subscribe import handle_post
from api.digest import handle_get, handle_data_get, handle_ai_post, handle_subscription_get
from api.index import route
from stock_news import auth
from stock_news.brevo import BrevoError, subscribe_verified

ENV = {'GOOGLE_CLIENT_ID': 'client', 'SESSION_SIGNING_SECRET': 'a-separate-test-secret',
       'SITE_URL': 'https://example.com', 'BREVO_API_KEY': 'key',
       'BREVO_DOI_TEMPLATE_ID': '10', 'FINNHUB_API_KEY': 'f', 'INDIANAPI_API_KEY': 'i'}
IDENTITY = {'sub': 'google-123', 'email': 'investor@gmail.com'}
CONTACT = {'id': 42, 'email': IDENTITY['email'], 'listIds': [7],
           'attributes': {'US_TICKERS': 'US:AAPL, IN:TCS'}}


def handler(path='/', payload=None, signed_in=False):
    body = json.dumps(payload or {}).encode()
    cookie = 'tickr_csrf=csrf'
    if signed_in:
        cookie += '; tickr_session=' + auth.sign_session(IDENTITY)
    return SimpleNamespace(path=path, headers={'Cookie': cookie, 'Origin': ENV['SITE_URL'],
        'X-CSRF-Token': 'csrf', 'Content-Length': str(len(body))}, rfile=io.BytesIO(body),
        wfile=io.BytesIO(), send_response=Mock(), send_header=Mock(), end_headers=Mock())


def result(h):
    return json.loads(h.wfile.getvalue())


@patch.dict(os.environ, ENV)
class AuthTests(unittest.TestCase):
    def test_signed_session_tampering_expiry_and_cookie_flags(self):
        h = handler(signed_in=True)
        self.assertEqual(auth.get_session(h)['sub'], IDENTITY['sub'])
        h.headers['Cookie'] += 'x'
        with self.assertRaises(auth.AuthError): auth.get_session(h)
        h = handler(signed_in=True)
        with patch('stock_news.auth.time.time', return_value=10**12):
            with self.assertRaises(auth.AuthError): auth.get_session(h)
        cookie = auth.cookie_header('s', 'value', 1)
        for flag in ['HttpOnly', 'Secure', 'SameSite=Lax']: self.assertIn(flag, cookie)
        with patch.dict(os.environ, {'SITE_URL': 'http://localhost:3000'}):
            self.assertNotIn('Secure', auth.cookie_header('s', 'value', 1))

    def test_google_state_cookie_does_not_hide_app_cookies(self):
        for google_state in ['g_state={"i_l":0}', 'g_state={"i_l":0,"i_ll":123}']:
            for position in ['before', 'between', 'after']:
                with self.subTest(state=google_state, position=position):
                    h = handler(signed_in=True)
                    if position == 'before':
                        h.headers['Cookie'] = google_state + '; ' + h.headers['Cookie']
                    elif position == 'between':
                        h.headers['Cookie'] = h.headers['Cookie'].replace('; ', '; ' + google_state + '; ', 1)
                    else:
                        h.headers['Cookie'] += '; ' + google_state
                    auth.require_csrf(h)
                    self.assertEqual(auth.get_session(h)['sub'], IDENTITY['sub'])

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_verification_and_authoritative_email(self, verify):
        verify.return_value = {**IDENTITY, 'email_verified': True}
        self.assertEqual(auth.verify_google('credential'), IDENTITY)
        self.assertEqual(verify.call_args.args[2], 'client')
        for changes in [{'email_verified': False}, {'email': 'person@third-party.com'}, {'sub': ''}]:
            verify.return_value = {**IDENTITY, 'email_verified': True, **changes}
            with self.assertRaises(auth.AuthError): auth.verify_google('credential')
        verify.return_value = {**IDENTITY, 'email': 'person@company.com', 'email_verified': True, 'hd': 'company.com'}
        self.assertEqual(auth.verify_google('credential')['email'], 'person@company.com')
        verify.side_effect = ValueError('invalid signature/audience/expiry')
        with self.assertRaises(auth.AuthError): auth.verify_google('bad')

    def test_csrf_rejects_origin_and_token(self):
        for key, value in [('Origin', 'https://evil.example'), ('X-CSRF-Token', 'bad')]:
            h = handler(); h.headers[key] = value
            with self.assertRaises(auth.AuthError): auth.require_csrf(h)

    @patch('stock_news.auth.get_contact', return_value=CONTACT)
    def test_session_existing_and_incomplete_contacts(self, lookup):
        for contact, needs in [(CONTACT, False), (None, True),
                ({**CONTACT, 'listIds': []}, True), ({**CONTACT, 'attributes': {}}, True),
                ({**CONTACT, 'emailBlacklisted': True}, True)]:
            lookup.return_value = contact
            state = auth.subscription(IDENTITY)
            self.assertEqual(state['needs_subscription'], needs)
        lookup.return_value = {**CONTACT, 'attributes': {'US_TICKERS': 'AAPL'}}
        self.assertEqual(auth.subscription(IDENTITY)['tickers'], ['US:AAPL'])

    @patch('api.auth.verify_google', return_value=IDENTITY)
    @patch('stock_news.auth.get_contact', return_value=CONTACT)
    def test_login_sets_cookie_and_full_watchlist(self, lookup, verify):
        h = handler(payload={'credential': 'google-token'})
        handle_auth(h, 'google')
        self.assertEqual(result(h)['tickers'], ['US:AAPL', 'IN:TCS'])
        self.assertFalse(result(h)['needs_subscription'])
        cookie = next(c.args[1] for c in h.send_header.call_args_list if c.args[0] == 'Set-Cookie')
        self.assertIn('Max-Age=604800', cookie)
        self.assertIn('HttpOnly', cookie)

    @patch('api.auth.verify_google', return_value=IDENTITY)
    @patch('stock_news.auth.get_contact', side_effect=BrevoError('offline'))
    def test_lookup_failure_does_not_create_session(self, lookup, verify):
        h = handler(payload={'credential': 'token'}); handle_auth(h, 'google')
        self.assertFalse(result(h)['ok'])
        self.assertFalse(any(c.args[0] == 'Set-Cookie' for c in h.send_header.call_args_list))

    def test_expired_session_status_clears_cookie_and_logout(self):
        h = handler(signed_in=True)
        with patch('stock_news.auth.time.time', return_value=10**12): handle_auth(h, 'session')
        self.assertFalse(result(h)['authenticated'])
        self.assertTrue(any('Max-Age=0' in str(c) for c in h.send_header.call_args_list))
        h = handler(signed_in=True); handle_auth(h, 'logout')
        self.assertTrue(result(h)['ok'])
        self.assertTrue(any('Max-Age=0' in str(c) for c in h.send_header.call_args_list))

    def test_all_auth_routes(self):
        for name in ['config', 'session', 'google', 'logout']:
            self.assertEqual(route(handler('/api/auth/' + name)), 'auth-' + name)
            self.assertEqual(route(handler('/api/index?route=auth-' + name)), 'auth-' + name)


@patch.dict(os.environ, ENV)
class SubscribeTests(unittest.TestCase):
    @patch('api.subscribe.validate_symbol', return_value=True)
    @patch('api.subscribe.send_welcome_email')
    @patch('api.subscribe.subscribe_verified', return_value=False)
    def test_verified_signup_welcome_failure_and_update(self, save, welcome, validate):
        for active, failure in [(False, False), (False, True), (True, False)]:
            save.return_value = active
            welcome.reset_mock(); welcome.side_effect = BrevoError('offline') if failure else None
            h = handler(payload={'email': IDENTITY['email'], 'tickers': ['US:AAPL', 'IN:TCS']}, signed_in=True)
            handle_post(h)
            self.assertEqual(result(h)['redirect'], '/digest')
            self.assertEqual(bool(result(h)['warning']), failure)
            self.assertEqual(welcome.call_count, 0 if active else 1)

    @patch('api.subscribe.subscribe_verified')
    def test_email_substitution_csrf_and_invalid_tickers(self, save):
        for payload in [{'email': 'other@gmail.com', 'tickers': ['AAPL']}, {'tickers': []}]:
            h = handler(payload=payload, signed_in=True); handle_post(h)
            self.assertFalse(result(h)['ok'])
        h = handler(payload={'tickers': ['AAPL']}, signed_in=True)
        h.headers['X-CSRF-Token'] = ''; handle_post(h)
        self.assertFalse(result(h)['ok']); save.assert_not_called()

    @patch('api.subscribe.validate_symbol', return_value=True)
    @patch('api.subscribe.subscribe_or_update', return_value={'ok': True, 'mode': 'doi'})
    @patch('api.subscribe.subscribe_verified')
    def test_email_only_cannot_claim_verification(self, verified, doi, validate):
        h = handler(payload={'email': IDENTITY['email'], 'tickers': ['AAPL'], 'verified': True})
        handle_post(h)
        self.assertEqual(result(h)['mode'], 'doi'); verified.assert_not_called(); doi.assert_called_once()

    @patch('api.subscribe.validate_symbol', return_value=True)
    @patch('api.subscribe.subscribe_verified', side_effect=BrevoError('save failed'))
    @patch('api.subscribe.send_welcome_email')
    def test_save_failure_does_not_send_email(self, welcome, save, validate):
        h = handler(payload={'tickers': ['AAPL']}, signed_in=True); handle_post(h)
        self.assertFalse(result(h)['ok']); welcome.assert_not_called()

    @patch('stock_news.brevo.requests.post')
    @patch('stock_news.brevo.update_contact_tickers')
    @patch('stock_news.brevo.get_contact')
    def test_brevo_create_update_and_suppression(self, lookup, update, post):
        post.return_value.ok = True
        lookup.return_value = None
        self.assertFalse(subscribe_verified(IDENTITY['email'], ['AAPL'], 'key', 7))
        self.assertEqual(post.call_args.kwargs['json']['listIds'], [7])
        lookup.return_value = CONTACT
        self.assertTrue(subscribe_verified(IDENTITY['email'], ['AAPL'], 'key', 7))
        update.assert_called_once()
        lookup.return_value = {**CONTACT, 'emailBlacklisted': True}
        with self.assertRaises(BrevoError): subscribe_verified(IDENTITY['email'], ['AAPL'], 'key', 7)
        self.assertEqual(update.call_count, 1)


@patch.dict(os.environ, ENV)
class DigestSessionTests(unittest.TestCase):
    @patch('stock_news.auth.get_contact', return_value=CONTACT)
    @patch('api.digest.build_web_digest', return_value='<html>digest</html>')
    def test_digest_uses_full_current_watchlist(self, render, lookup):
        h = handler('/digest', signed_in=True); handle_get(h)
        self.assertEqual(render.call_args.args[1], ['US:AAPL', 'IN:TCS'])
        self.assertIsNone(render.call_args.kwargs['progressive_token'])
        self.assertTrue(render.call_args.kwargs['progressive'])

    @patch('stock_news.auth.get_contact', return_value=None)
    def test_digest_redirects_new_user_to_popup(self, lookup):
        h = handler('/digest', signed_in=True); handle_get(h)
        h.send_header.assert_any_call('Location', '/#subscribe')
        h = handler('/digest'); handle_get(h)
        h.send_header.assert_any_call('Location', '/?signin=1')

    @patch('stock_news.auth.get_contact', return_value=CONTACT)
    @patch('api.digest.collect_digest_data', return_value=([{'ticker': 'IN:TCS'}], None))
    @patch('api.digest.build_web_section', return_value='section')
    def test_progressive_data_and_authorization(self, render, collect, lookup):
        h = handler('/api/digest-data?t=&ticker=IN:TCS', signed_in=True); handle_data_get(h)
        self.assertTrue(result(h)['ok'])
        h = handler('/api/digest-data?t=&ticker=US:MSFT', signed_in=True); handle_data_get(h)
        self.assertFalse(result(h)['ok']); self.assertEqual(collect.call_count, 1)

    @patch('stock_news.auth.get_contact', return_value=CONTACT)
    def test_subscription_prefill_and_ai_csrf(self, lookup):
        h = handler('/api/subscription', signed_in=True); handle_subscription_get(h)
        self.assertEqual(result(h)['email'], IDENTITY['email'])
        self.assertEqual(result(h)['tickers'], ['US:AAPL', 'IN:TCS'])
        h = handler('/api/digest-ai', signed_in=True); h.headers['X-CSRF-Token'] = 'bad'
        handle_ai_post(h); self.assertFalse(result(h)['ok'])

    @patch('stock_news.auth.get_contact', return_value=CONTACT)
    @patch('api.digest.generate_ai_summary', return_value=None)
    @patch('api.digest.generate_financial_health_summaries', return_value={})
    def test_ai_only_uses_saved_tickers(self, health, summary, lookup):
        h = handler('/api/digest-ai', {'sections': [{'ticker': 'IN:TCS'}, {'ticker': 'US:MSFT'}]}, signed_in=True)
        handle_ai_post(h)
        self.assertTrue(result(h)['ok'])
        self.assertEqual(summary.call_args.args[0], [{'ticker': 'IN:TCS'}])


if __name__ == '__main__': unittest.main()
