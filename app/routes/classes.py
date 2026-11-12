from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.training import (
    ClassType, GymClass, ClassSchedule, ClassBooking, ClassWaitlist,
    ClassAttendance, PTSession, WorkoutPlan, WorkoutPlanExercise, MemberWorkoutPlan
)
from app.models.staff import Trainer
from app.models.gym import Branch, Area
from app.models.member import Member
from app.forms.classes import (
    GymClassForm, ClassScheduleForm, BookClassForm, PTSessionForm,
    WorkoutPlanForm, AssignWorkoutPlanForm
)
from app.utils.decorators import role_required, ensure_member_access, get_current_member
from app.utils.audit import log_action
from app.utils.helpers import export_to_csv, stream_csv_response, today_pk

classes_bp = Blueprint('classes', __name__, url_prefix='/classes')

@classes_bp.route('/', methods=['GET'])
@login_required
def index():
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = GymClass.active().options(joinedload(GymClass.class_type), joinedload(GymClass.trainer))
    if search:
        query = query.filter(
            (GymClass.title.ilike(f"%{search}%")) |
            (GymClass.difficulty_level.ilike(f"%{search}%"))
        )

    pagination = query.order_by(GymClass.id.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'classes/index.html',
        pagination=pagination,
        classes=pagination.items,
        search=search
    )

@classes_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def export_csv():
    headers = ['ID', 'Title', 'Class Type', 'Trainer', 'Capacity', 'Difficulty', 'Branch']
    def row_generator():
        classes = GymClass.active().yield_per(100)
        for c in classes:
            yield [
                c.id, c.title,
                c.class_type.name if c.class_type else '',
                c.trainer.full_name if c.trainer else '',
                c.max_capacity,
                c.difficulty_level,
                c.branch.name if c.branch else ''
            ]
    return stream_csv_response(row_generator, headers, filename="gym_classes.csv")

@classes_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def create():
    form = GymClassForm()
    types = ClassType.active().all()
    trainers = Trainer.active().all()
    branches = Branch.active().all()

    form.class_type_id.choices = [(t.id, t.name) for t in types]
    form.trainer_id.choices = [(tr.id, tr.full_name) for tr in trainers]
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        gc = GymClass(
            class_type_id=form.class_type_id.data,
            trainer_id=form.trainer_id.data,
            branch_id=form.branch_id.data,
            title=form.title.data.strip(),
            max_capacity=form.max_capacity.data,
            difficulty_level=form.difficulty_level.data,
            description=form.description.data.strip() if form.description.data else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(gc)
        try:
            db.session.commit()
            log_action('CREATE', 'classes', gc.id, None, {'title': gc.title})
            flash(f"Class '{gc.title}' created successfully!", "success")
            return redirect(url_for('classes.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating class: {e}", exc_info=True)
            flash("An error occurred while creating the class.", "danger")

    return render_template('classes/create.html', form=form)

@classes_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def edit(id):
    gc = GymClass.active().filter_by(id=id).first_or_404()
    form = GymClassForm(obj=gc)
    types = ClassType.active().all()
    trainers = Trainer.active().all()
    branches = Branch.active().all()

    form.class_type_id.choices = [(t.id, t.name) for t in types]
    form.trainer_id.choices = [(tr.id, tr.full_name) for tr in trainers]
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        gc.class_type_id = form.class_type_id.data
        gc.trainer_id = form.trainer_id.data
        gc.branch_id = form.branch_id.data
        gc.title = form.title.data.strip()
        gc.max_capacity = form.max_capacity.data
        gc.difficulty_level = form.difficulty_level.data
        gc.description = form.description.data.strip() if form.description.data else None
        gc.updated_by = current_user.id

        try:
            db.session.commit()
            log_action('UPDATE', 'classes', gc.id, None, {'title': gc.title})
            flash(f"Class '{gc.title}' updated successfully.", "success")
            return redirect(url_for('classes.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating class: {e}", exc_info=True)
            flash("An error occurred while updating the class.", "danger")

    return render_template('classes/edit.html', form=form, gym_class=gc)

@classes_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def delete(id):
    gc = GymClass.active().filter_by(id=id).first_or_404()
    gc.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'classes', gc.id, {'title': gc.title}, None)
        flash(f"Class '{gc.title}' soft-deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting class: {e}", exc_info=True)
        flash("An error occurred while deleting the class.", "danger")
    return redirect(url_for('classes.index'))

@classes_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def schedule():
    form = ClassScheduleForm()
    classes = GymClass.active().all()
    areas = Area.active().all()

    form.class_id.choices = [(c.id, c.title) for c in classes]
    form.area_id.choices = [(a.id, f"{a.name} ({a.facility.name if a.facility else 'Main'})") for a in areas]

    if form.validate_on_submit():
        start_t = form.start_time.data.strip()
        end_t = form.end_time.data.strip()
        if end_t <= start_t:
            flash("Class schedule end time must be after start time.", "danger")
            return redirect(url_for('classes.schedule'))

        cs = ClassSchedule(
            class_id=form.class_id.data,
            area_id=form.area_id.data,
            day_of_week=form.day_of_week.data,
            start_time=start_t,
            end_time=end_t,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(cs)
        try:
            db.session.commit()
            flash("Class schedule slot added successfully.", "success")
            return redirect(url_for('classes.schedule'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating schedule: {e}", exc_info=True)
            flash("An error occurred while saving the class schedule.", "danger")

    schedules = ClassSchedule.active().all()
    return render_template('classes/schedule.html', form=form, schedules=schedules)

@classes_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    form = BookClassForm()
    classes = GymClass.active().all()
    members = Member.active().all()

    form.class_id.choices = [(c.id, f"{c.title} (Max: {c.max_capacity})") for c in classes]
    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    # Pre-select member if logged in as Member
    if current_user.role_name == 'Member':
        user_member = get_current_member()
        if user_member:
            if request.method == 'POST':
                submitted_member_id = request.form.get('member_id', type=int)
                if submitted_member_id and submitted_member_id != user_member.id:
                    abort(403)
            form.member_id.choices = [(user_member.id, user_member.full_name)]
            form.member_id.data = user_member.id

    if form.validate_on_submit():
        target_member_id = user_member.id if (current_user.role_name == 'Member' and user_member) else form.member_id.data
        ensure_member_access(target_member_id)

        target_member = Member.active().filter_by(id=target_member_id).first_or_404()

        # Enforce active membership check
        if not target_member.active_membership:
            flash("Member must have an active membership to book classes.", "danger")
            return redirect(url_for('classes.book'))

        booking_dt = form.booking_date.data
        today = today_pk()

        # Reject booking dates in the past
        if booking_dt < today:
            flash("Class booking date cannot be in the past.", "danger")
            return redirect(url_for('classes.book'))

        # Enforce capacity inside a transaction with row lock
        gc = db.session.query(GymClass).filter(GymClass.id == form.class_id.data, GymClass.is_deleted == False).with_for_update().first()
        if not gc:
            abort(404)

        # Check existing confirmed booking for this member on this date
        existing_booking = ClassBooking.active().filter_by(
            class_id=gc.id,
            member_id=target_member.id,
            booking_date=booking_dt
        ).first()

        if existing_booking and existing_booking.booking_status == 'Confirmed':
            flash("You already have a confirmed booking for this class on this date.", "warning")
            return redirect(url_for('classes.book'))

        # Check capacity
        current_confirmed = ClassBooking.active().filter_by(
            class_id=gc.id,
            booking_date=booking_dt,
            booking_status='Confirmed'
        ).count()

        if current_confirmed >= gc.max_capacity:
            # Capacity reached -> add to waitlist for THIS date
            existing_wl = ClassWaitlist.active().filter_by(
                class_id=gc.id,
                member_id=target_member.id,
                booking_date=booking_dt
            ).first()

            if existing_wl:
                flash("You are already on the waitlist for this class on this date.", "info")
                return redirect(url_for('classes.book'))

            max_p = db.session.query(func.coalesce(func.max(ClassWaitlist.priority), 0)).filter(
                ClassWaitlist.class_id == gc.id,
                ClassWaitlist.booking_date == booking_dt,
                ClassWaitlist.is_deleted == False
            ).scalar()
            waitlist_pos = max_p + 1

            wl = ClassWaitlist(
                class_id=gc.id,
                member_id=target_member.id,
                booking_date=booking_dt,
                request_date=today,
                priority=waitlist_pos,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(wl)
            try:
                db.session.commit()
                flash(f"Class is fully booked! You have been placed on the Waitlist for {booking_dt} (Priority #{waitlist_pos}).", "info")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error adding to waitlist: {e}", exc_info=True)
                flash("An error occurred while joining the waitlist.", "danger")
            return redirect(url_for('classes.book'))

        # Space available: create or reactivate confirmed booking
        if existing_booking:
            existing_booking.booking_status = 'Confirmed'
            existing_booking.schedule_id = form.schedule_id.data if form.schedule_id.data else None
            existing_booking.updated_by = current_user.id
            booking_obj = existing_booking
        else:
            booking_obj = ClassBooking(
                class_id=gc.id,
                member_id=target_member.id,
                schedule_id=form.schedule_id.data if form.schedule_id.data else None,
                booking_date=booking_dt,
                booking_status='Confirmed',
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(booking_obj)

        try:
            db.session.commit()
            log_action('CREATE', 'class_bookings', booking_obj.id, None, {'class': gc.title, 'member_id': target_member.id})
            flash(f"Class spot confirmed for '{gc.title}' on {booking_dt}!", "success")
            return redirect(url_for('classes.book'))
        except IntegrityError:
            db.session.rollback()
            flash("You already have a booking for this class on this date.", "warning")
            return redirect(url_for('classes.book'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error booking class: {e}", exc_info=True)
            flash("An error occurred while confirming your booking.", "danger")

    query = ClassBooking.active().options(joinedload(ClassBooking.gym_class), joinedload(ClassBooking.member), joinedload(ClassBooking.schedule))
    if current_user.role_name == 'Member':
        user_mem = get_current_member()
        if user_mem:
            query = query.filter_by(member_id=user_mem.id)
        else:
            query = query.filter_by(id=-1)
    bookings = query.order_by(ClassBooking.booking_date.desc()).limit(15).all()
    return render_template('classes/bookings.html', form=form, bookings=bookings)

@classes_bp.route('/cancel-booking/<int:id>', methods=['POST'])
@login_required
def cancel_booking(id):
    booking = ClassBooking.active().filter_by(id=id).first_or_404()
    ensure_member_access(booking.member)

    booking.booking_status = 'Cancelled'
    booking.updated_by = current_user.id

    # Recompute capacity before promoting
    curr_confirmed = ClassBooking.active().filter_by(
        class_id=booking.class_id,
        booking_date=booking.booking_date,
        booking_status='Confirmed'
    ).count()

    promoted_msg = ""
    if curr_confirmed < booking.gym_class.max_capacity:
        # Promote next waitlist candidate for the SAME class AND SAME date, ordered by priority
        next_wl = ClassWaitlist.active().filter_by(
            class_id=booking.class_id,
            booking_date=booking.booking_date
        ).order_by(ClassWaitlist.priority.asc()).first()

        if next_wl:
            existing_p = ClassBooking.query.filter_by(
                class_id=next_wl.class_id,
                member_id=next_wl.member_id,
                booking_date=booking.booking_date,
                is_deleted=False
            ).first()

            if existing_p:
                existing_p.booking_status = 'Confirmed'
                existing_p.schedule_id = booking.schedule_id
                existing_p.updated_by = current_user.id
            else:
                promoted_booking = ClassBooking(
                    class_id=next_wl.class_id,
                    member_id=next_wl.member_id,
                    schedule_id=booking.schedule_id,
                    booking_date=booking.booking_date,
                    booking_status='Confirmed',
                    created_by=current_user.id,
                    updated_by=current_user.id
                )
                db.session.add(promoted_booking)

            next_wl.soft_delete(current_user.id)
            promoted_msg = " The next member on the waitlist for this date was automatically promoted to confirmed!"

    try:
        db.session.commit()
        flash(f"Booking cancelled successfully.{promoted_msg}", "info")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling booking: {e}", exc_info=True)
        flash("An error occurred while cancelling the booking.", "danger")

    return redirect(url_for('classes.book'))

@classes_bp.route('/pt-sessions', methods=['GET', 'POST'])
@login_required
def pt_sessions():
    is_staff = current_user.role_name in ['Admin', 'Manager', 'Trainer', 'Receptionist']
    curr_mem = get_current_member()

    if not is_staff and current_user.role_name != 'Member':
        abort(403)

    # Member can only view their own; cannot POST schedule for others
    if current_user.role_name == 'Member' and request.method == 'POST':
        abort(403)

    form = PTSessionForm()
    trainers = Trainer.active().all()
    members = Member.active().all()

    form.trainer_id.choices = [(t.id, t.full_name) for t in trainers]
    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    if is_staff and form.validate_on_submit():
        def parse_time_minutes(t_val):
            if isinstance(t_val, str):
                parts = t_val.strip().split(':')
                return int(parts[0]) * 60 + int(parts[1])
            elif hasattr(t_val, 'hour'):
                return t_val.hour * 60 + t_val.minute
            return 0

        req_start_m = parse_time_minutes(form.start_time.data)
        req_end_m = req_start_m + int(form.duration_minutes.data)

        # Detect overlapping ranges for the SAME trainer OR the SAME member
        existing_sessions = PTSession.active().filter(
            PTSession.session_date == form.session_date.data,
            PTSession.session_status != 'Cancelled',
            (PTSession.trainer_id == form.trainer_id.data) | (PTSession.member_id == form.member_id.data)
        ).all()

        conflict = None
        for s in existing_sessions:
            s_start_m = parse_time_minutes(s.start_time)
            s_end_m = s_start_m + (s.duration_minutes or 60)
            if req_start_m < s_end_m and s_start_m < req_end_m:
                if s.trainer_id == form.trainer_id.data:
                    conflict = f"Trainer is already booked during this time slot ({s.start_time} for {s.duration_minutes} mins)."
                else:
                    conflict = f"Member already has a PT session scheduled during this time slot ({s.start_time} for {s.duration_minutes} mins)."
                break

        if conflict:
            flash(f"Schedule conflict: {conflict}", "danger")
            return redirect(url_for('classes.pt_sessions'))

        session_obj = PTSession(
            trainer_id=form.trainer_id.data,
            member_id=form.member_id.data,
            session_date=form.session_date.data,
            start_time=form.start_time.data.strip(),
            duration_minutes=form.duration_minutes.data,
            focus_area=form.focus_area.data.strip(),
            notes=form.notes.data.strip() if form.notes.data else None,
            session_status=form.session_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(session_obj)
        try:
            db.session.commit()
            log_action('CREATE', 'pt_sessions', session_obj.id, None, {'trainer_id': session_obj.trainer_id, 'member_id': session_obj.member_id})
            flash("Personal training session scheduled successfully!", "success")
            return redirect(url_for('classes.pt_sessions'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error booking PT session: {e}", exc_info=True)
            flash("An error occurred while scheduling personal training session.", "danger")

    query = PTSession.active()
    if current_user.role_name == 'Member':
        if curr_mem:
            query = query.filter_by(member_id=curr_mem.id)
        else:
            query = query.filter_by(id=-1)

    sessions = query.order_by(PTSession.session_date.desc()).limit(20).all()
    return render_template('classes/pt_sessions.html', form=form, sessions=sessions)

@classes_bp.route('/workouts', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer')
def workouts():
    form = WorkoutPlanForm()
    trainers = Trainer.active().all()
    form.trainer_id.choices = [(t.id, t.full_name) for t in trainers]

    assign_form = AssignWorkoutPlanForm()
    plans = WorkoutPlan.active().all()
    members = Member.active().all()
    assign_form.plan_id.choices = [(p.id, p.title) for p in plans]
    assign_form.member_id.choices = [(m.id, m.full_name) for m in members]

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_plan' and form.validate_on_submit():
            plan = WorkoutPlan(
                trainer_id=form.trainer_id.data,
                title=form.title.data.strip(),
                goal=form.goal.data.strip(),
                duration_weeks=form.duration_weeks.data,
                description=form.description.data.strip() if form.description.data else None,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(plan)
            try:
                db.session.commit()
                flash(f"Workout plan '{plan.title}' created!", "success")
                return redirect(url_for('classes.workouts'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving workout plan: {e}", exc_info=True)
                flash("An error occurred while saving the workout plan.", "danger")

        elif action == 'assign_plan' and assign_form.validate_on_submit():
            for prev in MemberWorkoutPlan.active().filter_by(member_id=assign_form.member_id.data).all():
                prev.is_current = False

            mwp = MemberWorkoutPlan(
                member_id=assign_form.member_id.data,
                plan_id=assign_form.plan_id.data,
                assigned_date=date.today(),
                is_current=True,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(mwp)
            try:
                db.session.commit()
                flash("Workout plan assigned to member successfully!", "success")
                return redirect(url_for('classes.workouts'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error assigning plan: {e}", exc_info=True)
                flash("An error occurred while assigning the workout plan.", "danger")

    return render_template('classes/workouts.html', form=form, assign_form=assign_form, plans=plans)
