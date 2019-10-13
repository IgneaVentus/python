#-*- coding: utf-8 -*-
from app import db, app
from app.models import User, Post, Comment, Error, Subforum
from datetime import timedelta, datetime


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
    dummy = User('[user deleted]', 'laHraDHNJUXdyfMlNNl9','')
    db.session.add(user)
    db.session.commit()
    forums=[]
    forums.append( Subforum('admin', 'Główna', 'main admin general główna', 'Zawsze obcena kategoria dla każdego.'))
    forums.append( Subforum('admin', 'Gaming', 'gaming admin gry drużyny', 'Podforum dla tych, którzy lubią gry.'))
    forums.append( Subforum('admin', 'Sztuka', 'artyści admin sztuka rysowanie malowanie muzyka', 'Lubisz rysować, malować, może tworzysz muzykę albo tańczysz? Zapraszamy!'))
    forums.append( Subforum('admin', 'Anime', 'chińskie bajki admin anime japonia sztuka kultura', '#weeblife'))
    x=8
    for forum in forums:
        x-=1
        forum.approved=True
        forum.pub_date=datetime.utcnow()-timedelta(minutes=x)
        print (forum.pub_date)
        db.session.add(forum)
    db.session.commit()
    posts=[]
    posts.append( Post("admin", 'Główna', 'Witaj na stronie!', 'powitanie początek hello admin', 'Witaj na tym skromnym forum. Bajinga! to krzyżówka pomiędzy redditem a 4chanem - każdy użytkownik może założyć podforum, napisać post czy komentarz jednakże wszystkie posty są usuwane po 7 dniach. Strona nadal znajduje się w rozwoju wobec czego proszę nie przejmować się możliwymi błędami.\n\n#Administracja'))
    posts.append( Post("admin", 'Gaming', 'Zasady podforum Gaming.', 'rules zasady gaming admin', 'Witaj w kategorii Gaming!\nGdy tu jesteś, prosimy byś przestrzegał poniższych zasad:\n- Nie wysyłaj niepoprawnych treści (NSFW).\n- Nie uniżaj celowo innym użytkownikom\n- Nie zamieszczaj treści niezgodnych z prawem.\n\n#Administracja'))
    posts.append( Post("admin", 'Sztuka', 'Zasady podforum Sztuka.', 'powitanie początek hello admin', 'Witaj w kategorii Sztuka!\nGdy tu jesteś, prosimy byś przestrzegał poniższych zasad:\n- Nie wysyłaj niepoprawnych treści (NSFW).\n- Nie uniżaj celowo innym użytkownikom\n- Nie zamieszczaj treści niezgodnych z prawem\n\n#Administracja'))
    posts.append( Post("admin", 'Anime', 'Zasady podforum Anime.', 'powitanie początek hello admin', 'Witaj w kategorii Anime!\nGdy tu jesteś, prosimy byś przestrzegał poniższych zasad:\n- Nie wysyłaj niepoprawnych treści (NSFW).\n- Nie uniżaj celowo innym użytkownikom\n- Nie zamieszczaj treści niezgodnych z prawem\n\n#Administracja'))
    for post in posts:
        x-=1
        post.pub_date=datetime.utcnow()-timedelta(minutes=x)
        print(post.pub_date)
        post.sticky=True
        db.session.add(post)
    db.session.commit()
    kom = Comment(posts[0].pub_date, "admin", 'Komentarz testowy 1')
    kom2 = Comment(posts[0].pub_date, "admin", 'Komentarz testowy 2')
    kom3 = Comment(posts[1].pub_date, "admin", 'Komentarz testowy 3')
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

def remove_comment(comments):
    if (isinstance(comments, list)):
        for comment in comments:
            remove_comment(comment)
    else:
        db.session.delete(comments)
        Post.query.filter_by(pub_date=comments.target).first().sub_count() 
    db.session.commit()
    return True

def remove_post(posts):
    if (isinstance(posts, list)):
        for post in posts:
            remove_post(post)
    else:
        remove_comment(posts.comments)
        Subforum.query.filter_by(name=posts.forum).first().sub_count() 
        db.session.delete(posts)
    db.session.commit()
    return True

def remove_forum(forum):
    remove_post(forum.posts)
    db.session.delete(forum)
    db.session.commit()
    return True

def rename_queries(user):
    for forum in user.subforums:
        forum.author="[user deleted]"
    for post in user.posts:
        post.author="[user deleted]"
    for comment in user.comments:
        comment.author="[user deleted]"
    db.session.commit()
    return True

def remove_user(user, transfer):
    if transfer==True:
        if not rename_queries(user):
            return False
    else:
        for forum in user.subforums:
            remove_forum(forum)
    for ban in user.bans:
        db.session.delete(ban)
    db.session.delete(user)
    db.session.commit()
    return True