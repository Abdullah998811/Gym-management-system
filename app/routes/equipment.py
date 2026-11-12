from decimal import Decimal
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.equipment import (
    Vendor, EquipmentCategory, Equipment, MaintenanceRecord,
    EquipmentIssue, PurchaseOrder, PurchaseOrderItem
)
from app.models.gym import Area
from app.forms.equipment import (
    VendorForm, EquipmentCategoryForm, EquipmentForm, MaintenanceRecordForm,
    EquipmentIssueForm, PurchaseOrderForm
)
from app.utils.decorators import role_required
from app.utils.audit import log_action
from app.utils.helpers import export_to_csv, stream_csv_response

equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment')

@equipment_bp.route('/', methods=['GET'])
@login_required
def index():
    search = request.args.get('search', '').strip()
    condition = request.args.get('condition', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Equipment.active()
    if search:
        query = query.filter(
            (Equipment.name.ilike(f"%{search}%")) |
            (Equipment.serial_number.ilike(f"%{search}%"))
        )
    if condition:
        query = query.filter(Equipment.condition_status == condition)

    pagination = query.order_by(Equipment.id.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'equipment/index.html',
        pagination=pagination,
        equipment_list=pagination.items,
        search=search,
        condition=condition
    )

@equipment_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def export_csv():
    headers = ['ID', 'Name', 'Serial #', 'Category', 'Vendor', 'Location', 'Purchase Cost (PKR)', 'Condition']
    def row_generator():
        items = Equipment.active().yield_per(100)
        for i in items:
            yield [
                i.id, i.name, i.serial_number,
                i.category.name if i.category else '',
                i.vendor.name if i.vendor else '',
                i.area.name if i.area else '',
                i.purchase_price,
                i.condition_status
            ]
    return stream_csv_response(row_generator, headers, filename="equipment_inventory.csv")

@equipment_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def create():
    form = EquipmentForm()
    cats = EquipmentCategory.active().all()
    vendors = Vendor.active().all()
    areas = Area.active().all()

    form.category_id.choices = [(c.id, c.name) for c in cats]
    form.vendor_id.choices = [(v.id, v.name) for v in vendors]
    form.area_id.choices = [(a.id, f"{a.name} ({a.facility.name if a.facility else 'Main'})") for a in areas]

    if form.validate_on_submit():
        price = Decimal(str(form.purchase_price.data))
        eq = Equipment(
            category_id=form.category_id.data,
            vendor_id=form.vendor_id.data,
            area_id=form.area_id.data,
            name=form.name.data.strip(),
            serial_number=form.serial_number.data.strip(),
            purchase_date=form.purchase_date.data,
            purchase_price=price,
            warranty_expiry=form.warranty_expiry.data,
            condition_status=form.condition_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(eq)
        try:
            db.session.commit()
            log_action('CREATE', 'equipment', eq.id, None, {'name': eq.name, 'serial': eq.serial_number})
            flash(f"Equipment '{eq.name}' registered successfully!", "success")
            return redirect(url_for('equipment.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error registering equipment: {e}", exc_info=True)
            flash("An error occurred while registering equipment.", "danger")

    return render_template('equipment/create.html', form=form)

@equipment_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def edit(id):
    eq = Equipment.active().filter_by(id=id).first_or_404()
    form = EquipmentForm(obj=eq)
    cats = EquipmentCategory.active().all()
    vendors = Vendor.active().all()
    areas = Area.active().all()

    form.category_id.choices = [(c.id, c.name) for c in cats]
    form.vendor_id.choices = [(v.id, v.name) for v in vendors]
    form.area_id.choices = [(a.id, f"{a.name} ({a.facility.name if a.facility else 'Main'})") for a in areas]

    if form.validate_on_submit():
        price = Decimal(str(form.purchase_price.data))
        eq.category_id = form.category_id.data
        eq.vendor_id = form.vendor_id.data
        eq.area_id = form.area_id.data
        eq.name = form.name.data.strip()
        eq.serial_number = form.serial_number.data.strip()
        eq.purchase_date = form.purchase_date.data
        eq.purchase_price = price
        eq.warranty_expiry = form.warranty_expiry.data
        eq.condition_status = form.condition_status.data
        eq.updated_by = current_user.id

        try:
            db.session.commit()
            log_action('UPDATE', 'equipment', eq.id, None, {'name': eq.name})
            flash(f"Equipment '{eq.name}' updated successfully.", "success")
            return redirect(url_for('equipment.index'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating equipment: {e}", exc_info=True)
            flash("An error occurred while updating equipment details.", "danger")

    return render_template('equipment/edit.html', form=form, equipment=eq)

@equipment_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def delete(id):
    eq = Equipment.active().filter_by(id=id).first_or_404()
    eq.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'equipment', eq.id, {'name': eq.name}, None)
        flash(f"Equipment '{eq.name}' soft-deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting equipment: {e}", exc_info=True)
        flash("An error occurred while deleting equipment.", "danger")
    return redirect(url_for('equipment.index'))

@equipment_bp.route('/maintenance', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer', 'Receptionist')
def maintenance():
    form = MaintenanceRecordForm()
    equipments = Equipment.active().all()
    form.equipment_id.choices = [(e.id, f"{e.name} ({e.serial_number})") for e in equipments]

    if form.validate_on_submit():
        cost_val = Decimal(str(form.cost.data or 0.0))
        mr = MaintenanceRecord(
            equipment_id=form.equipment_id.data,
            maintenance_date=form.maintenance_date.data,
            performed_by=form.performed_by.data.strip(),
            cost=cost_val,
            notes=form.notes.data.strip() if form.notes.data else None,
            next_due_date=form.next_due_date.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        eq = Equipment.active().filter_by(id=form.equipment_id.data).first()
        if eq and eq.condition_status == 'Maintenance Due':
            eq.condition_status = 'Good'

        db.session.add(mr)
        try:
            db.session.commit()
            log_action('CREATE', 'maintenance_records', mr.id, None, {'equipment_id': mr.equipment_id, 'cost': str(mr.cost)})
            flash("Maintenance service logged successfully!", "success")
            return redirect(url_for('equipment.maintenance'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving maintenance: {e}", exc_info=True)
            flash("An error occurred while logging maintenance.", "danger")

    records = MaintenanceRecord.active().order_by(MaintenanceRecord.maintenance_date.desc()).all()
    return render_template('equipment/maintenance.html', form=form, records=records)

@equipment_bp.route('/issues', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Trainer', 'Receptionist')
def issues():
    form = EquipmentIssueForm()
    equipments = Equipment.active().all()
    form.equipment_id.choices = [(e.id, f"{e.name} ({e.serial_number})") for e in equipments]

    if form.validate_on_submit():
        issue = EquipmentIssue(
            equipment_id=form.equipment_id.data,
            reported_by=current_user.id,
            reported_date=date.today(),
            description=form.description.data.strip(),
            severity=form.severity.data,
            resolution_status=form.resolution_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        if form.severity.data in ['High', 'Critical']:
            eq = Equipment.active().filter_by(id=form.equipment_id.data).first()
            if eq:
                eq.condition_status = 'Out of Order'

        db.session.add(issue)
        try:
            db.session.commit()
            log_action('CREATE', 'equipment_issues', issue.id, None, {'severity': issue.severity})
            flash("Equipment malfunction / issue reported.", "warning")
            return redirect(url_for('equipment.issues'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error reporting issue: {e}", exc_info=True)
            flash("An error occurred while reporting the issue.", "danger")

    all_issues = EquipmentIssue.active().order_by(EquipmentIssue.id.desc()).all()
    return render_template('equipment/issues.html', form=form, issues=all_issues)

@equipment_bp.route('/issues/<int:id>/resolve', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def issue_resolve(id):
    issue = EquipmentIssue.active().filter_by(id=id).first_or_404()
    issue.resolution_status = 'Resolved'
    issue.updated_by = current_user.id

    if issue.equipment:
        issue.equipment.condition_status = 'Good'

    try:
        db.session.commit()
        flash("Issue marked as Resolved. Equipment condition restored to Good.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resolving issue: {e}", exc_info=True)
        flash("An error occurred while resolving the issue.", "danger")
    return redirect(url_for('equipment.issues'))

@equipment_bp.route('/purchase-orders', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def purchase_orders():
    form = PurchaseOrderForm()
    vendors = Vendor.active().all()
    form.vendor_id.choices = [(v.id, v.name) for v in vendors]

    if form.validate_on_submit():
        total_amt = Decimal(str(form.total_amount.data or 0.0))
        po = PurchaseOrder(
            vendor_id=form.vendor_id.data,
            order_date=date.today(),
            expected_date=form.expected_date.data,
            total_amount=total_amt,
            order_status=form.order_status.data,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(po)
        try:
            db.session.commit()
            log_action('CREATE', 'purchase_orders', po.id, None, {'vendor_id': po.vendor_id, 'amount': str(po.total_amount)})
            flash("Purchase order created.", "success")
            return redirect(url_for('equipment.purchase_orders'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating PO: {e}", exc_info=True)
            flash("An error occurred while creating purchase order.", "danger")

    orders = PurchaseOrder.active().order_by(PurchaseOrder.order_date.desc()).all()
    return render_template('equipment/purchase_orders.html', form=form, orders=orders)
