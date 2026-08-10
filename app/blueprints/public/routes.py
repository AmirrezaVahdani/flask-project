from flask import render_template
from app.blueprints.public import public_bp
from app.models import AttendanceLog, Locker


@public_bp.route("/")
@public_bp.route("/home")
def home():
    return render_template("public/home.html")


# ۱. روت کیوسک ورود (آدرس: /public/kiosk)
@public_bp.route("/kiosk")
def gym_kiosk():
    return render_template("public/kiosk.html")


# ۲. روت کیوسک خروج (آدرس: /public/checkout-kiosk)
@public_bp.route("/checkout-kiosk")
def gym_checkout_kiosk():
    return render_template("public/checkout_kiosk.html")


# ۳. روت مانیتور سالن (آدرس: /public/monitor)
@public_bp.route("/monitor")
def gym_monitor():
    # محاسبه تعداد افراد حاضر و ظرفیت رختکن در اولین لود صفحه
    total_present = AttendanceLog.query.filter_by(check_out=None).count()
    total_capacity = Locker.query.filter(Locker.status != "broken").count()
    remaining_capacity = max(0, total_capacity - total_present)

    return render_template(
        "public/monitor.html",
        total_present=total_present,
        remaining_capacity=remaining_capacity,
    )
