from app import db
from app.models import Post
from datetime import datetime, timedelta

today=datetime.utcnow()
post=Post.query.first()

posts=Post.query.filter((today-Post.pub_date)>timedelta(days=14)).all()
i=0
for post in posts:
    for comment in post.comments:
        db.session.delete(comment)
    db.session.delete(post)
    i+=i
db.session.commit()

print ("Wyczyszczono "+str(i)+" postów.")