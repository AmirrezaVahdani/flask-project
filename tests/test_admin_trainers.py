import unittest

from app import create_app
from app.extensions import db
from app.models import Trainer, User


class TrainerManagementTest(unittest.TestCase):
    def test_manage_trainers_create_and_delete(self):
        app = create_app()
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

        with app.app_context():
            db.drop_all()
            db.create_all()

            admin = User(
                full_name="Admin Test",
                national_id="1234567890",
                phone_number="09120000000",
                role="admin",
            )
            admin.set_password("secret")
            db.session.add(admin)
            db.session.commit()
            admin_id = admin.id

        with app.test_client() as client:
            login_response = client.post(
                "/admin/login",
                data={"national_id": "1234567890", "password": "secret"},
                follow_redirects=True,
            )
            self.assertEqual(login_response.status_code, 200)

            response = client.get("/admin/trainers")
            self.assertEqual(response.status_code, 200)

            create_response = client.post(
                "/admin/trainers",
                data={"action": "create", "name": "مربی تست", "specialty": "بدنسازی"},
                follow_redirects=True,
            )
            self.assertEqual(create_response.status_code, 200)
            self.assertEqual(Trainer.query.filter_by(name="مربی تست").count(), 1)

            trainer = Trainer.query.filter_by(name="مربی تست").first()
            delete_response = client.post(
                "/admin/trainers",
                data={"action": "delete", "trainer_id": trainer.id},
                follow_redirects=True,
            )
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(Trainer.query.get(trainer.id))


if __name__ == "__main__":
    unittest.main()
