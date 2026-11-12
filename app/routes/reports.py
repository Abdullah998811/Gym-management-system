from datetime import date, datetime
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from app.extensions import db
from app.models.operations import AuditLog
from app.models.member import Member
from app.models.staff import Trainer
from app.models.training import GymClass
from app.models.finance import Invoice, Expense
from app.models.access import User
from app.utils.decorators import role_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/audit-logs', methods=['GET'])
@login_required
@role_required('Admin')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '').strip()
    table_name = request.args.get('table_name', '').strip()
    user_id = request.args.get('user_id', type=int)

    query = AuditLog.active()
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if table_name:
        query = query.filter(AuditLog.table_name == table_name.lower())
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
    users = User.active().all()

    return render_template(
        'reports/audit_logs.html',
        pagination=pagination,
        logs=pagination.items,
        users=users,
        action=action,
        table_name=table_name,
        user_id=user_id
    )

@reports_bp.route('/search', methods=['GET'])
@login_required
def search():
    q = request.args.get('q', '').strip()
    members = []
    trainers = []
    classes = []
    invoices = []

    if q:
        search_pattern = f"%{q}%"
        members = Member.active().filter(
            or_(
                Member.first_name.ilike(search_pattern),
                Member.last_name.ilike(search_pattern),
                Member.membership_number.ilike(search_pattern),
                Member.phone.ilike(search_pattern),
                Member.cnic.ilike(search_pattern)
            )
        ).limit(10).all()

        trainers = Trainer.active().join(User).filter(
            or_(
                User.full_name.ilike(search_pattern),
                Trainer.specialization.ilike(search_pattern)
            )
        ).limit(5).all()

        classes = GymClass.active().filter(
            or_(
                GymClass.title.ilike(search_pattern),
                GymClass.difficulty_level.ilike(search_pattern)
            )
        ).limit(5).all()

        if current_user.role_name in ['Admin', 'Manager', 'Receptionist']:
            invoices = Invoice.active().filter(Invoice.invoice_number.ilike(search_pattern)).limit(5).all()

    return render_template(
        'reports/search.html',
        q=q,
        members=members,
        trainers=trainers,
        classes=classes,
        invoices=invoices
    )

@reports_bp.route('/revenue', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def revenue():
    today = date.today()
    invoices = Invoice.active().order_by(Invoice.issue_date.desc()).limit(15).all()
    expenses = Expense.active().order_by(Expense.expense_date.desc()).limit(15).all()

    total_invoiced = db.session.query(func.coalesce(func.sum(Invoice.total_amount), 0.0)).filter(Invoice.is_deleted == False).scalar()
    total_expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(Expense.is_deleted == False).scalar()

    return render_template(
        'reports/revenue.html',
        invoices=invoices,
        expenses=expenses,
        total_invoiced=total_invoiced,
        total_expenses=total_expenses,
        today=today
    )
