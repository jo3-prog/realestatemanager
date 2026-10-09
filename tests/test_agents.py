from django.core import mail
from rest_framework.test import APITestCase

from agents.models import AgentProfile

from .helpers import (PASSWORD, client_for, make_admin, make_agent, make_category,
                      make_user, property_payload)

AGENT_REG = {"username": "sam", "email": "sam@example.com", "password": PASSWORD, "password2": PASSWORD,
             "company_name": "Sam Homes", "license_number": "L-99", "bio": "hi"}


class AgentApprovalTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_agent_registers_as_pending(self):
        r = self.client.post("/api/agents/register/", AGENT_REG, format="json")
        self.assertEqual(r.status_code, 201)
        profile = AgentProfile.objects.get(user__email="sam@example.com")
        self.assertEqual(profile.status, "pending")
        self.assertEqual(profile.user.role, "agent")
        self.assertFalse(profile.is_verified)

    def test_pending_agent_cannot_create_listing(self):
        agent = make_agent("p@example.com", approved=False)
        cat = make_category()
        r = client_for(agent).post("/api/properties/", property_payload(cat.id), format="json")
        self.assertEqual(r.status_code, 403)

    def test_admin_lists_and_approves_and_agent_can_then_list(self):
        self.client.post("/api/agents/register/", AGENT_REG, format="json")
        admin = client_for(self.admin)
        pending = admin.get("/api/admin/agents/pending/")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.data["count"], 1)
        pid = pending.data["results"][0]["id"]

        mail.outbox.clear()
        r = admin.patch(f"/api/admin/agents/{pid}/approve/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "approved")
        self.assertTrue(r.data["is_verified"])
        self.assertEqual(len(mail.outbox), 1)               # approval email

        agent = AgentProfile.objects.get(pk=pid).user
        cat = make_category()
        r = client_for(agent).post("/api/properties/", property_payload(cat.id), format="json")
        self.assertEqual(r.status_code, 201)

    def test_admin_rejects_with_reason(self):
        agent = make_agent("p@example.com", approved=False)
        pid = agent.agent_profile.id
        r = client_for(self.admin).patch(f"/api/admin/agents/{pid}/reject/", {"reason": "Bad license"}, format="json")
        self.assertEqual(r.data["status"], "rejected")
        self.assertEqual(r.data["rejection_reason"], "Bad license")

    def test_only_admin_can_approve_or_view_pending(self):
        agent = make_agent("p@example.com", approved=False)
        pid = agent.agent_profile.id
        for user in (None, make_user("u@example.com"), agent):
            c = client_for(user)
            self.assertIn(c.patch(f"/api/admin/agents/{pid}/approve/").status_code, (401, 403))
            self.assertIn(c.get("/api/admin/agents/pending/").status_code, (401, 403))

    def test_public_agent_list_shows_only_approved_and_agent_me(self):
        good = make_agent("good@example.com")
        make_agent("bad@example.com", approved=False)
        r = self.client.get("/api/agents/")
        self.assertEqual(r.data["count"], 1)
        r = client_for(good).patch("/api/agents/me/", {"bio": "Updated"}, format="json")
        self.assertEqual(r.data["bio"], "Updated")
        self.assertEqual(client_for(make_user("u@example.com")).get("/api/agents/me/").status_code, 403)

    def test_admin_can_manage_users(self):
        u = make_user("u@example.com")
        c = client_for(self.admin)
        self.assertEqual(c.get("/api/admin/users/").status_code, 200)
        r = c.patch(f"/api/admin/users/{u.id}/", {"is_active": False}, format="json")
        self.assertFalse(r.data["is_active"])
        self.assertEqual(client_for(u).get("/api/admin/users/").status_code, 403)
