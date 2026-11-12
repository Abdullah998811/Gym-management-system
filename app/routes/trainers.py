from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.staff import (
    Trainer, TrainerSpecialization, Staff, StaffAttendance, Shift,
    ShiftAssignment, Payroll
)
from app.models.access import User, Role
from app.models.gym import Branch, Department
from app.forms.trainers import (
    TrainerForm, StaffForm, StaffAttendanceForm, ShiftForm,
    ShiftAssignmentForm, PayrollForm
)
from app.utils.decorators import role_required
from app.utils.audit import log_action
from app.utils.helpers import export_to_csv, stream_csv_response

trainers_bp = Blueprint('trainers', __name__, url_prefix='/trainers')

@trainers_bp.route('/', methods=['GET'])
@login_required
def index():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Trainer.active().join(User)
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (Trainer.specialization.ilike(f"%{search}%"))
        )

    pagination = query.order_by(Trainer.id.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'trainers/index.html',
        pagination=pagination,
        trainers=pagination.items,
        search=search
    )

@trainers_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def export_csv():
    headers = ['ID', 'Name', 'Email', 'Phone', 'Specialization', 'Experience (Yrs)', 'Hourly Rate (PKR)']
    def row_generator():
        trainers = Trainer.active().yield_per(100)
        for t in trainers:
            yield [
                t.id, t.full_name,
                t.user.email if t.user else '',
                t.user.phone if t.user else '',
                t.specialization,
                t.experience_years,
                t.hourly_rate
            ]
    return stream_csv_response(row_generator, headers, filename="trainers.csv")

@trainers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def create():
    form = TrainerForm()
    trainer_role = Role.query.filter_by(name='Trainer').first()
    users = User.active().filter(User.role_id == trainer_role.id).all() if trainer_role else []
    form.user_id.choices = [(u.id, f"{u.full_name} ({u.email})") for u in users]

    if form.validate_on_submit():
        existing = Trainer.query.filter_by(user_id=form.user_id.data).first()
        if existing and not existing.is_deleted:
            flash("This user is already registered as a trainer.", "danger")
            return render_template('trainers/create.html', form=form)

        rate = Decimal(str(form.hourly_rate.data))
        trainer = Trainer(
            user_id=form.user_id.data,
            specialization=form.specialization.data.strip(),
            experience_years=form.experience_years.data,
            hourly_rate=rate,
            bio=form.bio.data.strip() if form.bio.data else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(trainer)
        try:
            db.session.commit()
            log_action('CREATE', 'trainers', trainer.id, None, {'trainer': trainer.full_name})
            flash(f"Trainer '{trainer.full_name}' added successfully!", "success")
            return redirect(url_for('trainers.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating trainer: {e}", exc_info=True)
            flash("An error occurred while creating the trainer.", "danger")

    return render_template('trainers/create.html', form=form)

@trainers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def edit(id):
    trainer = Trainer.active().filter_by(id=id).first_or_404()
    form = TrainerForm(obj=trainer)
    trainer_role = Role.query.filter_by(name='Trainer').first()
    users = User.active().filter(User.role_id == trainer_role.id).all() if trainer_role else []
    form.user_id.choices = [(u.id, f"{u.full_name} ({u.email})") for u in users]

    if form.validate_on_submit():
        rate = Decimal(str(form.hourly_rate.data))
        trainer.user_id = form.user_id.data
        trainer.specialization = form.specialization.data.strip()
        trainer.experience_years = form.experience_years.data
        trainer.hourly_rate = rate
        trainer.bio = form.bio.data.strip() if form.bio.data else None
        trainer.updated_by = current_user.id

        try:
            db.session.commit()
            log_action('UPDATE', 'trainers', trainer.id, None, {'trainer': trainer.full_name})
            flash(f"Trainer '{trainer.full_name}' updated successfully.", "success")
            return redirect(url_for('trainers.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating trainer: {e}", exc_info=True)
            flash("An error occurred while updating the trainer.", "danger")

    return render_template('trainers/edit.html', form=form, trainer=trainer)

@trainers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def delete(id):
    trainer = Trainer.active().filter_by(id=id).first_or_404()
    trainer.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'trainers', trainer.id, {'trainer': trainer.full_name}, None)
        flash(f"Trainer '{trainer.full_name}' soft-deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting trainer: {e}", exc_info=True)
        flash("An error occurred while deleting the trainer.", "danger")
    return redirect(url_for('trainers.index'))

@trainers_bp.route('/staff', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def staff():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Staff.active().join(User)
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (Staff.job_title.ilike(f"%{search}%"))
        )

    pagination = query.order_by(Staff.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('trainers/staff.html', pagination=pagination, staff_list=pagination.items, search=search)

@trainers_bp.route('/staff-create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def staff_create():
    form = StaffForm()
    users = User.active().all()
    branches = Branch.active().all()
    departments = Department.active().all()

    form.user_id.choices = [(u.id, f"{u.full_name} ({u.role_name})") for u in users]
    form.branch_id.choices = [(b.id, b.name) for b in branches]
    form.department_id.choices = [(d.id, d.name) for d in departments]

    if form.validate_on_submit():
        salary_val = Decimal(str(form.salary.data))
        st = Staff(
            user_id=form.user_id.data,
            branch_id=form.branch_id.data,
            department_id=form.department_id.data,
            job_title=form.job_title.data.strip(),
            hire_date=form.hire_date.data,
            salary=salary_val,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(st)
        try:
            db.session.commit()
            log_action('CREATE', 'staff', st.id, None, {'staff': st.full_name})
            flash(f"Staff member '{st.full_name}' added successfully!", "success")
            return redirect(url_for('trainers.staff'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding staff: {e}", exc_info=True)
            flash("An error occurred while saving the staff member.", "danger")

    return render_template('trainers/staff_create.html', form=form)

@trainers_bp.route('/staff/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def staff_edit(id):
    st = Staff.active().filter_by(id=id).first_or_404()
    form = StaffForm(obj=st)
    users = User.active().all()
    branches = Branch.active().all()
    departments = Department.active().all()

    form.user_id.choices = [(u.id, f"{u.full_name} ({u.role_name})") for u in users]
    form.branch_id.choices = [(b.id, b.name) for b in branches]
    form.department_id.choices = [(d.id, d.name) for d in departments]

    if form.validate_on_submit():
        salary_val = Decimal(str(form.salary.data))
        st.user_id = form.user_id.data
        st.branch_id = form.branch_id.data
        st.department_id = form.department_id.data
        st.job_title = form.job_title.data.strip()
        st.hire_date = form.hire_date.data
        st.salary = salary_val
        st.updated_by = current_user.id

        try:
            db.session.commit()
            log_action('UPDATE', 'staff', st.id, None, {'staff': st.full_name})
            flash(f"Staff member '{st.full_name}' updated successfully.", "success")
            return redirect(url_for('trainers.staff'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating staff: {e}", exc_info=True)
            flash("An error occurred while updating the staff member.", "danger")

    return render_template('trainers/staff_edit.html', form=form, staff=st)

@trainers_bp.route('/staff/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def staff_delete(id):
    st = Staff.active().filter_by(id=id).first_or_404()
    st.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'staff', st.id, {'staff': st.full_name}, None)
        flash(f"Staff member '{st.full_name}' soft-deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting staff: {e}", exc_info=True)
        flash("An error occurred while deleting the staff member.", "danger")
    return redirect(url_for('trainers.staff'))

@trainers_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def attendance():
    form = StaffAttendanceForm()
    staff_members = Staff.active().all()
    form.staff_id.choices = [(s.id, s.full_name) for s in staff_members]

    if form.validate_on_submit():
        att = StaffAttendance(
            staff_id=form.staff_id.data,
            date=form.date.data,
            check_in_time=form.check_in_time.data,
            check_out_time=form.check_out_time.data,
            attendance_status=form.attendance_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(att)
        try:
            db.session.commit()
            flash("Staff attendance logged.", "success")
            return redirect(url_for('trainers.attendance'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error logging staff attendance: {e}", exc_info=True)
            flash("An error occurred while saving staff attendance.", "danger")

    records = StaffAttendance.active().order_by(StaffAttendance.date.desc()).limit(20).all()
    return render_template('trainers/attendance.html', form=form, records=records)

@trainers_bp.route('/shifts', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def shifts():
    form = ShiftForm()
    branches = Branch.active().all()
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        shift = Shift(
            branch_id=form.branch_id.data,
            name=form.name.data.strip(),
            start_time=form.start_time.data.strip(),
            end_time=form.end_time.data.strip(),
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(shift)
        try:
            db.session.commit()
            flash(f"Shift '{shift.name}' added successfully.", "success")
            return redirect(url_for('trainers.shifts'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating shift: {e}", exc_info=True)
            flash("An error occurred while creating the shift.", "danger")

    all_shifts = Shift.active().all()
    return render_template('trainers/shifts.html', form=form, shifts=all_shifts)

@trainers_bp.route('/payroll', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def payroll():
    form = PayrollForm()
    staff_members = Staff.active().all()
    form.staff_id.choices = [(s.id, f"{s.full_name} ({s.job_title})") for s in staff_members]

    if form.validate_on_submit():
        basic = Decimal(str(form.basic_salary.data))
        bonus = Decimal(str(form.bonus.data or 0.0))
        ded = Decimal(str(form.deductions.data or 0.0))
        net = basic + bonus - ded

        pr = Payroll(
            staff_id=form.staff_id.data,
            month_year=form.month_year.data.strip(),
            basic_salary=basic,
            bonus=bonus,
            deductions=ded,
            net_salary=net,
            payment_date=form.payment_date.data,
            payment_status=form.payment_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(pr)
        try:
            db.session.commit()
            log_action('CREATE', 'payroll', pr.id, None, {'staff_id': pr.staff_id, 'net': str(net)})
            flash(f"Payroll record of PKR {net:,.2f} recorded.", "success")
            return redirect(url_for('trainers.payroll'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving payroll: {e}", exc_info=True)
            flash("An error occurred while saving the payroll record.", "danger")

    records = Payroll.active().order_by(Payroll.payment_date.desc()).all()
    return render_template('trainers/payroll.html', form=form, records=records)
