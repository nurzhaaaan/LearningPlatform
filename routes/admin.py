from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import User, Role, Course, Assignment, Quiz, AssignmentSubmission, QuizAttempt
from forms import UserCreationForm, UserEditForm
from sqlalchemy import func, desc
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

admin = Blueprint('admin', __name__)

def admin_required(func):
    """Decorator to require admin role for a route"""
    @login_required
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)  # Forbidden
        return func(*args, **kwargs)
    decorated_view.__name__ = func.__name__
    return decorated_view

@admin.route('/admin/dashboard')
@admin_required
def dashboard():
    """Admin dashboard showing system stats and recent activity"""
    # Gather system stats
    total_users = User.query.count()
    admin_count = User.query.filter_by(role=Role.ADMIN).count()
    teacher_count = User.query.filter_by(role=Role.TEACHER).count()
    student_count = User.query.filter_by(role=Role.STUDENT).count()
    
    course_count = Course.query.count()
    active_course_count = Course.query.filter_by(is_active=True).count()
    inactive_course_count = course_count - active_course_count
    
    assignment_count = Assignment.query.count()
    submission_count = AssignmentSubmission.query.count()
    
    quiz_count = Quiz.query.count()
    quiz_attempt_count = QuizAttempt.query.count()
    
    # Get recent users
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    
    # Mock system activity data
    system_activities = [
        {
            'type': 'Login',
            'type_color': 'primary',
            'description': 'User logged in',
            'user': 'john_doe',
            'time': '2 minutes ago'
        },
        {
            'type': 'Course',
            'type_color': 'success',
            'description': 'New course created',
            'user': 'teacher1',
            'time': '45 minutes ago'
        },
        {
            'type': 'Assignment',
            'type_color': 'info',
            'description': 'New assignment added',
            'user': 'teacher2',
            'time': '3 hours ago'
        },
        {
            'type': 'System',
            'type_color': 'warning',
            'description': 'Database backup completed',
            'user': None,
            'time': '6 hours ago'
        },
        {
            'type': 'User',
            'type_color': 'danger',
            'description': 'New user registered',
            'user': 'new_student',
            'time': '1 day ago'
        }
    ]
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        admin_count=admin_count,
        teacher_count=teacher_count,
        student_count=student_count,
        course_count=course_count,
        active_course_count=active_course_count,
        inactive_course_count=inactive_course_count,
        assignment_count=assignment_count,
        submission_count=submission_count,
        quiz_count=quiz_count,
        quiz_attempt_count=quiz_attempt_count,
        recent_users=recent_users,
        system_activities=system_activities
    )

@admin.route('/admin/users')
@admin_required
def users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Apply search and filters
    query = User.query
    
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%'))
        )
    
    role = request.args.get('role', '')
    if role:
        query = query.filter(User.role == role)
    
    sort = request.args.get('sort', 'created_desc')
    if sort == 'created_desc':
        query = query.order_by(User.created_at.desc())
    elif sort == 'created_asc':
        query = query.order_by(User.created_at)
    elif sort == 'name_asc':
        query = query.order_by(User.first_name, User.last_name)
    elif sort == 'name_desc':
        query = query.order_by(User.first_name.desc(), User.last_name.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    return render_template('admin/users.html', users=users, pagination=pagination)

@admin.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    form = UserCreationForm()
    
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                role=form.role.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'User {user.username} has been created successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash('Error creating user. Please try again.', 'danger')
    
    return render_template('admin/create_user.html', form=form)

@admin.route('/admin/users/<int:user_id>')
@admin_required
def view_user(user_id):
    """View user details"""
    user = User.query.get_or_404(user_id)
    
    # Get user activity details
    courses_enrolled = []
    if user.role == Role.STUDENT:
        for enrollment in user.enrollments:
            if enrollment.is_active:
                course = enrollment.course
                courses_enrolled.append({
                    'id': course.id,
                    'title': course.title,
                    'enrollment_date': enrollment.enrollment_date.strftime('%Y-%m-%d')
                })
    
    courses_teaching = []
    if user.role == Role.TEACHER:
        for course in user.courses_teaching:
            student_count = len([e for e in course.enrollments if e.is_active])
            courses_teaching.append({
                'id': course.id,
                'title': course.title,
                'code': course.code,
                'student_count': student_count,
                'created_at': course.created_at.strftime('%Y-%m-%d')
            })
    
    return render_template(
        'admin/view_user.html', 
        user=user,
        courses_enrolled=courses_enrolled,
        courses_teaching=courses_teaching
    )

@admin.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        try:
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.role = form.role.data
            
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.view_user', user_id=user.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {str(e)}")
            flash('Error updating user. Please try again.', 'danger')
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/admin/users/<int:user_id>/delete')
@admin_required
def delete_user(user_id):
    """Delete a user"""
    if current_user.id == user_id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        flash('Error deleting user. Please try again.', 'danger')
    
    return redirect(url_for('admin.users'))

@admin.route('/admin/system_settings')
@admin_required
def system_settings():
    """System settings page"""
    return render_template('admin/system_settings.html')
