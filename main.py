#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from google.appengine.ext import db
import time
import hashlib

# Creates a reference to templates dir
template_dir = os.path.join(os.path.dirname(__file__),'templates')

#Creates a reference to jinja2 environment
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
				autoescape=True)

class Blog(db.Model):
	title = db.StringProperty(required = True)
	blog = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True, indexed=True)
	blog_id = db.IntegerProperty(required=True)


class User(db.Model):
	user_id = db.IntegerProperty(required=True)
	user_name=db.StringProperty(required=True)
	password = db.StringProperty(required=True)
	email=db.StringProperty()


class Handler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.out.write(*a,**kw)

	def render_str(self,template,**params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self,template,**kw):
		self.write(self.render_str(template,**kw))

	def new_id(self,row_count):
		blog_id = 1000+row_count
		return blog_id

	def new_user_id(self,row_count):
		user_id = 5000+row_count
		return user_id

	def hashme(self,password):
		return hashlib.sha256(password).hexdigest()

class BlogHandler(Handler):
    def get(self):
    	if (db.GqlQuery("select * from Blog").count()) > 0:
	    	blogs = db.GqlQuery("select * from Blog order by created desc").fetch(limit=10)
	    	self.render("blog_front.html",blogs=blogs)

class SignUp(Handler):
	def get(self):
		# Setting a cookie in response header as soon as a request is received to sign up page
		users_count = db.GqlQuery("select * from User").count()
		user_id = self.new_user_id(users_count)
		cookie_value=str(user_id)+'|'+str(self.hashme(str(user_id)))
		self.response.headers.add_header('set-cookie','user_id=%s; path=/' % cookie_value)
		self.render("sign_up.html")
	def post(self,*args,**kw):
		username = self.request.get("username")
		password=self.request.get("password")
		verify_password = self.request.get("verify")
		email = self.request.get("email")
		users_count = db.GqlQuery("select * from User").count()
		user_id = self.new_user_id(users_count)
		if username and password and (password == verify_password):
			user_entry = User(user_name=username, password = self.hashme(password), user_id=user_id,email=email)
			user_entry.put()
			#time.sleep(2)
			self.redirect('/blog/welcome')
		elif username and (password != verify_password):
			error = "Password mismatch !!! Please retry"
			self.render("sign_up.html",username=username,password=password, verify_password=verify_password,error=error)
		else:
			error = "Both username and password required. Please give all required details"
			self.render("sign_up.html",username=username,password=password, verify_password=verify_password,error=error)			

class Welcome(Handler):
	def get(self):
		cookie_value = self.request.cookies.get('user_id')
		user_id=cookie_value.split('|')[0]
		username=db.GqlQuery("select * from User where user_id="+user_id).get().user_name
		self.render("welcome.html",username=username)

class NewPostHandler(Handler):
	def get(self):
		self.render("new_post.html")
	def post(self,*args, **kw):
		title=self.request.get("subject")
		blog=self.request.get("content")
		error = "Both title and blog should present"
		if title and blog:
			blogs_count = db.GqlQuery("select * from Blog").count()
			blog_id = self.new_id(blogs_count)
			blog_entry = Blog(title=title, blog=blog, blog_id=blog_id)
			blog_entry.put()
			redirect_url = '/blog/'+str(blog_id)
			self.redirect(redirect_url)
		else:
			self.render("new_post.html", title=title, blog=blog, error=error)

class PermaLink(Handler):
	def get(self,blog_id):
		# Get the latest blog entry from Blog table using newly generated blog_id. 
		# I can do this by 'select * from Blog order by created desc'.fetch(limit=1)
		
		blog = db.GqlQuery("select * from Blog where blog_id ="+ str(blog_id)).get()
		
		# Rendering Permalink page with details of title (Subject) and Blog (Content)
		self.render("blog_details.html",title=blog.title,blog=blog.blog)
	
	def post(self,*a,**kw):
		self.render("blog_details.html")

app = webapp2.WSGIApplication([
	('/blog/signup', SignUp),
    ('/blog', BlogHandler),
    ('/blog/newpost', NewPostHandler),
    ('/blog/([0-9]+)', PermaLink),
    ('/blog/welcome', Welcome)
], debug=True)
