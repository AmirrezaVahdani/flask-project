from app.extensions import db
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(10), unique=True, nullable=False)
    phone_number = db.Column(db.String(11), nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(20), default='member')  # admin, member
    wallet_balance = db.Column(db.Integer, default=0)
    gamification_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    attendance_logs = db.relationship('AttendanceLog', backref='user', lazy=True)
    transactions = db.relationship('FinancialTransaction', backref='user', lazy=True)

    #متد امنیتی رمز عبور 
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class GymPlan(db.Model):
    __tablename__ = 'gym_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    total_sessions = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    
    subscriptions = db.relationship('Subscription', backref='gym_plan', lazy=True)


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('gym_plans.id'), nullable=True)
    package_name = db.Column(db.String(100))
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    remaining_sessions = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    trainer_name = db.Column(db.String(100), default="بدون مربی")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Trainer(db.Model):
    __tablename__ = 'trainers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    specialty = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Locker(db.Model):
    __tablename__ = 'lockers'
    id = db.Column(db.Integer, primary_key=True)
    locker_number = db.Column(db.Integer, unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')  # available, occupied, broken
    current_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)


class AttendanceLog(db.Model):
    __tablename__ = 'attendance_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    locker_id = db.Column(db.Integer, db.ForeignKey('lockers.id'), nullable=True)
    check_in = db.Column(db.DateTime, default=datetime.utcnow)
    check_out = db.Column(db.DateTime, nullable=True)

    locker = db.relationship('Locker', backref='attendance_logs', lazy=True)


class FinancialTransaction(db.Model):
    __tablename__ = 'financial_transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # مثبت برای شارژ، منفی برای خرید بوفه/شهریه
    transaction_type = db.Column(db.String(50), nullable=True)  # e.g. 'buffet_purchase', 'wallet_charge', 'subscription'
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)