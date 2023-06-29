import base64
import hashlib
import random
import re
import numpy as np
import flask
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import json

from flask_cors import CORS

app = Flask(__name__)
# Need to uncomment the below line if running via docker-compose
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
credentials = json.load(open('config.json','r'))
db_user = credentials['credentials']['db_user']
db_passwd = credentials['credentials']['db_passwd']
# Need to comment this line if running via docker-compose
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://{db_user}:{db_passwd}@jpmcfg23.postgres.database.azure.com/postgres?sslmode=require'.format(db_user=db_user,db_passwd=db_passwd)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:2303sejal@localhost:3306/mydatabase'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 20
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 300
db = SQLAlchemy(app)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
email_regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
BASE_ROUTE = '/api/v1/'

class List_of_Companies(db.Model):
    company_name = db.Column(db.String(30), unique=False, nullable=False, primary_key=True)

    def __init__(self, company_name):
        self.company_name = company_name

class Users(db.Model):
    name = db.Column(db.String(200), unique=False, nullable=False)
    email_id = db.Column(db.String(100), unique=False, nullable=False,primary_key=True)
    passwd_hash = db.Column(db.String(256), unique=False, nullable=False)

    def __init__(self, name, email_id, passwd_hash):
        self.name = name
        self.email_id = email_id
        self.passwd_hash = passwd_hash

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Token(db.Model):
    email_id = db.Column(db.String(30), unique=False, nullable=False, primary_key=True)
    token = db.Column(db.String(256), unique=False, nullable=False, primary_key=True)

    def __init__(self, email_id, token):
        self.email_id = email_id
        self.token = token

class Scores(db.Model):
    email_id = db.Column(db.String(256), unique=False, nullable=False, primary_key=True)
    score = db.Column(db.Integer, unique=False, nullable=False)
    attempts = db.Column(db.Integer,unique=False,nullable=False)

    def __init__(self, score, token, attempts):
        self.score = score
        self.token = token
        self.attempts = attempts

class QuestionBank(db.Model):
    ques = db.Column(db.String(300), unique=False, nullable=False, primary_key=True)
    ans1 = db.Column(db.String(1), unique=False, nullable=False)
    ans2 = db.Column(db.String(1), unique=False, nullable=False)
    ans3 = db.Column(db.String(1), unique=False, nullable=False)
    ans4 = db.Column(db.String(1), unique=False, nullable=False)
    correct = db.Column(db.String(1), unique=False, nullable=False)

    def __init__(self, ques, ans1, ans2, ans3, ans4, correct):
        self.ques = ques
        self.ans1 = ans1
        self.ans2 = ans2
        self.ans3 = ans3
        self.ans4 = ans4
        self.correct = correct

    def __init__(self, email_id, token):
        self.email_id = email_id
        self.token = token

class Attempt_info(db.Model):
    email_id = db.Column(db.String(256), unique=False, nullable=False, primary_key=True)
    ques = db.Column(db.String(300), unique=False, nullable=False, primary_key=True)
    correct_attempts= db.Column(db.Integer, unique=False, nullable=False)
    wrong_attempts = db.Column(db.Integer,unique=False,nullable=False)

    def __init__(self, score, ques, correct_attempts, wrong_attempts):
        self.score = score
        self.ques = ques
        self.correct_attempts = correct_attempts
        self.wrong_attempts = wrong_attempts

   
@app.route('/')
def hello_world():
    db.create_all()
    return {"SUCCESS": "Hi! I am Sejal. Its working!"}

def getRandomHasheToken():
    x = ''.join(random.choice('0123456789ABCDEF') for i in range(16))
    return hashlib.sha256(x.encode()).hexdigest()

@app.route(BASE_ROUTE + 'register_user', methods=['POST'])
def register_user():
    body = flask.request.values
    company_name = body.getlist('company_name')[0]
    email_id = body.getlist('email_id')[0]
    name = body.getlist('name')[0]
    passwd_hash = body.getlist('passwd_hash')[0]

    company = List_of_Companies.query.get(company_name)
    if company is None:
        return {"ERROR": "Your Company is not a registered start-up "}

    # Check if the name or email isn't empty
    if len(name.strip()) == 0 or len(email_id.strip()) == 0:
        return {"ERROR": "Empty email or name received"}

    # Check if the email is of valid type or not
    if not re.search(email_regex, email_id):
        return {"ERROR": "Invalid email ID provided"}

    # Check if the teacher's email Id exists in database already
    exis_user = Users.query.get(email_id)
    if exis_user is not None:
        return {"ERROR": "User already exists with the same email ID"}

    # Registration Begins
    #  Adding the token for the teacher
    # First generate a random 16 character string and then create a hash out of it
    token = getRandomHasheToken()
    new_token = Token(email_id, token)
    # Stores the new token in the session, if anything bad happens to the future inserts then it will not get committed
    db.session.add(new_token)

    new_user = Users(name=name, email_id=email_id, passwd_hash=passwd_hash)
    db.session.add(new_user)
    
    # Committing the session if everything looks fine
    db.session.commit()
    x = new_user.as_dict()
    x['token'] = new_token.token
    return x

@app.route(BASE_ROUTE + 'login_user', methods=['POST'])
def login_user():
    body = flask.request.values
    email_id = body.getlist('email_id')[0]
    passwd_hash = body.getlist('passwd_hash')[0]
    # Check if the email is a valid email or not
    if not re.search(email_regex, email_id):
        return {"ERROR": "Invalid email ID provided"}
    # Fetch the existing token using the email and user_type
    exis_token = Token.query.filter_by(email_id=email_id).first()
    exis_user = Users.query.filter_by(email_id=email_id).first()
    if exis_token is None:
        return {"ERROR": "User doesn't exist"}
    elif exis_user.passwd_hash != passwd_hash:
        return {"ERROR": "Incorrect password provided"} # If the token exists then we need to match the hashes, return the token only if the hashes match else return ERROR
    x = exis_user.as_dict()
    x['token'] = exis_token.token
    return x

@app.route(BASE_ROUTE + 'update_score', methods=['POST'])
def update_score():
    body = flask.request.values
    email_id = body.getlist('email_id')[0]
    score = body.getlist('score')[0]
    # Fetch the existing token using the email
    exis_token = Token.query.filter_by(email_id=email_id).first()
    if exis_token is None:
        return {"ERROR": "User doesn't exist"}
    score = QuestionBank.query.get(email_id)
    score.score += 10
    score.attempts += 1
    # Committing the session if everything looks fine
    db.session.commit()
    return {"UPDATE: Rewarded Successfully"}

@app.route(BASE_ROUTE + 'deduct_score', methods=['POST'])
def deduct_score():
    body = flask.request.values
    email_id = body.getlist('email_id')[0]
    score = body.getlist('score')[0]
    # Fetch the existing token using the email
    exis_token = Token.query.filter_by(email_id=email_id).first()
    if exis_token is None:
        return {"ERROR": "User doesn't exist"}
    score = QuestionBank.query.get(email_id)
    score.score -= 10
    score.attempts += 1
    # Committing the session if everything looks fine
    db.session.commit()
    return {"UPDATE: Deducted Successfully"}

@app.route(BASE_ROUTE + 'get_ques', methods=['POST'])
def get_ques():
    body = flask.request.values
    token = body.getlist('token')[0]
    exis_token = Token.query.filter_by(token=token).first()
    if exis_token is None:
        return {"ERROR": "User doesn't exist"}
    return db.session.query(QuestionBank).all()

def get_valid_token(email_id):
    tokens_list = Token.query.filter_by(email_id=email_id).first()
    if tokens_list is None:
        return ''
    return tokens_list.token

@app.route(BASE_ROUTE + 'get_profile', methods=['POST'])
def get_profile():
    body = flask.request.values
    token = body.getlist('token')[0]
    email_id = body.getlist('email_id')[0]
    if get_valid_token(email_id) != token:
        return {"ERROR": "Incorrect token provided"}
    score = Scores.query.get(email_id)
    attempt = Scores.query.get(email_id)
    exis_user = Users.query.get(email_id)
    return {"User profile"}

@app.route(BASE_ROUTE + 'get_attempts', methods=['POST'])
def get_attempts():
    body = flask.request.values
    token = body.getlist('token')[0]
    email_id = body.getlist('email_id')[0]
    if get_valid_token(email_id) != token:
        return {"ERROR": "Incorrect token provided"}
    ques = Attempt_info.query.get(email_id)
    score = Scores.query.get(email_id)
    attempt = Scores.query.get(email_id)
    exis_user = Users.query.get(email_id)
    return {"User profile"}

if __name__ == '__main__':
    app.run()