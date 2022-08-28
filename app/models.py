from app import db


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, index=True)
    content = db.Column(db.String, index=True)

    def __repr__(self):
        return f"{self.id}: {self.title}"
