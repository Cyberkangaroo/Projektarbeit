from flask import Flask, render_template, request, redirect, url_for
import flask_login
from google.cloud import compute_v1
import sys


app = Flask(__name__)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
app.secret_key = 'super secret string'  # Change this!

users = {'foo@bar.tld': {'password': 'secret'}}

class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return

    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in users:
        return

    user = User()
    user.id = email
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'/>
                <input type='password' name='password' id='password' placeholder='password'/>
                <input type='submit' name='submit'/>
               </form>
               '''

    email = request.form['email']
    if request.form['password'] == users[email]['password']:
        user = User()
        user.id = email
        flask_login.login_user(user)
        return redirect(url_for('protected'))

    return 'Bad login'


@app.route('/protected')
@flask_login.login_required
def protected():
    return 'Logged in as: ' + flask_login.current_user.id

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'

# @login_manager.user_loader
# def load_user(user_id):
#     return User.get(user_id)
#
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     # Here we use a class of some kind to represent and validate our
#     # client-side form data. For example, WTForms is a library that will
#     # handle this for us, and we use a custom LoginForm to validate.
#     form = LoginForm()
#     if form.validate_on_submit():
#         # Login and validate the user.
#         # user should be an instance of your `User` class
#         login_user(user)
#
#         flask.flash('Logged in successfully.')
#
#         next = request.args.get('next')
#         # is_safe_url should check if the url is safe for redirects.
#         # See http://flask.pocoo.org/snippets/62/ for an example.
#         if not is_safe_url(next):
#             return flask.abort(400)
#
#         return flask.redirect(next or flask.url_for('index'))
#     return flask.render_template('login.html', form=form)



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/templates", methods=['GET', 'POST'])
def template_site():
    if request.method == 'POST':

        return request.form.get("vm_erstellen")
        #return redirect("/machines")
    elif request.method == 'GET':
        templates = list_all_templates()
        return render_template("templates.html", templates=templates)


@app.route("/machines", methods=['GET', 'POST'])
def machines_site():
    if request.method == 'POST':
        return "test"
    elif request.method == 'GET':
        machines = list_all_instance_names()
        return render_template("machines.html", machines=machines)




def list_all_instance_names(projekt="prj-kloos"):
    instance_client = compute_v1.InstancesClient()
    request = compute_v1.AggregatedListInstancesRequest(project=projekt)
    agg_list = instance_client.aggregated_list(request=request)

    names = []
    for zone, response in agg_list:
        if response.instances:
            # all_instances[zone] = response.instances
            for instance in response.instances:
                names.append(instance.name)

    return names

def list_all_images(projekt="prj-kloos"):
    image_client = compute_v1.ImagesClient()
    test_request = compute_v1.ListImagesRequest(project=projekt)
    image_list = image_client.list(request=test_request)
    images = []
    for responce in image_list:
        images.append(responce.name)
    return images

def list_all_templates(projekt="prj-kloos"):
    template_client = compute_v1.InstanceTemplatesClient()
    request = compute_v1.ListInstanceTemplatesRequest(project=projekt)
    list = template_client.list(request)
    templates = []
    for responce in list:
        templates.append(responce.name)
    return templates


# def create_instance_form_template(template:str, projekt="prj-kloos"):
#     instance_client = compute_v1.InstancesClient()
#     operation_client = compute_v1.ZoneOperationsClient()
#
#     template_str = "projects/prj-kloos/global/instanceTemplates/" + template
#
#     instance = compute_v1.Instance()
#     name = ""
#     for i in template.split("-")[1:]:
#         name += i
#
#     instance.name = name
#
#     request = compute_v1.InsertInstanceRequest()
#     request.instance_resource = instance
#     request.project = projekt
#     request.source_instance_template = template_str
#     request.zone = "europe-west3-b"
#
#
#     operation = instance_client.insert_unary(request=request)
#     while operation.status != compute_v1.Operation.Status.DONE:
#         operation = operation_client.wait(
#             operation=operation.name, zone="europe-west3-b", project="prj-kloos"
#         )
#     if operation.error:
#         print("Error during creation:", operation.error, file=sys.stderr)
#     if operation.warnings:
#         print("Warning during creation:", operation.warnings, file=sys.stderr)
#     print(f"Instance {instance.name} created.")
#     return(instance)



app.run(debug=True)