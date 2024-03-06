from flask_frozen import Freezer
from app import app, models
from app.models import Post, Visibility

freezer = Freezer(app)

@freezer.register_generator
def blog_post():
    for post in models.Post.query.filter(
        Post.visibility.in_([Visibility.PUBLISHED, Visibility.UNLISTED]),
    ):
        yield {"post_handle": post.handle}

if __name__ == '__main__':
    freezer.freeze()
