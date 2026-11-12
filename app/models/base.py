from datetime import datetime, timezone
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_by = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    updated_by = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_by = db.Column(db.Integer, nullable=True)

    @classmethod
    def active(cls):
        """Returns active, non-deleted records."""
        return db.session.query(cls).filter(cls.is_deleted == False)

    def soft_delete(self, user_id=None):
        """Perform soft delete by marking is_deleted=True and updating status."""
        self.is_deleted = True
        self.status = 'inactive'
        self.deleted_by = user_id
        self.updated_by = user_id
        self.updated_at = utc_now()
