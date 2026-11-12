from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import session, redirect, url_for, flash, abort, request, current_app
from flask_login import current_user, logout_user

def role_required(*allowed_roles):
    """Decorator to enforce role-based access control."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.path))

            # Admin has full access to all roles
            user_role = getattr(current_user, 'role_name', None)
            if user_role == 'Admin':
                return f(*args, **kwargs)

            if user_role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_member():
    """Retrieve the Member record linked to current_user, if any."""
    if not current_user.is_authenticated:
        return None
    from app.models.member import Member
    if hasattr(current_user, 'member_record') and current_user.member_record:
        if not current_user.member_record.is_deleted:
            return current_user.member_record
    return Member.active().filter_by(user_id=current_user.id).first()

def ensure_member_access(member_or_id):
    """
    Ensure the current user is authorized to access the given member's record.
    Staff roles (Admin, Manager, Trainer, Receptionist) have access to all members.
    Member role can only access their own record.
    Raises 403 Forbidden if unauthorized.
    """
    if not current_user.is_authenticated:
        abort(403)

    role = getattr(current_user, 'role_name', None)
    if role in ('Admin', 'Manager', 'Trainer', 'Receptionist'):
        return True

    curr_mem = get_current_member()
    if not curr_mem:
        abort(403)

    target_id = member_or_id.id if hasattr(member_or_id, 'id') else int(member_or_id)
    if curr_mem.id != target_id:
        abort(403)

    return True

def check_inactivity_timeout():
    """Check if the user's session has exceeded the inactivity threshold."""
    if current_user.is_authenticated:
        now = datetime.now(timezone.utc)
        last_active = session.get('last_active')
        if last_active:
            try:
                last_time = datetime.fromisoformat(last_active)
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                timeout = current_app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(minutes=30))
                if now - last_time > timeout:
                    logout_user()
                    session.clear()
                    flash("Your session has expired due to inactivity. Please log in again.", "info")
                    return redirect(url_for('auth.login', next=request.path))
            except (ValueError, TypeError):
                pass
        session['last_active'] = now.isoformat()
    return None
