import datetime
from flask import render_template, url_for, Markup
from app import app
from app.models import Post


@app.route("/")
@app.route("/index")
def index():
    posts = [
        {
            "title": "Time to Dual Class",
            "date": "2022-07-25",
            "intro": "I've been a mechanical engineer for nearly a decade, and it's time to branch out. My near-term focus is to branch my career towards software engineering while continuing to leverage my mechanical engineering skillset. In this post I'll explore my discontent with my current employment, which stems from geographic requirements, lack of desirable upward mobility, and knowledge-management practices that could use improvement.",
        },
        {
            "title": "False Starts",
            "date": "2022-08-25",
            "intro": "I have had a few false starts in my coding journey. The first started in late 2017. I came across Free Code Camp and started doing some of their JavaScript tutorials. I practiced doing short challenges on CodeWars, as I figured this would be a good way to build some fundamentals. I gave up on JS after not very long - I could swing it if I wanted to, but it isn't very applicable to engineering, and I didn't want to be a web developer.",
        },
    ]
    posts = Post.query.filter(~Post.hidden).order_by(Post.post_ts.desc()).all()
    for post in posts:
        post.datestr = datetime.datetime.date(post.post_ts).isoformat()
        post.content = Markup(post.content)
    return render_template("index.html", posts=posts)
