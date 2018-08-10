# -*- coding:utf-8 -*-
import os
import sys
import time
import base64
import sqlite3

import tornado.web
import tornado.httpserver
from tornado.web import URLSpec
import core.aiservices as AI

handlers = list()
setting = dict(
    compress_response = True,
    static_path = os.path.join(os.getcwd(), "static/assets"),
    template_path = os.path.join(os.getcwd(), "template"),
    # xsrf_cookies = True,
    # debug = True,
    cookie_secret = "919547850f4e497887d4e0d22a67e8a0",
    login_url = "/login",
    static_url_prefix = "/assets/",
    static_handler_args = dict(default_filename="index.html")  # 当一个目录被请求时，自动地伺服index.html文件
)

db_user = sqlite3.connect("db/user.db")

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        # 返回类型str 或者NoneType
        userName = self.get_secure_cookie('userName')
        if isinstance(userName, bytes):
            return userName.decode(encoding='utf-8')
        return None

class EntryHandler(BaseHandler):
    """只有被认证成功的用户才会被重定向到/welcome，否则定向到login_url指定的路径"""
    @tornado.web.authenticated
    def get(self):
        self.redirect("/welcome")


class RegisterHandler(BaseHandler):
    def initialize(self, db):
        self.db = db
    
    def prepare(self):
        self.cursor = self.db.cursor()
    
    def get(self):
        self.render("register.html")
    
    def post(self):
        userName = self.get_argument("userName", None)
        passWord = self.get_argument("passWord", None)
        print(userName, passWord)
        if all((userName, passWord)):
            sql = "SELECT username FROM login WHERE username=?"
            beforeRegQueryResult = self.cursor.execute(sql, (userName,))  # 返回int类型
            if beforeRegQueryResult:
                kwargs = dict()
                kwargs["userName"] = userName
                self.render("duplicatedRegisterUser.html", **kwargs)
            else:
                sql = "INSERT INTO login(username, password) VALUES(?, ?)"
                try:
                    insertResult = self.cursor.execute(sql, (userName, passWord))
                    if insertResult:
                        self.set_secure_cookie("userName", userName,
                                               expires=time.time() + 6 * 60 * 60)
                        self.redirect("/welcome")
                except Exception:
                    self.redirect("/wrong")
        else:
            self.redirect("/wrong")
    
    def on_finish(self):
        self.cursor.close()


class HelpHandler(BaseHandler):
    def get(self):
        self.render("help.html")

class LoginHandler(BaseHandler):
    def initialize(self, db):
        self.db = db
    
    def prepare(self):
        self.cursor = self.db.cursor()

    def get(self):
        userName = self.get_argument('user-name', default=None, strip=True)
        passWord = self.get_argument('user-password', default=None, strip=True)
        print("username: {0}".format(userName))
        print("password: {0}".format(passWord))
        if not all((userName, passWord)):
            self.set_header("Content-Type", "text/html")
            self.render("login.html")
        else:
            sql = "SELECT username, password FROM user_table WHERE username=? AND password=?"
            self.cursor.execute(sql, (userName, passWord))
            if len(self.cursor.fetchall()) == 1:
                self.set_secure_cookie("userName", userName, expires=time.time() + 6 * 60 * 60)
                self.redirect("/welcome")
            else:
                self.redirect("/login", permanent=False)
    
    def on_finish(self):
        self.cursor.close()

class WelcomeHandler(BaseHandler):
    def prepare(self):
        pass
    
    def get(self):
        userName = self.current_user
        if isinstance(userName, str):
            kwargs = dict()
            kwargs["userName"] = userName
            print("self.current_user: {0}".format(self.current_user))
            self.render("home.html", **kwargs)
        else:
            self.set_header("Content-Type", "text/html")
            self.redirect("/login")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect("/")


class WrongHandler(BaseHandler):
    def get(self):
        self.render("wrong.html")

handlers.extend([
    URLSpec(r"/", EntryHandler, name="enterPoint"),
    URLSpec(r"/register", RegisterHandler, dict(db=db_user), name="registerHandler"),
    URLSpec(r"/help", HelpHandler, name="helpHandler"),
    URLSpec(r"/login", LoginHandler, dict(db=db_user), name="loginHandler"),
    URLSpec(r"/welcome", WelcomeHandler, name="welcomeHandler"),
    URLSpec(r"/logout", LogoutHandler, name="logoutHandler"),
    URLSpec(r"/wrong", WrongHandler, name="wrongHandler"),
    URLSpec(r"/ai/train", AI.TrainHandler, name="trainHandler"),
    URLSpec(r"/ai/history", AI.HistoryHandler, name="historyHandler"),
    URLSpec(r"/ai/model", AI.ModelHandler, name="modelHandler"),
    URLSpec(r"/ai/mock/data", AI.MockHandler, name="mockHandler"),
    URLSpec(r"/ai/mock/preview", AI.PreviewHandler, name="previewHandler"),
    URLSpec(r"/ai/cancel", AI.CancelTrainHandler, name="cancelHandler"),
    URLSpec(r"/ai/query/request", AI.QueryRequestHandler, name="queryRequestHandler")
])

app = tornado.web.Application(
    handlers = handlers,
    **setting
)
