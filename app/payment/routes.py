from flask import Blueprint, request, jsonify
from app.payment.razorpay_utils import create_order, verify_payment
## Remove top-level imports of Payment and db

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/create_order', methods=['POST'])
def create_payment_order():
    data = request.json
    amount = data.get('amount')
    receipt = data.get('receipt')
    if not amount:
        return jsonify({'error': 'Amount required'}), 400
    order = create_order(amount, receipt=receipt)
    return jsonify(order)


# Route to handle payment success and insert into DB
@payment_bp.route('/payment/success', methods=['POST'])
def payment_success():
    from app.models import Payment
    from app import db
    data = request.json
    payment_id = data.get('payment_id')
    order_id = data.get('order_id')
    signature = data.get('signature')
    appointment_id = data.get('appointment_id')
    amount = data.get('amount')
    currency = data.get('currency', 'INR')
    status = data.get('status', 'success')

    # Verify payment signature
    if not verify_payment(payment_id, order_id, signature):
        return jsonify({'error': 'Payment verification failed'}), 400

    # Add payment record to DB
    payment = Payment(
        appointment_id=appointment_id,
        razorpay_payment_id=payment_id,
        amount=amount,
        currency=currency,
        status=status
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({'message': 'Payment recorded successfully'})
