from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from organisations.models import Coupon, Organisation, OrganisationMember

User = get_user_model()


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class CouponRedemptionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="owner@test.com",
            email="owner@test.com",
            password="TestPass1!",
            name="Owner",
        )
        self.org = Organisation.objects.create(
            name="Coupon Org", slug="coupon-org", owner=self.owner, plan="free"
        )
        OrganisationMember.objects.create(
            organisation=self.org, user=self.owner, role="owner"
        )
        self.owner.current_organisation = self.org
        self.owner.save()

        self.coupon, _ = Coupon.objects.get_or_create(
            code="DEMO-PRO",
            defaults={
                "plan": "pro",
                "active": True,
                "max_uses": 10,
                "used_count": 0,
            },
        )
        Coupon.objects.filter(pk=self.coupon.pk).update(used_count=0, active=True)
        self.coupon.refresh_from_db()

        login = self.client.post(
            "/api/login/",
            {"email": "owner@test.com", "password": "TestPass1!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_redeem_coupon_upgrades_plan(self):
        res = self.client.post(
            "/api/organisations/redeem-coupon/",
            {"code": "demo-pro"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["plan"], "pro")

        self.org.refresh_from_db()
        self.assertEqual(self.org.plan, "pro")

        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)

    def test_redeem_invalid_coupon(self):
        res = self.client.post(
            "/api/organisations/redeem-coupon/",
            {"code": "NOT-REAL"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_settings_returns_plan_and_usage(self):
        res = self.client.get("/api/organisations/settings/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["plan"], "free")
        self.assertIn("usage", res.data)
        self.assertTrue(res.data["can_redeem_coupons"])
