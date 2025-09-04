import razorpay
from flask import current_app

def get_razorpay_client():
    return razorpay.Client(auth=(
        current_app.config['RAZORPAY_KEY_ID'],
        current_app.config['RAZORPAY_KEY_SECRET']
    ))

def create_order(amount, currency='INR', receipt=None):
    client = get_razorpay_client()
    data = {
        'amount': int(amount * 100),  # Razorpay expects amount in paise
        'currency': currency,
        'receipt': receipt or f'receipt_{amount}'
    }
    return client.order.create(data=data)

def verify_payment(payment_id, order_id, signature):
    client = get_razorpay_client()
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
        return True
    except Exception:
        return False
