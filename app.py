from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps


app = Flask(__name__)

# config MySQL
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']='pass'
app.config['MYSQL_DB']='myflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'
# init MYSQL
mysql = MySQL(app)

# pylint: disable=no-member

#Articles = Articles()

#index or homepage
@app.route('/')
@app.route('/home')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

#Articles
@app.route('/articles')
def articles():
    #Create cursor
    cur = mysql.connection.cursor()

    #Get Articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    #Close connection
    cur.close()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        return render_template('articles.html', msg='No Articles Found')

#Single Article
@app.route('/article/<string:id>/')
def article(id):
    #Create cursor
    cur = mysql.connection.cursor()

    #Get Articles
    cur.execute("SELECT * FROM articles WHERE id=%s",[id])

    article = cur.fetchone()

    #Close connection
    cur.close()
    return render_template('article.html', article=article)

#Register form class
class RegisterForm(Form):
    name =  StringField('Name',[validators.length(min=1,max=50)])
    username = StringField('Username',[validators.length(min=4,max=25)])
    email = StringField('Email',[validators.length(min=6,max=50)])
    password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm',message='Password doesn\'t match')
    ])
    confirm = PasswordField('Confirm Password')

#User Registration
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        passowrd = sha256_crypt.encrypt(str(form.password.data))

        #create cursor
        cur = mysql.connection.cursor()
        #Execute Query
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s ,%s, %s, %s)",(name,email,username,passowrd))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('You are now registered and can log in.','success')

        return redirect(url_for('login'))

    return render_template('register.html',form=form)


# User Login
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        #Get Form Fields
        username = request.form.get('username')
        password_candidate = request.form.get('password')
        #Create cursor
        cur = mysql.connection.cursor()

        #Get user by username
        result = cur.execute("SELECT * FROM users WHERE username=%s",[username])
        if(result > 0):
            #Get stored hash
            data = cur.fetchone()
            password = data['password']

            #Close connection
            cur.close()

            #Compare the passwords
            if(sha256_crypt.verify(password_candidate,password)):   
                app.logger.info('PASSWORD MATCHED')
                #Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in','success')
                return redirect(url_for('dashboard'))
            else:
                app.logger.info("PASSWORD NOT MATCHED")
                error = 'Invalid Password'
                return render_template('login.html', error=error)
        else:
            app.logger.info("INVALID USER")
            return render_template('login.html', error='Username not found!')
        #Close connection
        cur.close()
    return render_template('login.html')    


#Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login!','danger')
            return redirect(url_for('login'))
    return wrap


#Dashboad >>> shows only after login
@app.route('/dashboard')
@is_logged_in
def dashboard():
    #Create cursor
    cur = mysql.connection.cursor()

    #Get Articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    #Close connection
    cur.close()
    if result > 0:
        return render_template('dashboard.html',articles=articles)
    else:
        msg = 'No Articles Found'
    return render_template('dashboard.html',msg=msg)


#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

#Article Form class
class ArticleForm(Form):
    title =  StringField('Title',[validators.length(min=10,max=200)])
    body = TextAreaField('Body',[validators.length(min=30)])
    
#Add Article
@app.route('/add_article',methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        #create cursor
        cur = mysql.connection.cursor()

        #Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s,%s,%s)",(title,body,session['username']))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article Created','success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


#Edit Article
@app.route('/edit_article/<string:id>',methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    #Create cursor
    cur = mysql.connection.cursor()

    #Get article by id
    cur.execute('SELECT * FROM articles WHERE id = %s',[id])
    article = cur.fetchone()

    #Get form
    form = ArticleForm(request.form)
    form.title.data = article['title']
    form.body.data = article['body']

    #Populate article form fields
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        #create cursor
        cur = mysql.connection.cursor()

        #Execute
        cur.execute("UPDATE articles SET title=%s,body=%s WHERE id=%s",(title, body, id))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article Updated','success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)


# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))


if(__name__ == "__main__"):
    app.secret_key='secret123'
    app.run(debug=True)



