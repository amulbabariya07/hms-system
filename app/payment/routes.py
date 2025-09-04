from flask import Blueprint, request, jsonify
from app.payment.razorpay_utils import create_order

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
