from app import app, db
from app.scripts import restart_db, killWeb
from app.models import User, Post, Comment, Subforum, Error
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from datetime import datetime, timedelta
from math import floor
from werkzeug.exceptions import HTTPException

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.context_processor
def inject_top5():
    return dict(top5=Subforum.query.filter(Subforum.approved==True).order_by(Subforum.post_count.desc()).limit(5), Post=Post, Comment=Comment, Subforum=Subforum)

@login_manager.user_loader
def user_loader(username):
    return User.query.get(username)

@app.route('/')
@app.route('/index', methods=["GET", "POST"])
def index():
    if request.method=="GET":
        if request.args.get('cat'): 
            category=request.args.get('cat')
        else:
            category="General"
        posts=Post.query.filter_by(forum=category).order_by(Post.pub_date.desc()).all()
        return render_template("index.html", posts=posts)
    target=request.form["forum_search"]
    forums=Subforum.query.filter(Subforum.name.contains(target)|Subforum.desc.contains(target)|Subforum.tags.contains(target)).order_by(Subforum.name.asc()).all()
    return render_template("index.html", forums=forums)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method=='GET':
        return redirect(url_for("login"))
    user=User(request.form["username"], request.form["password"], request.form["email"])
    try:
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Rejestracja zakończona pomyślnie", category="success")
    except:
        flash("Błąd - istnieje użytkownik o takiej nazwie", category="warning")
    return redirect(url_for("login"))

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method=='GET' and current_user.is_authenticated:
        flash ("Już zalogowano!", category="warning")
        return redirect(url_for("index"))
    if request.method == 'GET':
        return render_template('login.html')
    username=request.form["username"]
    password=request.form["password"]
    registered_user = User.query.filter_by(username=username, password=password).first()
    if registered_user is None:
        flash("Błąd, zła nazwa użytkownika lub hasło", category="warning")
        return redirect(url_for('login'))
    if registered_user.banned:
        if registered_user.ban_time > datetime.utcnow():
            time=registered_user.ban_time-datetime.utcnow()
            flash("Błąd, konto zostało zablokowane przez administratora. Pozostały czas: "+str(time.days)+" dni, "+str(floor(time.seconds/3600))+" godzin i "+str(floor((time.seconds/60)%60))+" minut.", category="warning")
            return redirect(url_for('login'))
        registered_user.banned=False
        db.session.commit()
    login_user(registered_user)
    flash("Logowanie zakończone sukcesem", category="success")
    return redirect(url_for("cpanel"))

@app.route('/logout')
def logout():
    logout_user()
    flash ("Wylogowano pomyślnie", category="success")
    return redirect(url_for("login"))   

@app.route('/add_post', methods=["GET", "POST"])
@login_required
def add_post():
    if request.method == "GET" and request.args.get("id"):
        return render_template("add_post.html", modpost=Post.query.filter_by(pub_date=request.args.get("id")).first())
    if request.method == "GET":
        return render_template("add_post.html")
    if request.method == "POST" and request.form["mod"]=="True":
        post = Post.query.filter_by(pub_date=request.args.get("id")).first()
        post.title=request.form["title"]
        post.tags=request.form["tags"]
        post.content=request.form["content"]
        post.modified = True
        try:
            db.session.commit()
            flash("Modyfikacja postu zakończona sukcesem.", category="success")
            return redirect(url_for("post", id=post.pub_date))
        except:
            flash("Modyfikacja postu nie powiodła się.", category="warning")
    else:
        post=Post(current_user.username,request.form["forum"],request.form["title"],request.form["tags"],request.form["content"])
        try:
            db.session.add(post)
            db.session.commit()
            flash("Utworzenie postu powiodło się.", category="success")
            return redirect(url_for("post", id=post.pub_date))
        except:
            flash("Utworzenie postu nie powiodło się.", category="warning")
    return redirect(url_for("add_post"))

@app.route("/add_sub", methods=["GET","POST"])
@login_required
def add_sub():
    if request.method=="GET":
        return render_template("add_sub.html")
    sub=Subforum(current_user.get_id(), request.form["name"], request.form["tags"], request.form["desc"])
    try:
        db.session.add(sub)
        db.session.commit()
        flash("Twoje subforum zostało dodane do listy oczekujących na akceptację.", category="success")
    except:
        flash("Błąd: Coś poszło nie tak, spróbuj ponownie później.", category="warning")
    return redirect(url_for("index", cat="General"))

@app.route('/post', methods=["GET","POST"])
def post():
    if request.method=="GET" and (request.args.get("del") or request.args.get("del_com")):
        if request.args.get("del_com"):
            try:
                com=Comment.query.filter_by(id=request.args.get("del_com")).first()
                buf=com.target
                post=Post.query.filter_by(pub_date=buf).first()
                post.com_count=post.com_count-1
                db.session.delete(com)
                db.session.commit()
                flash("Komentarz usunięty.", category="success")
            except:
                flash("Błąd, komentarz nie został usuniey.", category="warning")
            return redirect(url_for("post", id=buf))
        post=Post.query.filter_by(pub_date=request.args.get("del")).first()
        id=post.forum
        try:
            for comment in post.comments:
                db.session.delete(comment)
            sub=Subforum.query.filter_by(name=post.forum).first()
            sub.post_count=sub.post_count-1
            db.session.delete(post)
            db.session.commit()
            flash("Post został usunięty.", category="success")
            return redirect(url_for("index", cat=id))
        except:
            flash("Błąd: Post nie został usunięty.", category="warning")
            return redirect(url_for("post"+"?id="+id))
    if request.method == "GET":
        if request.args["id"]:
            post=Post.query.filter_by(pub_date=request.args.get("id")).first()
            comments=Comment.query.filter_by(target=post.pub_date).order_by(Comment.pub_date.desc()).all()
        return render_template("post.html", post=post, comments=comments)
    if request.method=="POST":
        id=request.args.get("id")
        try:
            target=Post.query.filter(Post.pub_date.contains(request.form["target"])).first()
            new_comment=Comment(target.pub_date,current_user.username, request.form["content"])
            db.session.add(new_comment)
            db.session.commit()
            flash("Komentarz dodany.", category="success")
        except:
            flash("Błąd. Komentarz nie został dodany.", category="warning")
    return redirect(url_for("post", id=id))

@app.route("/cpanel", methods=["GET","POST"])
def cpanel():
    if request.method=="GET":
        forums=Subforum.query.filter_by(author=current_user.username).order_by(Subforum.pub_date.desc()).all()
        posts=Post.query.filter_by(author=current_user.username).order_by(Post.pub_date.desc()).all()
        comments=Comment.query.filter_by(author=current_user.username).order_by(Comment.pub_date.desc()).all()
        if current_user.level>0:
            if request.args.get("user_id"):
                userlist=User.query.filter(User.username.contains(request.args["user_id"])).order_by(User.creation_date.desc()).all()
            else:
                userlist=User.query.order_by(User.creation_date.desc()).limit(50)
            if request.args.get("sub_id"):
                sublist=Subforum.query.filter(Subforum.name.contains(request.args["sub_id"]) | Subforum.tags.contains(request.args["sub_id"]) | Subforum.desc.contains(request.args["sub_id"])).order_by(Subforum.pub_date.desc()).all()
            else:
                sublist=Subforum.query.order_by(Subforum.pub_date.desc()).limit(50)
            if request.args.get("post_id"):
                postlist=Post.query.filter(Post.title.contains(request.args["post_id"]) | Post.tags.contains(request.args["post_id"] | Post.content.contains(request.args["post_id"]))).order_by(Post.pub_date.desc()).limit(50)
            else:
                postlist=Post.query.order_by(Post.pub_date.desc()).limit(50)
            errorlist=Error.query.order_by(Error.date.desc()).limit(50)
            return render_template("cpanel.html",forums=forums, posts=posts, comments=comments, userlist=userlist, sublist=sublist, postlist=postlist, errorlist=errorlist)
        return render_template("cpanel.html",forums=forums, posts=posts, comments=comments)
    if request.form.get("pass1"):
        if request.form["pass1"] and request.form["pass2"]:
            if request.form["pass1"]==request.form["pass2"]:
                try:
                    user=User.query.filter_by(username=current_user.username).first()
                    user.password=request.form["pass1"]
                    db.session.commit()
                    flash("Udało się zmienić hasło!", category="success")
                except:
                    flash("Zmiana hasła nie powiodła się.", category="warning")
            else:
                flash("Hasła z pola 1 i pola 2 nie są takie same!", category="warning")
    if request.form.get("action_target"):
        if request.form["action_target"]=="user":
            if request.form["action_type"] == "search":
                return redirect(url_for("cpanel", user_id=request.form["id"]))
            user=User.query.filter_by(username=request.form["id"]).first()
            if request.form["action_type"] == "del":
                try:
                    db.session.delete(user)
                    db.session.commit()
                    flash("Usunięto pomyślnie użytkownika "+user.username, category="success")
                except:
                    flash("Usunięcie nie powiodło się", category="warning")
            if request.form["action_type"] == "unban":
                try:
                    user.banned=False
                    db.session.commit()
                    flash("Odbanowanie użytkownika "+user.username+" zakończone sukcesem.", category="success")
                except:
                    flash("Odbanowanie użytkownika "+user.nickname+" zakończone niepowodzeniem.", category="warning")
            if request.form["action_type"] != "del" and request.form["action_type"] != "unban":
                try:
                    user.ban_time=datetime.utcnow()+timedelta(days=int(request.form["action_type"]))
                    user.banned=True
                    db.session.commit()
                    flash("Zbanowano pomyślnie na "+request.form["action_type"]+"dni.", category="success")
                except:
                    flash("Zbanowanie nie powiodło się", category="warning")
        if request.form["action_target"]=="sub":
            if request.form["action_type"] == "search":
                return redirect(url_for("cpanel", sub_id=request.form["id"]))
            if request.form["action_type"] == "approve":
                try:
                    sub=Subforum.query.filter_by(name=request.form["id"]).first()
                    sub.approved=True
                    db.session.commit()
                    flash("Subforum aktywne.", category="success")
                except:
                    flash("Aktywacja zawiodła", category="warning")
                return redirect(url_for("cpanel"))
            try:
                sub=Subforum.query.filter_by(name=request.form["id"]).first()
                for post in sub.posts:
                    for comment in post.comments:
                        db.session.delete(comment)
                    db.session.commit()
                    db.session.delete(post)
                db.session.commit()
                sub_name=sub.name
                db.session.delete(sub)
                db.session.commit()
                flash("Pomyślnie usunięto podforum '"+sub_name+"'.", category="success")
            except:
                flash("Usunięcie podforum nie powiodło się.", category="warning")
        if request.form["action_target"]=="post":
            if request.form["action_type"] == "search":
                return redirect(url_for("cpanel", post_id=request.form["id"]))
            try:
                post=Post.query.filter_by(pub_date=request.form.get("id")).first()
                for comment in post.comments:
                    db.session.delete(comment)
                db.session.commit()
                post_title=post.title
                sub=Subforum.query.filter_by(name=post.forum).first()
                sub.post_count=sub.post_count-1
                db.session.delete(post)
                db.session.commit()
                flash("Pomyślnie usunięto post '"+post_title+"'.", category="success")
            except:
                flash("Usunięcie postu nie powiodło się.", category="warning")
        if request.form["action_target"]=="error":
            if request.form.get("delAll"):
                try:
                    for error in Error.query.all():
                        db.session.delete(error)
                    db.session.commit()
                    flash("Wszystkie błędy usunięte.", category="success")
                except:
                    flash("Błąd podczas usuwania błędów.", categoru="warning")
            else:
                try:
                    err=Error.query.filter_by(date=request.form["id"]).first()
                    buf=err.date.isoformat(' ', "minutes")
                    db.session.delete(err)
                    db.session.commit()
                    flash("Pomyślnie usunięto błąd z "+buf+".", category="success")
                except:
                    flash("Usunięcie błędu nie powiodło się.", category="warning")
    if request.form.get("admin"):
        if request.form["admin"]=="0":
            restart_db()
        if request.form["admin"]=="1":
            killWeb()
    return redirect(url_for("cpanel"))


    
@app.errorhandler(HTTPException)
def error404(e):
    try:
        err=Error(e.code,e.name,e.description,request.headers.get("Referer"))
        db.session.add(err)
        db.session.commit()
        flash("Wygląda na to, że coś się zepsuło. Problem został zarejestrowany.", category="warning")
    except:
        flash("Wygląda na to, że coś się zepsuło.", category="warning")
    return redirect(url_for("index", cat="General"))