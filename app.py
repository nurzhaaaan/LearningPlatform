import os
import logging
import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect


# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
migrate = Migrate()
# Temporarily disable CSRF for testing
# csrf = CSRFProtect()

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
# csrf.init_app(app)

# Add context processor for templates
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}

# Register blueprints
with app.app_context():
    # Import models
    import models  # noqa: F401
    
    # Import and register blueprints
    from routes.auth import auth
    from routes.admin import admin
    from routes.courses import courses
    from routes.materials import materials
    from routes.assignments import assignments
    from routes.quizzes import quizzes
    from routes.profile import profile
    
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(courses)
    app.register_blueprint(materials)
    app.register_blueprint(assignments)
    app.register_blueprint(quizzes)
    app.register_blueprint(profile)
    
    # Setup user loader for Flask-Login
    from models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
