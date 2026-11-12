from decimal import Decimal
from datetime import date, datetime, timezone
from sqlalchemy import extract
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.finance import (
    Invoice, InvoiceItem, Payment, PaymentMethod, ExpenseCategory,
    Expense, Discount
)
from app.models.member import Member
from app.models.gym import Branch
from app.forms.finance import InvoiceForm, PaymentForm, ExpenseForm, DiscountForm
from app.utils.decorators import role_required, ensure_member_access
from app.utils.audit import log_action
from app.utils.pdf import generate_invoice_pdf, generate_revenue_report_pdf
from app.utils.helpers import export_to_csv, stream_csv_response, generate_invoice_number

finance_bp = Blueprint('finance', __name__, url_prefix='/finance')

@finance_bp.route('/invoices', methods=['GET'])
@login_required
def invoices():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Invoice.active().join(Member).options(joinedload(Invoice.member), selectinload(Invoice.payments))

    # If role is Member, only show their own invoices
    if current_user.role_name == 'Member':
        member = Member.active().filter_by(user_id=current_user.id).first()
        if member:
            query = query.filter(Invoice.member_id == member.id)
        else:
            query = query.filter(Invoice.id == -1)

    if search:
        query = query.filter(
            (Invoice.invoice_number.ilike(f"%{search}%")) |
            (Member.first_name.ilike(f"%{search}%")) |
            (Member.last_name.ilike(f"%{search}%")) |
            (Member.membership_number.ilike(f"%{search}%"))
        )
    if status:
        query = query.filter(Invoice.payment_status == status)

    pagination = query.order_by(Invoice.id.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'finance/invoices.html',
        pagination=pagination,
        invoices=pagination.items,
        search=search,
        status=status
    )

@finance_bp.route('/export-csv', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def export_csv():
    headers = ['ID', 'Invoice #', 'Member Name', 'Member #', 'Issue Date', 'Due Date', 'Total (PKR)', 'Paid (PKR)', 'Status']
    def row_generator():
        invoices = Invoice.active().yield_per(100)
        for inv in invoices:
            yield [
                inv.id, inv.invoice_number,
                inv.member.full_name if inv.member else '',
                inv.member.membership_number if inv.member else '',
                inv.issue_date, inv.due_date,
                inv.total_amount, inv.paid_amount,
                inv.payment_status
            ]
    return stream_csv_response(row_generator, headers, filename="gym_invoices.csv")

@finance_bp.route('/invoice-create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager', 'Receptionist')
def invoice_create():
    form = InvoiceForm()
    members = Member.active().all()
    discounts = Discount.active().all()

    form.member_id.choices = [(m.id, f"{m.full_name} ({m.membership_number})") for m in members]
    form.discount_id.choices = [(0, 'No Discount')] + [(d.id, f"{d.title} ({d.code})") for d in discounts]

    if form.validate_on_submit():
        sub = Decimal(str(form.subtotal.data))
        tax = Decimal(str(form.tax_amount.data or 0.0))
        disc_amount = Decimal('0.00')
        disc_id = form.discount_id.data if form.discount_id.data and form.discount_id.data != 0 else None

        if disc_id:
            d_obj = Discount.active().filter_by(id=disc_id).first()
            if not d_obj:
                flash("Selected discount voucher is invalid or deactivated.", "danger")
                return render_template('finance/invoice_create.html', form=form)
            val = Decimal(str(d_obj.value))
            if d_obj.amount_type == 'percentage':
                if val < Decimal('0.00') or val > Decimal('100.00'):
                    flash("Discount percentage must be between 0% and 100%.", "danger")
                    return render_template('finance/invoice_create.html', form=form)
                disc_amount = (sub * val) / Decimal('100.00')
            else:
                if val < Decimal('0.00') or val > sub:
                    flash(f"Fixed discount cannot exceed subtotal (PKR {sub:,.2f}).", "danger")
                    return render_template('finance/invoice_create.html', form=form)
                disc_amount = val

        total = max(Decimal('0.00'), sub + tax - disc_amount)

        # Link to member's active membership if available
        member_obj = Member.active().filter_by(id=form.member_id.data).first()
        mem_id = member_obj.active_membership.id if (member_obj and member_obj.active_membership) else None

        # Retry loop for collision-safe sequence number
        max_retries = 5
        for attempt in range(max_retries):
            inv_num = generate_invoice_number(db.session)
            invoice = Invoice(
                invoice_number=inv_num,
                member_id=form.member_id.data,
                membership_id=mem_id,
                discount_id=disc_id,
                issue_date=form.issue_date.data,
                due_date=form.due_date.data,
                subtotal=sub,
                tax_amount=tax,
                discount_amount=disc_amount,
                total_amount=total,
                payment_status='Unpaid',
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(invoice)
            db.session.flush()

            item = InvoiceItem(
                invoice_id=invoice.id,
                description=form.description.data.strip(),
                quantity=1,
                unit_price=sub,
                total_price=sub,
                created_by=current_user.id,
                updated_by=current_user.id
            )
            db.session.add(item)

            try:
                db.session.commit()
                log_action('CREATE', 'invoices', invoice.id, None, {'inv_num': invoice.invoice_number, 'total': str(invoice.total_amount)})
                flash(f"Invoice '{invoice.invoice_number}' created successfully!", "success")
                return redirect(url_for('finance.invoice_view', id=invoice.id))
            except IntegrityError:
                db.session.rollback()
                if attempt == max_retries - 1:
                    current_app.logger.error("Failed to generate unique invoice number after retries.")
                    flash("Failed to generate unique invoice number. Please try again.", "danger")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating invoice: {e}", exc_info=True)
                flash("An error occurred while creating the invoice. Please check the details and try again.", "danger")
                break

    return render_template('finance/invoice_create.html', form=form)

@finance_bp.route('/<int:id>/view', methods=['GET', 'POST'])
@login_required
def invoice_view(id):
    invoice = Invoice.active().filter_by(id=id).first_or_404()

    # Member security
    ensure_member_access(invoice.member)

    payment_form = PaymentForm()
    methods = PaymentMethod.active().all()
    payment_form.invoice_id.choices = [(invoice.id, invoice.invoice_number)]
    payment_form.payment_method_id.choices = [(pm.id, pm.name) for pm in methods]

    if request.method == 'GET':
        payment_form.amount.data = invoice.balance_due

    if payment_form.validate_on_submit() and current_user.role_name in ['Admin', 'Manager', 'Receptionist']:
        # Fetch with row lock (SELECT ... FOR UPDATE)
        inv_locked = db.session.query(Invoice).filter(Invoice.id == id, Invoice.is_deleted == False).with_for_update().first()
        if not inv_locked:
            abort(404)

        if inv_locked.payment_status == 'Paid':
            flash("This invoice is already fully paid.", "warning")
            return redirect(url_for('finance.invoice_view', id=inv_locked.id))

        pay_amt = Decimal(str(payment_form.amount.data))
        if pay_amt <= Decimal('0.00'):
            flash("Payment amount must be greater than 0.", "danger")
            return redirect(url_for('finance.invoice_view', id=inv_locked.id))

        if pay_amt > inv_locked.balance_due:
            flash(f"Payment amount (PKR {pay_amt:,.2f}) cannot exceed remaining balance due (PKR {inv_locked.balance_due:,.2f}).", "danger")
            return redirect(url_for('finance.invoice_view', id=inv_locked.id))

        payment = Payment(
            invoice_id=inv_locked.id,
            payment_method_id=payment_form.payment_method_id.data,
            payment_date=payment_form.payment_date.data,
            amount=pay_amt,
            transaction_reference=payment_form.transaction_reference.data.strip() if payment_form.transaction_reference.data else None,
            notes=payment_form.notes.data.strip() if payment_form.notes.data else None,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(payment)
        db.session.flush()

        inv_locked.update_status()

        try:
            db.session.commit()
            log_action('CREATE', 'payments', payment.id, None, {'inv': inv_locked.invoice_number, 'amount': str(pay_amt)})
            flash(f"Payment of PKR {pay_amt:,.2f} recorded! Invoice status is now {inv_locked.payment_status}.", "success")
            return redirect(url_for('finance.invoice_view', id=inv_locked.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing payment: {e}", exc_info=True)
            flash("An error occurred while processing payment. Please try again.", "danger")

    return render_template('finance/invoice_view.html', invoice=invoice, payment_form=payment_form)

@finance_bp.route('/<int:id>/pdf', methods=['GET'])
@login_required
def invoice_pdf(id):
    invoice = Invoice.active().filter_by(id=id).first_or_404()
    ensure_member_access(invoice.member)
    pdf_bytes = generate_invoice_pdf(invoice)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Invoice_{invoice.invoice_number}.pdf"}
    )

@finance_bp.route('/payments', methods=['GET'])
@login_required
def payments():
    page = request.args.get('page', 1, type=int)
    query = Payment.active().join(Invoice).options(joinedload(Payment.invoice).joinedload(Invoice.member), joinedload(Payment.payment_method))

    if current_user.role_name == 'Member':
        member = Member.active().filter_by(user_id=current_user.id).first()
        if member:
            query = query.filter(Invoice.member_id == member.id)
        else:
            query = query.filter(Payment.id == -1)

    pagination = query.order_by(Payment.payment_date.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('finance/payments.html', pagination=pagination, payments=pagination.items)

@finance_bp.route('/expenses', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def expenses():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category_id', type=int)

    query = Expense.active()
    if category_id:
        query = query.filter(Expense.category_id == category_id)

    pagination = query.order_by(Expense.expense_date.desc()).paginate(page=page, per_page=10, error_out=False)
    categories = ExpenseCategory.active().all()

    return render_template('finance/expenses.html', pagination=pagination, expenses=pagination.items, categories=categories, category_id=category_id)

@finance_bp.route('/expense-create', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Manager')
def expense_create():
    form = ExpenseForm()
    cats = ExpenseCategory.active().all()
    branches = Branch.active().all()

    form.category_id.choices = [(c.id, c.name) for c in cats]
    form.branch_id.choices = [(b.id, b.name) for b in branches]

    if form.validate_on_submit():
        amt = Decimal(str(form.amount.data))
        exp = Expense(
            category_id=form.category_id.data,
            branch_id=form.branch_id.data,
            title=form.title.data.strip(),
            amount=amt,
            expense_date=form.expense_date.data,
            paid_to=form.paid_to.data.strip(),
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.session.add(exp)
        try:
            db.session.commit()
            log_action('CREATE', 'expenses', exp.id, None, {'title': exp.title, 'amount': str(exp.amount)})
            flash(f"Expense '{exp.title}' (PKR {exp.amount:,.2f}) recorded.", "success")
            return redirect(url_for('finance.expenses'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error recording expense: {e}", exc_info=True)
            flash("An error occurred while saving the expense.", "danger")

    return render_template('finance/expense_create.html', form=form)

@finance_bp.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Manager')
def expense_delete(id):
    exp = Expense.active().filter_by(id=id).first_or_404()
    exp.soft_delete(current_user.id)
    try:
        db.session.commit()
        log_action('DELETE', 'expenses', exp.id, {'title': exp.title}, None)
        flash(f"Expense '{exp.title}' deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting expense: {e}", exc_info=True)
        flash("An error occurred while deleting the expense.", "danger")
    return redirect(url_for('finance.expenses'))

@finance_bp.route('/revenue-pdf', methods=['GET'])
@login_required
@role_required('Admin', 'Manager')
def revenue_pdf():
    now = datetime.now(timezone.utc)
    month_param = request.args.get('month', now.strftime("%B"))
    year = request.args.get('year', now.year, type=int)

    if not (2000 <= year <= 2100):
        year = now.year

    MONTH_NAMES = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    month_num = None
    month_name = None
    if isinstance(month_param, int) or (isinstance(month_param, str) and month_param.isdigit()):
        m_int = int(month_param)
        if 1 <= m_int <= 12:
            month_num = m_int
            month_name = MONTH_NAMES[month_num]

    if not month_num:
        m_str = str(month_param).strip().capitalize()
        for num, name in MONTH_NAMES.items():
            if m_str.lower() in (name.lower(), name[:3].lower()):
                month_num = num
                month_name = name
                break

    if not month_num:
        month_num = now.month
        month_name = MONTH_NAMES[month_num]

    invoices = Invoice.active().filter(
        extract('year', Invoice.issue_date) == year,
        extract('month', Invoice.issue_date) == month_num
    ).all()
    expenses = Expense.active().filter(
        extract('year', Expense.expense_date) == year,
        extract('month', Expense.expense_date) == month_num
    ).all()

    pdf_bytes = generate_revenue_report_pdf(month_name, year, invoices, expenses)
    safe_month = "".join(c for c in month_name if c.isalnum())
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="RevenueReport_{year}_{safe_month}.pdf"'}
    )
