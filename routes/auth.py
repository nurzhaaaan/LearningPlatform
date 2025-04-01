from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User, Role
from forms import (
    LoginForm, RegistrationForm, RequestPasswordResetForm, 
    VerifyCodeForm, ResetPasswordForm
)
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

@auth.route('/')
def index():
    """Homepage route"""
    return render_template('index.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('courses.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('courses.index'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('courses.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=Role.STUDENT
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during registration: {str(e)}")
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@auth.route('/about')
def about():
    """About Us page"""
    return render_template('about.html')

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Password reset request route"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    form = RequestPasswordResetForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Generate reset code
            reset_code = user.generate_reset_code()
            db.session.commit()
            
            # In a real application, send the code via email
            # For now, we'll just show it in a flash message for demonstration
            flash(f'Your password reset code is: {reset_code}. This code is valid for 30 minutes.', 'info')
            return redirect(url_for('auth.verify_reset_code', email=user.email))
        else:
            flash('No account found with that email address.', 'danger')
    
    return render_template('reset_password_request.html', form=form)

@auth.route('/reset-password/verify', methods=['GET', 'POST'])
def verify_reset_code():
    """Verify reset code route"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    email = request.args.get('email', '')
    if not email:
        flash('Email address is required.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('No account found with that email address.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    form = VerifyCodeForm()
    
    if form.validate_on_submit():
        if user.verify_reset_code(form.code.data):
            # Code is valid, redirect to reset password page
            return redirect(url_for('auth.reset_password', email=email, code=form.code.data))
        else:
            flash('Invalid or expired code. Please try again.', 'danger')
    
    return render_template('verify_reset_code.html', form=form, email=email)

@auth.route('/reset-password/reset', methods=['GET', 'POST'])
def reset_password():
    """Reset password route"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    email = request.args.get('email', '')
    code = request.args.get('code', '')
    
    if not email or not code:
        flash('Email address and verification code are required.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    user = User.query.filter_by(email=email).first()
    if not user or not user.verify_reset_code(code):
        flash('Invalid or expired code. Please try again.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_code()
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))
