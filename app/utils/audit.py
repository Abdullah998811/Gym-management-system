import json
from datetime import datetime, date
from flask import request, current_app
from flask_login import current_user
from app.extensions import db
from app.models.operations import AuditLog

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)

def log_action(action, table_name, record_id=None, old_values=None, new_values=None):
    """
    Stage an AuditLog row in the current SQLAlchemy session.
    Committed in the SAME transaction as the parent database change.
    """
    try:
        user_id = current_user.id if (current_user and current_user.is_authenticated) else None
        ip_addr = request.remote_addr if request else '127.0.0.1'

        old_str = json.dumps(old_values, default=json_serial) if old_values is not None else None
        new_str = json.dumps(new_values, default=json_serial) if new_values is not None else None

        log = AuditLog(
            user_id=user_id,
            action=action.upper(),
            table_name=table_name,
            record_id=record_id,
            old_values=old_str,
            new_values=new_str,
            ip_address=ip_addr,
            created_by=user_id,
            updated_by=user_id
        )
        db.session.add(log)
        return log
    except Exception as e:
        if current_app:
            current_app.logger.exception("Failed to prepare audit log for table %s: %s", table_name, e)
        return None
