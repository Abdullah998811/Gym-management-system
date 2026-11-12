from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
import re

def validate_phone(form, field):
    if field.data:
        cleaned = re.sub(r'[\s\-+]', '', field.data)
        if not (10 <= len(cleaned) <= 15 and cleaned.isdigit()):
            raise ValidationError("Please provide a valid phone number.")

class CheckInForm(FlaskForm):
    member_identifier = StringField('Member ID, CNIC or Phone', validators=[DataRequired(), Length(min=3, max=100)])
    branch_id = SelectField('Gym Branch', coerce=int, validators=[DataRequired()])
    method = SelectField('Check-in Method', choices=[('Manual', 'Manual Desk Entry'), ('QR', 'QR Code Scan'), ('RFID', 'RFID Card / Keyfob')], default='Manual')
    submit = SubmitField('Process Check-In')

class LockerForm(FlaskForm):
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    area_id = SelectField('Area / Locker Room', coerce=int, validators=[DataRequired()])
    locker_number = StringField('Locker Number (e.g. L-101)', validators=[DataRequired(), Length(max=20)])
    locker_type = SelectField('Locker Type', choices=[('Standard', 'Standard'), ('VIP', 'VIP Executive')], default='Standard')
    submit = SubmitField('Save Locker')

class AssignLockerForm(FlaskForm):
    locker_id = SelectField('Select Available Locker', coerce=int, validators=[DataRequired()])
    member_id = SelectField('Select Member', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', default=date.today, validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Assign Locker')

class VisitorForm(FlaskForm):
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    name = StringField('Visitor Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), validate_phone])
    purpose = StringField('Purpose of Visit', default='Gym Tour & Membership Query', validators=[DataRequired(), Length(max=100)])
    visit_date = DateField('Visit Date', default=date.today, validators=[DataRequired()])
    follow_up_status = SelectField('Status', choices=[('Interested', 'Interested'), ('Joined', 'Joined'), ('Not Interested', 'Not Interested')], default='Interested')
    submit = SubmitField('Log Visitor')

class FeedbackForm(FlaskForm):
    member_id = SelectField('Member', coerce=int, validators=[DataRequired()])
    rating = SelectField('Overall Rating (1 to 5 Stars)', coerce=int, choices=[(5, '5 - Outstanding'), (4, '4 - Good'), (3, '3 - Average'), (2, '2 - Poor'), (1, '1 - Terrible')], default=5)
    comments = TextAreaField('Feedback & Comments', validators=[DataRequired(), Length(min=5)])
    submit = SubmitField('Submit Feedback')

class ComplaintForm(FlaskForm):
    member_id = SelectField('Member', coerce=int, validators=[DataRequired()])
    subject = StringField('Complaint Subject', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Detailed Issue Description', validators=[DataRequired(), Length(min=10)])
    priority = SelectField('Priority Level', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Urgent', 'Urgent')], default='Medium')
    resolution_status = SelectField('Status', choices=[('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Resolved', 'Resolved')], default='Pending')
    submit = SubmitField('File Complaint')
