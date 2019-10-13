#-*- coding: utf-8 -*-
from app import app, db
from app.scripts import restart_db, killWeb, remove_comment, remove_post, remove_user, remove_forum
from app.models import User, Post, Comment, Subforum, Error, Ban
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, fresh_login_required
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from datetime import datetime, timedelta
from math import floor
from werkzeug.exceptions import HTTPException
import re

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Musisz się najpierw zalogować."
login_manager.login_message_category = "info"
login_manager.needs_refresh_message = "Ta strona wymaga ponownego zalogowania"
login_manager.refresh_view="login"

@app.context_processor
def inject_top5():
    return dict(top5=Subforum.query.filter(Subforum.approved.is_(True) & Subforum.name.isnot("Główna")).order_by(Subforum.post_count.desc()).limit(5), Post=Post, Comment=Comment, Subforum=Subforum, len=len)

@login_manager.user_loader
def user_loader(username):
    return User.query.get(username)

@app.route('/')
def first_index():
    return redirect(url_for("index", forum="Główna"))
@app.route('/<forum>', methods=["GET", "POST"])
def index(forum):
    if request.method=="GET":
        posts=Post.query.filter_by(forum=forum).order_by(Post.pub_date.desc()).all()
        return render_template("index.html", posts=posts)
    target=request.form["forum_search"]
    forums=Subforum.query.filter(Subforum.name.contains(target)|Subforum.desc.contains(target)|Subforum.tags.contains(target)).order_by(Subforum.name.asc()).all()
    return render_template("index.html", forums=forums)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method=='GET':
        return redirect(url_for("login"))
    username=request.form["username"]
    username.strip()
    username=re.sub("\s{2,}"," ",username)
    check=re.sub("\s","",username)
    if(not re.search("\S{3}", check)):
        flash("Uwaga, nick powinien być dłuższy niż 3 znaki, nie licząc białych znaków.", category="warning")
        return redirect(url_for("login"))
    else:
        check=re.findall("[<>@#$%*&^~\[\]\"\{\}]+", username)
        if (check):
            string="Uwaga, nick zawiera nieprawidłowe znaki: "
            first=True
            for letter in check:
                if first:
                    first=False
                    string+=letter
                else:
                    string+=", "+letter
            flash(string, category="warning")
            return redirect(url_for("login"))
        else:
            user=User(username, request.form["password"], request.form["email"])
            try:
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("Rejestracja zakończona pomyślnie", category="success")
            except:
                flash("Błąd - istnieje użytkownik o takiej nazwie", category="warning")
    return redirect(url_for("cpanel"))

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method=='GET' and not current_user.is_anonymous:
        flash ("Już zalogowano!", category="warning")
        dest_url = request.args.get('next')
        if not dest_url:
            dest_url="/Główna"
        return redirect(dest_url)
    if request.method == 'GET':
        return render_template('login.html')
    username=request.form["username"]
    password=request.form["password"]
    registered_user = User.query.filter_by(username=username, password=password).first()
    if registered_user is None:
        flash("Błąd, zła nazwa użytkownika lub hasło", category="warning")
        return redirect(url_for('login'))
    if registered_user.banned:
        ban_time=Ban.query.filter_by(target=registered_user.username).order_by(Ban.time_stop.asc()).first()
        if ban_time>0:
            flash("Błąd, konto zostało zablokowane przez administratora. Pozostały czas: "+str(ban_time.days)+" dni, "+str(floor(ban_time.seconds/3600))+" godzin i "+str(floor((ban_time.seconds/60)%60))+" minut.", category="warning")
            return redirect(url_for('login'))
        registered_user.banned=False
        db.session.commit()
    login_user(registered_user)
    flash("Logowanie zakończone sukcesem", category="success")
    dest_url = request.args.get('next')
    if not dest_url:
        dest_url="/cpanel"
    return redirect(dest_url)

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
            sub=Subforum.query.filter_by(name=post.forum).first()
            sub.add_count()
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
    return redirect(url_for("index", forum="Główna"))

@app.route('/p/<post>', methods=["GET","POST"])
def post(post):
    if request.method=="GET" and (request.args.get("del") or request.args.get("del_com")):
        if request.args.get("del_com"):
            com=Comment.query.filter_by(id=request.args.get("del_com")).first()
            buf=com.target
            flash("Komentarz usunięty.", category="success") if remove_comment(com) else flash("Błąd, komentarz nie został usunięty.", category="warning")
            return redirect(url_for("post", post=buf))
        post=Post.query.filter_by(pub_date=request.args.get("del")).first()
        id=post.forum
        if(remove_post(post)):
            flash("Post został usunięty.", category="success")
            return redirect(url_for("index", forum=id))
        else:
            flash("Błąd: Post nie został usunięty.", category="warning")
            return redirect(url_for("post",post=id))
    if request.method == "GET":
        post=Post.query.filter_by(pub_date=post).first()
        comments=Comment.query.filter_by(target=post.pub_date).order_by(Comment.pub_date.desc()).all()
        return render_template("post.html", post=post, comments=comments)
    if request.method=="POST":
        id=request.args.get("id")
        try:
            target=Post.query.filter(Post.pub_date.contains(request.form["target"])).first()
            new_comment=Comment(target.pub_date,current_user.username, request.form["content"])
            target.add_count()
            db.session.add(new_comment)
            db.session.commit()
            flash("Komentarz dodany.", category="success")
        except:
            flash("Błąd. Komentarz nie został dodany.", category="warning")
    return redirect(url_for("post", post=id))

@app.route("/u/<user>")
@login_required
def user_profile(user):
    user=User.query.filter_by(username=user).first()
    if (user):
        return render_template("user.html", user=user)
    else:
        flash("Nie ma takiego użytkownika!", category="warning")
        return redirect(request.args.get("referer"))

@app.route("/cpanel", methods=["GET","POST"])
@fresh_login_required
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
                flash("Usunięto pomyślnie użytkownika "+user.username, category="success") if(remove_user(user, True)) else flash("Usunięcie nie powiodło się", category="warning")
            if request.form["action_type"] == "del_hard":
                flash("Usunięto pomyślnie użytkownika "+user.username, category="success") if(remove_user(user, False)) else flash("Usunięcie nie powiodło się", category="warning")
            if request.form["action_type"] == "unban":
                try:
                    user.banned=False
                    db.session.commit()
                    flash("Odbanowanie użytkownika "+user.username+" zakończone sukcesem.", category="success")
                except:
                    flash("Odbanowanie użytkownika "+user.nickname+" zakończone niepowodzeniem.", category="warning")
            if request.form["action_type"] != "del" and request.form["action_type"] != "unban":
                try:
                    ban=Ban(user.username, datetime.utcnow()+timedelta(days=int(request.form["action_type"])))
                    user.banned=True
                    db.session.add(ban)
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
            sub=Subforum.query.filter_by(name=request.form["id"]).first()
            sub_name=sub.name
            flash("Pomyślnie usunięto podforum '"+sub_name+"'.", category="success") if remove_forum(sub) else flash("Usunięcie podforum nie powiodło się.", category="warning")
        if request.form["action_target"]=="post":
            print ("Flag 0")
            if request.form.get("action_type") == "search":
                print ("Flag 01")
                return redirect(url_for("cpanel", post_id=request.form["id"]))
            print ("Flag 02")
            post=Post.query.filter_by(pub_date=request.form.get("id")).first()
            print ("Flag 1")
            post_title=post.title
            print ("Flag 2")
            flash("Pomyślnie usunięto post '"+post_title+"'.", category="success") if remove_post(post) else flash("Usunięcie postu nie powiodło się.", category="warning")
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
            logout_user()
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
    return redirect(url_for("index", forum="Główna"))