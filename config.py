import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # TODO: Make this an actual secret
    SECRET_KEY = (
        os.environ.get("SECRET_KEY")
        or "6b020b802d2a6b4128635201c40e59fea21440b979da3097286edc39fb0d6c04"
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "blog.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
