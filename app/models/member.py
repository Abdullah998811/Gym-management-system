from datetime import date, datetime
from app.extensions import db
from app.models.base import BaseModel

class Member(BaseModel):
    __tablename__ = 'members'
    __table_args__ = (
        db.Index(
            'ix_members_email_active',
            'email',
            unique=True,
            postgresql_where=db.text('is_deleted = false'),
            sqlite_where=db.text('is_deleted = 0')
        ),
        db.Index(
            'ix_members_cnic_active',
            'cnic',
            unique=True,
            postgresql_where=db.text('is_deleted = false'),
            sqlite_where=db.text('is_deleted = 0')
        ),
    )

    membership_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)

    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    cnic = db.Column(db.String(20), nullable=False, index=True)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Male, Female, Other
    blood_group = db.Column(db.String(10), nullable=True)
    join_date = db.Column(db.Date, default=date.today, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='member_record')
    branch = db.relationship('Branch', back_populates='members')
    profile = db.relationship('MemberProfile', back_populates='member', uselist=False, cascade='all, delete-orphan')
    emergency_contacts = db.relationship('EmergencyContact', back_populates='member', cascade='all, delete-orphan')
    documents = db.relationship('MemberDocument', back_populates='member', cascade='all, delete-orphan')
    measurements = db.relationship('MemberMeasurement', back_populates='member', cascade='all, delete-orphan')
    goals = db.relationship('MemberGoal', back_populates='member', cascade='all, delete-orphan')
    notes = db.relationship('MemberNote', back_populates='member', cascade='all, delete-orphan')
    memberships = db.relationship('Membership', back_populates='member')
    member_promotions = db.relationship('MemberPromotion', back_populates='member')
    class_bookings = db.relationship('ClassBooking', back_populates='member')
    class_waitlists = db.relationship('ClassWaitlist', back_populates='member')
    class_attendances = db.relationship('ClassAttendance', back_populates='member')
    pt_sessions = db.relationship('PTSession', back_populates='member')
    member_workout_plans = db.relationship('MemberWorkoutPlan', back_populates='member')
    member_diet_plans = db.relationship('MemberDietPlan', back_populates='member')
    supplement_sales = db.relationship('SupplementSale', back_populates='member')
    invoices = db.relationship('Invoice', back_populates='member')
    attendances = db.relationship('Attendance', back_populates='member')
    locker_assignments = db.relationship('LockerAssignment', back_populates='member')
    feedbacks = db.relationship('Feedback', back_populates='member')
    complaints = db.relationship('Complaint', back_populates='member')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def active_membership(self):
        from app.utils.helpers import today_pk
        from app.models.plan import Membership, MembershipFreeze
        today = today_pk()

        # Query DB directly (ordered by end_date desc, limit 1) avoiding full Python iteration
        m = Membership.query.filter(
            Membership.member_id == self.id,
            Membership.is_deleted == False,
            Membership.status.in_(['active', 'frozen']),
            Membership.start_date <= today,
            Membership.end_date >= today
        ).order_by(Membership.end_date.desc()).first()

        if not m:
            return None

        # Date-aware check: a membership is frozen only when today is inside an approved freeze window
        is_currently_frozen = MembershipFreeze.query.filter(
            MembershipFreeze.membership_id == m.id,
            MembershipFreeze.is_deleted == False,
            MembershipFreeze.status.in_(['active', 'approved', 'Active', 'Approved']),
            MembershipFreeze.start_date <= today,
            MembershipFreeze.end_date >= today
        ).first() is not None

        if is_currently_frozen:
            return None
        return m

    def __repr__(self):
        return f"<Member {self.full_name} ({self.membership_number})>"

class MemberProfile(BaseModel):
    __tablename__ = 'member_profiles'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    occupation = db.Column(db.String(100), nullable=True)
    fitness_level = db.Column(db.String(50), default='Beginner', nullable=False)  # Beginner, Intermediate, Advanced
    medical_conditions = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True)

    member = db.relationship('Member', back_populates='profile')

class EmergencyContact(BaseModel):
    __tablename__ = 'emergency_contacts'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=True)

    member = db.relationship('Member', back_populates='emergency_contacts')

class MemberDocument(BaseModel):
    __tablename__ = 'member_documents'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # ID Card, Medical Cert, Agreement
    file_path = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.Date, default=date.today, nullable=False)

    member = db.relationship('Member', back_populates='documents')

class MemberMeasurement(BaseModel):
    __tablename__ = 'member_measurements'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    measurement_date = db.Column(db.Date, default=date.today, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    height_cm = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    chest_cm = db.Column(db.Float, nullable=True)
    waist_cm = db.Column(db.Float, nullable=True)
    hips_cm = db.Column(db.Float, nullable=True)
    bicep_cm = db.Column(db.Float, nullable=True)
    body_fat_pct = db.Column(db.Float, nullable=True)

    member = db.relationship('Member', back_populates='measurements')

    @staticmethod
    def calculate_bmi(weight_kg, height_cm):
        if not weight_kg or not height_cm or height_cm <= 0:
            return 0.0
        height_m = height_cm / 100.0
        return round(weight_kg / (height_m * height_m), 1)

class MemberGoal(BaseModel):
    __tablename__ = 'member_goals'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    goal_type = db.Column(db.String(50), nullable=False)  # Weight Loss, Muscle Gain, Endurance
    target_value = db.Column(db.String(50), nullable=False)
    current_value = db.Column(db.String(50), nullable=True)
    target_date = db.Column(db.Date, nullable=False)
    achieved = db.Column(db.Boolean, default=False, nullable=False)

    member = db.relationship('Member', back_populates='goals')

class MemberNote(BaseModel):
    __tablename__ = 'member_notes'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='General', nullable=False)  # General, Health, Performance

    member = db.relationship('Member', back_populates='notes')
    author = db.relationship('User')
