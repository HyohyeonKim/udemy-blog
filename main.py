from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

## LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

##CONFIGURE TABLES

class User(db.Model, UserMixin):
    __tablename__= "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250),  unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")
    
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

#Comment DB table
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    comment_author = relationship("User", back_populates="comments")
    
    text = db.Column(db.Text, nullable=False)
    
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    

# with app.app_context():
#     db.create_all()

# with app.app_context():
#     posts = BlogPost.query.all()

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


## MAKE DECORATION
def admin_only(func): #🤔왜 wraps를 붙였는지, 왜 *args와 **kargs를 붙였는지 알아보자
    @wraps(func)
    def check_admin(*args, **kwargs):
        
        if current_user.is_authenticated == False:
            return abort(401)
    
        if current_user.id != 1:
            return abort(401)
        return func(*args, **kwargs) 
    return check_admin


## Resister Form
class Form(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name  = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Submit")
    
class Login(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


# db.create_all()

# with app.app_context():
#     db.create_all()
   

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    state = current_user.is_authenticated
    
    return render_template("index.html", all_posts=posts, loged_in=state, admin=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = Form()
    
    if form.validate_on_submit():
        
        users = User.query.all()
        user_list = [user.email for user in users]
        
        if form.data.get('email') in user_list:
            
            flash("You've already signed up with that eamil, log in instead!")
            
            return redirect(url_for('login'))
        
        else:
            user = User(
                name = form.data.get('name'),
                password = generate_password_hash(form.data.get('password'),method='pbkdf2:sha256', salt_length=16),
                email = form.data.get('email')
            )
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
        
            return redirect(url_for('get_all_posts'))
        
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    
    form = Login()
    
    if form.validate_on_submit():
        
        users = User.query.all()
        user_list = [user.email for user in users]
        
        if not form.data.get('email') in user_list:
            flash("That email does  not exist, please try again.")
            return redirect(url_for('login'))
        
        
        pwd = form.data.get('password')
        user_data = db.session.execute(db.select(User).filter_by(email=form.data.get('email'))).scalar_one()
        pwd_hs = user_data.password
        
        if check_password_hash(pwd_hs,pwd):
            
            login_user(user_data)
            
            return redirect(url_for('get_all_posts'))
    
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    
    comments = Comment.query.all()
    
    if form.validate_on_submit():
        
        if not current_user.is_authenticated:
            flash("You need a login!")
            return redirect(url_for('login'))
        
        
        comment = Comment(
            text = form.data.get('comment'),
            author_id = current_user.id,
            post_id = post_id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return redirect(url_for('show_post', post_id=post_id))
    
    return render_template("post.html", post=requested_post, form=form, comments=comments, gravatar=gravatar)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        
        new_post = BlogPost(
            title=form.data.get('title'),
            subtitle=form.data.get('subtitle'),
            body=form.data.get('body'),
            img_url=form.data.get('img_url'),
            # author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y"),
            author=current_user
        )
        
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.data.get('title')
        post.subtitle = edit_form.data.get('subtitle')
        post.img_url = edit_form.data.get('img_url')
        post.body = edit_form.data.get('body')
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)

#The Life of Cactus
#Who knew that cacti lived such interesting lives.
#October 20, 2020
#<p>Nori grape silver beet broccoli kombu beet greens fava bean potato quandong celery.</p>
#<p>Bunya nuts black-eyed pea prairie turnip leek lentil turnip greens parsnip.</p>
#<p>Sea lettuce lettuce water chestnut eggplant winter purslane fennel azuki bean earthnut pea sierra leone bologi leek soko chicory celtuce parsley j&iacute;cama salsify.</p>
#https://images.unsplash.com/photo-1530482054429-cc491f61333b?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=1651&q=80
#Angela Yu

