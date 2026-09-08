import unittest
from datetime import date

from app import create_app
from app.extensions import db
from app.models import GymPlan, Trainer, User
from config import Config


class MemberPortalTest(unittest.TestCase):
    def setUp(self):
        test_config = type(
            "MemberTestConfig",
            (Config,),
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            },
        )
        self.app = create_app(test_config)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.member = User(
            full_name="عضو تست",
            national_id="1111111111",
            phone_number="09121111111",
            role="member",
            wallet_balance=500000,
        )
        db.session.add(self.member)
        db.session.add(
            GymPlan(
                name="پلن یک ماهه",
                duration_days=30,
                total_sessions=12,
                price=300000,
            )
        )
        db.session.add(Trainer(name="مربی تست", specialty="فیتنس"))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_member_login_and_dashboard(self):
        response = self.client.get("/member/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/member/login", response.location)

        response = self.client.post(
            "/member/login",
            data={
                "national_id": self.member.national_id,
                "phone_number": self.member.phone_number,
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("عضو تست", response.get_data(as_text=True))
        self.assertIn("500000", response.get_data(as_text=True))

    def test_member_can_buy_plan_with_wallet_and_choose_trainer(self):
        response = self.client.post(
            "/member/login",
            data={
                "national_id": self.member.national_id,
                "phone_number": self.member.phone_number,
            },
        )
        self.assertEqual(response.status_code, 302)

        plan = GymPlan.query.first()
        response = self.client.post(
            "/member/subscribe",
            data={"plan_id": plan.id, "trainer_name": "مربی تست"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        subscription = self.member.subscriptions[0]
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.trainer_name, "مربی تست")
        self.assertEqual(subscription.remaining_sessions, 12)
        self.assertEqual(subscription.end_date, date.today().fromordinal(date.today().toordinal() + 30))
        self.assertEqual(self.member.wallet_balance, 200000)


if __name__ == "__main__":
    unittest.main()
