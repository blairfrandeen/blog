from datetime import datetime
from enum import IntEnum

from sqlalchemy import Enum

from app import db


class Visibility(IntEnum):
    HIDDEN = 0
    UNLISTED = 1
    PUBLISHED = 2


vis_enum = Enum(Visibility)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, index=True)
    handle = db.Column(db.String, index=True)
    content = db.Column(db.String, index=True)
    summary = db.Column(db.String, index=True)
    post_ts = db.Column(db.DateTime, index=True, default=datetime.today)
    post_update_ts = db.Column(db.DateTime, index=True, default=datetime.today)
    visibility = db.Column(vis_enum, nullable=False, default=Visibility.HIDDEN)

    def __repr__(self):
        return f"{self.id}: {self.handle} ({self.post_ts.strftime('%D %X')})"
