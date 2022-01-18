from flask import Flask, render_template, request, redirect, url_for
import flask_login
from google.cloud import compute_v1
import sqlite3
import sys
import hashlib
import os



"""App initialisieren"""


app = Flask(__name__)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
app.secret_key = 'super secret string'  # Change this!



"""Funktion zum erstellen einer Datenbankverbindung"""


def db_connection():
    conn = None
    try:
        conn = sqlite3.connect('user.sqlite')
    except sqlite3.error as e:
        print(e)
    return conn



"""Die User Klasse"""


class User(flask_login.UserMixin):
    pass



"""Funktion zum laden von Usern"""


@login_manager.user_loader
def user_loader(name):
    conn = db_connection()
    cursor = conn.execute("SELECT * FROM user")
    users = [
        dict(name=row[0], password=row[1]) for row in cursor.fetchall()
    ]
    for u in users:
        if name == u['name']:
            user = User()
            user.id = name
            return user
    return


@login_manager.request_loader
def request_loader(request):
    name = request.form.get('name')
    conn = db_connection()
    cursor = conn.execute("SELECT * FROM user")
    users = [
        dict(name=row[0], password=row[1]) for row in cursor.fetchall()
    ]
    for u in users:
        if name == u['name']:
            user = User()
            user.id = name
            return user
    return



"""Anzeigefunktion für die Loginseite / Funktion zum Einloggen"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    conn = db_connection()
    cursor = conn.execute('SELECT * FROM user WHERE name=?', (request.form['name'],))
    users = [
        dict(name=row[0], password=row[1], salt=row[2]) for row in cursor.fetchall()
    ]

    name = request.form['name']
    password = request.form['password']

    key = hashlib.pbkdf2_hmac(
        'sha256',  # The hash digest algorithm for HMAC
        password.encode('utf-8'),  # Convert the password to bytes
        users[0]['salt'],  # Provide the salt
        100000,  # It is recommended to use at least 100,000 iterations of SHA-256
        dklen=128  # Get a 128 byte key
    )

    if key == users[0]['password']:
        user = User()
        user.id = name
        flask_login.login_user(user)
        return redirect(url_for('protected'))

    return 'Bad login'


# @app.route('/protected')
# @flask_login.login_required
# def protected():
#     return 'Logged in as: ' + flask_login.current_user.id



"""Anzeige Funktion für die Logoutseite / Funktion zum ausloggen."""


@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return 'Logged out'



"""Weiterleitung zur Loginseite, wenn nicht eingelogt."""



@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))



"""Anzeige für die Registerseite.
   """


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'password' in request.form:
        name = request.form['username']
        password = request.form['password']
        msg = createAccount(name, password)
    elif request.method == 'POST':
        msg = 'Füll bitte das Formular aus!'

    return render_template('register.html', msg=msg)



"""Validiert ob ein Account existiert, wenn nicht erstellt es ihn.
   Gibt eine passende Fehlermeldung zurück.
   Generiert zum Passwort einen Salt und Hasht die kombination beider.
   """


def createAccount(name, password):
    msg = ''
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE name=?', (name,))
    account = cursor.fetchone()

    if account:
        msg = 'Die Daten gibts leider schon!'
    elif not name or not password:
        msg = 'Füll bitte das Formular aus!'
    else:
        # Account existiert nicht

        # generiert salt
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac(
            'sha256',  # The hash digest algorithm for HMAC
            password.encode('utf-8'),  # Convert the password to bytes
            salt,  # Provide the salt
            100000,  # It is recommended to use at least 100,000 iterations of SHA-256
            dklen=128  # Get a 128 byte key
        )
        cursor.execute('INSERT INTO user(name, password, salt) VALUES (?, ?, ?)',
                       (name, key, salt,))
        cursor.close()
        msg = 'Du wurdest erfolgreich Registriert!'
    conn.commit()
    return msg



"""Hasht einen angegeben String mit SHA 256.
   """


def hash_sha256(text_string):
    text_string = hashlib.sha256(text_string.encode()).hexdigest()
    return text_string



"""Anzeigefunktion für die Indexseite"""


@app.route("/")
def index():
    return render_template("index.html")



"""Anzeigefunktion für alle Maschinentemplates.
   Login: erforderlich"""


@app.route("/templates", methods=['GET', 'POST'])
@flask_login.login_required
def template_site():
    if request.method == 'POST':
        create_instance_form_template(request.form.get("vm_erstellen"))
        return request.form.get("vm_erstellen")
        #return redirect("/machines")
    elif request.method == 'GET':
        templates = list_all_templates()
        return render_template("templates.html", templates=templates)



"""Anzteigefunktion für alle existierenden Maschinen.
   Login: erforderlich"""


@app.route("/machines", methods=['GET', 'POST'])
@flask_login.login_required
def machines_site():
    if request.method == 'POST':
        return "test"
    elif request.method == 'GET':
        machines = list_all_instance_names()
        return render_template("machines.html", machines=machines)



"""Funktion zum finden aller Instanzen.
   Parameter:
        projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
   Return: Liste der Instanznamen
   """


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



"""Funktion zum finden aller Machine-Images.
   Parameter:
        projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
   Return: Liste der Imagenamen
   """


def list_all_images(projekt="prj-kloos"):
    image_client = compute_v1.ImagesClient()
    test_request = compute_v1.ListImagesRequest(project=projekt)
    image_list = image_client.list(request=test_request)
    images = []
    for responce in image_list:
        images.append(responce.name)
    return images



"""Funktion zum finden aller Machin-Templates.
   Parameter:
        projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
   Return: Liste der Templatenamen
   """


def list_all_templates(projekt="prj-kloos"):
    template_client = compute_v1.InstanceTemplatesClient()
    request = compute_v1.ListInstanceTemplatesRequest(project=projekt)
    list = template_client.list(request)
    templates = []
    for responce in list:
        templates.append(responce.name)
    return templates



"""Funktion zum erstellen einer Instanzen.
   Parameter:
        template: 
        template: String, der Name der Vorlage, die verwendet werden soll
        projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
   Return: Liste der Instanznamen
   """


def create_instance_form_template(template:str, projekt="prj-kloos"):
    instance_client = compute_v1.InstancesClient()
    operation_client = compute_v1.ZoneOperationsClient()

    template_str = "projects/prj-kloos/global/instanceTemplates/" + template

    instance = compute_v1.Instance()
    name = ""
    for i in template.split("-")[1:]:
        name += i

    name = name + flask_login.current_user.id

    if name not in list_all_instance_names():
        return

    instance.name = name
    request = compute_v1.InsertInstanceRequest()
    request.instance_resource = instance
    request.project = projekt
    request.source_instance_template = template_str
    request.zone = "europe-west3-b"


    operation = instance_client.insert_unary(request=request)
    while operation.status != compute_v1.Operation.Status.DONE:
        operation = operation_client.wait(
            operation=operation.name, zone="europe-west3-b", project="prj-kloos"
        )
    if operation.error:
        print("Error during creation:", operation.error, file=sys.stderr)
    if operation.warnings:
        print("Warning during creation:", operation.warnings, file=sys.stderr)
    print(f"Instance {instance.name} created.")
    return(instance)



app.run(debug=True)