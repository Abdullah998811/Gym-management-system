from app.extensions import db
from app.models.base import BaseModel

class Branch(BaseModel):
    __tablename__ = 'branches'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, default=200, nullable=False)

    users = db.relationship('User', back_populates='branch')
    departments = db.relationship('Department', back_populates='branch', cascade='all, delete-orphan')
    facilities = db.relationship('Facility', back_populates='branch', cascade='all, delete-orphan')
    areas = db.relationship('Area', back_populates='branch', cascade='all, delete-orphan')
    operating_hours = db.relationship('OperatingHour', back_populates='branch', cascade='all, delete-orphan')
    holidays = db.relationship('Holiday', back_populates='branch', cascade='all, delete-orphan')
    members = db.relationship('Member', back_populates='branch')
    staff = db.relationship('Staff', back_populates='branch')
    shifts = db.relationship('Shift', back_populates='branch')
    gym_classes = db.relationship('GymClass', back_populates='branch')
    expenses = db.relationship('Expense', back_populates='branch')
    attendances = db.relationship('Attendance', back_populates='branch')
    lockers = db.relationship('Locker', back_populates='branch')
    visitors = db.relationship('Visitor', back_populates='branch')

    def __repr__(self):
        return f"<Branch {self.name} ({self.code})>"

class Department(BaseModel):
    __tablename__ = 'departments'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    branch = db.relationship('Branch', back_populates='departments')
    staff = db.relationship('Staff', back_populates='department')

    def __repr__(self):
        return f"<Department {self.name}>"

class Facility(BaseModel):
    __tablename__ = 'facilities'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_operational = db.Column(db.Boolean, default=True, nullable=False)

    branch = db.relationship('Branch', back_populates='facilities')
    areas = db.relationship('Area', back_populates='facility', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Facility {self.name}>"

class Area(BaseModel):
    __tablename__ = 'areas'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    floor = db.Column(db.String(50), default='Ground', nullable=False)
    max_capacity = db.Column(db.Integer, default=50, nullable=False)

    branch = db.relationship('Branch', back_populates='areas')
    facility = db.relationship('Facility', back_populates='areas')
    equipment = db.relationship('Equipment', back_populates='area')
    class_schedules = db.relationship('ClassSchedule', back_populates='area')
    lockers = db.relationship('Locker', back_populates='area')

    def __repr__(self):
        return f"<Area {self.name}>"

class OperatingHour(BaseModel):
    __tablename__ = 'operating_hours'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    opening_time = db.Column(db.String(10), default='06:00', nullable=False)
    closing_time = db.Column(db.String(10), default='22:00', nullable=False)
    is_closed = db.Column(db.Boolean, default=False, nullable=False)

    branch = db.relationship('Branch', back_populates='operating_hours')

class Holiday(BaseModel):
    __tablename__ = 'holidays'

    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    branch = db.relationship('Branch', back_populates='holidays')
