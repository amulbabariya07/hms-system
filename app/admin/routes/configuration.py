from flask import render_template, request, redirect, url_for, flash, session, jsonify
from . import admin_bp

@admin_bp.route('/configuration/receptionist-auth', methods=['POST'])
def update_receptionist_auth():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        
        # Validation
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'})
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters long'})
        
        if len(password) < 3:
            return jsonify({'success': False, 'message': 'Password must be at least 3 characters long'})
        
        session['receptionist_credentials'] = {
            'username': username,
            'password': password
        }
        
        if 'receptionist_logged_in' in session:
            session.pop('receptionist_logged_in', None)
            session.pop('receptionist_username', None)
        
        return jsonify({'success': True, 'message': 'Receptionist credentials updated successfully! The receptionist will need to log in again with the new credentials.'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error updating credentials'})
