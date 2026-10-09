import re

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from .helpers import PASSWORD, client_for, make_user

REGISTER = {"username": "joe", "email": "Joe@Example.com", "password": PASSWORD,
            "password2": PASSWORD, "first_name": "Joe", "last_name": "D"}


class AuthTests(APITestCase):
    def test_register_success_lowercases_email_and_hashes_password(self):
        r = self.client.post("/api/auth/register/", REGISTER, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("password", r.data)
        from accounts.models import User
        u = User.objects.get(username="joe")
        self.assertEqual(u.email, "joe@example.com")
        self.assertNotEqual(u.password, PASSWORD)          # stored hashed
        self.assertEqual(u.role, "user")                    # can't self-assign admin
        self.assertEqual(len(mail.outbox), 1)               # verification email sent

    def test_register_duplicate_email_and_password_mismatch(self):
        make_user("joe@example.com")
        r = self.client.post("/api/auth/register/", REGISTER, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data)
        bad = {**REGISTER, "email": "new@example.com", "password2": "different"}
        self.assertEqual(self.client.post("/api/auth/register/", bad, format="json").status_code, 400)

    def test_register_cannot_choose_role(self):
        r = self.client.post("/api/auth/register/", {**REGISTER, "role": "admin"}, format="json")
        self.assertEqual(r.status_code, 201)
        from accounts.models import User
        self.assertEqual(User.objects.get(username="joe").role, "user")

    def test_login_refresh_logout(self):
        make_user("a@example.com")
        r = self.client.post("/api/auth/login/", {"email": "A@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertEqual(r.data["user"]["role"], "user")
        refresh = r.data["refresh"]

        r2 = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r2.status_code, 200)
        new_refresh = r2.data["refresh"]                    # rotated

        r3 = self.client.post("/api/auth/logout/", {"refresh": new_refresh}, format="json")
        self.assertEqual(r3.status_code, 200)
        # the blacklisted token can no longer be used
        r4 = self.client.post("/api/auth/refresh/", {"refresh": new_refresh}, format="json")
        self.assertEqual(r4.status_code, 401)

    def test_login_wrong_password(self):
        make_user("a@example.com")
        r = self.client.post("/api/auth/login/", {"email": "a@example.com", "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_protected_endpoint_needs_token(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_me_endpoint_cannot_change_role(self):
        user = make_user("a@example.com")
        c = client_for(user)
        r = c.patch("/api/auth/me/", {"first_name": "Ann", "role": "admin"}, format="json")
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.role), ("Ann", "user"))

    def test_email_verification_flow(self):
        self.client.post("/api/auth/register/", REGISTER, format="json")
        body = mail.outbox[0].body
        uid, token = re.search(r"uid=([^&]+)&token=(\S+)", body).groups()
        r = self.client.get(f"/api/auth/verify-email/?uid={uid}&token={token}")
        self.assertEqual(r.status_code, 200)
        from accounts.models import User
        self.assertTrue(User.objects.get(username="joe").is_email_verified)
        bad = self.client.get(f"/api/auth/verify-email/?uid={uid}&token=wrong")
        self.assertEqual(bad.status_code, 400)

    @override_settings(REQUIRE_EMAIL_VERIFICATION=True)
    def test_login_blocked_until_verified(self):
        make_user("a@example.com")
        r = self.client.post("/api/auth/login/", {"email": "a@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_password_reset_flow(self):
        user = make_user("a@example.com")
        r = self.client.post("/api/auth/reset-password/", {"email": "a@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        body = mail.outbox[0].body
        uid = re.search(r'"uid": "([^"]+)"', body).group(1)
        token = re.search(r'"token": "([^"]+)"', body).group(1)
        r = self.client.post("/api/auth/reset-password/confirm/",
                             {"uid": uid, "token": token, "new_password": "BrandNew#Pass987"}, format="json")
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("BrandNew#Pass987"))

    def test_password_reset_unknown_email_gives_same_answer(self):
        r = self.client.post("/api/auth/reset-password/", {"email": "ghost@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
