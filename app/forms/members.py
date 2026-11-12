from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, FloatField, TextAreaField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
import re

def validate_cnic(form, field):
    if field.data:
        val = field.data.strip()
        cleaned = re.sub(r'[\s\-]', '', val)
        if not (len(cleaned) == 13 and cleaned.isdigit()):
            raise ValidationError("CNIC must be 13 digits (format: 42101-1234567-1 or 4210112345671).")

def validate_phone(form, field):
    if field.data:
        cleaned = re.sub(r'[\s\-+]', '', field.data)
        if not (10 <= len(cleaned) <= 15 and cleaned.isdigit()):
            raise ValidationError("Please enter a valid phone number (e.g. 03001234567).")

def validate_age(form, field):
    if field.data:
        today = date.today()
        age = today.year - field.data.year - ((today.month, today.day) < (field.data.month, field.data.day))
        if age < 12:
            raise ValidationError("Member must be at least 12 years of age.")
        if age > 100:
            raise ValidationError("Please check date of birth.")

class MemberForm(FlaskForm):
    branch_id = SelectField('Gym Branch', coerce=int, validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[DataRequired(), validate_phone])
    cnic = StringField('CNIC / National ID', validators=[DataRequired(), validate_cnic])
    dob = DateField('Date of Birth', validators=[DataRequired(), validate_age])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[DataRequired()])
    blood_group = SelectField('Blood Group', choices=[('', 'Select Blood Group'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')], validators=[Optional()])

    # Profile Fields
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    city = StringField('City', default='Lahore', validators=[Optional(), Length(max=50)])
    fitness_level = SelectField('Fitness Level', choices=[('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'), ('Advanced', 'Advanced')], default='Beginner')
    medical_conditions = TextAreaField('Medical Conditions / Injuries', validators=[Optional()])

    # User Account Options
    create_user = BooleanField('Create User Login Account (Role: Member)', default=False)
    temp_password = StringField('Temporary Password', validators=[Optional(), Length(min=6, max=50)])

    submit = SubmitField('Save Member')

class MemberMeasurementForm(FlaskForm):
    measurement_date = DateField('Date', default=date.today, validators=[DataRequired()])
    weight_kg = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=30.0, max=300.0, message="Weight must be between 30kg and 300kg.")])
    height_cm = FloatField('Height (cm)', validators=[DataRequired(), NumberRange(min=100.0, max=250.0, message="Height must be between 100cm and 250cm.")])
    chest_cm = FloatField('Chest (cm)', validators=[Optional(), NumberRange(min=50.0, max=200.0)])
    waist_cm = FloatField('Waist (cm)', validators=[Optional(), NumberRange(min=40.0, max=200.0)])
    hips_cm = FloatField('Hips (cm)', validators=[Optional(), NumberRange(min=50.0, max=200.0)])
    bicep_cm = FloatField('Bicep (cm)', validators=[Optional(), NumberRange(min=15.0, max=70.0)])
    body_fat_pct = FloatField('Body Fat (%)', validators=[Optional(), NumberRange(min=3.0, max=60.0)])
    submit = SubmitField('Record Measurement')

class MemberGoalForm(FlaskForm):
    goal_type = SelectField('Goal Type', choices=[
        ('Weight Loss', 'Weight Loss'),
        ('Muscle Gain', 'Muscle Gain'),
        ('Endurance & Stamina', 'Endurance & Stamina'),
        ('Strength & Power', 'Strength & Power'),
        ('Flexibility & Mobility', 'Flexibility & Mobility')
    ], validators=[DataRequired()])
    target_value = StringField('Target Goal (e.g. 75 kg or 100 kg Bench)', validators=[DataRequired(), Length(max=50)])
    current_value = StringField('Current Status', validators=[Optional(), Length(max=50)])
    target_date = DateField('Target Date', validators=[DataRequired()])
    submit = SubmitField('Set Goal')

class MemberNoteForm(FlaskForm):
    note_type = SelectField('Note Type', choices=[('General', 'General'), ('Health', 'Health / Medical'), ('Performance', 'Performance')], default='General')
    note_text = TextAreaField('Note', validators=[DataRequired(), Length(min=3)])
    submit = SubmitField('Add Note')

class EmergencyContactForm(FlaskForm):
    name = StringField('Contact Name', validators=[DataRequired(), Length(min=2, max=100)])
    relationship = StringField('Relationship (e.g. Spouse, Father, Friend)', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone', validators=[DataRequired(), validate_phone])
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Contact')

class MemberFreezeForm(FlaskForm):
    start_date = DateField('Freeze Start Date', default=date.today, validators=[DataRequired()])
    end_date = DateField('Freeze End Date', validators=[DataRequired()])
    reason = StringField('Reason for Freeze', validators=[DataRequired(), Length(min=5, max=255)])
    submit = SubmitField('Freeze Membership')

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data <= self.start_date.data:
            raise ValidationError("Freeze end date must be after start date.")

class MemberRenewForm(FlaskForm):
    plan_id = SelectField('Membership Plan', coerce=int, validators=[DataRequired()])
    amount_paid = FloatField('Amount Paid (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    discount_code = StringField('Promotion / Discount Code', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Process Renewal')
