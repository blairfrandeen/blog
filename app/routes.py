import datetime
from flask import render_template, url_for, Markup
from app import app
from app.models import Post


@app.route("/")
@app.route("/index")
def index():
    posts = Post.query.filter(~Post.hidden).order_by(Post.post_ts.desc()).all()
    for post in posts:
        post.datestr = datetime.datetime.date(post.post_ts).isoformat()
        post.content = Markup(post.content)
    return render_template("index.html", posts=posts)


@app.route("/blog/<post_handle>")
def blog_post(post_handle):
    try:
        post = Post.query.filter(~Post.hidden, Post.handle == post_handle).order_by(
            Post.post_ts.desc()
        )[-1]
    except IndexError:  # no post found
        return render_template("404.html")

    post.datestr = datetime.datetime.date(post.post_ts).isoformat()
    post.content = Markup(post.content)
    return render_template("index.html", posts=[post])
