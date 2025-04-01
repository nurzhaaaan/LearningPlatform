from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import Course, User, Enrollment, Material, Assignment, Quiz, Role
from forms import CourseForm, EnrollmentForm
from sqlalchemy import desc
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

courses = Blueprint('courses', __name__)

@courses.route('/courses')
@login_required
def index():
    """Display all courses or filtered courses based on criteria"""
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of courses per page
    
    # Apply search and filters
    search = request.args.get('search', '')
    filter_option = request.args.get('filter', 'all')
    sort_option = request.args.get('sort', 'recent')
    
    # Base query
    query = Course.query
    
    # Apply search
    if search:
        query = query.filter(
            (Course.title.ilike(f'%{search}%')) |
            (Course.code.ilike(f'%{search}%')) |
            (Course.description.ilike(f'%{search}%'))
        )
    
    # Apply filters
    if filter_option == 'enrolled' and current_user.is_student():
        query = query.join(Enrollment).filter(
            Enrollment.student_id == current_user.id,
            Enrollment.is_active == True
        )
    elif filter_option == 'available' and current_user.is_student():
        enrolled_course_ids = db.session.query(Enrollment.course_id).filter(
            Enrollment.student_id == current_user.id
        ).subquery()
        query = query.filter(Course.id.notin_(enrolled_course_ids))
    elif filter_option == 'teaching' and current_user.is_teacher():
        query = query.filter(Course.teacher_id == current_user.id)
    
    # Apply sorting
    if sort_option == 'recent':
        query = query.order_by(desc(Course.created_at))
    elif sort_option == 'title_asc':
        query = query.order_by(Course.title)
    elif sort_option == 'title_desc':
        query = query.order_by(desc(Course.title))
    elif sort_option == 'enrolled':
        # Sort by number of enrollments (requires additional query)
        pass  # This would require a more complex query with subqueries
    
    # Execute paginated query
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    courses_result = pagination.items
    
    # Prepare courses data with additional information
    courses_data = []
    for course in courses_result:
        # Get teacher name
        teacher = User.query.get(course.teacher_id)
        teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown"
        
        # Get student count
        student_count = Enrollment.query.filter_by(course_id=course.id, is_active=True).count()
        
        # Check if current user is enrolled (for students)
        is_enrolled = False
        progress = 0
        if current_user.is_student():
            enrollment = Enrollment.query.filter_by(
                student_id=current_user.id,
                course_id=course.id,
                is_active=True
            ).first()
            is_enrolled = enrollment is not None
            
            # Calculate progress (simplified version)
            # In a real implementation, this would be more sophisticated
            progress = 30  # Mock progress percentage
        
        course_data = {
            'id': course.id,
            'title': course.title,
            'code': course.code,
            'description': course.description,
            'teacher_id': course.teacher_id,
            'teacher_name': teacher_name,
            'student_count': student_count,
            'is_enrolled': is_enrolled,
            'progress': progress
        }
        courses_data.append(course_data)
    
    return render_template(
        'courses/index.html',
        courses=courses_data,
        pagination=pagination
    )

@courses.route('/courses/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new course (teachers and admins only)"""
    if not (current_user.is_teacher() or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = CourseForm()
    
    if form.validate_on_submit():
        try:
            course = Course(
                title=form.title.data,
                code=form.code.data,
                description=form.description.data,
                teacher_id=current_user.id,
                is_active=form.is_active.data
            )
            
            db.session.add(course)
            db.session.commit()
            
            flash(f'Course "{course.title}" has been created successfully!', 'success')
            return redirect(url_for('courses.view', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating course: {str(e)}")
            flash('Error creating course. Please try again.', 'danger')
    
    return render_template('courses/create.html', form=form)

@courses.route('/courses/<int:course_id>')
@login_required
def view(course_id):
    """View course details and materials"""
    course = Course.query.get_or_404(course_id)
    teacher = User.query.get(course.teacher_id)
    
    # Check if current user is enrolled (for students)
    is_enrolled = False
    enrollment = None
    if current_user.is_student():
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        is_enrolled = enrollment is not None
    
    # Get course materials
    materials = Material.query.filter_by(course_id=course.id).order_by(Material.created_at.desc()).all()
    
    # Get course assignments
    assignments = Assignment.query.filter_by(course_id=course.id).order_by(Assignment.due_date.asc()).all()
    
    # Get course quizzes
    quizzes = Quiz.query.filter_by(course_id=course.id).order_by(Quiz.created_at.desc()).all()
    
    # Get enrolled students
    students = []
    if current_user.id == course.teacher_id or current_user.is_admin():
        enrollments = Enrollment.query.filter_by(course_id=course.id, is_active=True).all()
        for enroll in enrollments:
            student = User.query.get(enroll.student_id)
            students.append({
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'email': student.email,
                'enrollment_date': enroll.enrollment_date.strftime('%Y-%m-%d')
            })
    
    return render_template(
        'courses/view.html',
        course=course,
        teacher=teacher,
        is_enrolled=is_enrolled,
        enrollment=enrollment,
        materials=materials,
        assignments=assignments,
        quizzes=quizzes,
        students=students
    )

@courses.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(course_id):
    """Edit course details (course teacher or admin only)"""
    course = Course.query.get_or_404(course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    form = CourseForm(obj=course)
    
    if form.validate_on_submit():
        try:
            course.title = form.title.data
            course.code = form.code.data
            course.description = form.description.data
            course.is_active = form.is_active.data
            
            db.session.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('courses.view', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating course: {str(e)}")
            flash('Error updating course. Please try again.', 'danger')
    
    return render_template('courses/edit.html', form=form, course=course)

@courses.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def delete(course_id):
    """Delete a course (course teacher or admin only)"""
    course = Course.query.get_or_404(course_id)
    
    # Check permissions
    if not (current_user.id == course.teacher_id or current_user.is_admin()):
        abort(403)  # Forbidden
    
    try:
        db.session.delete(course)
        db.session.commit()
        flash(f'Course "{course.title}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting course: {str(e)}")
        flash('Error deleting course. Please try again.', 'danger')
    
    return redirect(url_for('courses.index'))

@courses.route('/courses/<int:course_id>/enroll', methods=['POST'])
@login_required
def enroll(course_id):
    """Enroll in a course (students only)"""
    if not current_user.is_student():
        abort(403)  # Forbidden
    
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if existing_enrollment:
        if existing_enrollment.is_active:
            flash('You are already enrolled in this course.', 'info')
        else:
            # Reactivate enrollment
            existing_enrollment.is_active = True
            db.session.commit()
            flash(f'You have re-enrolled in "{course.title}".', 'success')
        return redirect(url_for('courses.view', course_id=course.id))
    
    # Create new enrollment
    try:
        enrollment = Enrollment(
            student_id=current_user.id,
            course_id=course.id,
            enrollment_date=datetime.utcnow(),
            is_active=True
        )
        
        db.session.add(enrollment)
        db.session.commit()
        flash(f'You have successfully enrolled in "{course.title}".', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error enrolling in course: {str(e)}")
        flash('Error enrolling in course. Please try again.', 'danger')
    
    return redirect(url_for('courses.view', course_id=course.id))

@courses.route('/courses/<int:course_id>/unenroll', methods=['POST'])
@login_required
def unenroll(course_id):
    """Unenroll from a course (students only)"""
    if not current_user.is_student():
        abort(403)  # Forbidden
    
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id,
        is_active=True
    ).first_or_404()
    
    try:
        enrollment.is_active = False
        db.session.commit()
        flash(f'You have unenrolled from "{course.title}".', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unenrolling from course: {str(e)}")
        flash('Error unenrolling from course. Please try again.', 'danger')
    
    return redirect(url_for('courses.index'))

@courses.route('/enrolled-courses')
@login_required
def enrolled():
    """Display all courses the student is enrolled in"""
    if not current_user.is_student():
        flash('This page is only available for students.', 'warning')
        return redirect(url_for('courses.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of courses per page
    
    # Get enrolled courses
    enrolled_courses_query = Course.query.join(Enrollment).filter(
        Enrollment.student_id == current_user.id,
        Enrollment.is_active == True
    ).order_by(desc(Enrollment.enrollment_date))
    
    # Execute paginated query
    pagination = enrolled_courses_query.paginate(page=page, per_page=per_page, error_out=False)
    courses_result = pagination.items
    
    # Prepare courses data with additional information
    courses_data = []
    for course in courses_result:
        # Get teacher name
        teacher = User.query.get(course.teacher_id)
        teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown"
        
        # Get enrollment date
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course.id,
            is_active=True
        ).first()
        enrollment_date = enrollment.enrollment_date if enrollment else None
        
        # Calculate progress (simplified version)
        # In a real implementation, this would be more sophisticated
        progress = 30  # Mock progress percentage
        
        # Count materials, assignments, and quizzes for this course
        materials_count = Material.query.filter_by(course_id=course.id).count()
        assignments_count = Assignment.query.filter_by(course_id=course.id).count()
        quizzes_count = Quiz.query.filter_by(course_id=course.id).count()
        
        course_data = {
            'id': course.id,
            'title': course.title,
            'code': course.code,
            'description': course.description,
            'teacher_id': course.teacher_id,
            'teacher_name': teacher_name,
            'enrollment_date': enrollment_date,
            'progress': progress,
            'materials_count': materials_count,
            'assignments_count': assignments_count,
            'quizzes_count': quizzes_count
        }
        courses_data.append(course_data)
    
    return render_template(
        'courses/enrolled.html',
        courses=courses_data,
        pagination=pagination
    )
