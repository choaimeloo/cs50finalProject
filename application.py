from cs50 import SQL
from flask import Flask
from flask import redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from tempfile import mkdtemp

from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

import datetime
import re


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure to use SQLite database
db = SQL("sqlite:///penser.db")


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/manage", methods=["GET", "POST"])
@login_required
def manage():
    """Render manage page"""

    # Sort posts by tags/title
    if request.args.get("sortby") == "tags":
        posts = db.execute("SELECT * FROM memos WHERE id=:id ORDER BY tags", id=session["user_id"])
        for i in range(0, len(posts)):
            post = posts[i]["post"]
            tags = posts[i]["tags"]
            day = posts[i]["day"]
            date = posts[i]["date"]
            time = posts[i]["time"]

        return render_template("manage.html", posts=posts)

    # Delete post by postID
    if request.method == "POST":
        db.execute("DELETE FROM memos WHERE postID=:postID", postID=request.form.get("postID"))
        posts = db.execute("SELECT * FROM memos WHERE id=:id", id=session["user_id"])
        for i in range(0, len(posts)):
            post = posts[i]["post"]
            tags = posts[i]["tags"]
            day = posts[i]["day"]
            date = posts[i]["date"]
            time = posts[i]["time"]
            postID = posts[i]["postID"]

        return render_template("manage.html", posts=posts)

    # Render posts with delete buttons
    posts = db.execute("SELECT * FROM memos WHERE id=:id", id=session["user_id"])
    for i in range(0, len(posts)):
        post = posts[i]["post"]
        tags = posts[i]["tags"]
        day = posts[i]["day"]
        date = posts[i]["date"]
        time = posts[i]["time"]
        postID = posts[i]["postID"]

    return render_template("manage.html", posts=posts)


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Render home page"""

    # Sort posts by tags/title
    if request.args.get("sortby") == "tags":
        posts = db.execute("SELECT * FROM memos WHERE id=:id ORDER BY tags", id=session["user_id"])
        for i in range(0, len(posts)):
            post = posts[i]["post"]
            tags = posts[i]["tags"]
            day = posts[i]["day"]
            date = posts[i]["date"]
            time = posts[i]["time"]

        return render_template("index.html", posts=posts)

    # Render all posts
    posts = db.execute("SELECT * FROM memos WHERE id=:id", id=session["user_id"])
    for i in range(0, len(posts)):
        post = posts[i]["post"]
        tags = posts[i]["tags"]
        day = posts[i]["day"]
        date = posts[i]["date"]
        time = posts[i]["time"]

    return render_template("index.html", posts=posts)


@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    """Post on site"""

    # Check user wrote a post
    if request.method == "POST":
        if not request.form.get("post"):
            return("you forgot to write something", 400)

        else:
            # Record post & tags in memos table
            x = datetime.datetime.now()
            db.execute("INSERT INTO memos (id, post, tags, day, date, time) VALUES (:id, :p, :t, :d, :date, :time)",
                       id=session["user_id"], p=request.form.get("post"), t=request.form.get("tags"), d=x.strftime("%a"), date=x.strftime("%x"), time=x.strftime("%X"))

            return redirect("/", code=302)

    else:
        return render_template("post.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST
    if request.method == "POST":
        if not request.form.get("username"):
            return("doh! remember to enter username", 403)

        elif not request.form.get("password"):
            return("doh! remember to enter password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        return redirect("/", code=302)

    # User reached route via GET
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return("must provide password", 400)

        # Ensure password was confirmed
        elif not request.form.get("confirmation"):
            return("please confirm password", 400)

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return("passwords must match", 400)

        # Ensure password is between six and sixteen characters and contains at least one lowercase, one uppercase, one number, and one symbol
        # Adapted from w3r resource: https://www.w3resource.com/python-exercises/python-conditional-exercise-15.php
        password = request.form.get("password")
        x = True
        while x:
            if len(password) < 6 or len(password) > 16:
                return("password must be between 6 and 16 characters")
                break
            elif not re.search("[a-z]", password):
                return("password must contain at least one lowercase letter")
                break
            elif not re.search("[0-9]", password):
                return("password must contain at least one number")
                break
            elif not re.search("[A-Z]", password):
                return("password must contain at least one uppercase letter")
                break
            # https://stackoverflow.com/questions/26130604/check-if-string-contains-special-characters-in-python
            elif not set("!@#$%^&*{};:-_+=<>/()[]?|~`").intersection(password):
                return("password must contain at least one special character (e.g. $#@)")
                break
            else:
                x = False

                # Hash password
                hash = generate_password_hash(request.form.get("password"))

                # Check username is unique
                result = db.execute("INSERT INTO users(username, hash) VALUES (:username, :hash)",
                                    username=request.form.get("username"), hash=hash)
                if not result:
                    return("choose a different username")

                # Log user in automatically, storing session id
                rows = db.execute("SELECT id FROM users WHERE username=:username",
                                  username=request.form.get("username"))
                session["user_id"] = rows[0]["id"]

                return redirect("/", code=302)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


if __name__ == "__main__":
    app.run()
