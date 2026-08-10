from datetime import date, datetime, timedelta
from calendar import monthrange

from sqlalchemy import func, or_

from app.extensions import db
from app.models import AttendanceLog, FinancialTransaction, Subscription


def deactivate_expired_subscriptions(user_id=None):
    """Deactivate subscriptions past end_date or with no sessions left."""
    today = date.today()
    query = Subscription.query.filter(
        Subscription.is_active == True,
        or_(
            Subscription.end_date < today,
            Subscription.remaining_sessions <= 0,
        ),
    )
    if user_id is not None:
        query = query.filter(Subscription.user_id == user_id)

    count = query.update({Subscription.is_active: False}, synchronize_session=False)
    if count:
        db.session.commit()
    return count


def validate_national_id(national_id):
    """Validate Iranian national ID format (10 digits)."""
    if not national_id or len(national_id) != 10 or not national_id.isdigit():
        return False
    return True


def validate_phone_number(phone):
    """Validate Iranian mobile number (11 digits starting with 09)."""
    return bool(phone and len(phone) == 11 and phone.isdigit() and phone.startswith("09"))


def get_analytics_data():
    """Build real chart data from database records."""
    today = date.today()

    # Financial: last 6 months of revenue (negative transactions = income for gym)
    persian_months = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    ]
    financial_labels = []
    financial_data = []

    for i in range(5, -1, -1):
        target = today.replace(day=1) - timedelta(days=i * 30)
        year, month = target.year, target.month
        month_label = persian_months[month - 1]
        financial_labels.append(month_label)

        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)

        total = (
            db.session.query(func.coalesce(func.sum(FinancialTransaction.amount), 0))
            .filter(
                FinancialTransaction.amount < 0,
                FinancialTransaction.created_at >= datetime.combine(start, datetime.min.time()),
                FinancialTransaction.created_at <= datetime.combine(end, datetime.max.time()),
            )
            .scalar()
        )
        financial_data.append(abs(int(total)) // 1000)

    # Traffic: check-ins grouped by time-of-day buckets (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    traffic_labels = ["8-12", "12-16", "16-20", "20-24"]
    traffic_data = [0, 0, 0, 0]

    logs = AttendanceLog.query.filter(AttendanceLog.check_in >= thirty_days_ago).all()
    for log in logs:
        hour = log.check_in.hour
        if 8 <= hour < 12:
            traffic_data[0] += 1
        elif 12 <= hour < 16:
            traffic_data[1] += 1
        elif 16 <= hour < 20:
            traffic_data[2] += 1
        elif 20 <= hour < 24:
            traffic_data[3] += 1

    return {
        "financial": {"labels": financial_labels, "data": financial_data},
        "traffic": {"labels": traffic_labels, "data": traffic_data},
    }
