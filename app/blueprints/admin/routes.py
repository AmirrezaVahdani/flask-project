from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app.auth import admin_required
from app.extensions import db
from app.models import (
    User,
    Locker,
    Subscription,
    AttendanceLog,
    FinancialTransaction,
    GymPlan,
    Trainer,
)
from app.utils import (
    deactivate_expired_subscriptions,
    validate_national_id,
    validate_phone_number,
    get_analytics_data,
)
from datetime import date, datetime, timedelta
from sqlalchemy import desc, or_

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        national_id = request.form.get('national_id')
        password = request.form.get('password')

        user = User.query.filter_by(national_id=national_id, role='admin').first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.admin_dashboard'))

        flash('کد ملی یا رمز عبور اشتباه است.')

    return render_template('admin/login.html')

@admin_bp.route('/logout')
@admin_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    total_members = User.query.filter_by(role='member').count()
    active_presents = AttendanceLog.query.filter_by(check_out=None).count()
    broken_lockers = Locker.query.filter_by(status='broken').count()
    lockers = Locker.query.order_by(Locker.locker_number).all()

    locker_details = []
    for locker in lockers:
        owner = None
        presence_status = 'خالی'
        if locker.current_user_id:
            owner = User.query.get(locker.current_user_id)
        if locker.status == 'occupied' and owner:
            active_log = AttendanceLog.query.filter_by(user_id=owner.id, check_out=None).first()
            presence_status = 'در باشگاه' if active_log else 'خارج از باشگاه'
        elif locker.status == 'available':
            presence_status = 'خالی'
        elif locker.status == 'broken':
            presence_status = 'خراب'

        locker_details.append({
            'locker': locker,
            'owner': owner,
            'presence_status': presence_status,
        })

    # پیدا کردن ورزشکارانی که اشتراکشان تا ۳ روز آینده تمام می‌شود
    three_days_later = date.today() + timedelta(days=3)
    expiring_subs = Subscription.query.filter(
        Subscription.is_active.is_(True),
        Subscription.end_date >= date.today(),
        Subscription.end_date <= three_days_later,
    ).all()

    trainer_summary = []
    trainer_rows = (
        Subscription.query.filter_by(is_active=True)
        .with_entities(Subscription.trainer_name)
        .distinct()
        .order_by(Subscription.trainer_name)
        .all()
    )
    for trainer_name, in trainer_rows:
        if trainer_name:
            trainer_summary.append({
                'trainer_name': trainer_name,
                'student_count': Subscription.query.filter_by(
                    trainer_name=trainer_name,
                    is_active=True,
                ).count(),
            })

    return render_template(
        'admin/dashboard.html',
        total_members=total_members,
        active_presents=active_presents,
        broken_lockers=broken_lockers,
        lockers=lockers,
        locker_details=locker_details,
        expiring_subs=expiring_subs,
        trainer_summary=trainer_summary,
    )

@admin_bp.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    deactivate_expired_subscriptions()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        national_id = request.form.get('national_id', '').strip()
        phone_number = request.form.get('phone_number', '').strip()

        if not full_name or not national_id or not phone_number:
            flash('لطفاً تمام اطلاعات ورزشکار را وارد کنید.')
            return redirect(url_for('admin.manage_users'))

        if not validate_national_id(national_id):
            flash('کد ملی نامعتبر است. باید ۱۰ رقم باشد.')
            return redirect(url_for('admin.manage_users'))

        if not validate_phone_number(phone_number):
            flash('شماره موبایل نامعتبر است. باید ۱۱ رقم و با ۰۹ شروع شود.')
            return redirect(url_for('admin.manage_users'))

        existing_user = User.query.filter_by(national_id=national_id).first()
        if existing_user:
            flash('این کد ملی قبلاً ثبت شده است.')
            return redirect(url_for('admin.manage_users'))

        new_user = User(
            full_name=full_name,
            national_id=national_id,
            phone_number=phone_number,
            role='member',
        )
        db.session.add(new_user)
        db.session.commit()
        flash('ورزشکار جدید با موفقیت ثبت شد.')
        return redirect(url_for('admin.manage_users'))

    search_query = request.args.get('q', '').strip()
    users_query = User.query.filter_by(role='member')
    if search_query:
        users_query = users_query.filter(
            or_(
                User.full_name.ilike(f"%{search_query}%"),
                User.national_id.contains(search_query),
                User.phone_number.contains(search_query),
            )
        )

    all_users = users_query.order_by(User.full_name).all()
    for user in all_users:
        user.active_sub = Subscription.query.filter_by(user_id=user.id, is_active=True).first()

    all_plans = GymPlan.query.all()
    all_trainers = Trainer.query.filter_by(is_active=True).order_by(Trainer.name).all()
    return render_template(
        'admin/users.html',
        users=all_users,
        plans=all_plans,
        trainers=all_trainers,
        search_query=search_query,
    )

@admin_bp.route('/users/<int:user_id>/profile')
@admin_required
def user_profile(user_id):
    deactivate_expired_subscriptions(user_id=user_id)

    user = User.query.get_or_404(user_id)
    subscriptions = Subscription.query.filter_by(user_id=user.id).order_by(desc(Subscription.id)).all()
    active_sub = next((s for s in subscriptions if s.is_active), None)
    
    days_left = 0
    if active_sub:
        days_left = (active_sub.end_date - date.today()).days
        if days_left < 0:
            days_left = 0
            
    transactions = FinancialTransaction.query.filter_by(user_id=user.id).order_by(desc(FinancialTransaction.created_at)).all()
    last_attendance = AttendanceLog.query.filter_by(user_id=user.id).order_by(desc(AttendanceLog.check_in)).first()
    is_present = last_attendance and last_attendance.check_out is None
    current_locker = Locker.query.filter_by(current_user_id=user.id).first()
    attendance_history = (
        AttendanceLog.query
        .filter_by(user_id=user.id)
        .order_by(desc(AttendanceLog.check_in))
        .limit(10)
        .all()
    )

    return render_template(
        'admin/user_profile.html',
        user=user,
        subscriptions=subscriptions,
        active_sub=active_sub,
        days_left=days_left,
        transactions=transactions,
        is_present=is_present,
        last_attendance=last_attendance,
        current_locker=current_locker,
        attendance_history=attendance_history,
    )

@admin_bp.route('/users/<int:user_id>/subscribe', methods=['POST'])
@admin_required
def subscribe_user(user_id):
    user = User.query.get_or_404(user_id)
    plan_id = request.form.get('plan_id')
    trainer_name = request.form.get('trainer_name', '').strip() or "بدون مربی"
    
    plan = GymPlan.query.get_or_404(plan_id)

    if user.wallet_balance < plan.price:
        flash(
            f'موجودی کیف پول کافی نیست. موجودی فعلی: {user.wallet_balance} تومان، '
            f'هزینه پلن: {plan.price} تومان.'
        )
        return redirect(url_for('admin.manage_users'))
    
    # غیرفعال کردن اشتراک‌های فعال قبلی این کاربر
    Subscription.query.filter_by(user_id=user_id, is_active=True).update({"is_active": False})
    
    start_dt = date.today()
    end_dt = start_dt + timedelta(days=plan.duration_days)
    
    new_sub = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        package_name=plan.name,
        start_date=start_dt,
        end_date=end_dt,
        remaining_sessions=plan.total_sessions,
        is_active=True,
        trainer_name=trainer_name
    )
    
    user.wallet_balance -= plan.price

    new_tx = FinancialTransaction(
        user_id=user_id,
        amount=-plan.price,
        description=f"خرید اشتراک: {plan.name} با مربیگری {trainer_name}"
    )
    
    db.session.add(new_sub)
    db.session.add(new_tx)
    db.session.commit()
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/wallet-charge', methods=['POST'])
@admin_required
def wallet_charge(user_id):
    user = User.query.get_or_404(user_id)
    amount_text = request.form.get('amount', '').strip()
    description = request.form.get('description', '').strip() or 'شارژ کیف پول توسط مدیر'

    if not amount_text.isdigit() or int(amount_text) <= 0:
        flash('مبلغ وارد شده باید عددی مثبت باشد.')
        return redirect(url_for('admin.user_profile', user_id=user_id))

    amount = int(amount_text)
    user.wallet_balance += amount
    tx = FinancialTransaction(
        user_id=user.id,
        amount=amount,
        transaction_type='wallet_charge',
        description=description,
    )
    db.session.add(tx)
    db.session.commit()
    flash('کیف پول ورزشکار با موفقیت شارژ شد.')
    return redirect(url_for('admin.user_profile', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/force-checkout', methods=['POST'])
@admin_required
def force_checkout(user_id):
    user = User.query.get_or_404(user_id)
    active_attendance = AttendanceLog.query.filter_by(user_id=user.id, check_out=None).first()
    if not active_attendance:
        flash('این ورزشکار در حال حاضر داخل باشگاه نیست.')
        return redirect(url_for('admin.user_profile', user_id=user_id))

    locker = Locker.query.filter_by(current_user_id=user.id).first()
    if locker:
        locker.status = 'available'
        locker.current_user_id = None

    active_attendance.check_out = datetime.utcnow()
    db.session.commit()
    flash('خروج کاربر ثبت و کمد آزاد شد.')
    return redirect(url_for('admin.user_profile', user_id=user_id))

@admin_bp.route('/trainers', methods=['GET', 'POST'])
@admin_required
def manage_trainers():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name', '').strip()
            specialty = request.form.get('specialty', '').strip()
            if not name:
                flash('نام مربی را وارد کنید.')
                return redirect(url_for('admin.manage_trainers'))

            if Trainer.query.filter_by(name=name).first():
                flash('این نام مربی قبلاً ثبت شده است.')
                return redirect(url_for('admin.manage_trainers'))

            db.session.add(Trainer(name=name, specialty=specialty or None))
            db.session.commit()
            flash('مربی جدید با موفقیت اضافه شد.')
            return redirect(url_for('admin.manage_trainers'))

        if action == 'delete':
            trainer_id = request.form.get('trainer_id')
            trainer = Trainer.query.get(trainer_id)
            if trainer:
                db.session.delete(trainer)
                db.session.commit()
                flash('مربی با موفقیت حذف شد.')
            else:
                flash('مربی مورد نظر یافت نشد.')
            return redirect(url_for('admin.manage_trainers'))

    trainers = Trainer.query.order_by(Trainer.name).all()
    return render_template('admin/trainers.html', trainers=trainers)


@admin_bp.route('/plans', methods=['GET', 'POST'])
@admin_required
def manage_plans():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration_days = request.form.get('duration_days', '').strip()
        total_sessions = request.form.get('total_sessions', '').strip()
        price = request.form.get('price', '').strip()

        if not name or not duration_days.isdigit() or not total_sessions.isdigit() or not price.isdigit():
            flash('لطفاً تمامی فیلدهای پلن را با مقادیر معتبر تکمیل کنید.')
            return redirect(url_for('admin.manage_plans'))

        new_plan = GymPlan(
            name=name,
            duration_days=int(duration_days),
            total_sessions=int(total_sessions),
            price=int(price),
        )
        db.session.add(new_plan)
        db.session.commit()
        flash('پلن جدید با موفقیت اضافه شد.')
        return redirect(url_for('admin.manage_plans'))

    plans = GymPlan.query.all()
    return render_template('admin/plans.html', plans=plans)

@admin_bp.route('/trainer/panel', methods=['GET'])
@admin_required
def trainer_panel():
    deactivate_expired_subscriptions()

    trainer_name = request.args.get('trainer_name', '').strip()
    trainers = Trainer.query.filter_by(is_active=True).order_by(Trainer.name).all()
    my_students = []
    if trainer_name:
        my_students = Subscription.query.filter_by(trainer_name=trainer_name, is_active=True).all()

    return render_template(
        'admin/trainer_panel.html',
        my_students=my_students,
        trainer_name=trainer_name,
        trainers=trainers,
    )

@admin_bp.route('/lockers/<int:locker_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_locker_status(locker_id):
    locker = Locker.query.get_or_404(locker_id)
    if locker.status == 'available':
        locker.status = 'broken'
    elif locker.status == 'broken':
        locker.status = 'available'
    db.session.commit()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/api/analytics-data')
@admin_required
def analytics_data():
    return get_analytics_data()
