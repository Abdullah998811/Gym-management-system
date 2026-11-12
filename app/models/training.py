from datetime import date
from app.extensions import db
from app.models.base import BaseModel

class ClassType(BaseModel):
    __tablename__ = 'class_types'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    intensity_level = db.Column(db.String(50), default='Moderate', nullable=False)  # Low, Moderate, High, Extreme

    classes = db.relationship('GymClass', back_populates='class_type', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ClassType {self.name}>"

class GymClass(BaseModel):
    __tablename__ = 'classes'

    class_type_id = db.Column(db.Integer, db.ForeignKey('class_types.id'), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    max_capacity = db.Column(db.Integer, default=20, nullable=False)
    difficulty_level = db.Column(db.String(50), default='All Levels', nullable=False)

    class_type = db.relationship('ClassType', back_populates='classes')
    trainer = db.relationship('Trainer', back_populates='classes')
    branch = db.relationship('Branch', back_populates='gym_classes')
    schedules = db.relationship('ClassSchedule', back_populates='gym_class', cascade='all, delete-orphan')
    bookings = db.relationship('ClassBooking', back_populates='gym_class', cascade='all, delete-orphan')
    waitlists = db.relationship('ClassWaitlist', back_populates='gym_class', cascade='all, delete-orphan')
    attendances = db.relationship('ClassAttendance', back_populates='gym_class', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<GymClass {self.title}>"

class ClassSchedule(BaseModel):
    __tablename__ = 'class_schedules'

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)

    gym_class = db.relationship('GymClass', back_populates='schedules')
    area = db.relationship('Area', back_populates='class_schedules')
    bookings = db.relationship('ClassBooking', back_populates='schedule')

class ClassBooking(BaseModel):
    __tablename__ = 'class_bookings'
    __table_args__ = (
        db.UniqueConstraint('class_id', 'member_id', 'booking_date', name='uq_class_booking_member_date'),
    )

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('class_schedules.id'), nullable=True)
    booking_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    booking_status = db.Column(db.String(20), default='Confirmed', nullable=False, index=True)  # Confirmed, Cancelled

    gym_class = db.relationship('GymClass', back_populates='bookings')
    member = db.relationship('Member', back_populates='class_bookings')
    schedule = db.relationship('ClassSchedule', back_populates='bookings')

class ClassWaitlist(BaseModel):
    __tablename__ = 'class_waitlist'

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    booking_date = db.Column(db.Date, default=date.today, nullable=False)
    request_date = db.Column(db.Date, default=date.today, nullable=False)
    priority = db.Column(db.Integer, default=1, nullable=False)

    gym_class = db.relationship('GymClass', back_populates='waitlists')
    member = db.relationship('Member', back_populates='class_waitlists')

class ClassAttendance(BaseModel):
    __tablename__ = 'class_attendance'

    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    attendance_status = db.Column(db.String(20), default='Attended', nullable=False)  # Attended, Missed

    gym_class = db.relationship('GymClass', back_populates='attendances')
    member = db.relationship('Member', back_populates='class_attendances')

class PTSession(BaseModel):
    __tablename__ = 'pt_sessions'

    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    session_date = db.Column(db.Date, default=date.today, nullable=False)
    start_time = db.Column(db.String(10), default='10:00', nullable=False)
    duration_minutes = db.Column(db.Integer, default=60, nullable=False)
    focus_area = db.Column(db.String(100), default='Full Body Strength', nullable=False)
    notes = db.Column(db.Text, nullable=True)
    session_status = db.Column(db.String(20), default='Scheduled', nullable=False)  # Scheduled, Completed, Cancelled

    trainer = db.relationship('Trainer', back_populates='pt_sessions')
    member = db.relationship('Member', back_populates='pt_sessions')

class ExerciseCategory(BaseModel):
    __tablename__ = 'exercise_categories'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    exercises = db.relationship('Exercise', back_populates='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ExerciseCategory {self.name}>"

class Exercise(BaseModel):
    __tablename__ = 'exercises'

    category_id = db.Column(db.Integer, db.ForeignKey('exercise_categories.id'), nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    target_muscle = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), default='Intermediate', nullable=False)

    category = db.relationship('ExerciseCategory', back_populates='exercises')
    workout_plan_exercises = db.relationship('WorkoutPlanExercise', back_populates='exercise', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Exercise {self.name}>"

class WorkoutPlan(BaseModel):
    __tablename__ = 'workout_plans'

    trainer_id = db.Column(db.Integer, db.ForeignKey('trainers.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    goal = db.Column(db.String(100), nullable=False)  # Muscle hypertrophy, Fat loss, Conditioning
    duration_weeks = db.Column(db.Integer, default=8, nullable=False)
    description = db.Column(db.Text, nullable=True)

    trainer = db.relationship('Trainer', back_populates='workout_plans')
    plan_exercises = db.relationship('WorkoutPlanExercise', back_populates='workout_plan', cascade='all, delete-orphan')
    member_workout_plans = db.relationship('MemberWorkoutPlan', back_populates='workout_plan', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<WorkoutPlan {self.title}>"

class WorkoutPlanExercise(BaseModel):
    __tablename__ = 'workout_plan_exercises'

    plan_id = db.Column(db.Integer, db.ForeignKey('workout_plans.id', ondelete='CASCADE'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    day_number = db.Column(db.Integer, default=1, nullable=False)  # Day 1, Day 2, etc.
    sets = db.Column(db.Integer, default=4, nullable=False)
    reps = db.Column(db.String(20), default='10-12', nullable=False)
    rest_seconds = db.Column(db.Integer, default=60, nullable=False)

    workout_plan = db.relationship('WorkoutPlan', back_populates='plan_exercises')
    exercise = db.relationship('Exercise', back_populates='workout_plan_exercises')

class MemberWorkoutPlan(BaseModel):
    __tablename__ = 'member_workout_plans'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('workout_plans.id', ondelete='CASCADE'), nullable=False)
    assigned_date = db.Column(db.Date, default=date.today, nullable=False)
    is_current = db.Column(db.Boolean, default=True, nullable=False)

    member = db.relationship('Member', back_populates='member_workout_plans')
    workout_plan = db.relationship('WorkoutPlan', back_populates='member_workout_plans')
