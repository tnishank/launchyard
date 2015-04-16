from flask import Flask, request, g, session, redirect, url_for
from flask import render_template_string
from flask.ext.github import GitHub
import json
import urllib2
import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker


SECRET_KEY = 'Hard to guess string'
DEBUG = True

# Set these values
GITHUB_CLIENT_ID = 'ce016dfe9bef280addd3'
GITHUB_CLIENT_SECRET = '47cd887755135fa194fd3d16782ed1a6165dc5a5'

# setup flask
app = Flask(__name__)
app.config.from_object(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')


# setup github-flask
github = GitHub(app)

# setup sqlalchemy
engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    Base.metadata.create_all(bind=engine)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(200))
    github_access_token = Column(String(200))

    def __init__(self, github_access_token):
        self.github_access_token = github_access_token


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@app.after_request
def after_request(response):
    db_session.remove()
    return response


@app.route('/')
def index():
    if g.user:
        temp = 'Hello! <a href="{{ url_for("user") }}">Get Repos</a> ' \
            '<a href="{{ url_for("logout") }}">Logout</a>'
    else:
        temp = 'Hello! <a href="{{ url_for("login") }}">Login</a>'

    return render_template_string(temp)


@github.access_token_getter
def token_getter():
    user = g.user
    if user is not None:
        return user.github_access_token


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        #return redirect(next_url)
        return 'access token is none'

    user = User.query.filter_by(github_access_token=access_token).first()
    if user is None:
        user = User(access_token)
        db_session.add(user)
    user.github_access_token = access_token
    db_session.commit()

    session['user_id'] = user.id
    return redirect(url_for('index'))


@app.route('/login')
def login():
    if session.get('user_id', None) is None:
        return github.authorize()
    else:
        return 'User id in use'


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/user')
def user():
    lis = []
    data = github.request('GET', 'user/repos')
    repos = []
    for i in data:
        repos.append(i['full_name'])
    return json.dumps({'repos': repos})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
