from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, IntegerField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, Email

class VendorForm(FlaskForm):
    name = StringField('Vendor / Company Name', validators=[DataRequired(), Length(max=100)])
    contact_person = StringField('Contact Person', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=100)])
    address = StringField('Office Address', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Vendor')

class EquipmentCategoryForm(FlaskForm):
    name = StringField('Category Name (e.g. Cardio, Free Weights, Resistance)', validators=[DataRequired(), Length(max=100)])
    description = StringField('Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Category')

class EquipmentForm(FlaskForm):
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    vendor_id = SelectField('Vendor / Supplier', coerce=int, validators=[DataRequired()])
    area_id = SelectField('Location / Area', coerce=int, validators=[DataRequired()])
    name = StringField('Machine / Equipment Name', validators=[DataRequired(), Length(max=100)])
    serial_number = StringField('Serial Number / Asset Tag', validators=[DataRequired(), Length(max=100)])
    purchase_date = DateField('Purchase Date', default=date.today, validators=[DataRequired()])
    purchase_price = FloatField('Purchase Cost (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    warranty_expiry = DateField('Warranty Expiry Date', validators=[Optional()])
    condition_status = SelectField('Operational Condition', choices=[
        ('Excellent', 'Excellent'),
        ('Good', 'Good'),
        ('Maintenance Due', 'Maintenance Due'),
        ('Out of Order', 'Out of Order')
    ], default='Good')
    submit = SubmitField('Save Equipment')

class MaintenanceRecordForm(FlaskForm):
    equipment_id = SelectField('Equipment Asset', coerce=int, validators=[DataRequired()])
    maintenance_date = DateField('Service Date', default=date.today, validators=[DataRequired()])
    performed_by = StringField('Technician / Service Company', validators=[DataRequired(), Length(max=100)])
    cost = FloatField('Service Cost (PKR)', default=0.0, validators=[NumberRange(min=0.0)])
    notes = TextAreaField('Work Done & Parts Replaced', validators=[Optional()])
    next_due_date = DateField('Next Scheduled Due Date', validators=[DataRequired()])
    submit = SubmitField('Save Maintenance Log')

class EquipmentIssueForm(FlaskForm):
    equipment_id = SelectField('Equipment Asset', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Problem Description', validators=[DataRequired(), Length(min=5)])
    severity = SelectField('Severity Level', choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')], default='Medium')
    resolution_status = SelectField('Resolution Status', choices=[('Open', 'Open'), ('In Progress', 'In Progress'), ('Resolved', 'Resolved')], default='Open')
    submit = SubmitField('Report Issue')

class PurchaseOrderForm(FlaskForm):
    vendor_id = SelectField('Vendor', coerce=int, validators=[DataRequired()])
    expected_date = DateField('Expected Delivery Date', validators=[DataRequired()])
    total_amount = FloatField('Total Order Amount (PKR)', default=0.0, validators=[NumberRange(min=0.0)])
    order_status = SelectField('Status', choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')], default='Pending')
    submit = SubmitField('Create Purchase Order')
