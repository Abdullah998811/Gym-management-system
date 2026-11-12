from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.base import BaseModel, utc_now

class Role(BaseModel):
    __tablename__ = 'roles'

    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    users = db.relationship('User', back_populates='role')
    role_permissions = db.relationship('RolePermission', back_populates='role', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Role {self.name}>"

class Permission(BaseModel):
    __tablename__ = 'permissions'

    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    role_permissions = db.relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Permission {self.code}>"

class RolePermission(BaseModel):
    __tablename__ = 'role_permissions'

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)

    role = db.relationship('Role', back_populates='role_permissions')
    permission = db.relationship('Permission', back_populates='role_permissions')

class User(BaseModel, UserMixin):
    __tablename__ = 'users'

    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)

    # Security & Lockout attributes
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(50), nullable=True)
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    role = db.relationship('Role', back_populates='users')
    branch = db.relationship('Branch', back_populates='users')
    login_logs = db.relationship('LoginLog', back_populates='user', cascade='all, delete-orphan')
    member_record = db.relationship('Member', back_populates='user', uselist=False)
    staff_record = db.relationship('Staff', back_populates='user', uselist=False)
    trainer_record = db.relationship('Trainer', back_populates='user', uselist=False)
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        if self.locked_until:
            now = datetime.now(timezone.utc)
            if self.locked_until.tzinfo is None:
                # Handle naive datetime stored in SQLite
                return self.locked_until > datetime.now()
            return self.locked_until > now
        return False

    @property
    def role_name(self):
        return self.role.name if self.role else 'Guest'

    def has_role(self, *role_names):
        return self.role_name in role_names

    def __repr__(self):
        return f"<User {self.username} ({self.role_name})>"

class LoginLog(BaseModel):
    __tablename__ = 'login_logs'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False)  # success, failed, locked
    failure_reason = db.Column(db.String(100), nullable=True)

    user = db.relationship('User', back_populates='login_logs')
