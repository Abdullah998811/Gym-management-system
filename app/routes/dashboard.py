from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from app.extensions import db
from app.models.access import User
from app.models.member import Member, MemberMeasurement
from app.models.plan import Membership, MembershipPlan
from app.models.training import GymClass, ClassBooking, PTSession, MemberWorkoutPlan
from app.models.nutrition import MemberDietPlan
from app.models.finance import Invoice, Payment, Expense
from app.models.operations import Attendance, Complaint, Notification
from app.models.equipment import Equipment, MaintenanceRecord
from app.utils.decorators import role_required, ensure_member_access
from app.utils.helpers import today_pk

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    user_role = current_user.role_name
    if user_role == 'Member':
        return redirect(url_for('dashboard.member_dashboard'))
    elif user_role == 'Trainer':
        return redirect(url_for('dashboard.trainer_dashboard'))

    today = today_pk()
    start_of_month = today.replace(day=1)
    two_weeks_out = today + timedelta(days=14)

    start_of_today = datetime.combine(today, datetime.min.time())
    end_of_today = datetime.combine(today, datetime.max.time())

    # Key Performance Indicators (KPIs)
    total_members = Member.active().count()
    today_checkins = Attendance.active().filter(
        Attendance.check_in_time >= start_of_today,
        Attendance.check_in_time <= end_of_today
    ).count()
    active_classes = GymClass.active().count()

    monthly_revenue = db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0.0))\
        .filter(Invoice.is_deleted == False, Invoice.issue_date >= start_of_month).scalar()

    expiring_soon = Membership.active().filter(
        Membership.end_date >= today,
        Membership.end_date <= two_weeks_out
    ).count()

    overdue_invoices = Invoice.active().filter(
        Invoice.payment_status.in_(['Unpaid', 'Overdue', 'Partial']),
        Invoice.due_date < today
    ).count()

    maintenance_due = Equipment.active().filter(
        Equipment.condition_status.in_(['Maintenance Due', 'Out of Order'])
    ).count()

    recent_checkins = Attendance.active().order_by(Attendance.check_in_time.desc()).limit(7).all()
    recent_invoices = Invoice.active().order_by(Invoice.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard/index.html',
        total_members=total_members,
        today_checkins=today_checkins,
        active_classes=active_classes,
        monthly_revenue=monthly_revenue,
        expiring_soon=expiring_soon,
        overdue_invoices=overdue_invoices,
        maintenance_due=maintenance_due,
        recent_checkins=recent_checkins,
        recent_invoices=recent_invoices
    )

@dashboard_bp.route('/member-dashboard')
@login_required
def member_dashboard():
    member = Member.active().filter_by(user_id=current_user.id).first()
    if not member and current_user.role_name == 'Admin':
        # Admin viewing sample member dashboard
        member = Member.active().first()

    active_membership = member.active_membership if member else None
    recent_attendance = Attendance.active().filter_by(member_id=member.id).order_by(Attendance.check_in_time.desc()).limit(10).all() if member else []
    bookings = ClassBooking.active().filter_by(member_id=member.id, booking_status='Confirmed').order_by(ClassBooking.booking_date.desc()).limit(5).all() if member else []
    invoices = Invoice.active().filter_by(member_id=member.id).order_by(Invoice.issue_date.desc()).limit(5).all() if member else []
    latest_measurement = MemberMeasurement.active().filter_by(member_id=member.id).order_by(MemberMeasurement.measurement_date.desc()).first() if member else None
    workout_plan = MemberWorkoutPlan.active().filter_by(member_id=member.id, is_current=True).first() if member else None
    diet_plan = MemberDietPlan.active().filter_by(member_id=member.id, is_current=True).first() if member else None

    return render_template(
        'dashboard/member_dashboard.html',
        member=member,
        active_membership=active_membership,
        recent_attendance=recent_attendance,
        bookings=bookings,
        invoices=invoices,
        latest_measurement=latest_measurement,
        workout_plan=workout_plan,
        diet_plan=diet_plan
    )

@dashboard_bp.route('/trainer-dashboard')
@login_required
def trainer_dashboard():
    trainer = current_user.trainer_record
    if not trainer and current_user.role_name == 'Admin':
        # Admin preview
        from app.models.staff import Trainer
        trainer = Trainer.active().first()

    trainer_id = trainer.id if trainer else 0
    classes = GymClass.active().filter_by(trainer_id=trainer_id).all() if trainer else []
    pt_sessions = PTSession.active().filter_by(trainer_id=trainer_id).order_by(PTSession.session_date.desc()).limit(10).all() if trainer else []
    workout_plans = current_user.trainer_record.workout_plans if (current_user.trainer_record and current_user.trainer_record.workout_plans) else []

    return render_template(
        'dashboard/trainer_dashboard.html',
        trainer=trainer,
        classes=classes,
        pt_sessions=pt_sessions,
        workout_plans=workout_plans
    )

# ----------------- Analytics JSON Endpoints for Chart.js -----------------

@dashboard_bp.route('/api/analytics/revenue-monthly')
@login_required
@role_required('Admin', 'Manager')
def api_revenue_monthly():
    months_labels = []
    revenue_data = []
    expenses_data = []

    today = date.today()
    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        label = datetime(year, month, 1).strftime("%b %Y")
        months_labels.append(label)

        # Revenue
        rev = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))\
            .filter(
                Payment.is_deleted == False,
                extract('year', Payment.payment_date) == year,
                extract('month', Payment.payment_date) == month
            ).scalar()
        revenue_data.append(float(rev))

        # Expenses
        exp = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0))\
            .filter(
                Expense.is_deleted == False,
                extract('year', Expense.expense_date) == year,
                extract('month', Expense.expense_date) == month
            ).scalar()
        expenses_data.append(float(exp))

    return jsonify({
        'labels': months_labels,
        'revenue': revenue_data,
        'expenses': expenses_data
    })

@dashboard_bp.route('/api/analytics/members-monthly')
@login_required
@role_required('Admin', 'Manager')
def api_members_monthly():
    labels = []
    counts = []
    today = date.today()

    for i in range(5, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        labels.append(datetime(year, month, 1).strftime("%b %Y"))
        cnt = Member.active().filter(
            extract('year', Member.join_date) == year,
            extract('month', Member.join_date) == month
        ).count()
        counts.append(cnt)

    return jsonify({'labels': labels, 'counts': counts})

@dashboard_bp.route('/api/analytics/plan-distribution')
@login_required
@role_required('Admin', 'Manager')
def api_plan_distribution():
    plans = MembershipPlan.active().all()
    labels = [p.name for p in plans]
    counts = []

    for p in plans:
        c = Membership.active().filter_by(plan_id=p.id).count()
        counts.append(c)

    return jsonify({'labels': labels, 'data': counts})

@dashboard_bp.route('/api/analytics/attendance-weekly')
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def api_attendance_weekly():
    days = []
    counts = []
    today = today_pk()

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        days.append(d.strftime("%a (%d %b)"))
        s_d = datetime.combine(d, datetime.min.time())
        e_d = datetime.combine(d, datetime.max.time())
        cnt = Attendance.active().filter(
            Attendance.check_in_time >= s_d,
            Attendance.check_in_time <= e_d
        ).count()
        counts.append(cnt)

    return jsonify({'labels': days, 'counts': counts})

@dashboard_bp.route('/api/analytics/member-measurements/<int:member_id>')
@login_required
def api_member_measurements(member_id):
    ensure_member_access(member_id)
    records = MemberMeasurement.active().filter_by(member_id=member_id).order_by(MemberMeasurement.measurement_date.asc()).all()
    dates = [str(r.measurement_date) for r in records]
    weights = [r.weight_kg for r in records]
    bmis = [r.bmi for r in records]
    return jsonify({'dates': dates, 'weights': weights, 'bmis': bmis})
