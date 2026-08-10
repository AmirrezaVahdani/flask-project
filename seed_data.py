import argparse
import random
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import FinancialTransaction, GymPlan, Locker, Subscription, Trainer, User

app = create_app()


def seed_demo_data():
    print("--- در حال آماده‌سازی داده‌های نمونه ... ---")

    locker_count = app.config.get("LOCKER_COUNT", 4)
    if Locker.query.count() == 0:
        print(f"--- در حال ساخت {locker_count} کمد رختکن ... ---")
        for locker_number in range(1, locker_count + 1):
            db.session.add(Locker(locker_number=locker_number, status='available'))

    if GymPlan.query.count() == 0:
        print("--- در حال تعریف پلن‌های نمونه ... ---")
        plans_data = [
            {"name": "تک جلسه تفریحی", "duration": 1, "sessions": 1, "price": 50000},
            {"name": "۱ ماهه عمومی (۱۲ جلسه)", "duration": 30, "sessions": 12, "price": 450000},
            {"name": "۱ ماهه آزاد (بدون محدودیت)", "duration": 30, "sessions": 30, "price": 600000},
            {"name": "۳ ماهه نقره‌ای (۳۶ جلسه)", "duration": 90, "sessions": 36, "price": 1200000},
            {"name": "۳ ماهه VIP با مربی (VIP)", "duration": 90, "sessions": 24, "price": 2500000},
        ]
        plans_objects = []
        for plan_data in plans_data:
            plan = GymPlan(
                name=plan_data["name"],
                duration_days=plan_data["duration"],
                total_sessions=plan_data["sessions"],
                price=plan_data["price"],
            )
            db.session.add(plan)
            plans_objects.append(plan)
        db.session.flush()
    else:
        plans_objects = GymPlan.query.all()

    if Trainer.query.count() == 0:
        print("--- در حال ساخت مربیان نمونه ... ---")
        default_trainers = [
            ("استاد علی حسینی", "بدنسازی"),
            ("مهندس رضا علوی", "فیتنس"),
            ("کاپیتان سهراب زاهدی", "کاردیو"),
            ("خانم دکتر مریم راد", "یوگا"),
            ("استاد حسن مرادی", "پاورلیفینگ"),
        ]
        for name, specialty in default_trainers:
            db.session.add(Trainer(name=name, specialty=specialty))

    if User.query.filter_by(role='member').count() == 0:
        print("--- در حال ساخت ورزشکاران نمونه ... ---")
        trainers = [trainer.name for trainer in Trainer.query.all()]
        members_data = [
            {"name": "امیرحسین محمدی", "nid": "1111111111", "phone": "09121111111"},
            {"name": "علیرضا کریمی", "nid": "2222222222", "phone": "09122222222"},
            {"name": "محمد جواد اکبری", "nid": "3333333333", "phone": "09123333333"},
            {"name": "سینا رضایی", "nid": "4444444444", "phone": "09124444444"},
            {"name": "مهدی احمدی", "nid": "5555555555", "phone": "09125555555"},
            {"name": "حسین موسوی", "nid": "6666666666", "phone": "09126666666"},
            {"name": "پوریا غفاری", "nid": "7777777777", "phone": "09127777777"},
            {"name": "نیما سلطانی", "nid": "8888888888", "phone": "09128888888"},
            {"name": "شایان قاسمی", "nid": "9999999999", "phone": "09129999999"},
            {"name": "امیرعلی طاهری", "nid": "1010101010", "phone": "09121010101"},
            {"name": "عرفان ابراهیمی", "nid": "2020202020", "phone": "09122020202"},
            {"name": "میلاد حیدری", "nid": "3030303030", "phone": "09123030303"},
            {"name": "سهراب تقوی", "nid": "4040404040", "phone": "09124040404"},
            {"name": "آرمین صادقی", "nid": "5050505050", "phone": "09125050505"},
            {"name": "امید رحیمی", "nid": "6060606060", "phone": "09126060606"},
        ]

        for member_data in members_data:
            user = User(
                full_name=member_data["name"],
                national_id=member_data["nid"],
                phone_number=member_data["phone"],
                role='member',
                wallet_balance=20000,
            )
            db.session.add(user)
            db.session.flush()

            chosen_plan = random.choice(plans_objects)
            chosen_trainer = random.choice(trainers)

            if member_data["nid"] in ["1111111111", "3333333333"]:
                end_date = date.today() + timedelta(days=2)
            else:
                end_date = date.today() + timedelta(days=chosen_plan.duration_days)

            db.session.add(
                Subscription(
                    user_id=user.id,
                    plan_id=chosen_plan.id,
                    package_name=chosen_plan.name,
                    start_date=date.today() - timedelta(days=5),
                    end_date=end_date,
                    remaining_sessions=chosen_plan.total_sessions - random.randint(0, 3),
                    is_active=True,
                    trainer_name=chosen_trainer,
                )
            )
            db.session.add(
                FinancialTransaction(
                    user_id=user.id,
                    amount=-chosen_plan.price,
                    description=(
                        f"ثبت نام اولیه در پلن {chosen_plan.name} با مربیگری "
                        f"{chosen_trainer}"
                    ),
                )
            )

    if User.query.filter_by(role='admin').count() == 0:
        print("--- در حال ساخت حساب مدیر نمونه ... ---")
        admin = User(
            full_name="مدیریت مجموعه",
            national_id="0000000000",
            phone_number="09120000000",
            role='admin',
        )
        admin.set_password("admin123")
        db.session.add(admin)

    db.session.commit()
    print("\n========================================================")
    print("داده‌های نمونه با موفقیت آماده شدند.")
    print("Admin -> National ID: 0000000000 | Password: admin123")
    print("Kiosk Test National IDs: 1111111111 , 2222222222")
    print("========================================================")


def main():
    parser = argparse.ArgumentParser(description="Seed demo data for the gym app")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing data before seeding demo data",
    )
    args = parser.parse_args()

    with app.app_context():
        if args.reset:
            print("--- در حال پاک‌سازی پایگاه داده ... ---")
            db.drop_all()

        db.create_all()

        if args.reset or (User.query.count() == 0 and GymPlan.query.count() == 0):
            seed_demo_data()
        else:
            print("داده‌های فعلی حفظ شدند. برای بازسازی از --reset استفاده کنید.")


if __name__ == "__main__":
    main()