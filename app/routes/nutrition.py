from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.nutrition import (
    Meal, DietPlan, DietPlanMeal, MemberDietPlan, Supplement, SupplementSale
)
from app.models.member import Member
from app.forms.nutrition import (
    MealForm, DietPlanForm, AssignDietPlanForm, SupplementForm, SupplementSaleForm
)
from app.utils.decorators import role_required, get_current_member, ensure_member_access
from app.utils.audit import log_action
from app.utils.helpers import export_to_csv, stream_csv_response, today_pk

nutrition_bp = Blueprint('nutrition', __name__, url_prefix='/nutrition')

@nutrition_bp.route('/', methods=['GET'])
@login_required
def index():
    meals = Meal.active().all()
    diet_plans = DietPlan.active().all()
    return render_template('nutrition/index.html', meals=meals, diet_plans=diet_plans)

@nutrition_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager', 'Trainer', 'Receptionist')
def export_csv():
    headers = ['ID', 'Name', 'Brand', 'Category', 'Price (PKR)', 'Stock Quantity', 'Expiry Date']
    def row_generator():
        supplements = Supplement.active().yield_per(100)
        for s in supplements:
            yield [s.id, s.name, s.brand, s.category, s.price, s.stock_quantity, s.expiry_date]
    return stream_csv_response(row_generator, headers, filename="supplements_inventory.csv")

@nutrition_bp.route('/meal-create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer')
def meal_create():
    form = MealForm()
    if form.validate_on_submit():
        meal = Meal(
            name=form.name.data.strip(),
            meal_time=form.meal_time.data,
            calories=form.calories.data,
            protein_g=form.protein_g.data,
            carbs_g=form.carbs_g.data,
            fats_g=form.fats_g.data,
            description=form.description.data.strip() if form.description.data else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(meal)
        try:
            db.session.commit()
            log_action('CREATE', 'meals', meal.id, None, {'name': meal.name, 'calories': meal.calories})
            flash(f"Meal '{meal.name}' saved successfully!", "success")
            return redirect(url_for('nutrition.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating meal: {e}", exc_info=True)
            flash("An error occurred while saving the meal.", "danger")

    return render_template('nutrition/meal_create.html', form=form)

@nutrition_bp.route('/diet-plans', methods=['GET', 'POST'])
@login_required
def diet_plans():
    is_staff = current_user.role_name in ['Admin', 'Manager', 'Trainer', 'Receptionist']
    curr_mem = get_current_member()

    if not is_staff and current_user.role_name != 'Member':
        abort(403)

    if current_user.role_name == 'Member' and request.method == 'POST':
        abort(403)

    form = DietPlanForm()
    assign_form = AssignDietPlanForm()

    plans = DietPlan.active().all()
    members = Member.active().all()

    assign_form.diet_plan_id.choices = [(p.id, p.title) for p in plans]
    assign_form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    if is_staff and request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_plan' and form.validate_on_submit():
            dp = DietPlan(
                title=form.title.data.strip(),
                goal=form.goal.data.strip(),
                daily_calories=form.daily_calories.data,
                description=form.description.data.strip() if form.description.data else None,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(dp)
            try:
                db.session.commit()
                log_action('CREATE', 'diet_plans', dp.id, None, {'title': dp.title})
                flash(f"Diet plan '{dp.title}' created!", "success")
                return redirect(url_for('nutrition.diet_plans'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating diet plan: {e}", exc_info=True)
                flash("An error occurred while creating diet plan.", "danger")

        elif action == 'assign_plan' and assign_form.validate_on_submit():
            for prev in MemberDietPlan.active().filter_by(member_id=assign_form.member_id.data).all():
                prev.is_current = False

            mdp = MemberDietPlan(
                member_id=assign_form.member_id.data,
                diet_plan_id=assign_form.diet_plan_id.data,
                assigned_date=date.today(),
                is_current=True,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(mdp)
            try:
                db.session.commit()
                flash("Diet plan assigned to member successfully!", "success")
                return redirect(url_for('nutrition.diet_plans'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error assigning diet plan: {e}", exc_info=True)
                flash("An error occurred while assigning diet plan.", "danger")

    # Member sees only their own diet plan
    if current_user.role_name == 'Member':
        member_plans = []
        if curr_mem:
            assigned = MemberDietPlan.active().filter_by(member_id=curr_mem.id, is_current=True).first()
            if assigned and assigned.diet_plan:
                member_plans = [assigned.diet_plan]
        plans = member_plans

    return render_template('nutrition/diet_plans.html', form=form, assign_form=assign_form, plans=plans)

@nutrition_bp.route('/supplements', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer', 'Receptionist')
def supplements():
    form = SupplementForm()
    if form.validate_on_submit():
        price = Decimal(str(form.price.data))
        sup = Supplement(
            name=form.name.data.strip(),
            brand=form.brand.data.strip(),
            category=form.category.data,
            price=price,
            stock_quantity=form.stock_quantity.data,
            expiry_date=form.expiry_date.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(sup)
        try:
            db.session.commit()
            log_action('CREATE', 'supplements', sup.id, None, {'name': sup.name, 'stock': sup.stock_quantity})
            flash(f"Supplement '{sup.name}' added to inventory!", "success")
            return redirect(url_for('nutrition.supplements'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding supplement: {e}", exc_info=True)
            flash("An error occurred while adding supplement.", "danger")

    all_supplements = Supplement.active().all()
    return render_template('nutrition/supplements.html', form=form, supplements=all_supplements)

@nutrition_bp.route('/sales', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def sales():
    form = SupplementSaleForm()
    supplements = Supplement.active().filter(Supplement.stock_quantity > 0).all()
    members = Member.active().all()

    form.supplement_id.choices = [(s.id, f"{s.name} ({s.brand}) - PKR {float(s.price):,.0f} [Stock: {s.stock_quantity}]") for s in supplements]
    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]

    if form.validate_on_submit():
        sup = Supplement.active().filter_by(id=form.supplement_id.data).first_or_404()
        qty = form.quantity.data

        # Block selling expired supplements
        today = today_pk()
        if sup.expiry_date and sup.expiry_date < today:
            flash(f"Cannot sell expired supplement '{sup.name}' (expired on {sup.expiry_date}).", "danger")
            return redirect(url_for('nutrition.sales'))

        # Do not trust unit_price from form; fetch Supplement.price from DB (allow override only for Admin/Manager)
        user_role = getattr(current_user, 'role_name', None) or (current_user.role.name if getattr(current_user, 'role', None) else '')
        if user_role in ('Admin', 'Manager') and form.unit_price.data is not None:
            unit_p = Decimal(str(form.unit_price.data))
        else:
            unit_p = Decimal(str(sup.price))

        total = unit_p * qty

        # Atomic stock reduction: check rowcount
        stmt = (
            db.update(Supplement)
            .where(Supplement.id == sup.id, Supplement.stock_quantity >= qty)
            .values(stock_quantity=Supplement.stock_quantity - qty)
        )
        res = db.session.execute(stmt)
        if res.rowcount == 0:
            flash(f"Insufficient stock! Available: {sup.stock_quantity}", "danger")
            return redirect(url_for('nutrition.sales'))

        sale = SupplementSale(
            supplement_id=sup.id,
            member_id=form.member_id.data,
            quantity=qty,
            unit_price=unit_p,
            total_amount=total,
            sale_date=today,
            created_by=current_user.id,
            updated_by=current_user.id
        )

        db.session.add(sale)
        try:
            db.session.commit()
            log_action('CREATE', 'supplement_sales', sale.id, None, {'supplement': sup.name, 'qty': qty, 'total': str(total)})
            flash(f"Sale of {qty}x {sup.name} recorded (PKR {total:,.2f})!", "success")
            return redirect(url_for('nutrition.sales'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing sale: {e}", exc_info=True)
            flash("An error occurred while recording the sale.", "danger")

    all_sales = SupplementSale.active().order_by(SupplementSale.sale_date.desc()).limit(20).all()
    return render_template('nutrition/sales.html', form=form, sales=all_sales)
