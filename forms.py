from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField, DateTimeField, IntegerField, FileField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User, Role

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different one.')

class UserCreationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    role = SelectField('Role', choices=[(Role.ADMIN, 'Admin'), (Role.TEACHER, 'Teacher'), (Role.STUDENT, 'Student')], 
                      validators=[DataRequired()])
    submit = SubmitField('Create User')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different one.')

class UserEditForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    role = SelectField('Role', choices=[(Role.ADMIN, 'Admin'), (Role.TEACHER, 'Teacher'), (Role.STUDENT, 'Student')], 
                      validators=[DataRequired()])
    submit = SubmitField('Update User')

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(max=100)])
    code = StringField('Course Code', validators=[DataRequired(), Length(max=20)])
    description = TextAreaField('Description', validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Course')

class MaterialForm(FlaskForm):
    title = StringField('Material Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    file_url = StringField('File URL (optional)')
    submit = SubmitField('Save Material')

class AssignmentForm(FlaskForm):
    title = StringField('Assignment Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    due_date = DateTimeField('Due Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    points = IntegerField('Points', default=100, validators=[DataRequired()])
    submit = SubmitField('Save Assignment')

class AssignmentSubmissionForm(FlaskForm):
    content = TextAreaField('Your Answer', validators=[DataRequired()])
    file_url = StringField('File URL (optional)')
    submit = SubmitField('Submit Assignment')

class GradeAssignmentForm(FlaskForm):
    grade = IntegerField('Grade', validators=[DataRequired()])
    feedback = TextAreaField('Feedback')
    submit = SubmitField('Submit Grade')

class QuizForm(FlaskForm):
    title = StringField('Quiz Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    time_limit = IntegerField('Time Limit (minutes)', default=60, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Quiz')

class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False')
    ], validators=[DataRequired()])
    points = IntegerField('Points', default=1, validators=[DataRequired()])
    submit = SubmitField('Save Question')

class OptionForm(FlaskForm):
    option_text = StringField('Option', validators=[DataRequired()])
    is_correct = BooleanField('Correct Answer')
    submit = SubmitField('Add Option')

class EnrollmentForm(FlaskForm):
    submit = SubmitField('Enroll in Course')

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password')
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('new_password')])
    submit = SubmitField('Update Profile')

class RequestPasswordResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class VerifyCodeForm(FlaskForm):
    code = StringField('Verification Code', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify Code')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')
