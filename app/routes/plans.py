from decimal import Decimal
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.plan import MembershipPlan, PlanFeature, Membership, Promotion, MemberPromotion
from app.models.member import Member
from app.forms.plans import MembershipPlanForm, PlanFeatureForm, PromotionForm, AssignMembershipForm
from app.utils.decorators import role_required
from app.utils.audit import log_action
from app.utils.helpers import export_to_csv, stream_csv_response

plans_bp = Blueprint('plans', __name__, url_prefix='/plans')

@plans_bp.route('/', methods=['GET'])
@login_required
def index():
    search = request.args.get('search', '').strip()
    plan_type = request.args.get('plan_type', '').strip()
    page = request.args.get('page', 1, type=int)

    query = MembershipPlan.active()
    if search:
        query = query.filter(MembershipPlan.name.ilike(f"%{search}%"))
    if plan_type:
        query = query.filter(MembershipPlan.plan_type == plan_type)

    pagination = query.order_by(MembershipPlan.price.asc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'plans/index.html',
        pagination=pagination,
        plans=pagination.items,
        search=search,
        plan_type=plan_type
    )

@plans_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def export_csv():
    headers = ['ID', 'Name', 'Type', 'Duration (Days)', 'Price (PKR)', 'Classes/Week', 'Status']
    def row_generator():
        plans = MembershipPlan.active().yield_per(100)
        for p in plans:
            yield [p.id, p.name, p.plan_type, p.duration_days, p.price, p.max_classes_per_week, p.status]
    return stream_csv_response(row_generator, headers, filename="membership_plans.csv")

@plans_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def create():
    form = MembershipPlanForm()
    if form.validate_on_submit():
        price_val = Decimal(str(form.price.data))
        plan = MembershipPlan(
            name=form.name.data.strip(),
            plan_type=form.plan_type.data,
            duration_days=form.duration_days.data,
            price=price_val,
            max_classes_per_week=form.max_classes_per_week.data,
            description=form.description.data.strip() if form.description.data else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(plan)
        try:
            db.session.commit()
            log_action('CREATE', 'membership_plans', plan.id, None, {'name': plan.name, 'price': str(plan.price)})
            flash(f"Plan '{plan.name}' created successfully!", "success")
            return redirect(url_for('plans.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating plan: {e}", exc_info=True)
            flash("An error occurred while creating the membership plan.", "danger")

    return render_template('plans/create.html', form=form)

@plans_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def edit(id):
    plan = MembershipPlan.active().filter_by(id=id).first_or_404()
    form = MembershipPlanForm(obj=plan)

    if form.validate_on_submit():
        old_val = {'name': plan.name, 'price': str(plan.price)}
        price_val = Decimal(str(form.price.data))
        plan.name = form.name.data.strip()
        plan.plan_type = form.plan_type.data
        plan.duration_days = form.duration_days.data
        plan.price = price_val
        plan.max_classes_per_week = form.max_classes_per_week.data
        plan.description = form.description.data.strip() if form.description.data else None
        plan.updated_by = current_user.id

        try:
            db.session.commit()
            log_action('UPDATE', 'membership_plans', plan.id, old_val, {'name': plan.name, 'price': str(plan.price)})
            flash(f"Plan '{plan.name}' updated successfully.", "success")
            return redirect(url_for('plans.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating plan: {e}", exc_info=True)
            flash("An error occurred while updating the membership plan.", "danger")

    return render_template('plans/edit.html', form=form, plan=plan)

@plans_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def delete(id):
    plan = MembershipPlan.active().filter_by(id=id).first_or_404()
    plan.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'membership_plans', plan.id, {'name': plan.name}, None)
        flash(f"Plan '{plan.name}' soft-deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting plan: {e}", exc_info=True)
        flash("An error occurred while deleting the plan.", "danger")

    return redirect(url_for('plans.index'))

@plans_bp.route('/memberships', methods=['GET'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist', 'Trainer')
def memberships():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Membership.active().join(Member)
    if search:
        query = query.filter(
            (Member.first_name.ilike(f"%{search}%")) |
            (Member.last_name.ilike(f"%{search}%")) |
            (Member.membership_number.ilike(f"%{search}%"))
        )
    if status:
        query = query.filter(Membership.status == status)

    pagination = query.order_by(Membership.end_date.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'plans/memberships.html',
        pagination=pagination,
        memberships=pagination.items,
        search=search,
        status=status
    )

@plans_bp.route('/assign', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def assign():
    form = AssignMembershipForm()
    members = Member.active().all()
    plans = MembershipPlan.active().all()

    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]
    form.plan_id.choices = [(p.id, f"{p.name} - PKR {float(p.price):,.0f} ({p.duration_days} days)") for p in plans]

    if form.validate_on_submit():
        plan = MembershipPlan.active().filter_by(id=form.plan_id.data).first_or_404()
        start_date = form.start_date.data
        end_date = start_date + timedelta(days=plan.duration_days - 1)
        price_val = Decimal(str(form.price_paid.data))

        # Prevent assigning a second overlapping active membership
        overlapping = Membership.active().filter(
            Membership.member_id == form.member_id.data,
            Membership.status.in_(['active', 'frozen']),
            Membership.start_date <= end_date,
            Membership.end_date >= start_date
        ).first()
        if overlapping:
            flash(f"Member already has an active membership during this timeframe ({overlapping.start_date} to {overlapping.end_date}). Use renewal instead.", "danger")
            return redirect(url_for('plans.assign'))

        ms = Membership(
            member_id=form.member_id.data,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            price_paid=price_val,
            auto_renew=form.auto_renew.data,
            status='active',
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(ms)
        try:
            db.session.commit()
            log_action('CREATE', 'memberships', ms.id, None, {'member_id': ms.member_id, 'plan_id': ms.plan_id})
            flash("Membership assigned successfully!", "success")
            return redirect(url_for('plans.memberships'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error assigning membership: {e}", exc_info=True)
            flash("An error occurred while assigning membership.", "danger")

    return render_template('plans/assign.html', form=form)

@plans_bp.route('/promotions', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def promotions():
    form = PromotionForm()
    if form.validate_on_submit():
        disc_pct = Decimal(str(form.discount_pct.data))
        promo = Promotion(
            code=form.code.data.strip().upper(),
            title=form.title.data.strip(),
            discount_pct=disc_pct,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            max_uses=form.max_uses.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(promo)
        try:
            db.session.commit()
            log_action('CREATE', 'promotions', promo.id, None, {'code': promo.code})
            flash(f"Promotion '{promo.code}' created!", "success")
            return redirect(url_for('plans.promotions'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating promotion: {e}", exc_info=True)
            flash("An error occurred while creating promotion.", "danger")

    all_promos = Promotion.active().order_by(Promotion.id.desc()).all()
    return render_template('plans/promotions.html', form=form, promotions=all_promos)

@plans_bp.route('/promotions/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def promo_delete(id):
    promo = Promotion.active().filter_by(id=id).first_or_404()
    promo.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'promotions', promo.id, {'code': promo.code}, None)
        flash(f"Promotion '{promo.code}' deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting promotion: {e}", exc_info=True)
        flash("An error occurred while deleting promotion.", "danger")
    return redirect(url_for('plans.promotions'))
