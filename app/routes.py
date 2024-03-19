import datetime
from urllib.parse import urljoin
from flask import render_template, Markup, request
from feedwerk.atom import AtomFeed
from app import app
from app.models import Post, Visibility


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/")
def home():
    posts = (
        Post.query.filter(Post.visibility == Visibility.PUBLISHED)
        .order_by(Post.post_ts.desc())
        .all()
    )
    for post in posts:
        post.datestr = datetime.datetime.date(post.post_ts).strftime("%-d %B, %Y")
        post.summary = Markup(post.summary)
    return render_template("index.html", posts=posts)


@app.route("/blog/<post_handle>")
def blog_post(post_handle):
    post = (
        Post.query.filter(
            Post.visibility.in_([Visibility.PUBLISHED, Visibility.UNLISTED]),
            Post.handle == post_handle,
        )
        .order_by(Post.post_ts.desc())
        .first()
    )
    if not post:
        return render_template("404.html")

    post.datestr = datetime.datetime.date(post.post_ts).strftime("%-d %B, %Y")
    post.content = Markup(post.content)
    return render_template("post.html", post=post)


@app.route("/feed")
def feed():
    feed = AtomFeed(title="Blair Frandeen", feed_url=request.url, url=request.url_root)
    posts = (
        Post.query.filter(Post.visibility == Visibility.PUBLISHED)
        .order_by(Post.post_ts.desc())
        .all()
    )
    for post in posts:
        feed.add(
            post.title,
            Markup(post.content),
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
