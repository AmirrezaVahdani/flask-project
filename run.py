from app import create_app, socketio
from app.extensions import db
from app.models import Locker, User

app = create_app()


with app.app_context():
    db.create_all()

    locker_count = app.config.get("LOCKER_COUNT", 4)
    existing_lockers = Locker.query.count()
    if existing_lockers < locker_count:
        for i in range(existing_lockers + 1, locker_count + 1):
            # Check if locker already exists to avoid duplicate key errors
            if not Locker.query.filter_by(locker_number=i).first():
                db.session.add(Locker(locker_number=i, status="available"))
        db.session.commit()
        created = locker_count - existing_lockers
        if created > 0:
            print(
                f"--> {created} locker(s) created, total {locker_count} lockers."
            )

    if User.query.filter_by(role="admin").count() == 0:
        admin_user = User(
            full_name="System Admin",
            national_id="0000000000",
            phone_number="09123456789",
            role="admin",
        )
        admin_user.set_password("admin123")
        db.session.add(admin_user)
        db.session.commit()
        print(
            "--> Default admin user created (National ID: 0000000000, Pass: admin123)."
        )


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True,
    )
