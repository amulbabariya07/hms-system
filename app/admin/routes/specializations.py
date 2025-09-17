from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from app.models import Specialization
from . import admin_bp

@admin_bp.route('/specializations')
def admin_specializations():
    if 'admin_logged_in' not in session:
        flash('Please login to access specializations.', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    specializations = Specialization.query.order_by(Specialization.created_at.desc()).all()
    return render_template('admin/specializations.html', specializations=specializations)


@admin_bp.route('/specializations/add', methods=['POST'])
def admin_add_specialization():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Name is required.'})

        # Prevent duplicates
        if Specialization.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Specialization already exists.'})

        specialization = Specialization(name=name, description=description)
        db.session.add(specialization)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Specialization added successfully!'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error while adding specialization.'})


@admin_bp.route('/specializations/edit/<int:spec_id>', methods=['POST'])
def admin_edit_specialization(spec_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        specialization = Specialization.query.get_or_404(spec_id)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Name is required.'})

        # Check duplicate (exclude current)
        existing = Specialization.query.filter(Specialization.name == name, Specialization.id != spec_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Specialization name already exists.'})

        specialization.name = name
        specialization.description = description
        db.session.commit()
        return jsonify({'success': True, 'message': 'Specialization updated successfully!'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error while updating specialization.'})


@admin_bp.route('/specializations/delete/<int:spec_id>', methods=['POST'])
def admin_delete_specialization(spec_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        specialization = Specialization.query.get_or_404(spec_id)
        db.session.delete(specialization)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Specialization deleted successfully!'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error while deleting specialization.'})
