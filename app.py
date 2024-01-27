import os

from flask import Flask, render_template, request, flash, redirect, session, g, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from flask_login import login_required

from forms import UserAddForm, LoginForm, MessageForm, EditProfileForm
from models import db, connect_db, User, Message, Likes

CURR_USER_KEY = "curr_user"

#Creates an instance of Flask, with configurations between Flask and PostgreSQL:
def create_app():
    app = Flask(__name__)

    # Get DB_URI from environ variable (useful for production/testing) or,
    # if not set there, use development local db.
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        os.getenv('DATABASE_URL', 'postgresql://postgres:admin@localhost/warbler_db'))

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "def_not_a_secret_key")
    toolbar = DebugToolbarExtension(app)
    
    return app


#Initializing an instance of Flask:
app = create_app()

#Connecting the Flask instance to PostgreSQL:
connect_db(app)

#Decorator that ensures PostgreSQL initailizing with Flask under the application's context:
@app.cli.command('initdb')
def init_db_command():
    """Initialize the database."""
    set_database()
    print('Initialized the database.')

def set_database():
    with app.app_context():
        db.drop_all()
        db.create_all()


##############################################################################
# User signup/login/logout


@app.before_request #Registers the g.user to the Flask instance, before sending a request:
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""
    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required  #Authentication to determine if the user is logged in, before executing logout:
def logout():
    """Handle logout of user."""
    do_logout()
    flash("You've been successfully logged out!", "success")
    return redirect(url_for('login'))


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
@login_required  #Authenticates the profile, if the user updates anything within their profile:
def profile():
    """Update profile for current user."""
    user = g.user  

    if request.method == "POST":
        # Handles the form submission to update user profile
        location = request.form.get("location")
        bio = request.form.get("bio")
        header_image = request.form.get("header_image")

        # Updates the user's profile information
        user.location = location
        user.bio = bio
        user.header_image = header_image

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # For the GET request displays the User's current profile:
    return render_template('users/profile.html', user=user)



@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")

@app.route('/users/edit', methods=['GET', 'POST'])
def edit_profile():
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect(url_for('home'))

    form = EditProfileForm(obj=g.user)

    if form.validate_on_submit():
        if User.authenticate(g.user.username, form.password.data):
            # Update user details
            g.user.username = form.username.data
            g.user.email = form.email.data
            g.user.image_url = form.image_url.data or User.default_image_url
            g.user.header_image_url = form.header_image_url.data or User.default_header_image_url
            g.user.bio = form.bio.data

            db.session.commit()
            return redirect(url_for('profile', user_id=g.user.id))
        else:
            flash("Wrong password. Please try again.", "danger")

    return render_template('edit.html', form=form)



##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")

@app.route('/messages/<int:message_id>/like', methods=['POST'])
@login_required
def message_like(message_id):
    # Retrieves the message or returns 404 if not found
    message = Message.query.get_or_404(message_id)

    # Prevents users from liking their own messages
    if message.user_id == g.user.id:
        flash("You cannot like your own message.", "danger")
        return redirect(request.referrer or url_for('homepage'))

    # Checks if the user has already liked the message
    if not any(like.message_id == message_id for like in g.user.likes):
        like = Likes(user_id=g.user.id, message_id=message_id)
        db.session.add(like)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("An error occurred. Please try again.", "danger")
            return redirect(request.referrer or url_for('homepage'))

    return redirect(request.referrer or url_for('homepage'))


@app.route('/messages/<int:message_id>/unlike', methods=['POST'])
@login_required
def message_unlike(message_id):
    # Retrieves the message or returns 404 if not found
    message = Message.query.get_or_404(message_id)

    # Retrieves the like object
    like = Likes.query.filter_by(user_id=g.user.id, message_id=message_id).first()

    # If the like exists, remove it
    if like:
        db.session.delete(like)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("An error occurred. Please try again.", "danger")
            return redirect(request.referrer or url_for('homepage'))

    return redirect(request.referrer or url_for('homepage'))




##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    #Selects the IDs of users that the current user is following:
    if g.user:
        #Stores user ID list of following users, w/o the current user appended:
        following_id = [user.id for user in g.user.following]
        #Appends the current user into the IDs list:
        following_id.append(g.user.id)
        
        #Query and filter the last 100 messages from the followers of the curent user:
        messages = (Message
            .query
            .filter(Message.user_id.in_(following_id))
            .order_by(Message.timestamp.desc())
            .limit(100)
            .all())
        
        #Returns the last 100 messages of followed_users with the user themselves:
        return render_template('home.html',messages=messages)
    else:
        
        #Returns no message:
        return render_template('home-anon.html')
        
        


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
