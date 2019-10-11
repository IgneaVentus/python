from app import db, datetime

class User(db.Model):
    #__tablename__ = "users"
    username = db.Column(db.String(25), primary_key=True, nullable=False)
    password = db.Column(db.String(30), nullable=False)
    mail = db.Column(db.String(30), nullable=True)
    creation_date = db.Column(db.DateTime)
    authenticated = db.Column(db.Boolean, default=False)
    banned = db.Column(db.Boolean, default=False)
    ban_time = db.Column(db.DateTime)
    level = db.Column(db.SmallInteger, default=0)

    posts = db.relationship("Post", backref=db.backref("user_posts",lazy=True))
    comments = db.relationship("Comment", backref=db.backref("user_comments",lazy=True))
    subforums = db.relationship("Subforum", backref=db.backref("created_forums", lazy=True))
    
    def __init__(self, username, password, email):
        self.username=username
        self.password=password
        self.mail=email
        self.creation_date=datetime.utcnow().replace(microsecond=0)

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return self.authenticated

    def get_id(self):
        return self.username

    def __repr__(self):
        return '<User %r>' % self.username

    def is_mod(self):
        if self.level==1:
            return True
        return False

    def is_admin(self):
        if self.level==2:
            return True
        return False

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.DateTime, db.ForeignKey('post.pub_date'), nullable=False)
    author = db.Column(db.String(25), db.ForeignKey('user.username'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self,target,author,content):
        self.target=target
        self.author=author
        self.content=content
        Post.query.filter_by(pub_date=target).first().add_count()

    def __repr__(self):
        return '<Comment: %r>' % self.id

class Post(db.Model):
    author = db.Column(db.String(25), db.ForeignKey('user.username'), nullable=False)
    title = db.Column(db.String(40), nullable=False)
    content = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, primary_key=True, default=datetime.utcnow)
    tags = db.Column(db.String(20), nullable=True)
    forum = db.Column(db.String(30), db.ForeignKey("subforum.name"), nullable=False)
    modified = db.Column(db.Boolean, default=False)
    com_count = db.Column(db.Integer, default=0)

    comments = db.relationship('Comment',backref=db.backref('comments',lazy=True))
    
    def __init__(self,author,forum,title,tags,content):
        self.author=author
        self.title=title
        self.content=content
        self.tags=tags
        self.forum=forum
        Subforum.query.filter_by(name=forum).first().add_count()

    def __repr__(self):
        return '<Title: %r>' % self.title

    def get_id(self):
        return self.pub_date

    def is_modified(self):
        return self.modified

    def add_count(self):
        self.com_count=self.com_count+1
        return True
    
    def sub_count(self):
        self.com_count=self.com_count-1
        return True

class Subforum(db.Model):
    author = db.Column(db.String(25), db.ForeignKey("user.username"), nullable=False)
    name = db.Column(db.String(30),primary_key=True ,nullable=False)
    tags = db.Column(db.String(20))
    desc = db.Column(db.String(120), nullable=False)
    pub_date = db.Column(db.DateTime, default=datetime.utcnow)
    post_count = db.Column(db.Integer, default=0)
    approved = db.Column(db.Boolean, default=False)
    
    posts = db.relationship('Post',backref=db.backref('posts',lazy=True))

    def __init__(self, author, name, tags, desc):
        self.author=author
        self.name=name
        self.tags=tags
        self.desc = desc

    def __repr__(self):
        return '<Subforum: %r>' % self.name

    def add_count(self):
        self.post_count=self.post_count+1
        return True
    
    def sub_count(self):
        self.post_count=self.post_count-1
        return True

class Error(db.Model):
    date=db.Column(db.DateTime, primary_key=True, default=datetime.utcnow)
    code=db.Column(db.String(3), nullable=False)
    name=db.Column(db.String(12), nullable=False)
    desc=db.Column(db.Text, nullable=False)
    site=db.Column(db.Text, nullable=False)

    def __init__(self, code, name, desc, site):
        self.code=code
        self.name=name
        self.desc=desc
        self.site=site
