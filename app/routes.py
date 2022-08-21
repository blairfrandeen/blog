from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    letter = "Q"
    user = {"username": "Kivo"}
    return render_template('index.html', letter=letter, user=user)
