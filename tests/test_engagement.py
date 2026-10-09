from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from inspections.models import InspectionBooking
from notifications.models import Notification

from .helpers import client_for, make_admin, make_agent, make_property, make_user


class FavoriteTests(APITestCase):
    def test_save_list_remove(self):
        prop = make_property(make_agent())
        user = make_user("u@example.com")
        c = client_for(user)
        r = c.post("/api/favorites/", {"property": prop.id}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(c.post("/api/favorites/", {"property": prop.id}, format="json").status_code, 400)  # duplicate
        self.assertEqual(c.get("/api/favorites/").data["count"], 1)
        # someone else can't see or delete it
        other = client_for(make_user("o@example.com"))
        self.assertEqual(other.get("/api/favorites/").data["count"], 0)
        self.assertEqual(other.delete(f"/api/favorites/{r.data['id']}/").status_code, 404)
        self.assertEqual(c.delete(f"/api/favorites/{r.data['id']}/").status_code, 204)
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)


class InquiryTests(APITestCase):
    def setUp(self):
        self.agent = make_agent()
        self.prop = make_property(self.agent)
        self.body = {"property": self.prop.id, "name": "Visitor", "email": "v@example.com",
                     "phone_number": "0801", "message": "Is it available?"}

    def test_visitor_can_send_and_agent_is_notified(self):
        r = self.client.post("/api/inquiries/", self.body, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Notification.objects.filter(user=self.agent, notification_type="inquiry").count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_agent_sees_only_own_inquiries_and_can_respond(self):
        self.client.post("/api/inquiries/", self.body, format="json")
        inq_id = self.agent.listings.first().inquiries.first().id
        other_agent = client_for(make_agent("x@example.com"))
        self.assertEqual(other_agent.get("/api/inquiries/").data["count"], 0)
        self.assertEqual(other_agent.get(f"/api/inquiries/{inq_id}/").status_code, 404)
        mine = client_for(self.agent)
        self.assertEqual(mine.get("/api/inquiries/").data["count"], 1)
        mail.outbox.clear()
        r = mine.patch(f"/api/inquiries/{inq_id}/respond/", {"response": "Yes it is"}, format="json")
        self.assertEqual(r.data["status"], "responded")
        self.assertEqual(mail.outbox[0].to, ["v@example.com"])

    def test_logged_in_user_tracks_own_inquiries_and_cannot_respond(self):
        user = make_user("v@example.com")
        c = client_for(user)
        r = c.post("/api/inquiries/", self.body, format="json")
        self.assertEqual(c.get("/api/inquiries/").data["count"], 1)
        self.assertEqual(c.patch(f"/api/inquiries/{r.data['id']}/respond/", {"response": "x"}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/inquiries/").status_code, 401)
        self.assertEqual(client_for(make_admin()).get("/api/inquiries/").data["count"], 1)

    def test_cannot_inquire_about_unpublished(self):
        draft = make_property(self.agent, publication_status="draft")
        r = self.client.post("/api/inquiries/", {**self.body, "property": draft.id}, format="json")
        self.assertEqual(r.status_code, 400)


class InspectionTests(APITestCase):
    def setUp(self):
        self.agent = make_agent()
        self.prop = make_property(self.agent)
        self.user = make_user("u@example.com")
        self.when = (timezone.now() + timedelta(days=2)).isoformat()

    def book(self):
        return client_for(self.user).post(
            "/api/inspections/", {"property": self.prop.id, "scheduled_at": self.when}, format="json")

    def test_book_approve_complete(self):
        r = self.book()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["status"], "pending")
        bid = r.data["id"]
        agent = client_for(self.agent)
        self.assertEqual(agent.get("/api/inspections/").data["count"], 1)
        r = agent.patch(f"/api/inspections/{bid}/status/", {"status": "approved"}, format="json")
        self.assertEqual(r.data["status"], "approved")
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type="inspection").exists())

    def test_past_date_rejected_and_login_required(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        r = client_for(self.user).post("/api/inspections/", {"property": self.prop.id, "scheduled_at": past}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.post("/api/inspections/", {}, format="json").status_code, 401)

    def test_status_permissions(self):
        bid = self.book().data["id"]
        user = client_for(self.user)
        self.assertEqual(user.patch(f"/api/inspections/{bid}/status/", {"status": "approved"}, format="json").status_code, 400)  # can't self-approve
        self.assertEqual(user.patch(f"/api/inspections/{bid}/status/", {"status": "cancelled"}, format="json").data["status"], "cancelled")
        stranger = client_for(make_user("s@example.com"))
        self.assertEqual(stranger.patch(f"/api/inspections/{bid}/status/", {"status": "cancelled"}, format="json").status_code, 404)

    def test_reminder_command(self):
        InspectionBooking.objects.create(property=self.prop, user=self.user, status="approved",
                                         scheduled_at=timezone.now() + timedelta(hours=5))
        call_command("send_inspection_reminders")
        self.assertTrue(InspectionBooking.objects.first().reminder_sent)
        self.assertEqual(Notification.objects.filter(title="Inspection reminder").count(), 2)


class ReviewTests(APITestCase):
    def test_review_agent_and_property_average(self):
        agent = make_agent()
        prop = make_property(agent)
        u1, u2 = make_user("a@example.com"), make_user("b@example.com")
        self.assertEqual(self.client.post("/api/reviews/", {"agent": agent.agent_profile.id, "rating": 5}, format="json").status_code, 401)
        for u, rating in ((u1, 5), (u2, 3)):
            r = client_for(u).post("/api/reviews/", {"agent": agent.agent_profile.id, "rating": rating, "comment": "ok"}, format="json")
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.get(f"/api/agents/{agent.agent_profile.id}/").data["average_rating"], 4.0)
        # duplicates / bad ratings / both targets / self-review
        c = client_for(u1)
        self.assertEqual(c.post("/api/reviews/", {"agent": agent.agent_profile.id, "rating": 1}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/reviews/", {"property": prop.id, "rating": 6}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/reviews/", {"property": prop.id, "agent": agent.agent_profile.id, "rating": 4}, format="json").status_code, 400)
        self.assertEqual(client_for(agent).post("/api/reviews/", {"agent": agent.agent_profile.id, "rating": 5}, format="json").status_code, 400)
        r = c.post("/api/reviews/", {"property": prop.id, "rating": 4}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get(f"/api/reviews/?property={prop.id}").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/properties/{prop.id}/").data["average_rating"], 4.0)


class NotificationAndAnalyticsTests(APITestCase):
    def test_notifications_are_private_and_markable(self):
        u, o = make_user("u@example.com"), make_user("o@example.com")
        n = Notification.objects.create(user=u, title="Hi", message="m")
        self.assertEqual(client_for(o).get("/api/notifications/").data["count"], 0)
        c = client_for(u)
        self.assertEqual(c.get("/api/notifications/").data["count"], 1)
        self.assertTrue(c.patch(f"/api/notifications/{n.id}/read/").data["is_read"])
        self.assertEqual(client_for(o).patch(f"/api/notifications/{n.id}/read/").status_code, 404)

    def test_agent_and_admin_analytics(self):
        agent = make_agent()
        prop = make_property(agent)
        for _ in range(4):
            self.client.get(f"/api/properties/{prop.id}/")
        self.client.post("/api/inquiries/", {"property": prop.id, "name": "n", "email": "e@e.com", "message": "m"}, format="json")
        r = client_for(agent).get("/api/analytics/agent/")
        self.assertEqual(r.data["total_listings"], 1)
        self.assertEqual(r.data["total_views"], 4)
        self.assertEqual(r.data["total_inquiries"], 1)
        self.assertEqual(r.data["conversion_rate_percent"], 25.0)
        self.assertEqual(client_for(make_user("u@example.com")).get("/api/analytics/agent/").status_code, 403)
        admin = client_for(make_admin())
        r = admin.get("/api/analytics/admin/")
        self.assertEqual(r.data["total_agents"], 1)
        self.assertEqual(r.data["most_viewed_properties"][0]["id"], prop.id)
        self.assertEqual(client_for(agent).get("/api/analytics/admin/").status_code, 403)
