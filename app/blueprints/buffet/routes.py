from decimal import Decimal

from flask import render_template, request, redirect, url_for, flash
from . import buffet_bp
from app.auth import admin_required
from app.extensions import db
from app.models import User, Locker, FinancialTransaction


@buffet_bp.route('/sales', methods=['GET', 'POST'])
@admin_required
def buffet_sales():
    if request.method == 'POST':
        action = request.form.get('action')

        try:
            amount_value = request.form.get('amount', '0').strip()
            amount = int(Decimal(amount_value))
        except Exception:
            flash('مبلغ وارد شده معتبر نیست.')
            return redirect(url_for('buffet.buffet_sales'))

        if amount <= 0:
            flash('مبلغ باید عددی مثبت باشد.')
            return redirect(url_for('buffet.buffet_sales'))

        # سناریو اول: خرید از بوفه با شماره کمد
        if action == 'purchase':
            locker_number = request.form.get('locker_number', '').strip()
            description = (
                request.form.get('description', 'خرید از بوفه').strip()
                or 'خرید از بوفه'
            )

            locker = Locker.query.filter_by(
                locker_number=locker_number,
                status='occupied',
            ).first()
            if not locker or not locker.current_user_id:
                flash(
                    'این کمد در حال حاضر به هیچ کاربر حاضری اختصاص داده نشده '
                    'است.'
                )
                return redirect(url_for('buffet.buffet_sales'))

            user = User.query.get(locker.current_user_id)
            if not user:
                flash('کاربر مرتبط با این کمد یافت نشد.')
                return redirect(url_for('buffet.buffet_sales'))

            if user.wallet_balance < amount:
                flash(
                    f'موجودی کیف پول ورزشکار کافی نیست. موجودی فعلی: '
                    f'{user.wallet_balance} تومان'
                )
                return redirect(url_for('buffet.buffet_sales'))

            user.wallet_balance -= amount
            tx = FinancialTransaction(
                user_id=user.id,
                amount=-amount,
                transaction_type='buffet_purchase',
                description=f"کمد {locker_number} - {description}",
            )
            db.session.add(tx)
            db.session.commit()
            flash('پرداخت بوفه با موفقیت ثبت شد.')
            return redirect(url_for('buffet.buffet_sales'))

        # سناریو دوم: شارژ مستقیم کیف پول ورزشکار توسط بوفه‌دار/ادمین
        elif action == 'charge':
            national_id = request.form.get('national_id', '').strip()
            if not national_id:
                flash('کد ملی ورزشکار الزامی است.')
                return redirect(url_for('buffet.buffet_sales'))

            user = User.query.filter_by(national_id=national_id).first()
            if not user:
                flash('ورزشکار یافت نشد.')
                return redirect(url_for('buffet.buffet_sales'))

            user.wallet_balance += amount
            tx = FinancialTransaction(
                user_id=user.id,
                amount=amount,
                transaction_type='wallet_charge',
                description='شارژ نقدی کیف پول در بوفه',
            )
            db.session.add(tx)
            db.session.commit()
            flash('شارژ کیف پول با موفقیت انجام شد.')
            return redirect(url_for('buffet.buffet_sales'))

    # نمایش لیست آخرین تراکنش‌های بوفه در صفحه
    recent_transactions = (
        FinancialTransaction.query.filter_by(
            transaction_type='buffet_purchase'
        )
        .order_by(FinancialTransaction.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        'buffet/sales.html',
        transactions=recent_transactions,
    )
