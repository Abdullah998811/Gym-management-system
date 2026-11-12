from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class GymClassForm(FlaskForm):
    class_type_id = SelectField('Class Type', coerce=int, validators=[DataRequired()])
    trainer_id = SelectField('Instructor / Trainer', coerce=int, validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    title = StringField('Class Title', validators=[DataRequired(), Length(min=2, max=100)])
    max_capacity = IntegerField('Maximum Capacity', default=20, validators=[DataRequired(), NumberRange(min=1, max=200)])
    difficulty_level = SelectField('Difficulty', choices=[('All Levels', 'All Levels'), ('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'), ('Advanced', 'Advanced')], default='All Levels')
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Class')

class ClassScheduleForm(FlaskForm):
    class_id = SelectField('Gym Class', coerce=int, validators=[DataRequired()])
    area_id = SelectField('Room / Area', coerce=int, validators=[DataRequired()])
    day_of_week = SelectField('Day of Week', choices=[
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')
    ], validators=[DataRequired()])
    start_time = StringField('Start Time (e.g. 07:00)', default='07:00', validators=[DataRequired(), Length(max=10)])
    end_time = StringField('End Time (e.g. 08:00)', default='08:00', validators=[DataRequired(), Length(max=10)])
    submit = SubmitField('Add Schedule')

class BookClassForm(FlaskForm):
    class_id = SelectField('Select Class', coerce=int, validators=[DataRequired()])
    member_id = SelectField('Select Member', coerce=int, validators=[DataRequired()])
    schedule_id = SelectField('Schedule Slot', coerce=int, validators=[Optional()])
    booking_date = DateField('Date of Class', default=date.today, validators=[DataRequired()])
    submit = SubmitField('Book Spot')

class PTSessionForm(FlaskForm):
    trainer_id = SelectField('Personal Trainer', coerce=int, validators=[DataRequired()])
    member_id = SelectField('Member', coerce=int, validators=[DataRequired()])
    session_date = DateField('Session Date', default=date.today, validators=[DataRequired()])
    start_time = StringField('Start Time (e.g. 15:00)', default='15:00', validators=[DataRequired()])
    duration_minutes = IntegerField('Duration (Minutes)', default=60, validators=[DataRequired(), NumberRange(min=15, max=180)])
    focus_area = StringField('Focus Area', default='Strength & Conditioning', validators=[DataRequired(), Length(max=100)])
    notes = TextAreaField('Training Notes', validators=[Optional()])
    session_status = SelectField('Status', choices=[('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Scheduled')
    submit = SubmitField('Schedule PT Session')

class WorkoutPlanForm(FlaskForm):
    trainer_id = SelectField('Created By (Trainer)', coerce=int, validators=[DataRequired()])
    title = StringField('Plan Title', validators=[DataRequired(), Length(max=100)])
    goal = StringField('Target Goal', validators=[DataRequired(), Length(max=100)])
    duration_weeks = IntegerField('Duration (Weeks)', default=8, validators=[DataRequired(), NumberRange(min=1, max=52)])
    description = TextAreaField('Overview / Instructions', validators=[Optional()])
    submit = SubmitField('Create Workout Plan')

class AssignWorkoutPlanForm(FlaskForm):
    member_id = SelectField('Select Member', coerce=int, validators=[DataRequired()])
    plan_id = SelectField('Select Workout Plan', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Plan to Member')
