from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.operations import Notification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/', methods=['GET'])
@login_required
def index():
    notes = Notification.active().filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications/index.html', notifications=notes)

@notifications_bp.route('/<int:id>/read', methods=['POST'])
@login_required
def mark_read(id):
    note = Notification.active().filter_by(id=id, user_id=current_user.id).first_or_404()
    note.is_read = True
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.active().filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    try:
        db.session.commit()
        flash("All notifications marked as read.", "success")
    except Exception:
        db.session.rollback()
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/unread-count', methods=['GET'])
@login_required
def unread_count():
    count = Notification.active().filter_by(user_id=current_user.id, is_read=False).count()
    recent = Notification.active().filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    notes_data = [{'id': n.id, 'title': n.title, 'message': n.message, 'type': n.notification_type, 'created_at': n.created_at.strftime('%d %b %H:%M')} for n in recent]
    return jsonify({'count': count, 'notifications': notes_data})
