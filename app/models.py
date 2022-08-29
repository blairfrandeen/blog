from datetime import datetime

from app import db


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, index=True)
    handle = db.Column(db.String, index=True)
    content = db.Column(db.String, index=True)
    post_ts = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    post_update_ts = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    hidden = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"{self.id}: {self.title}"