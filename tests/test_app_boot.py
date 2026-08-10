import unittest

from app import create_app
from app.extensions import db
from app.models import AttendanceLog, Locker, User


class AppBootstrapTest(unittest.TestCase):
    def test_app_creates_and_registers_expected_routes(self):
        app = create_app()
        self.assertIsNotNone(app)
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        self.assertIn("/admin/login", rules)
        self.assertIn("/public/home", rules)

    def test_admin_dashboard_shows_current_locker_owner_and_presence(self):
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        with app.app_context():
            db.drop_all()
            db.create_all()

            admin_user = User(
                full_name='مدیر تست',
                national_id='1111111111',
                phone_number='09111111111',
                role='admin',
            )
            admin_user.set_password('secret123')
            member_user = User(
                full_name='رضا احمدی',
                national_id='2222222222',
                phone_number='09222222222',
                role='member',
            )
            db.session.add_all([admin_user, member_user])
            db.session.commit()

            locker = Locker(locker_number=1, status='occupied', current_user_id=member_user.id)
            db.session.add(locker)
            db.session.commit()

            AttendanceLog(user_id=member_user.id, locker_id=locker.id, check_out=None)
            db.session.add(AttendanceLog(user_id=member_user.id, locker_id=locker.id, check_out=None))
            db.session.commit()

            client = app.test_client()
            response = client.post('/admin/login', data={
                'national_id': admin_user.national_id,
                'password': 'secret123',
            }, follow_redirects=True)
            dashboard_response = client.get('/admin/dashboard')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dashboard_response.status_code, 200)
        html = dashboard_response.get_data(as_text=True)
        self.assertIn('رضا احمدی', html)
        self.assertIn('در باشگاه', html)


if __name__ == "__main__":
    unittest.main()
