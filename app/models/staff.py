from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models.base import BaseModel

class Trainer(BaseModel):
    __tablename__ = 'trainers'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    specialization = db.Column(db.String(100), default='General Fitness', nullable=False)
    experience_years = db.Column(db.Integer, default=1, nullable=False)
    hourly_rate = db.Column(db.Numeric(12, 2), default=Decimal('1500.00'), nullable=False)
    bio = db.Column(db.Text, nullable=True)

    user = db.relationship('User', back_populates='trainer_record')
    specializations = db.relationship('TrainerSpecialization', back_populates='trainer', cascade='all, delete-orphan')
    certifications = db.relationship('TrainerCertification', back_populates='trainer', cascade='all, delete-orphan')
    classes = db.relationship('GymClass', back_populates='trainer')
    pt_sessions = db.relationship('PTSession', back_populates='trainer')
    workout_plans = db.relationship('WorkoutPlan', back_populates='trainer')

    @property
    def full_name(self):
        return self.user.full_name if self.user else "Unknown"

    def __repr__(self):
        return f"<Trainer {self.full_name}>"

class TrainerSpecialization(BaseModel):
    __tablename__ = 'trainer_specializations'

    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    proficiency_level = db.Column(db.String(50), default='Expert', nullable=False)

    trainer = db.relationship('Trainer', back_populates='specializations')

class TrainerCertification(BaseModel):
    __tablename__ = 'trainer_certifications'

    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    issuing_org = db.Column(db.String(150), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    certificate_url = db.Column(db.String(255), nullable=True)

    trainer = db.relationship('Trainer', back_populates='certifications')

class Staff(BaseModel):
    __tablename__ = 'staff'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    hire_date = db.Column(db.Date, default=date.today, nullable=False)
    salary = db.Column(db.Numeric(12, 2), default=Decimal('35000.00'), nullable=False)

    user = db.relationship('User', back_populates='staff_record')
    branch = db.relationship('Branch', back_populates='staff')
    department = db.relationship('Department', back_populates='staff')
    attendances = db.relationship('StaffAttendance', back_populates='staff', cascade='all, delete-orphan')
    shift_assignments = db.relationship('ShiftAssignment', back_populates='staff', cascade='all, delete-orphan')
    payrolls = db.relationship('Payroll', back_populates='staff', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return self.user.full_name if self.user else "Unknown Staff"

    def __repr__(self):
        return f"<Staff {self.full_name} ({self.job_title})>"

class StaffAttendance(BaseModel):
    __tablename__ = 'staff_attendance'

    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    check_in_time = db.Column(db.String(10), nullable=True)
    check_out_time = db.Column(db.String(10), nullable=True)
    attendance_status = db.Column(db.String(20), default='Present', nullable=False)  # Present, Late, Absent, Leave

    staff = db.relationship('Staff', back_populates='attendances')

class Shift(BaseModel):
    __tablename__ = 'shifts'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # Morning, Evening, Night
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)

    branch = db.relationship('Branch', back_populates='shifts')
    shift_assignments = db.relationship('ShiftAssignment', back_populates='shift', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Shift {self.name} ({self.start_time} - {self.end_time})>"

class ShiftAssignment(BaseModel):
    __tablename__ = 'shift_assignments'

    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id', ondelete='CASCADE'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    staff = db.relationship('Staff', back_populates='shift_assignments')
    shift = db.relationship('Shift', back_populates='shift_assignments')

class Payroll(BaseModel):
    __tablename__ = 'payroll'

    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id', ondelete='CASCADE'), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)  # e.g. "2026-11"
    basic_salary = db.Column(db.Numeric(12, 2), nullable=False)
    bonus = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    deductions = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    net_salary = db.Column(db.Numeric(12, 2), nullable=False)
    payment_date = db.Column(db.Date, default=date.today, nullable=False)
    payment_status = db.Column(db.String(20), default='Paid', nullable=False)  # Paid, Pending

    staff = db.relationship('Staff', back_populates='payrolls')
