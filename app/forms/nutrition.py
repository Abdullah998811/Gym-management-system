from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, IntegerField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class MealForm(FlaskForm):
    name = StringField('Meal Name', validators=[DataRequired(), Length(max=100)])
    meal_time = SelectField('Meal Type', choices=[('Breakfast', 'Breakfast'), ('Lunch', 'Lunch'), ('Snack', 'Snack'), ('Dinner', 'Dinner')], default='Breakfast')
    calories = IntegerField('Calories (kcal)', default=450, validators=[DataRequired(), NumberRange(min=0, max=5000)])
    protein_g = FloatField('Protein (g)', default=30.0, validators=[DataRequired(), NumberRange(min=0)])
    carbs_g = FloatField('Carbohydrates (g)', default=40.0, validators=[DataRequired(), NumberRange(min=0)])
    fats_g = FloatField('Fats (g)', default=12.0, validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Ingredients & Preparation', validators=[Optional()])
    submit = SubmitField('Save Meal')

class DietPlanForm(FlaskForm):
    title = StringField('Diet Plan Title', validators=[DataRequired(), Length(max=100)])
    goal = StringField('Nutritional Goal (e.g. Muscle Hypertrophy)', validators=[DataRequired(), Length(max=100)])
    daily_calories = IntegerField('Daily Target Calories', default=2200, validators=[DataRequired(), NumberRange(min=500, max=10000)])
    description = TextAreaField('Plan Guidelines', validators=[Optional()])
    submit = SubmitField('Save Diet Plan')

class AssignDietPlanForm(FlaskForm):
    member_id = SelectField('Select Member', coerce=int, validators=[DataRequired()])
    diet_plan_id = SelectField('Select Diet Plan', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Diet Plan')

class SupplementForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    brand = StringField('Brand / Manufacturer', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Category', choices=[('Whey Protein', 'Whey Protein'), ('Creatine', 'Creatine'), ('Pre-Workout', 'Pre-Workout'), ('Amino Acids (BCAA)', 'Amino Acids (BCAA)'), ('Multivitamins', 'Multivitamins'), ('Other', 'Other')], default='Whey Protein')
    price = FloatField('Retail Price (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    stock_quantity = IntegerField('Stock Quantity', default=20, validators=[DataRequired(), NumberRange(min=0)])
    expiry_date = DateField('Expiry Date', validators=[DataRequired()])
    submit = SubmitField('Save Supplement')

class SupplementSaleForm(FlaskForm):
    supplement_id = SelectField('Supplement Product', coerce=int, validators=[DataRequired()])
    member_id = SelectField('Purchasing Member', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired(), NumberRange(min=1)])
    unit_price = FloatField('Unit Price (PKR)', validators=[DataRequired(), NumberRange(min=0.0)])
    submit = SubmitField('Record Sale')
