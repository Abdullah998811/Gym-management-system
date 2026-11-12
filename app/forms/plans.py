from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, IntegerField, TextAreaField, BooleanField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError

class MembershipPlanForm(FlaskForm):
    name = StringField('Plan Name', validators=[DataRequired(), Length(min=2, max=100)])
    plan_type = SelectField('Billing Cycle', choices=[
        ('Monthly', 'Monthly (30 Days)'),
        ('Quarterly', 'Quarterly (90 Days)'),
        ('Biannual', 'Biannual (180 Days)'),
        ('Annual', 'Annual (365 Days)')
    ], validators=[DataRequired()])
    duration_days = IntegerField('Duration (Days)', default=30, validators=[DataRequired(), NumberRange(min=1, max=1000)])
    price = FloatField('Price (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    max_classes_per_week = IntegerField('Max Classes / Week', default=5, validators=[DataRequired(), NumberRange(min=0, max=50)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Plan')

class PlanFeatureForm(FlaskForm):
    feature_name = StringField('Feature Name (e.g. Free Sauna Access)', validators=[DataRequired(), Length(max=100)])
    is_included = BooleanField('Included in Plan', default=True)
    submit = SubmitField('Add Feature')

class PromotionForm(FlaskForm):
    code = StringField('Promo Code (e.g. FIT2026)', validators=[DataRequired(), Length(min=3, max=50)])
    title = StringField('Campaign Title', validators=[DataRequired(), Length(max=100)])
    discount_pct = FloatField('Discount Percentage (%)', default=10.0, validators=[DataRequired(), NumberRange(min=1.0, max=100.0)])
    start_date = DateField('Start Date', default=date.today, validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    max_uses = IntegerField('Max Total Redemptions', default=100, validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save Promotion')

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError("End date cannot be earlier than start date.")

class AssignMembershipForm(FlaskForm):
    member_id = SelectField('Select Member', coerce=int, validators=[DataRequired()])
    plan_id = SelectField('Select Plan', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', default=date.today, validators=[DataRequired()])
    price_paid = FloatField('Price Paid (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    auto_renew = BooleanField('Auto-Renew upon expiration')
    submit = SubmitField('Assign Membership')
