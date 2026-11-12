from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models.base import BaseModel

class Meal(BaseModel):
    __tablename__ = 'meals'

    name = db.Column(db.String(100), nullable=False)
    meal_time = db.Column(db.String(50), default='Breakfast', nullable=False)  # Breakfast, Lunch, Snack, Dinner
    calories = db.Column(db.Integer, default=400, nullable=False)
    protein_g = db.Column(db.Float, default=30.0, nullable=False)
    carbs_g = db.Column(db.Float, default=40.0, nullable=False)
    fats_g = db.Column(db.Float, default=10.0, nullable=False)
    description = db.Column(db.Text, nullable=True)

    diet_plan_meals = db.relationship('DietPlanMeal', back_populates='meal', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Meal {self.name} ({self.calories} kcal)>"

class DietPlan(BaseModel):
    __tablename__ = 'diet_plans'

    title = db.Column(db.String(100), nullable=False)
    goal = db.Column(db.String(100), nullable=False)  # High Protein, Keto, Caloric Deficit
    daily_calories = db.Column(db.Integer, default=2200, nullable=False)
    description = db.Column(db.Text, nullable=True)

    diet_plan_meals = db.relationship('DietPlanMeal', back_populates='diet_plan', cascade='all, delete-orphan')
    member_diet_plans = db.relationship('MemberDietPlan', back_populates='diet_plan', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<DietPlan {self.title}>"

class DietPlanMeal(BaseModel):
    __tablename__ = 'diet_plan_meals'

    diet_plan_id = db.Column(db.Integer, db.ForeignKey('diet_plans.id', ondelete='CASCADE'), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey('meals.id'), nullable=False)
    day_of_week = db.Column(db.String(20), default='Monday', nullable=False)

    diet_plan = db.relationship('DietPlan', back_populates='diet_plan_meals')
    meal = db.relationship('Meal', back_populates='diet_plan_meals')

class MemberDietPlan(BaseModel):
    __tablename__ = 'member_diet_plans'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    diet_plan_id = db.Column(db.Integer, db.ForeignKey('diet_plans.id', ondelete='CASCADE'), nullable=False)
    assigned_date = db.Column(db.Date, default=date.today, nullable=False)
    is_current = db.Column(db.Boolean, default=True, nullable=False)

    member = db.relationship('Member', back_populates='member_diet_plans')
    diet_plan = db.relationship('DietPlan', back_populates='member_diet_plans')

class Supplement(BaseModel):
    __tablename__ = 'supplements'

    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Protein', nullable=False)  # Whey, Creatine, Pre-workout, Vitamins
    price = db.Column(db.Numeric(12, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=50, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)

    sales = db.relationship('SupplementSale', back_populates='supplement', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Supplement {self.name} - {self.brand}>"

class SupplementSale(BaseModel):
    __tablename__ = 'supplement_sales'

    supplement_id = db.Column(db.Integer, db.ForeignKey('supplements.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    sale_date = db.Column(db.Date, default=date.today, nullable=False)

    supplement = db.relationship('Supplement', back_populates='sales')
    member = db.relationship('Member', back_populates='supplement_sales')
