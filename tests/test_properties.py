import shutil
import tempfile

from django.test import override_settings
from rest_framework.test import APITestCase

from properties.models import Category, Property

from .helpers import (client_for, make_admin, make_agent, make_category, make_property,
                      make_user, png_file, property_payload)

TMP_MEDIA = tempfile.mkdtemp()


class CategoryTests(APITestCase):
    def test_slug_generation_and_permissions(self):
        admin = client_for(make_admin())
        r = admin.post("/api/categories/", {"name": "Office Space"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["slug"], "office-space")
        cid = r.data["id"]
        self.assertEqual(self.client.get("/api/categories/").status_code, 200)     # public read
        self.assertEqual(client_for(make_agent()).post("/api/categories/", {"name": "X"}, format="json").status_code, 403)
        self.assertEqual(admin.put(f"/api/categories/{cid}/", {"name": "Offices"}, format="json").status_code, 200)
        self.assertEqual(admin.delete(f"/api/categories/{cid}/").status_code, 204)

    def test_duplicate_names_rejected(self):
        make_category("Land")
        r = client_for(make_admin()).post("/api/categories/", {"name": "Land"}, format="json")
        self.assertEqual(r.status_code, 400)


class PropertyCrudTests(APITestCase):
    def setUp(self):
        self.agent = make_agent("a1@example.com")
        self.other = make_agent("a2@example.com")
        self.cat = make_category("Duplex")
        self.c = client_for(self.agent)

    def test_create_read_update_delete(self):
        r = self.c.post("/api/properties/", property_payload(self.cat.id), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        pid = r.data["id"]
        self.assertEqual(r.data["created_by"], self.agent.id)
        self.assertFalse(r.data["featured"])
        self.assertEqual(self.client.get(f"/api/properties/{pid}/").status_code, 200)   # public
        r = self.c.put(f"/api/properties/{pid}/", property_payload(self.cat.id, title="New title"), format="json")
        self.assertEqual(r.data["title"], "New title")
        r = self.c.patch(f"/api/properties/{pid}/", {"status": "sold"}, format="json")
        self.assertEqual(r.data["status"], "sold")
        self.assertEqual(self.c.delete(f"/api/properties/{pid}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/properties/{pid}/").status_code, 404)

    def test_validation_rules(self):
        for bad in ({"price": "-5"}, {"bedrooms": -1}, {"bathrooms": -2},
                    {"amenities": "pool"}, {"latitude": 95, "longitude": 3}, {"publication_status": "suspended"}):
            r = self.c.post("/api/properties/", property_payload(self.cat.id, **bad), format="json")
            self.assertEqual(r.status_code, 400, bad)

    def test_visitor_and_normal_user_cannot_create(self):
        self.assertEqual(self.client.post("/api/properties/", property_payload(self.cat.id), format="json").status_code, 401)
        u = client_for(make_user("u@example.com"))
        self.assertEqual(u.post("/api/properties/", property_payload(self.cat.id), format="json").status_code, 403)

    def test_agent_cannot_edit_or_delete_someone_elses_listing(self):
        prop = make_property(self.agent, self.cat)
        other = client_for(self.other)
        self.assertEqual(other.patch(f"/api/properties/{prop.id}/", {"title": "hack"}, format="json").status_code, 403)
        self.assertEqual(other.delete(f"/api/properties/{prop.id}/").status_code, 403)
        admin = client_for(make_admin())
        self.assertEqual(admin.patch(f"/api/properties/{prop.id}/", {"title": "ok"}, format="json").status_code, 200)

    def test_agent_cannot_set_featured_or_views(self):
        r = self.c.post("/api/properties/", property_payload(self.cat.id, featured=True, views_count=999), format="json")
        self.assertFalse(r.data["featured"])
        self.assertEqual(r.data["views_count"], 0)

    def test_drafts_hidden_from_public_but_visible_to_owner(self):
        draft = make_property(self.agent, self.cat, publication_status="draft")
        self.assertEqual(self.client.get(f"/api/properties/{draft.id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/properties/").data["count"], 0)
        self.assertEqual(self.c.get(f"/api/properties/{draft.id}/").status_code, 200)
        self.assertEqual(self.c.get("/api/properties/mine/").data["count"], 1)
        self.assertEqual(client_for(self.other).get(f"/api/properties/{draft.id}/").status_code, 404)

    def test_view_counter(self):
        prop = make_property(self.agent, self.cat)
        self.client.get(f"/api/properties/{prop.id}/")
        self.client.get(f"/api/properties/{prop.id}/")
        self.c.get(f"/api/properties/{prop.id}/")           # owner views don't count
        prop.refresh_from_db()
        self.assertEqual(prop.views_count, 2)

    def test_admin_suspend_feature_and_public_featured_list(self):
        prop = make_property(self.agent, self.cat)
        admin = client_for(make_admin())
        self.assertEqual(self.c.patch(f"/api/properties/{prop.id}/feature/").status_code, 403)
        self.assertTrue(admin.patch(f"/api/properties/{prop.id}/feature/").data["featured"])
        self.assertEqual(self.client.get("/api/properties/featured/").data["count"], 1)
        admin.patch(f"/api/properties/{prop.id}/suspend/")
        self.assertEqual(self.client.get(f"/api/properties/{prop.id}/").status_code, 404)
        admin.patch(f"/api/properties/{prop.id}/reinstate/")
        self.assertEqual(self.client.get(f"/api/properties/{prop.id}/").status_code, 200)

    def test_compare(self):
        a, b = make_property(self.agent), make_property(self.agent)
        r = self.client.get(f"/api/properties/compare/?ids={a.id},{b.id}")
        self.assertEqual(len(r.data), 2)
        self.assertEqual(self.client.get(f"/api/properties/compare/?ids={a.id}").status_code, 400)

    @override_settings(MEDIA_ROOT=TMP_MEDIA)
    def test_multiple_image_upload_and_delete(self):
        prop = make_property(self.agent, self.cat)
        r = self.c.post(f"/api/properties/{prop.id}/images/",
                        {"images": [png_file("a.png"), png_file("b.png")]}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(r.data), 2)
        self.assertTrue(r.data[0]["is_primary"])
        self.assertEqual(len(self.client.get(f"/api/properties/{prop.id}/").data["images"]), 2)
        img_id = r.data[1]["id"]
        self.assertEqual(self.c.delete(f"/api/properties/{prop.id}/images/{img_id}/").status_code, 204)
        # another agent cannot upload to it
        r = client_for(self.other).post(f"/api/properties/{prop.id}/images/", {"images": [png_file()]}, format="multipart")
        self.assertEqual(r.status_code, 403)

    @override_settings(MEDIA_ROOT=TMP_MEDIA)
    def test_invalid_image_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        prop = make_property(self.agent, self.cat)
        fake = SimpleUploadedFile("evil.png", b"not an image", content_type="image/png")
        r = self.c.post(f"/api/properties/{prop.id}/images/", {"images": [fake]}, format="multipart")
        self.assertEqual(r.status_code, 400)
        txt = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
        self.assertEqual(self.c.post(f"/api/properties/{prop.id}/images/", {"images": [txt]}, format="multipart").status_code, 400)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)


class SearchFilterTests(APITestCase):
    def setUp(self):
        agent = make_agent()
        duplex, land = make_category("Duplex"), make_category("Land")
        make_property(agent, duplex, title="Big Duplex", price=3000000, bedrooms=4, bathrooms=3, city="Lagos", status="for_sale")
        make_property(agent, land, title="Plot of land", price=500000, bedrooms=0, bathrooms=0, city="Abuja", status="for_rent")
        make_property(agent, duplex, title="Small flat", price=1500000, bedrooms=3, bathrooms=2, city="Lagos", status="for_rent")

    def titles(self, query):
        r = self.client.get(f"/api/properties/{query}")
        self.assertEqual(r.status_code, 200)
        return sorted(p["title"] for p in r.data["results"])

    def test_filters(self):
        self.assertEqual(self.titles("?search=duplex"), ["Big Duplex", "Small flat"])   # matches category name too
        self.assertEqual(self.titles("?city=lagos"), ["Big Duplex", "Small flat"])
        self.assertEqual(self.titles("?min_price=1000000&max_price=2000000"), ["Small flat"])
        self.assertEqual(self.titles("?bedrooms=3"), ["Small flat"])
        self.assertEqual(self.titles("?bathrooms=3"), ["Big Duplex"])
        self.assertEqual(self.titles("?status=rent"), ["Plot of land", "Small flat"])
        self.assertEqual(self.titles("?status=for_sale"), ["Big Duplex"])
        self.assertEqual(self.titles("?category=land"), ["Plot of land"])
        self.assertEqual(self.titles("?location=abuja"), ["Plot of land"])
        self.assertEqual(self.titles("?city=Lagos&status=rent&max_price=2000000"), ["Small flat"])

    def test_sorting_and_pagination(self):
        r = self.client.get("/api/properties/?ordering=price")
        prices = [float(p["price"]) for p in r.data["results"]]
        self.assertEqual(prices, sorted(prices))
        r = self.client.get("/api/properties/?ordering=-price")
        self.assertEqual(r.data["results"][0]["title"], "Big Duplex")
        self.assertIn("count", r.data)
