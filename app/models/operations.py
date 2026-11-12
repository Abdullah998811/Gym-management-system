from datetime import datetime, date
from app.extensions import db
from app.models.base import BaseModel, utc_now

class Attendance(BaseModel):
    __tablename__ = 'attendance'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False, index=True)
    check_in_time = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)
    check_out_time = db.Column(db.DateTime, nullable=True, index=True)
    method = db.Column(db.String(20), default='Manual', nullable=False)  # Manual, QR, RFID

    member = db.relationship('Member', back_populates='attendances')
    branch = db.relationship('Branch', back_populates='attendances')

    def __repr__(self):
        return f"<Attendance Member #{self.member_id} at {self.check_in_time}>"

class Locker(BaseModel):
    __tablename__ = 'lockers'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    locker_number = db.Column(db.String(20), nullable=False)
    locker_type = db.Column(db.String(50), default='Standard', nullable=False)  # Standard, VIP
    is_occupied = db.Column(db.Boolean, default=False, nullable=False)

    branch = db.relationship('Branch', back_populates='lockers')
    area = db.relationship('Area', back_populates='lockers')
    assignments = db.relationship('LockerAssignment', back_populates='locker', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Locker {self.locker_number}>"

class LockerAssignment(BaseModel):
    __tablename__ = 'locker_assignments'

    locker_id = db.Column(db.Integer, db.ForeignKey('lockers.id', ondelete='CASCADE'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    start_date = db.Column(db.Date, default=date.today, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    assignment_status = db.Column(db.String(20), default='Active', nullable=False)  # Active, Expired, Returned

    locker = db.relationship('Locker', back_populates='assignments')
    member = db.relationship('Member', back_populates='locker_assignments')

class Visitor(BaseModel):
    __tablename__ = 'visitors'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.String(100), default='Gym Tour & Inquiry', nullable=False)
    visit_date = db.Column(db.Date, default=date.today, nullable=False)
    follow_up_status = db.Column(db.String(50), default='Interested', nullable=False)  # Interested, Joined, Not Interested

    branch = db.relationship('Branch', back_populates='visitors')

class Feedback(BaseModel):
    __tablename__ = 'feedback'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, default=5, nullable=False)  # 1 to 5
    comments = db.Column(db.Text, nullable=False)
    feedback_date = db.Column(db.Date, default=date.today, nullable=False)

    member = db.relationship('Member', back_populates='feedbacks')

class Complaint(BaseModel):
    __tablename__ = 'complaints'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium', nullable=False)  # Low, Medium, High, Urgent
    resolution_status = db.Column(db.String(20), default='Pending', nullable=False)  # Pending, In Progress, Resolved

    member = db.relationship('Member', back_populates='complaints')

class Notification(BaseModel):
    __tablename__ = 'notifications'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(20), default='info', nullable=False)  # info, warning, danger, success
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)

    user = db.relationship('User', back_populates='notifications')

    def __repr__(self):
        return f"<Notification {self.title} to User #{self.user_id}>"

class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.Text, nullable=True)
    new_values = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False)

    user = db.relationship('User', back_populates='audit_logs')

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.table_name}>"
