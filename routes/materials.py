from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import Material, Course, Enrollment
from forms import MaterialForm
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

materials = Blueprint('materials', __name__)

@materials.route('/courses/<int:course_id>/materials/create', methods=['GET', 'POST'])
@login_required
def create(course_id):
    """Create a new course material (teacher or admin only)"""
    course = Course.query.get_or_404(course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = MaterialForm()
    
    if form.validate_on_submit():
        try:
            material = Material(
                title=form.title.data,
                content=form.content.data,
                file_url=form.file_url.data,
                course_id=course.id
            )
            
            db.session.add(material)
            db.session.commit()
            
            flash(f'Material "{material.title}" has been added.', 'success')
            return redirect(url_for('courses.view', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating material: {str(e)}")
            flash('Error adding material. Please try again.', 'danger')
    
    return render_template('materials/create.html', form=form, course=course)

@materials.route('/materials/<int:material_id>')
@login_required
def view(material_id):
    """View a specific material"""
    material = Material.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Check permission: teacher of the course, admin, or enrolled student
    if current_user.id == course.teacher_id or current_user.is_admin():
        # Teachers and admins can access
        pass
    elif current_user.is_student():
        # Students need to be enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course.id,
            is_active=True
        ).first()
        
        if not enrollment:
            flash('You must be enrolled in this course to view its materials.', 'warning')
            return redirect(url_for('courses.view', course_id=course.id))
    else:
        abort(403)  # Forbidden
    
    return render_template('materials/view.html', material=material, course=course)

@materials.route('/materials/<int:material_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(material_id):
    """Edit a material (teacher or admin only)"""
    material = Material.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = MaterialForm(obj=material)
    
    if form.validate_on_submit():
        try:
            material.title = form.title.data
            material.content = form.content.data
            material.file_url = form.file_url.data
            
            db.session.commit()
            flash('Material updated successfully!', 'success')
            return redirect(url_for('materials.view', material_id=material.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating material: {str(e)}")
            flash('Error updating material. Please try again.', 'danger')
    
    return render_template('materials/create.html', form=form, course=course, material=material, edit_mode=True)

@materials.route('/materials/<int:material_id>/delete', methods=['POST'])
@login_required
def delete(material_id):
    """Delete a material (teacher or admin only)"""
    material = Material.query.get_or_404(material_id)
    course = Course.query.get_or_404(material.course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    try:
        db.session.delete(material)
        db.session.commit()
        flash(f'Material "{material.title}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting material: {str(e)}")
        flash('Error deleting material. Please try again.', 'danger')
    
    return redirect(url_for('courses.view', course_id=course.id))
