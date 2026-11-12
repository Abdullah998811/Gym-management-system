from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, IntegerField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class TrainerForm(FlaskForm):
    user_id = SelectField('Select User Account', coerce=int, validators=[DataRequired()])
    specialization = StringField('Specialization (e.g. Strength, HIIT, Yoga)', validators=[DataRequired(), Length(max=100)])
    experience_years = IntegerField('Years of Experience', default=2, validators=[DataRequired(), NumberRange(min=0, max=50)])
    hourly_rate = FloatField('Hourly PT Rate (PKR)', default=2000.0, validators=[DataRequired(), NumberRange(min=0.0)])
    bio = TextAreaField('Trainer Biography', validators=[Optional()])
    submit = SubmitField('Save Trainer')

class StaffForm(FlaskForm):
    user_id = SelectField('Select User Account', coerce=int, validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    job_title = StringField('Job Title (e.g. Receptionist, Floor Supervisor)', validators=[DataRequired(), Length(max=100)])
    hire_date = DateField('Hire Date', default=date.today, validators=[DataRequired()])
    salary = FloatField('Monthly Salary (PKR)', default=40000.0, validators=[DataRequired(), NumberRange(min=0.0)])
    submit = SubmitField('Save Staff Member')

class StaffAttendanceForm(FlaskForm):
    staff_id = SelectField('Staff Member', coerce=int, validators=[DataRequired()])
    date = DateField('Date', default=date.today, validators=[DataRequired()])
    check_in_time = StringField('Check-in Time (HH:MM)', default='09:00', validators=[DataRequired()])
    check_out_time = StringField('Check-out Time (HH:MM)', default='17:00', validators=[Optional()])
    attendance_status = SelectField('Status', choices=[('Present', 'Present'), ('Late', 'Late'), ('Absent', 'Absent'), ('Leave', 'Leave')], default='Present')
    submit = SubmitField('Log Attendance')

class ShiftForm(FlaskForm):
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    name = StringField('Shift Name (e.g. Morning Shift)', validators=[DataRequired(), Length(max=50)])
    start_time = StringField('Start Time (e.g. 06:00)', validators=[DataRequired(), Length(max=10)])
    end_time = StringField('End Time (e.g. 14:00)', validators=[DataRequired(), Length(max=10)])
    submit = SubmitField('Save Shift')

class ShiftAssignmentForm(FlaskForm):
    staff_id = SelectField('Staff Member', coerce=int, validators=[DataRequired()])
    shift_id = SelectField('Shift', coerce=int, validators=[DataRequired()])
    date = DateField('Date', default=date.today, validators=[DataRequired()])
    notes = StringField('Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Assign Shift')

class PayrollForm(FlaskForm):
    staff_id = SelectField('Staff Member', coerce=int, validators=[DataRequired()])
    month_year = StringField('Month & Year (YYYY-MM)', validators=[DataRequired(), Length(min=7, max=7)])
    basic_salary = FloatField('Basic Salary (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    bonus = FloatField('Bonus (PKR)', default=0.0, validators=[NumberRange(min=0.0)])
    deductions = FloatField('Deductions (PKR)', default=0.0, validators=[NumberRange(min=0.0)])
    payment_date = DateField('Payment Date', default=date.today, validators=[DataRequired()])
    payment_status = SelectField('Status', choices=[('Paid', 'Paid'), ('Pending', 'Pending')], default='Paid')
    submit = SubmitField('Process Payroll')
