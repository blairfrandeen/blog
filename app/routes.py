import datetime
from urllib.parse import urljoin
from flask import render_template, url_for, Markup, request
from feedwerk.atom import AtomFeed
from app import app
from app.models import Post


@app.route("/")
@app.route("/home")
def home():
    posts = Post.query.filter(~Post.hidden).order_by(Post.post_ts.desc()).all()
    for post in posts:
        post.datestr = datetime.datetime.date(post.post_ts).strftime("%-d %B, %Y")
        post.content = Markup(post.content).split("\n")[1]
    return render_template("index.html", posts=posts)


@app.route("/blog/<post_handle>")
def blog_post(post_handle):
    try:
        post = Post.query.filter(~Post.hidden, Post.handle == post_handle).order_by(
            Post.post_ts.desc()
        )[-1]
    except IndexError:  # no post found
        return render_template("404.html")

    post.datestr = datetime.datetime.date(post.post_ts).strftime("%-d %B, %Y")
    post.content = Markup(post.content)
    return render_template("post.html", post=post)


@app.route("/feed/")
def feed():
    feed = AtomFeed(title="Datum-B", feed_url=request.url, url=request.url_root)
    posts = Post.query.filter(~Post.hidden).order_by(Post.post_ts.desc()).all()
    for post in posts:
        feed.add(
            post.title,
            Markup(post.content).split("\n")[1],  # TODO: make summary function
            content_type="html",
            author="Blair Frandeen",
            updated=post.post_update_ts,
            published=post.post_ts,
            url=_get_abs_url(f"/blog/{post.handle}"),
        )

    return feed.get_response()


def _get_abs_url(url):
    """Return absolute URL by joining with base URL"""
    return urljoin(request.url_root, url)
