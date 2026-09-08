from datetime import date, timedelta
from functools import wraps

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import desc

from app.extensions import db
from app.models import (
    AttendanceLog,
    FinancialTransaction,
    GymPlan,
    Locker,
    Subscription,
    Trainer,
    User,
)
from app.utils import deactivate_expired_subscriptions

from . import member_bp


def member_required(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "member":
            flash("برای مشاهده پنل اعضا وارد شوید.")
            return redirect(url_for("member.login"))
        return view(*args, **kwargs)

    return decorated


def _member_dashboard_data(user):
    deactivate_expired_subscriptions(user_id=user.id)
    subscriptions = (
        Subscription.query.filter_by(user_id=user.id)
        .order_by(desc(Subscription.id))
        .all()
    )
    active_sub = next(
        (
            subscription
            for subscription in subscriptions
            if subscription.is_active
        ),
        None,
    )
    days_left = 0
    if active_sub and active_sub.end_date:
        days_left = max(0, (active_sub.end_date - date.today()).days)

    last_attendance = (
        AttendanceLog.query.filter_by(user_id=user.id)
        .order_by(desc(AttendanceLog.check_in))
        .first()
    )
    current_locker = Locker.query.filter_by(current_user_id=user.id).first()
    transactions = (
        FinancialTransaction.query.filter_by(user_id=user.id)
        .order_by(desc(FinancialTransaction.created_at))
        .limit(10)
        .all()
    )
    attendance_history = (
        AttendanceLog.query.filter_by(user_id=user.id)
        .order_by(desc(AttendanceLog.check_in))
        .limit(10)
        .all()
    )
    return {
        "active_sub": active_sub,
        "days_left": days_left,
        "last_attendance": last_attendance,
        "current_locker": current_locker,
        "transactions": transactions,
        "attendance_history": attendance_history,
    }


@member_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and current_user.role == "member":
        return redirect(url_for("member.dashboard"))

    if request.method == "POST":
        national_id = request.form.get("national_id", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        user = User.query.filter_by(
            national_id=national_id,
            phone_number=phone_number,
            role="member",
        ).first()
        if user:
            login_user(user)
            return redirect(url_for("member.dashboard"))
        flash("کد ملی یا شماره موبایل صحیح نیست.")

    return render_template("member/login.html")


@member_bp.route("/logout")
@member_required
def logout():
    logout_user()
    return redirect(url_for("member.login"))


@member_bp.route("/dashboard")
@member_required
def dashboard():
    user = current_user
    data = _member_dashboard_data(user)
    plans = GymPlan.query.order_by(GymPlan.price).all()
    trainers = (
        Trainer.query.filter_by(is_active=True).order_by(Trainer.name).all()
    )
    return render_template(
        "member/dashboard.html",
        user=user,
        plans=plans,
        trainers=trainers,
        **data,
    )


@member_bp.route("/subscribe", methods=["POST"])
@member_required
def subscribe():
    user = User.query.get_or_404(current_user.id)
    plan = GymPlan.query.get_or_404(request.form.get("plan_id"))
    trainer_name = request.form.get("trainer_name", "").strip() or "بدون مربی"

    trainer = Trainer.query.filter_by(
        name=trainer_name,
        is_active=True,
    ).first()
    if trainer_name != "بدون مربی" and trainer is None:
        flash("مربی انتخاب‌شده معتبر نیست.")
        return redirect(url_for("member.dashboard"))

    if user.wallet_balance < plan.price:
        flash(
            f"موجودی کیف پول کافی نیست. موجودی فعلی: "
            f"{user.wallet_balance} تومان، "
            f"هزینه پلن: {plan.price} تومان."
        )
        return redirect(url_for("member.dashboard"))

    Subscription.query.filter_by(user_id=user.id, is_active=True).update(
        {"is_active": False}
    )
    start_dt = date.today()
    new_sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        package_name=plan.name,
        start_date=start_dt,
        end_date=start_dt + timedelta(days=plan.duration_days),
        remaining_sessions=plan.total_sessions,
        is_active=True,
        trainer_name=trainer_name,
    )
    user.wallet_balance -= plan.price
    db.session.add(new_sub)
    db.session.add(
        FinancialTransaction(
            user_id=user.id,
            amount=-plan.price,
            transaction_type="subscription",
            description=f"تمدید اشتراک: {plan.name} با مربیگری {trainer_name}",
        )
    )
    db.session.commit()
    flash("اشتراک شما با موفقیت فعال شد.")
    return redirect(url_for("member.dashboard"))
