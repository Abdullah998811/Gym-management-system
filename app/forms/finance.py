from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class InvoiceForm(FlaskForm):
    member_id = SelectField('Member', coerce=int, validators=[DataRequired()])
    discount_id = SelectField('Apply Discount Voucher', coerce=int, validators=[Optional()])
    issue_date = DateField('Issue Date', default=date.today, validators=[DataRequired()])
    due_date = DateField('Payment Due Date', validators=[DataRequired()])
    description = StringField('Invoice Item Description', default='Gym Monthly Subscription & Facilities', validators=[DataRequired(), Length(max=255)])
    subtotal = FloatField('Subtotal Amount (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    tax_amount = FloatField('Tax Amount (PKR)', default=0.0, validators=[NumberRange(min=0.0)])
    submit = SubmitField('Generate Invoice')

class PaymentForm(FlaskForm):
    invoice_id = SelectField('Invoice #', coerce=int, validators=[DataRequired()])
    payment_method_id = SelectField('Payment Method', coerce=int, validators=[DataRequired()])
    amount = FloatField('Payment Amount (PKR)', validators=[DataRequired(), NumberRange(min=1.0)])
    payment_date = DateField('Payment Date', default=date.today, validators=[DataRequired()])
    transaction_reference = StringField('Transaction / Receipt Reference', validators=[Optional(), Length(max=100)])
    notes = StringField('Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Payment')

class ExpenseForm(FlaskForm):
    category_id = SelectField('Expense Category', coerce=int, validators=[DataRequired()])
    branch_id = SelectField('Branch', coerce=int, validators=[DataRequired()])
    title = StringField('Expense Title / Purpose', validators=[DataRequired(), Length(max=100)])
    amount = FloatField('Expense Amount (PKR)', validators=[DataRequired(), NumberRange(min=1.0)])
    expense_date = DateField('Expense Date', default=date.today, validators=[DataRequired()])
    paid_to = StringField('Paid To (Vendor/Person)', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Record Expense')

class DiscountForm(FlaskForm):
    code = StringField('Discount Code', validators=[DataRequired(), Length(max=50)])
    title = StringField('Discount Title', validators=[DataRequired(), Length(max=100)])
    amount_type = SelectField('Discount Type', choices=[('percentage', 'Percentage (%)'), ('fixed', 'Fixed Amount (PKR)')], default='percentage')
    value = FloatField('Discount Value', validators=[DataRequired(), NumberRange(min=0.0)])
    submit = SubmitField('Save Discount')
