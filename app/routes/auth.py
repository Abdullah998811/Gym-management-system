from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models.access import User, LoginLog, Role
from app.forms.auth import LoginForm, ChangePasswordForm, ProfileForm
from app.utils.audit import log_action
from app.utils.helpers import is_safe_url

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10/minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip()
        user = User.query.filter(
            ((User.username == identifier) | (User.email == identifier)) & 
            (User.is_deleted == False)
        ).first()

        ip_addr = request.remote_addr or '127.0.0.1'
        now = datetime.now(timezone.utc)

        if not user:
            flash("Invalid username or password.", "danger")
            return render_template('auth/login.html', form=form)

        # Check account lockout (15 minutes after 5 failed attempts)
        if user.is_locked():
            flash("Account is temporarily locked due to multiple failed login attempts. Please try again in 15 minutes.", "danger")
            log = LoginLog(user_id=user.id, ip_address=ip_addr, status='locked', failure_reason='Account locked')
            db.session.add(log)
            db.session.commit()
            return render_template('auth/login.html', form=form)

        if not user.check_password(form.password.data):
            user.failed_logins += 1
            reason = "Bad password"
            if user.failed_logins >= 5:
                user.locked_until = now + timedelta(minutes=15)
                reason = "Account locked after 5 failed attempts"
                flash("Too many failed attempts. Account has been locked for 15 minutes.", "danger")
            else:
                flash("Invalid username or password.", "danger")

            log = LoginLog(user_id=user.id, ip_address=ip_addr, status='failed', failure_reason=reason)
            db.session.add(log)
            db.session.commit()
            return render_template('auth/login.html', form=form)

        # Successful login
        user.failed_logins = 0
        user.locked_until = None
        user.last_login_at = now
        user.last_login_ip = ip_addr

        log = LoginLog(user_id=user.id, ip_address=ip_addr, status='success')
        db.session.add(log)
        db.session.commit()

        # Session fixate prevention: clear session before login_user
        session.clear()
        login_user(user, remember=form.remember_me.data)
        session.permanent = True
        session['last_active'] = now.isoformat()

        log_action('LOGIN', 'users', user.id, None, {'username': user.username, 'ip': ip_addr})

        if user.force_password_change:
            flash("Please change your temporary password to continue.", "warning")
            return redirect(url_for('auth.profile'))

        flash(f"Welcome back, {user.full_name}!", "success")
        next_page = request.args.get('next')
        if not is_safe_url(next_page):
            next_page = url_for('dashboard.index')
        return redirect(next_page)

    return render_template('auth/login.html', form=form)

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    log_action('LOGOUT', 'users', current_user.id)
    logout_user()
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile' and profile_form.validate_on_submit():
            old_data = {'full_name': current_user.full_name, 'email': current_user.email, 'phone': current_user.phone}
            current_user.full_name = profile_form.full_name.data.strip()
            current_user.email = profile_form.email.data.strip()
            current_user.phone = profile_form.phone.data.strip() if profile_form.phone.data else None
            try:
                db.session.commit()
                log_action('UPDATE', 'users', current_user.id, old_data, {
                    'full_name': current_user.full_name, 'email': current_user.email, 'phone': current_user.phone
                })
                flash("Your profile details have been updated.", "success")
                return redirect(url_for('auth.profile'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating profile: {e}", exc_info=True)
                flash("Error updating profile. Email may already be in use.", "danger")

        elif action == 'change_password' and password_form.validate_on_submit():
            if not current_user.check_password(password_form.current_password.data):
                flash("Current password entered is incorrect.", "danger")
            else:
                current_user.set_password(password_form.new_password.data)
                current_user.force_password_change = False
                try:
                    db.session.commit()
                    log_action('UPDATE', 'users', current_user.id, None, {'event': 'Password changed'})
                    flash("Your password has been changed successfully.", "success")
                    return redirect(url_for('auth.profile'))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error changing password: {e}", exc_info=True)
                    flash("An error occurred while changing your password.", "danger")

    return render_template('auth/profile.html', profile_form=profile_form, password_form=password_form)
