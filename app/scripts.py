from app import db, app
from app.models import User, Post, Comment, Error, Subforum


def purge_db():
    db.init_app(app)
    db.drop_all()  
    db.create_all()
    admin = User('admin', 'template','')
    admin.level = 2
    db.session.add(admin)
    db.session.commit()
    print("Zakończono czyszczenie bazy danych")

def refill_db():
    user = User('user', 'user','')
    user.level = 0
    db.session.add(user)
    db.session.commit()
    forum = Subforum('admin', 'General', '', 'Zawsze obcena kategoria dla każdego.')
    forum.approved=True
    db.session.add(forum)
    db.session.commit()
    post = Post("admin", 'General', 'Post testowy', 'test', 'Jeżeli widzisz ten post, najpewniej coś na stronie się kłóci.\nZignoruj go.')
    db.session.add(post)
    db.session.commit()
    kom = Comment(post.pub_date, "admin", 'Komentarz testowy 1')
    kom2 = Comment(post.pub_date, "admin", 'Komentarz testowy 2')
    kom3 = Comment(post.pub_date, "admin", 'Komentarz testowy 3')
    db.session.add(kom)
    db.session.add(kom2)
    db.session.add(kom3)
    db.session.commit()
    print("Zakończono wypełnianie bazy danych podstawowymi danymi testowymi")

def restart_db():
    purge_db()
    refill_db()

def killWeb():
    exit()