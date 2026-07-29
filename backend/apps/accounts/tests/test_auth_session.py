"""Member auth session: login, httpOnly refresh cookie refresh, logout blacklist (P1)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.auth_cookies import MEMBER_REFRESH_COOKIE

User = get_user_model()

LOGIN_URL = "/api/member/auth/login"
REFRESH_URL = "/api/member/auth/refresh"
LOGOUT_URL = "/api/member/auth/logout"


class AuthSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "pass12345"
        self.user = User.objects.create_user(
            email="member_session@test.local",
            password=self.password,
            role="member",
            is_active=True,
        )

    def _login(self):
        res = self.client.post(
            LOGIN_URL, {"email": self.user.email, "password": self.password}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["code"], "OK")
        return res

    def test_login_sets_httponly_refresh_cookie(self):
        res = self._login()
        self.assertIn("access", res.data["data"]["tokens"])
        cookie = res.cookies.get(MEMBER_REFRESH_COOKIE)
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie["httponly"])
        self.assertTrue(cookie.value)

    def test_login_fails_with_wrong_password(self):
        res = self.client.post(
            LOGIN_URL, {"email": self.user.email, "password": "wrong-pass"}, format="json"
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data["code"], "AUTH_CREDENTIALS_INVALID")

    def test_refresh_via_cookie_rotates_token(self):
        login_res = self._login()
        old_refresh = login_res.cookies[MEMBER_REFRESH_COOKIE].value
        self.assertIn(MEMBER_REFRESH_COOKIE, self.client.cookies)

        refresh_res = self.client.post(REFRESH_URL)
        self.assertEqual(refresh_res.status_code, 200, refresh_res.data)
        self.assertEqual(refresh_res.data["code"], "OK")
        self.assertTrue(refresh_res.data["data"].get("access"))
        new_refresh = refresh_res.cookies[MEMBER_REFRESH_COOKIE].value
        self.assertTrue(new_refresh)
        self.assertNotEqual(new_refresh, old_refresh)

        # 轮换后旧 refresh 已被拉黑；用无 Cookie 的新客户端在 body 带回旧值应失败
        # （Cookie 优先于 body，需用独立客户端避免带上已轮换的新 Cookie）
        stale_client = APIClient()
        retry_res = stale_client.post(REFRESH_URL, {"refresh": old_refresh}, format="json")
        self.assertEqual(retry_res.status_code, 401)
        self.assertEqual(retry_res.data["code"], "AUTH_REFRESH_INVALID")

    def test_refresh_without_token_fails(self):
        anon_client = APIClient()
        res = anon_client.post(REFRESH_URL)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data["code"], "AUTH_REFRESH_MISSING")

    def test_logout_blacklists_refresh_and_clears_cookie(self):
        login_res = self._login()
        refresh_token = login_res.cookies[MEMBER_REFRESH_COOKIE].value

        logout_res = self.client.post(LOGOUT_URL)
        self.assertEqual(logout_res.status_code, 200, logout_res.data)
        self.assertEqual(logout_res.data["code"], "OK")
        cleared_cookie = logout_res.cookies.get(MEMBER_REFRESH_COOKIE)
        self.assertIsNotNone(cleared_cookie)
        self.assertEqual(cleared_cookie.value, "")

        # 登出后该 refresh 已拉黑，即便手动带回旧值也应刷新失败
        retry_res = self.client.post(REFRESH_URL, {"refresh": refresh_token}, format="json")
        self.assertEqual(retry_res.status_code, 401)
        self.assertEqual(retry_res.data["code"], "AUTH_REFRESH_INVALID")

    def test_logout_without_token_still_succeeds(self):
        """access 过期但仍需允许登出清 Cookie（未认证也可调用）。"""
        anon_client = APIClient()
        res = anon_client.post(LOGOUT_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["code"], "OK")
