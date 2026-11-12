import io
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, Response, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.member import (
    Member, MemberProfile, EmergencyContact, MemberMeasurement,
    MemberGoal, MemberNote
)
from app.models.plan import (
    Membership, MembershipPlan, MembershipFreeze, MembershipRenewal,
    Promotion, MemberPromotion
)
from app.models.finance import Invoice, InvoiceItem, Payment, PaymentMethod, Discount
from app.models.access import User, Role
from app.models.gym import Branch
from app.models.operations import Attendance
from app.forms.members import (
    MemberForm, MemberMeasurementForm, MemberGoalForm, MemberNoteForm,
    EmergencyContactForm, MemberFreezeForm, MemberRenewForm
)
from app.utils.decorators import role_required, ensure_member_access
from app.utils.audit import log_action
from app.utils.pdf import generate_member_card_pdf
from app.utils.helpers import (
    export_to_csv, stream_csv_response, generate_membership_number, generate_invoice_number, today_pk
)

members_bp = Blueprint('members', __name__, url_prefix='/members')

@members_bp.route('/', methods=['GET'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist', 'Trainer')
def index():
    search = request.args.get('search', '').strip()
    branch_id = request.args.get('branch_id', type=int)
    gender = request.args.get('gender', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Member.active().options(joinedload(Member.branch), selectinload(Member.memberships))

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Member.first_name.ilike(search_filter),
                Member.last_name.ilike(search_filter),
                Member.membership_number.ilike(search_filter),
                Member.phone.ilike(search_filter),
                Member.cnic.ilike(search_filter),
                Member.email.ilike(search_filter)
            )
        )

    if branch_id:
        query = query.filter(Member.branch_id == branch_id)
    if gender:
        query = query.filter(Member.gender == gender)
    if status:
        query = query.filter(Member.status == status)

    pagination = query.order_by(Member.id.desc()).paginate(page=page, per_page=10, error_out=False)
    branches = Branch.active().all()

    return render_template(
        'members/index.html',
        pagination=pagination,
        members=pagination.items,
        branches=branches,
        search=search,
        branch_id=branch_id,
        gender=gender,
        status=status
    )

@members_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def export_csv():
    headers = ['ID', 'Membership #', 'First Name', 'Last Name', 'Email', 'Phone', 'CNIC', 'Gender', 'Join Date', 'Branch', 'Status']
    def row_generator():
        members = Member.active().order_by(Member.id.desc()).yield_per(100)
        for m in members:
            yield [
                m.id,
                m.membership_number,
                m.first_name,
                m.last_name,
                m.email,
                m.phone,
                m.cnic,
                m.gender,
                m.join_date,
                m.branch.name if m.branch else 'N/A',
                m.status
            ]
    return stream_csv_response(row_generator, headers, filename="gym_members.csv")

@members_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def create():
    form = MemberForm()
    branches = Branch.active().all()
    form.branch_id.choices = [(b.id, f"{b.name} ({b.city})") for b in branches]

    if form.validate_on_submit():
        # Duplicate checks must check active members only, allowing soft-deleted email/CNIC reuse
        if Member.active().filter_by(email=form.email.data.strip()).first():
            flash("An active member with this email address already exists.", "danger")
            return render_template('members/create.html', form=form)
        if Member.active().filter_by(cnic=form.cnic.data.strip()).first():
            flash("An active member with this CNIC already exists.", "danger")
            return render_template('members/create.html', form=form)

        # Retry loop for unique membership number
        max_retries = 5
        member = None
        for attempt in range(max_retries):
            mem_num = generate_membership_number(db.session)
            member = Member(
                membership_number=mem_num,
                branch_id=form.branch_id.data,
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=form.email.data.strip(),
                phone=form.phone.data.strip(),
                cnic=form.cnic.data.strip(),
                dob=form.dob.data,
                gender=form.gender.data,
                blood_group=form.blood_group.data if form.blood_group.data else None,
                join_date=date.today(),
                created_by=current_user.id,
                updated_by=current_user.id,
                status='active'
            )
            db.session.add(member)
            db.session.flush()

            # Optional linked user
            if getattr(form, 'create_user', None) and form.create_user.data:
                member_role = Role.active().filter_by(name='Member').first()
                if not member_role:
                    member_role = Role(name='Member', description='Gym Member Account')
                    db.session.add(member_role)
                    db.session.flush()

                base_username = form.email.data.strip().split('@')[0]
                uname = base_username
                idx = 1
                while User.query.filter_by(username=uname).first():
                    uname = f"{base_username}{idx}"
                    idx += 1

                temp_pw = form.temp_password.data.strip() if (form.temp_password.data and form.temp_password.data.strip()) else "Member@123"
                linked_user = User(
                    username=uname,
                    email=form.email.data.strip(),
                    full_name=f"{form.first_name.data.strip()} {form.last_name.data.strip()}",
                    phone=form.phone.data.strip(),
                    role_id=member_role.id,
                    branch_id=form.branch_id.data,
                    force_password_change=True,
                    created_by=current_user.id,
                    updated_by=current_user.id
                )
                linked_user.set_password(temp_pw)
                db.session.add(linked_user)
                db.session.flush()
                member.user_id = linked_user.id

            profile = MemberProfile(
                member_id=member.id,
                address=form.address.data.strip() if form.address.data else None,
                city=form.city.data.strip() if form.city.data else 'Lahore',
                fitness_level=form.fitness_level.data,
                medical_conditions=form.medical_conditions.data.strip() if form.medical_conditions.data else None,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(profile)

            try:
                db.session.commit()
                log_action('CREATE', 'members', member.id, None, {'name': member.full_name, 'membership_number': member.membership_number})
                flash(f"Member '{member.full_name}' ({member.membership_number}) registered successfully!", "success")
                return redirect(url_for('members.view', id=member.id))
            except IntegrityError:
                db.session.rollback()
                if attempt == max_retries - 1:
                    current_app.logger.error("Failed to generate unique membership number after retries.")
                    flash("Failed to generate unique membership number. Please try again.", "danger")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error while saving member: {e}", exc_info=True)
                flash("An error occurred while saving the member. Please try again.", "danger")
                break

    return render_template('members/create.html', form=form)

@members_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    member = Member.active().filter_by(id=id).first_or_404()
    ensure_member_access(member)

    measurement_form = MemberMeasurementForm()
    goal_form = MemberGoalForm()
    note_form = MemberNoteForm()
    contact_form = EmergencyContactForm()
    freeze_form = MemberFreezeForm()
    renew_form = MemberRenewForm()

    plans = MembershipPlan.active().all()
    renew_form.plan_id.choices = [(p.id, f"{p.name} - PKR {float(p.price):,.0f} ({p.duration_days} days)") for p in plans]

    recent_attendance = Attendance.active().filter_by(member_id=member.id).order_by(Attendance.check_in_time.desc()).limit(7).all()
    measurements = MemberMeasurement.active().filter_by(member_id=member.id).order_by(MemberMeasurement.measurement_date.desc()).all()
    goals = MemberGoal.active().filter_by(member_id=member.id).order_by(MemberGoal.target_date.asc()).all()
    notes = MemberNote.active().filter_by(member_id=member.id).order_by(MemberNote.created_at.desc()).all()

    return render_template(
        'members/view.html',
        member=member,
        measurement_form=measurement_form,
        goal_form=goal_form,
        note_form=note_form,
        contact_form=contact_form,
        freeze_form=freeze_form,
        renew_form=renew_form,
        recent_attendance=recent_attendance,
        measurements=measurements,
        goals=goals,
        notes=notes
    )

@members_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def edit(id):
    member = Member.active().filter_by(id=id).first_or_404()
    form = MemberForm(obj=member)
    branches = Branch.active().all()
    form.branch_id.choices = [(b.id, f"{b.name} ({b.city})") for b in branches]

    if request.method == 'GET' and member.profile:
        form.address.data = member.profile.address
        form.city.data = member.profile.city
        form.fitness_level.data = member.profile.fitness_level
        form.medical_conditions.data = member.profile.medical_conditions

    if form.validate_on_submit():
        existing_email = Member.active().filter(Member.email == form.email.data.strip(), Member.id != member.id).first()
        if existing_email:
            flash("Another active member already has this email address.", "danger")
            return render_template('members/edit.html', form=form, member=member)

        existing_cnic = Member.active().filter(Member.cnic == form.cnic.data.strip(), Member.id != member.id).first()
        if existing_cnic:
            flash("Another active member already has this CNIC.", "danger")
            return render_template('members/edit.html', form=form, member=member)

        old_val = {'first_name': member.first_name, 'last_name': member.last_name, 'email': member.email, 'phone': member.phone}

        member.branch_id = form.branch_id.data
        member.first_name = form.first_name.data.strip()
        member.last_name = form.last_name.data.strip()
        member.email = form.email.data.strip()
        member.phone = form.phone.data.strip()
        member.cnic = form.cnic.data.strip()
        member.dob = form.dob.data
        member.gender = form.gender.data
        member.blood_group = form.blood_group.data if form.blood_group.data else None
        member.updated_by = current_user.id

        if member.profile:
            member.profile.address = form.address.data.strip() if form.address.data else None
            member.profile.city = form.city.data.strip() if form.city.data else 'Lahore'
            member.profile.fitness_level = form.fitness_level.data
            member.profile.medical_conditions = form.medical_conditions.data.strip() if form.medical_conditions.data else None
            member.profile.updated_by = current_user.id

        try:
            db.session.commit()
            log_action('UPDATE', 'members', member.id, old_val, {'first_name': member.first_name, 'last_name': member.last_name})
            flash(f"Member '{member.full_name}' details updated successfully.", "success")
            return redirect(url_for('members.view', id=member.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating member: {e}", exc_info=True)
            flash("An error occurred while updating member details.", "danger")

    return render_template('members/edit.html', form=form, member=member)

@members_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def delete(id):
    member = Member.active().filter_by(id=id).first_or_404()
    member.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'members', member.id, {'name': member.full_name}, None)
        flash(f"Member '{member.full_name}' was soft-deleted successfully.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting member: {e}", exc_info=True)
        flash("An error occurred while deleting the member.", "danger")

    return redirect(url_for('members.index'))

@members_bp.route('/<int:id>/restore', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def restore(id):
    member = Member.query.filter_by(id=id, is_deleted=True).first_or_404()
    member.is_deleted = False
    member.deleted_at = None
    member.deleted_by = None
    member.status = 'active'
    if member.profile:
        member.profile.is_deleted = False
        member.profile.deleted_at = None
        member.profile.deleted_by = None

    try:
        db.session.commit()
        log_action('RESTORE', 'members', member.id, None, {'name': member.full_name, 'mem_num': member.membership_number})
        flash(f"Member '{member.full_name}' ({member.membership_number}) has been restored successfully!", "success")
        return redirect(url_for('members.view', id=member.id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error restoring member: {e}", exc_info=True)
        flash("An error occurred while restoring the member.", "danger")
        return redirect(url_for('members.index'))

@members_bp.route('/<int:id>/card-pdf', methods=['GET'])
@login_required
def card_pdf(id):
    member = Member.active().filter_by(id=id).first_or_404()
    ensure_member_access(member)
    pdf_bytes = generate_member_card_pdf(member)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=MemberCard_{member.membership_number}.pdf"}
    )

@members_bp.route('/<int:id>/measurements', methods=['POST'])
@login_required
def add_measurement(id):
    member = Member.active().filter_by(id=id).first_or_404()
    ensure_member_access(member)
    form = MemberMeasurementForm()
    if form.validate_on_submit():
        bmi = MemberMeasurement.calculate_bmi(form.weight_kg.data, form.height_cm.data)
        measurement = MemberMeasurement(
            member_id=member.id,
            measurement_date=form.measurement_date.data,
            weight_kg=form.weight_kg.data,
            height_cm=form.height_cm.data,
            bmi=bmi,
            chest_cm=form.chest_cm.data,
            waist_cm=form.waist_cm.data,
            hips_cm=form.hips_cm.data,
            bicep_cm=form.bicep_cm.data,
            body_fat_pct=form.body_fat_pct.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(measurement)
        try:
            db.session.commit()
            log_action('CREATE', 'member_measurements', measurement.id, None, {'weight': form.weight_kg.data, 'bmi': bmi})
            flash(f"New measurement added (BMI: {bmi}).", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving measurement: {e}", exc_info=True)
            flash("An error occurred while saving the measurement.", "danger")
    else:
        for err in form.errors.values():
            flash(err[0], "danger")
    return redirect(url_for('members.view', id=member.id))

@members_bp.route('/<int:id>/goals', methods=['POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer')
def add_goal(id):
    member = Member.active().filter_by(id=id).first_or_404()
    form = MemberGoalForm()
    if form.validate_on_submit():
        goal = MemberGoal(
            member_id=member.id,
            goal_type=form.goal_type.data,
            target_value=form.target_value.data.strip(),
            current_value=form.current_value.data.strip() if form.current_value.data else None,
            target_date=form.target_date.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(goal)
        try:
            db.session.commit()
            log_action('CREATE', 'member_goals', goal.id, None, {'type': goal.goal_type, 'target': goal.target_value})
            flash("Fitness goal saved.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving goal: {e}", exc_info=True)
            flash("An error occurred while saving your goal.", "danger")
    return redirect(url_for('members.view', id=member.id))

@members_bp.route('/<int:id>/notes', methods=['POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer')
def add_note(id):
    member = Member.active().filter_by(id=id).first_or_404()
    form = MemberNoteForm()
    if form.validate_on_submit():
        note = MemberNote(
            member_id=member.id,
            author_id=current_user.id,
            note_type=form.note_type.data,
            note_text=form.note_text.data.strip(),
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(note)
        try:
            db.session.commit()
            log_action('CREATE', 'member_notes', note.id, None, {'author': current_user.username})
            flash("Note recorded.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving note: {e}", exc_info=True)
            flash("An error occurred while recording note.", "danger")
    return redirect(url_for('members.view', id=member.id))

@members_bp.route('/<int:id>/freeze', methods=['POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def freeze(id):
    member = Member.active().filter_by(id=id).first_or_404()
    form = MemberFreezeForm()
    if form.validate_on_submit():
        # Get current active or future membership
        active_m = None
        today = today_pk()
        for m in member.memberships:
            if not m.is_deleted and m.end_date >= today:
                active_m = m
                break

        if not active_m:
            flash("This member does not have an active membership to freeze.", "danger")
            return redirect(url_for('members.view', id=member.id))

        start_dt = form.start_date.data
        end_dt = form.end_date.data

        if start_dt < today:
            flash("Freeze start date cannot be in the past.", "danger")
            return redirect(url_for('members.view', id=member.id))

        if end_dt < start_dt:
            flash("Freeze end date must be on or after start date.", "danger")
            return redirect(url_for('members.view', id=member.id))

        freeze_days = (end_dt - start_dt).days + 1
        max_freeze_days = current_app.config.get('MAX_FREEZE_DAYS', 90)
        if freeze_days > max_freeze_days:
            flash(f"Maximum allowed freeze duration is {max_freeze_days} days.", "danger")
            return redirect(url_for('members.view', id=member.id))

        # Prevent overlapping freezes
        overlap = MembershipFreeze.active().filter(
            MembershipFreeze.membership_id == active_m.id,
            MembershipFreeze.start_date <= end_dt,
            MembershipFreeze.end_date >= start_dt
        ).first()

        if overlap:
            flash(f"Freeze overlaps with an existing freeze period ({overlap.start_date} to {overlap.end_date}).", "danger")
            return redirect(url_for('members.view', id=member.id))

        freeze_rec = MembershipFreeze(
            membership_id=active_m.id,
            start_date=start_dt,
            end_date=end_dt,
            reason=form.reason.data.strip(),
            approved_by=current_user.id,
            created_by=current_user.id,
            updated_by=current_user.id
        )

        # Extend membership by the freeze period
        active_m.end_date = active_m.end_date + timedelta(days=freeze_days)

        # Do NOT set status to 'frozen' immediately if start_date is in the future
        if start_dt <= today <= end_dt:
            active_m.status = 'frozen'
        else:
            active_m.status = 'active'

        db.session.add(freeze_rec)
        try:
            db.session.commit()
            log_action('CREATE', 'membership_freezes', freeze_rec.id, None, {'freeze_days': freeze_days})
            flash(f"Membership freeze scheduled ({start_dt} to {end_dt}). Expiry extended by {freeze_days} days.", "info")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error freezing membership: {e}", exc_info=True)
            flash("An error occurred while processing membership freeze.", "danger")
    else:
        for err in form.errors.values():
            flash(err[0], "danger")
    return redirect(url_for('members.view', id=member.id))

@members_bp.route('/<int:id>/renew', methods=['POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def renew(id):
    member = Member.active().filter_by(id=id).first_or_404()
    form = MemberRenewForm()
    plans = MembershipPlan.active().all()
    form.plan_id.choices = [(p.id, f"{p.name}") for p in plans]

    if form.validate_on_submit():
        plan = MembershipPlan.active().filter_by(id=form.plan_id.data).first_or_404()
        active_m = member.active_membership
        today = today_pk()

        start_date = active_m.end_date + timedelta(days=1) if (active_m and active_m.end_date >= today) else today
        end_date = start_date + timedelta(days=plan.duration_days - 1)

        # Mark previous membership as renewed if new one starts immediately
        if active_m and start_date <= today:
            active_m.status = 'renewed'

        plan_price = Decimal(str(plan.price))
        discount_amount = Decimal('0.00')

        # Check for Promotion or Discount code if provided
        promo_code = form.discount_code.data.strip() if getattr(form, 'discount_code', None) and form.discount_code.data else None
        promo_obj = None
        disc_obj = None

        if promo_code:
            promo = Promotion.active().filter_by(code=promo_code).first()
            if promo and promo.is_valid():
                promo_obj = promo
                discount_amount = (plan_price * Decimal(str(promo.discount_pct))) / Decimal('100.00')
                promo.current_uses += 1
            else:
                disc = Discount.active().filter_by(code=promo_code).first()
                if disc:
                    disc_obj = disc
                    if disc.amount_type == 'percentage':
                        discount_amount = (plan_price * Decimal(str(disc.value))) / Decimal('100.00')
                    else:
                        discount_amount = Decimal(str(disc.value))

        total_payable = max(Decimal('0.00'), plan_price - discount_amount)
        amount_paid = Decimal(str(form.amount_paid.data))

        # Validate amount_paid <= total
        if amount_paid > total_payable:
            flash(f"Amount paid (PKR {amount_paid:,.2f}) cannot exceed total payable amount (PKR {total_payable:,.2f}).", "danger")
            return redirect(url_for('members.view', id=member.id))

        new_membership = Membership(
            member_id=member.id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            price_paid=amount_paid,
            created_by=current_user.id,
            updated_by=current_user.id,
            status='active'
        )
        db.session.add(new_membership)
        db.session.flush()

        if promo_obj:
            mp = MemberPromotion(member_id=member.id, promotion_id=promo_obj.id, applied_date=date.today())
            db.session.add(mp)

        renewal_log = MembershipRenewal(
            membership_id=new_membership.id,
            renewal_date=date.today(),
            extended_until=end_date,
            amount_paid=amount_paid,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(renewal_log)

        # Auto-create Invoice and InvoiceItem
        inv_num = generate_invoice_number(db.session)
        invoice = Invoice(
            invoice_number=inv_num,
            member_id=member.id,
            membership_id=new_membership.id,
            discount_id=disc_obj.id if disc_obj else None,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=plan_price,
            tax_amount=Decimal('0.00'),
            discount_amount=discount_amount,
            total_amount=total_payable,
            payment_status='Unpaid',
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(invoice)
        db.session.flush()

        item = InvoiceItem(
            invoice_id=invoice.id,
            description=f"Membership Plan: {plan.name} ({plan.duration_days} days)",
            quantity=1,
            unit_price=plan_price,
            total_price=plan_price,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(item)

        # If payment made on renewal, record payment
        if amount_paid > Decimal('0.00'):
            cash_method = PaymentMethod.active().first()
            method_id = cash_method.id if cash_method else 1
            pay = Payment(
                invoice_id=invoice.id,
                payment_method_id=method_id,
                payment_date=date.today(),
                amount=amount_paid,
                transaction_reference='MEM-RENEWAL',
                notes='Paid upon renewal',
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(pay)
            db.session.flush()

        invoice.update_status()

        try:
            db.session.commit()
            log_action('CREATE', 'memberships', new_membership.id, None, {'plan': plan.name, 'end_date': str(end_date), 'invoice': invoice.invoice_number})
            flash(f"Membership renewed with '{plan.name}' until {end_date}! Invoice #{invoice.invoice_number} created.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error renewing membership: {e}", exc_info=True)
            flash("An error occurred while renewing membership.", "danger")
    else:
        for err in form.errors.values():
            flash(err[0], "danger")
    return redirect(url_for('members.view', id=member.id))
