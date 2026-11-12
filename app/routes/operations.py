from datetime import datetime, date, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.operations import (
    Attendance, Locker, LockerAssignment, Visitor, Feedback, Complaint
)
from app.models.member import Member
from app.models.gym import Branch, Area
from app.forms.operations import (
    CheckInForm, LockerForm, AssignLockerForm, VisitorForm,
    FeedbackForm, ComplaintForm
)
from app.utils.decorators import role_required, ensure_member_access, get_current_member
from app.utils.audit import log_action
from app.utils.helpers import export_to_csv, stream_csv_response, today_pk

operations_bp = Blueprint('operations', __name__, url_prefix='/operations')

@operations_bp.route('/checkin', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def checkin():
    form = CheckInForm()
    branches = Branch.active().all()
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        ident = form.member_identifier.data.strip()
        member = Member.active().filter(
            or_(
                Member.membership_number.ilike(ident),
                Member.cnic == ident,
                Member.phone == ident,
                Member.email == ident
            )
        ).first()

        if not member:
            flash(f"No active member found matching '{ident}'.", "danger")
            return redirect(url_for('operations.checkin'))

        # Check membership status: block if not active unless Admin/Manager provides override logged in audit log
        override = request.form.get('staff_override') == '1'
        override_reason = request.form.get('override_reason', '').strip()

        if not member.active_membership:
            is_admin_or_mgr = current_user.role_name in ['Admin', 'Manager']
            if not is_admin_or_mgr or not override or not override_reason:
                flash(f"Access Denied: Member '{member.full_name}' does NOT have an active membership. Staff override with reason is required to check in.", "danger")
                return redirect(url_for('operations.checkin'))
            log_action('OVERRIDE_CHECKIN', 'attendance', member.id, None, {
                'member': member.full_name,
                'staff': current_user.username,
                'reason': override_reason
            })

        # Check if already checked in today without checking out
        today = today_pk()
        open_att = Attendance.active().filter_by(member_id=member.id, check_out_time=None).order_by(Attendance.check_in_time.desc()).first()
        if open_att:
            att_date = open_att.check_in_time.date() if hasattr(open_att.check_in_time, 'date') else None
            if att_date == today:
                flash(f"Member '{member.full_name}' is ALREADY checked in since {open_att.check_in_time.strftime('%I:%M %p')}.", "warning")
                return redirect(url_for('operations.checkin'))
            else:
                open_att.check_out_time = open_att.check_in_time + timedelta(hours=2)
                db.session.flush()

        att = Attendance(
            member_id=member.id,
            branch_id=form.branch_id.data,
            check_in_time=datetime.now(timezone.utc),
            method=form.method.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(att)
        try:
            db.session.commit()
            log_action('CREATE', 'attendance', att.id, None, {'member': member.full_name, 'method': att.method})
            flash(f"Check-in SUCCESS: Welcome {member.full_name} ({member.membership_number})!", "success")
            return redirect(url_for('operations.checkin'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error checking in: {e}", exc_info=True)
            flash("An error occurred during check-in.", "danger")

    recent_attendance = Attendance.active().options(joinedload(Attendance.member), joinedload(Attendance.branch)).order_by(Attendance.check_in_time.desc()).limit(20).all()
    return render_template('operations/checkin.html', form=form, recent_attendance=recent_attendance)

@operations_bp.route('/checkout/<int:id>', methods=['POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def checkout(id):
    att = Attendance.active().filter_by(id=id).first_or_404()
    if att.check_out_time:
        flash("Already checked out.", "info")
    else:
        att.check_out_time = datetime.now(timezone.utc)
        att.updated_by = current_user.id
        try:
            db.session.commit()
            flash(f"Member '{att.member.full_name}' checked out at {att.check_out_time.strftime('%I:%M %p')}.", "info")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error checking out: {e}", exc_info=True)
            flash("An error occurred during checkout.", "danger")

    return redirect(url_for('operations.checkin'))

@operations_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def export_csv():
    headers = ['ID', 'Member Name', 'Member #', 'Branch', 'Check In', 'Check Out', 'Method']
    def row_generator():
        records = Attendance.active().order_by(Attendance.check_in_time.desc()).limit(500).all()
        for a in records:
            yield [
                a.id,
                a.member.full_name if a.member else '',
                a.member.membership_number if a.member else '',
                a.branch.name if a.branch else '',
                a.check_in_time,
                a.check_out_time or 'Active in Gym',
                a.method
            ]
    return stream_csv_response(row_generator, headers, filename="gym_attendance.csv")

@operations_bp.route('/lockers', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def lockers():
    form = LockerForm()
    assign_form = AssignLockerForm()

    branches = Branch.active().all()
    areas = Area.active().all()
    all_lockers_list = Locker.active().all()
    members = Member.active().all()

    form.branch_id.choices = [(b.id, b.name) for b in branches]
    form.area_id.choices = [(a.id, a.name) for a in areas]

    assign_form.locker_id.choices = [(l.id, f"{l.locker_number} ({l.locker_type})" + (" [Occupied]" if l.is_occupied else "")) for l in all_lockers_list]
    assign_form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_locker' and form.validate_on_submit():
            l = Locker(
                branch_id=form.branch_id.data,
                area_id=form.area_id.data,
                locker_number=form.locker_number.data.strip().upper(),
                locker_type=form.locker_type.data,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(l)
            try:
                db.session.commit()
                flash(f"Locker '{l.locker_number}' added successfully!", "success")
                return redirect(url_for('operations.lockers'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error adding locker: {e}", exc_info=True)
                flash("An error occurred while adding the locker.", "danger")

        elif action == 'assign_locker' and assign_form.validate_on_submit():
            if assign_form.end_date.data <= assign_form.start_date.data:
                flash("Locker assignment end date must be strictly after start date.", "danger")
                return redirect(url_for('operations.lockers'))

            locker = db.session.query(Locker).filter(Locker.id == assign_form.locker_id.data, Locker.is_deleted == False).with_for_update().first()
            if not locker:
                flash("Locker not found.", "danger")
                return redirect(url_for('operations.lockers'))
            if locker.is_occupied:
                flash(f"Locker '{locker.locker_number}' is already occupied.", "danger")
                return redirect(url_for('operations.lockers'))

            la = LockerAssignment(
                locker_id=locker.id,
                member_id=assign_form.member_id.data,
                start_date=assign_form.start_date.data,
                end_date=assign_form.end_date.data,
                assignment_status='Active',
                created_by=current_user.id,
                updated_by=current_user.id
            )
            locker.is_occupied = True
            db.session.add(la)
            try:
                db.session.commit()
                flash(f"Locker '{locker.locker_number}' assigned to member!", "success")
                return redirect(url_for('operations.lockers'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error assigning locker: {e}", exc_info=True)
                flash("An error occurred while assigning the locker.", "danger")

    all_lockers = Locker.active().order_by(Locker.locker_number.asc()).all()
    assignments = LockerAssignment.active().filter_by(assignment_status='Active').all()
    return render_template('operations/lockers.html', form=form, assign_form=assign_form, lockers=all_lockers, assignments=assignments)

@operations_bp.route('/lockers/<int:id>/release', methods=['POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def locker_release(id):
    assignment = LockerAssignment.active().filter_by(id=id).first_or_404()
    assignment.assignment_status = 'Returned'
    assignment.updated_by = current_user.id

    if assignment.locker:
        assignment.locker.is_occupied = False

    try:
        db.session.commit()
        flash(f"Locker '{assignment.locker.locker_number}' has been released and is now available.", "info")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error releasing locker: {e}", exc_info=True)
        flash("An error occurred while releasing the locker.", "danger")

    return redirect(url_for('operations.lockers'))

@operations_bp.route('/visitors', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def visitors():
    form = VisitorForm()
    branches = Branch.active().all()
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        vis = Visitor(
            branch_id=form.branch_id.data,
            name=form.name.data.strip(),
            phone=form.phone.data.strip(),
            purpose=form.purpose.data.strip(),
            visit_date=form.visit_date.data,
            follow_up_status=form.follow_up_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(vis)
        try:
            db.session.commit()
            log_action('CREATE', 'visitors', vis.id, None, {'name': vis.name, 'phone': vis.phone})
            flash(f"Visitor '{vis.name}' logged successfully!", "success")
            return redirect(url_for('operations.visitors'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving visitor: {e}", exc_info=True)
            flash("An error occurred while logging the visitor.", "danger")

    all_visitors = Visitor.active().order_by(Visitor.visit_date.desc()).limit(20).all()
    return render_template('operations/visitors.html', form=form, visitors=all_visitors)

@operations_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    form = FeedbackForm()
    members = Member.active().all()
    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    curr_mem = get_current_member()
    if current_user.role_name == 'Member':
        if not curr_mem:
            abort(403)
        form.member_id.choices = [(curr_mem.id, curr_mem.full_name)]
        form.member_id.data = curr_mem.id

    if form.validate_on_submit():
        target_member_id = curr_mem.id if current_user.role_name == 'Member' else form.member_id.data
        ensure_member_access(target_member_id)
        fb = Feedback(
            member_id=target_member_id,
            rating=form.rating.data,
            comments=form.comments.data.strip(),
            feedback_date=date.today(),
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(fb)
        try:
            db.session.commit()
            flash("Thank you for your valuable feedback!", "success")
            return redirect(url_for('operations.feedback'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error recording feedback: {e}", exc_info=True)
            flash("An error occurred while saving your feedback.", "danger")

    query = Feedback.active()
    if current_user.role_name == 'Member':
        if curr_mem:
            query = query.filter_by(member_id=curr_mem.id)
        else:
            query = query.filter_by(id=-1)
    feedbacks = query.order_by(Feedback.id.desc()).all()
    return render_template('operations/feedback.html', form=form, feedbacks=feedbacks)

@operations_bp.route('/complaints', methods=['GET', 'POST'])
@login_required
def complaints():
    form = ComplaintForm()
    members = Member.active().all()
    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    curr_mem = get_current_member()
    if current_user.role_name == 'Member':
        if not curr_mem:
            abort(403)
        form.member_id.choices = [(curr_mem.id, curr_mem.full_name)]
        form.member_id.data = curr_mem.id

    if form.validate_on_submit():
        target_member_id = curr_mem.id if current_user.role_name == 'Member' else form.member_id.data
        ensure_member_access(target_member_id)
        cmp = Complaint(
            member_id=target_member_id,
            subject=form.subject.data.strip(),
            description=form.description.data.strip(),
            priority=form.priority.data,
            resolution_status=form.resolution_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(cmp)
        try:
            db.session.commit()
            log_action('CREATE', 'complaints', cmp.id, None, {'subject': cmp.subject})
            flash("Complaint registered. Our team will review and resolve it promptly.", "warning")
            return redirect(url_for('operations.complaints'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error filing complaint: {e}", exc_info=True)
            flash("An error occurred while submitting your complaint.", "danger")

    query = Complaint.active()
    if current_user.role_name == 'Member':
        if curr_mem:
            query = query.filter_by(member_id=curr_mem.id)
        else:
            query = query.filter_by(id=-1)
    all_complaints = query.order_by(Complaint.id.desc()).all()
    return render_template('operations/complaints.html', form=form, complaints=all_complaints)

@operations_bp.route('/complaints/<int:id>/resolve', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def complaint_resolve(id):
    cmp = Complaint.active().filter_by(id=id).first_or_404()
    cmp.resolution_status = 'Resolved'
    cmp.updated_by = current_user.id
    try:
        db.session.commit()
        flash(f"Complaint '{cmp.subject}' marked as Resolved.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating complaint: {e}", exc_info=True)
        flash("An error occurred while resolving the complaint.", "danger")
    return redirect(url_for('operations.complaints'))
