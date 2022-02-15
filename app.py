from flask import Flask, render_template, request, redirect, url_for, session
import flask_login
from google.cloud import compute_v1
import sqlite3
import hashlib
import os
from datetime import timedelta
import re
import machines

"""App initialisieren"""

app = Flask(__name__)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.refresh_view = 'relogin'
login_manager.needs_refresh_message = (u"Sitzung abgleaufen, bitte erneut einloggen")
login_manager.needs_refresh_message_category = "info"

app.secret_key = 'super secret string'  # Change this!


@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)


def db_connection():
    """Funktion zum erstellen einer Datenbankverbindung"""

    conn = None
    try:
        conn = sqlite3.connect('user.sqlite')
    except sqlite3.error as e:
        print(e)
    return conn


class User(flask_login.UserMixin):
    """Die User Klasse"""
    pass


@login_manager.user_loader
def user_loader(name):
    """Funktion zum laden von Usern"""
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Anzeigefunktion für die Loginseite / Funktion zum Einloggen"""

    msg = ""
    if request.method == 'GET':
        return render_template('login.html')

    conn = db_connection()
    cursor = conn.execute('SELECT * FROM user WHERE name=?', (request.form['name'],))
    users = [
        dict(name=row[0], password=row[1], salt=row[2]) for row in cursor.fetchall()
    ]

    if len(users) == 0:
        return render_template("login.html", msg="Dieser Nutzer existiert nicht!")

    name = request.form['name']
    password = request.form['password']

    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        users[0]['salt'],
        100000,
        dklen=128
    )

    if key == users[0]['password']:
        user = User()
        user.id = name
        flask_login.login_user(user)
        return redirect(url_for('index'))

    return render_template("login.html", msg="Nutzername oder Passwort inkorrekt")


@app.route('/logout')
def logout():
    """Anzeige Funktion für die Logoutseite / Funktion zum ausloggen."""

    flask_login.logout_user()
    return render_template('logout.html')


@login_manager.unauthorized_handler
def unauthorized_handler():
    """Weiterleitung zur Loginseite, wenn nicht eingelogt."""
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Anzeigefunktion für die Registerseite.
       """
    password_regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_])[A-Za-z\d@$!%*?&_]{8,}$"

    msg = ''

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and \
            re.match(password_regex, request.form.get('password')):
        name = request.form['username']
        password = request.form['password']
        msg = createaccount(name, password)
    # elif request.method == 'POST': #
    #     print(request.form.get("password"))
    #     msg = 'Füll bitte das Formular aus!'
    elif request.method == 'POST' and 'password' in request.form:
        msg = "Das Passwort muss mindestens 8 Zeichen lang sein, mindestens einen Großbuchstaben, einen Kleinbuchstaben, eine Zahl und eins dieser Zeichen enthalten [@$!%*?&_]"

    return render_template('register.html', msg=msg)


def createaccount(name, password):
    """Validiert ob ein Account existiert, wenn nicht erstellt es ihn.
       Gibt eine passende Fehlermeldung zurück.
       Generiert zum Passwort einen Salt und Hasht die kombination beider.
       """

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
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,
            dklen=128
        )
        cursor.execute('INSERT INTO user(name, password, salt) VALUES (?, ?, ?)',
                       (name, key, salt,))
        cursor.close()
        msg = 'Du wurdest erfolgreich Registriert!'
    conn.commit()
    return msg


@app.route("/")
@flask_login.login_required
def index():
    """Anzeigefunktion für die Indexseite.
       Login: Erforderlich"""

    return render_template("index.html")


@app.route("/templates", methods=['GET', 'POST'])
@flask_login.login_required
def template_site(msg: str = ""):
    """Anzeigefunktion für alle Maschinentemplates.
       Login: erforderlich"""
    zone_dict = list_all_zones()
    templates = list_all_templates()
    if request.method == 'POST':
        if not re.match('(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?)', request.form.get("name")):
            return render_template("templates.html", templates=templates, zone_dict=zone_dict,
                                   msg="Ungültiger Maschinenname: Der erste Buchstabe muss klein sein!")
        print(request.form.get("template"))
        if machines.create_instance_form_template(name=request.form.get("name"), template=request.form.get("template"),
                                                  zone=request.form.get("zone")) == "existiert bereits":
            return render_template("templates.html", templates=templates, zone_dict=zone_dict,
                                   msg="Eine Instanz mit diesem Namen existiert bereits")
        return redirect("/machines")
        # return request.form.get("name")
    elif request.method == 'GET':
        return render_template("templates.html", templates=templates, zone_dict=zone_dict, msg=msg)


@app.route("/machines", methods=['GET', 'POST'])
@flask_login.login_required
def machines_site():
    """Anzteigefunktion für alle existierenden Maschinen.
       Login: erforderlich"""

    if request.method == 'POST':
        maschinen = machines.list_all_instance()
        if "starten" in request.form:
            maschine = [m for m in maschinen if m["name"] == request.form.get("starten")][0]
            machines.start_instance(zone=maschine["zone"], instance_name=maschine["name"], project_id="prj-kloos")
            return redirect(url_for('machines_site'))
        elif "stoppen" in request.form:
            maschine = [m for m in maschinen if m["name"] == request.form.get("stoppen")][0]
            machines.stop_instance(zone=maschine["zone"], instance_name=maschine["name"], project_id="prj-kloos")
            return redirect(url_for('machines_site'))
        elif "löschen" in request.form:
            maschine = [m for m in maschinen if m["name"] == request.form.get("löschen")][0]
            machines.delete_instance(zone=maschine["zone"], instance_name=maschine["name"], project_id="prj-kloos")
            return redirect(url_for('machines_site'))
    elif request.method == 'GET':
        maschinen = machines.list_all_instance()
        user_machines = [m for m in maschinen if m["name"].split("-")[-1] == flask_login.current_user.id]
        return render_template("machines.html", machines=user_machines)


# @app.route("/create_template", methods=['GET', 'POST'])
# @flask_login.login_required
# def create_template_site():
#     # image_dict = {}
#     # image_dict["debian"] = list_all_images("debian-cloud")
#     # print(len(image_dict["debian"]))
#     images = [maschine["name"] for maschine in mashines.list_all_instance(projekt="prj-kloos")]
#     if request.method == 'POST':
#         name = request.form.get("name")
#         instance = request.form.get("image")
#         if create_template(name=name, source_instance=instance) == "existiert bereits":
#             return render_template("create_template.html",images=images, msg="vorlage existiert bereits")
#         return redirect("/templates")
#     else:
#         return render_template("create_template.html", images=images)


def list_all_zones(projekt: str = "prj-kloos"):
    """Funktion zum auflisten aller Verfügbaren Zonen
       :parameter: projekt: Das ausgewählte Projekt
       :returns: Verfügbare Zonen: Dict{List[]}
       """

    zone_client = compute_v1.ZonesClient()
    zone_request = compute_v1.ListZonesRequest()

    zone_request.project = projekt

    zone_dict = {}
    for responce in zone_client.list(zone_request):
        if responce.name.split("-")[0] not in zone_dict.keys():
            zone_dict[responce.name.split("-")[0]] = [responce.name]
        else:
            zone_dict[responce.name.split("-")[0]].append(responce.name)

    for region in zone_dict.keys():
        zone_dict[region] = sorted(zone_dict[region])
    sorted_dict = {}
    for elem in sorted(zone_dict.items()):
        sorted_dict[elem[0]] = zone_dict[elem[0]]
    return sorted_dict["europe"]


def list_all_images(projekt="prj-kloos"):
    """Funktion zum finden aller Machine-Images.
       Parameter:
            projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
       Return: Liste der Imagenamen
       """

    image_client = compute_v1.ImagesClient()
    image_request = compute_v1.ListImagesRequest()
    image_request.project = projekt
    image_list = image_client.list(request=image_request)
    images = []
    for responce in image_list:
        images.append(responce.name)
    return images


def list_all_templates(projekt="prj-kloos"):
    """Funktion zum finden aller Machine-Templates.
       Parameter:
            projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
       Return: Liste der Templatenamen
       """

    template_client = compute_v1.InstanceTemplatesClient()
    template_request = compute_v1.ListInstanceTemplatesRequest()
    template_request.project = projekt
    temp_list = template_client.list(template_request)
    templates = []
    for response in temp_list:
        templates.append(response.name)
    return templates


# def create_template(source_instance:str, name:str):
#     """Funktion zum Erstellen von Maschinen-Vorlagen
#        :parameter"""
#
#     print(list_all_templates())
#     for t in list_all_templates():
#         if name == t:
#             return "existiert bereits"
#             # return render_template("create_template.html", msg="Vorlage existiert bereits!")
#
#     template_client = compute_v1.InstanceTemplatesClient()
#     template_request = compute_v1.InsertInstanceTemplateRequest()
#     template_request.project = "prj-kloos"
#     instance_list = mashines.list_all_instance()
#     instance = {}
#     for i in instance_list:
#         if i["name"] == source_instance:
#             instance = i
#
#     instance_client = compute_v1.InstancesClient()
#     instance_request = compute_v1.GetInstanceRequest()
#
#     print(instance)
#     instance_request.instance = instance["name"]
#     instance_request.zone = instance["zone"].split("/")[1]
#     instance_request.project = "prj-kloos"
#
#     instance = instance_client.get(request=instance_request)
#     # print(instance)
#
#     template = compute_v1.InstanceTemplate()
#     template.source_instance = instance.self_link
#     template.name = name
#
#     # request.source_instance_template = template.name
#     template_request.instance_template_resource = template
#     #
#     template_client.insert_unary(request=template_request)
#     return None

app.run(debug=True, host="0.0.0.0")
