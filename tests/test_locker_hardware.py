import unittest
from datetime import datetime
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import AttendanceLog, Locker, Subscription, User


class LockerHardwareTest(unittest.TestCase):
    def test_check_in_returns_locker_open_signal(self):
        app = create_app()
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, LOCKER_HARDWARE_MODE="mock")

        with app.app_context():
            db.drop_all()
            db.create_all()

            user = User(
                full_name="آرمان رضایی",
                national_id="3333333333",
                phone_number="09333333333",
                role="member",
            )
            db.session.add(user)
            db.session.commit()

            locker = Locker(locker_number=7, status="available", current_user_id=None)
            db.session.add(locker)
            db.session.commit()

            subscription = Subscription(
                user_id=user.id,
                plan_id=None,
                package_name="پکیج تست",
                remaining_sessions=5,
                is_active=True,
            )
            db.session.add(subscription)
            db.session.commit()

        with app.test_client() as client:
            response = client.post(
                "/api/gate/check-in",
                json={"national_id": "3333333333"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["locker_opened"])
        self.assertEqual(payload["locker_open_duration"], 30)

    def test_check_out_closes_assigned_locker_hardware(self):
        app = create_app()
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, LOCKER_HARDWARE_MODE="mock")

        with app.app_context():
            db.drop_all()
            db.create_all()

            user = User(
                full_name="سعید قاسمی",
                national_id="4444444444",
                phone_number="09444444444",
                role="member",
            )
            db.session.add(user)
            db.session.commit()

            locker = Locker(locker_number=2, status="occupied", current_user_id=user.id)
            db.session.add(locker)
            db.session.commit()

            attendance_log = AttendanceLog(
                user_id=user.id,
                locker_id=locker.id,
                check_in=datetime.utcnow(),
                check_out=None,
            )
            db.session.add(attendance_log)
            db.session.commit()

        fake_service = unittest.mock.Mock()
        fake_service.close_locker.return_value = {"closed": True}

        with patch("app.blueprints.api.routes.get_locker_hardware_service", return_value=fake_service):
            with app.test_client() as client:
                response = client.post(
                    "/api/gate/check-out",
                    json={"national_id": "4444444444"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        fake_service.close_locker.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
