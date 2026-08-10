from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import User, Locker, AttendanceLog, Subscription
from app.utils import deactivate_expired_subscriptions
from datetime import datetime, date
import random
from app import socketio
from app.locker_hardware import get_locker_hardware_service

api_bp = Blueprint("api", __name__)


@api_bp.route("/gate/check-in", methods=["POST"])
def check_in():
    data = request.get_json() or {}
    national_id = data.get("national_id", "").strip()

    if not national_id:
        return (
            jsonify({"success": False, "error": "لطفاً کد ملی خود را وارد کنید."}),
            400,
        )

    # ۱. پیدا کردن کاربر
    user = User.query.filter_by(national_id=national_id).first()
    if not user:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "ورزشکاری با این کد ملی یافت نشد. لطفاً به پذیرش مراجعه کنید.",
                }
            ),
            404,
        )

    # ۲. غیرفعال‌سازی اشتراک‌های منقضی و بررسی اشتراک فعال
    deactivate_expired_subscriptions(user_id=user.id)
    active_sub = Subscription.query.filter_by(user_id=user.id, is_active=True).first()
    if not active_sub or active_sub.remaining_sessions <= 0:
        trainer_name = active_sub.trainer_name if active_sub else "تعیین نشده"
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"اشتراک شما به پایان رسیده یا جلسات شما صفر است. مربی: {trainer_name}",
                }
            ),
            403,
        )

    if active_sub.end_date and active_sub.end_date < date.today():
        trainer_name = active_sub.trainer_name
        active_sub.is_active = False
        db.session.commit()
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"اشتراک شما منقضی شده است. تاریخ پایان: {active_sub.end_date}. مربی: {trainer_name}",
                }
            ),
            403,
        )

    # ۳. بررسی اینکه کاربر هم‌اکنون داخل باشگاه نباشد (حل مشکل ورود مجدد)
    current_attendance = AttendanceLog.query.filter_by(
        user_id=user.id, check_out=None
    ).first()
    if current_attendance:
        current_locker = Locker.query.get(current_attendance.locker_id)
        locker_num = current_locker.locker_number if current_locker else "بدون کمد"
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"شما قبلاً وارد شده‌اید و کمد شماره {locker_num} در اختیار شماست!",
                }
            ),
            400,
        )

    # 🛑 ۴. تخصیص تصادفی کمد (اصلاح اساسی: مستقل از استاتوس‌های متنی دیتابیس)
    available_lockers = Locker.query.filter(
        (Locker.current_user_id == None) & (Locker.status != "broken")
    ).all()
    if not available_lockers:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "متأسفانه در حال حاضر کمد خالی و سالمی در رختکن موجود نیست.",
                }
            ),
            400,
        )

    chosen_locker = random.choice(available_lockers)
    chosen_locker.status = "occupied"
    chosen_locker.current_user_id = user.id  # قفل کردن کمد به نام کاربر

    # ۵. کسر یک جلسه از اشتراک کاربر
    active_sub.remaining_sessions -= 1
    if active_sub.remaining_sessions <= 0 or (
        active_sub.end_date is not None and active_sub.end_date < date.today()
    ):
        active_sub.is_active = False

    # ۶. ثبت در سوابق تردد باشگاه (هماهنگ با زمان UTC)
    log = AttendanceLog(
        user_id=user.id, locker_id=chosen_locker.id, check_in=datetime.utcnow()
    )
    db.session.add(log)

    # ذخیره نهایی تغییرات در دیتابیس
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "error": "خطا در ثبت اطلاعات دیتابیس ورود."}),
            500,
        )

    # ۷. باز کردن کمد فیزیکی/شبیه‌سازی شده برای ۳۰ ثانیه
    hardware_service = get_locker_hardware_service()
    hardware_result = hardware_service.open_locker(chosen_locker.locker_number)

    # ۸. ارسال سیگنال وب‌سوکت برای مانیتور بزرگ سالن جهت به‌روزرسانی ریل‌تایم
    try:
        total_present = AttendanceLog.query.filter_by(check_out=None).count()
        total_capacity = Locker.query.filter(Locker.status != "broken").count()

        socketio.emit(
            "update_dashboard",
            {
                "total_present": total_present,
                "remaining_capacity": max(0, total_capacity - total_present),
                "last_user": f"{user.full_name or 'ورزشکار'} (ورود)",
                "assigned_locker": chosen_locker.locker_number,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
            namespace="/public",
        )
    except Exception as e:
        print("SocketIO Error In Check-in:", e)

    # ۹. بازگرداندن پاسخ نهایی به کیوسک برای نمایش پاپ‌آپ (هماهنگ با فرانت‌آند)
    return (
        jsonify(
            {
                "success": True,
                "message": f"خوش آمدید! ورود شما با موفقیت ثبت شد. کمد شماره: {chosen_locker.locker_number}",
                "assigned_locker": chosen_locker.locker_number,
                "full_name": user.full_name or "ورزشکار",
                "trainer_name": active_sub.trainer_name,
                "remaining_sessions": active_sub.remaining_sessions,
                "locker_opened": hardware_result.get("opened", True),
                "locker_open_duration": hardware_result.get("duration", 30),
            }
        ),
        200,
    )


@api_bp.route("/gate/check-out", methods=["POST"])
def check_out_user():
    data = request.get_json() or {}
    national_id = data.get("national_id")
    locker_number = data.get("locker_number")

    if not national_id and not locker_number:
        return (
            jsonify(
                {"success": False, "error": "وارد کردن کد ملی یا شماره کمد الزامی است."}
            ),
            400,
        )

    user = None

    # ۱. یافتن دقیق کاربر بر اساس فیلترهای ارسالی
    if national_id:
        user = User.query.filter_by(national_id=national_id).first()

    # اگر با کد ملی پیدا نشد یا ارسال نشده بود، از طریق شماره کمد اقدام می‌کنیم
    if not user and locker_number:
        locker = Locker.query.filter_by(
            locker_number=locker_number, status="occupied"
        ).first()
        if locker:
            user = User.query.get(locker.current_user_id)

    if not user:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "ورزشکار حاضری با این مشخصات در باشگاه یافت نشد.",
                }
            ),
            404,
        )

    # ۲. پیدا کردن لاگ حضور فعال (وارد شده اما خارج نشده)
    active_log = AttendanceLog.query.filter_by(user_id=user.id, check_out=None).first()
    if not active_log:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "هیچ رکورد ورودی فعالی برای این کاربر ثبت نشده است (کاربر خارج از باشگاه است).",
                }
            ),
            400,
        )

    # ۳. آزاد کردن کمد اختصاص یافته
    user_locker = Locker.query.filter_by(current_user_id=user.id).first()
    assigned_locker_num = "-"
    if user_locker:
        assigned_locker_num = user_locker.locker_number
        user_locker.status = "available"
        user_locker.current_user_id = None

    # ۴. ثبت ساعت خروج (UTC)
    now_time = datetime.utcnow()
    active_log.check_out = now_time

    # ۴.۱. بستن کمد فیزیکی/شبیه‌سازی‌شده پس از خروج
    if user_locker:
        hardware_service = get_locker_hardware_service()
        hardware_result = hardware_service.close_locker(user_locker.locker_number)

    # ۵. سیستم امتیازدهی و گیمیفیکیشن
    points_earned = 1
    if active_log.check_in:
        duration = now_time - active_log.check_in
        hours_trained = duration.total_seconds() / 3600
        points_earned = max(1, int(hours_trained * 10))  # هر ساعت ۱۰ امتیاز
        if (
            hasattr(user, "gamification_points")
            and user.gamification_points is not None
        ):
            user.gamification_points += points_earned
        else:
            user.gamification_points = points_earned

    # ۶. تراکنش امن دیتابیس
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"success": False, "error": "خطا در سطح تراکنش دیتابیس خروج."}),
            500,
        )

    # ۷. به‌روزرسانی آمار ریل‌تایم باشگاه پس از خروج موفق
    try:
        total_present = AttendanceLog.query.filter_by(check_out=None).count()
        total_capacity = Locker.query.filter(Locker.status != "broken").count()
        remaining_capacity = total_capacity - total_present

        socketio.emit(
            "update_dashboard",
            {
                "total_present": total_present,
                "remaining_capacity": max(0, remaining_capacity),
                "last_user": f"{user.full_name or 'ورزشکار'} (خروج)",
                "assigned_locker": assigned_locker_num,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
            namespace="/public",
        )
    except Exception as e:
        print("SocketIO Error In Check-out:", e)

    return (
        jsonify(
            {
                "success": True,
                "message": "خروج شما با موفقیت ثبت شد. خسته نباشید!",
                "points_earned": points_earned,
            }
        ),
        200,
    )
