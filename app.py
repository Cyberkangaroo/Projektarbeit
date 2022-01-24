from flask import Flask, render_template, request, redirect, url_for, session
import flask_login
from google.cloud import compute_v1
import sqlite3
import sys
import hashlib
import os
from datetime import timedelta

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
        return redirect(url_for('index'))

    return "Bad login"


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

    msg = ''

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        name = request.form['username']
        password = request.form['password']
        msg = createaccount(name, password)
    elif request.method == 'POST':
        msg = 'Füll bitte das Formular aus!'

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


@app.route("/")
@flask_login.login_required
def index():
    """Anzeigefunktion für die Indexseite.
       Login: Erforderlich"""

    return render_template("index.html")


@app.route("/templates", methods=['GET', 'POST'])
@flask_login.login_required
def template_site():
    """Anzeigefunktion für alle Maschinentemplates.
       Login: erforderlich"""
    zone_dict = list_all_zones()
    if request.method == 'POST':
        print(request.form.get("template"))
        if create_instance_form_template(name=request.form.get("name"), template=request.form.get("template"),
                                         zone=request.form.get("zone")) == "existiert bereits":
            return "existiert bereits"
        return redirect("/machines")
        # return request.form.get("name")
    elif request.method == 'GET':
        templates = list_all_templates()
        return render_template("templates.html", templates=templates, zone_dict=zone_dict)


@app.route("/machines", methods=['GET', 'POST'])
@flask_login.login_required
def machines_site():
    """Anzteigefunktion für alle existierenden Maschinen.
       Login: erforderlich"""

    if request.method == 'POST':
        maschinen = list_all_instance()
        if "starten" in request.form:
            maschine = [m for m in maschinen if m["name"] == request.form.get("starten")][0]
            start_instance(zone=maschine["zone"], instance_name=maschine["name"], project_id="prj-kloos")
            return redirect(url_for('machines_site'))
        elif "stoppen" in request.form:
            maschine = [m for m in maschinen if m["name"] == request.form.get("stoppen")][0]
            stop_instance(zone=maschine["zone"], instance_name=maschine["name"], project_id="prj-kloos")
            return redirect(url_for('machines_site'))
        elif "löschen" in request.form:
            maschine = [m for m in maschinen if m["name"] == request.form.get("löschen")][0]
            delete_instance(zone=maschine["zone"], instance_name=maschine["name"], project_id="prj-kloos")
            return redirect(url_for('machines_site'))
    elif request.method == 'GET':
        machines = list_all_instance()
        user_mashines = [m for m in machines if m["name"].split("-")[-1] == flask_login.current_user.id]
        return render_template("machines.html", machines=user_mashines)


def list_all_instance(projekt="prj-kloos"):
    """Funktion zum finden aller Instanzen.
       Parameter:
            projekt: String, der Name des Projektes in dem gesucht werden soll(default: prj-kloos)
       Return: Liste der Instanzen
       """

    instance_client = compute_v1.InstancesClient()
    instance_request = compute_v1.AggregatedListInstancesRequest()
    instance_request.project = projekt
    agg_list = instance_client.aggregated_list(request=instance_request)
    machines = []

    for zone, response in agg_list:
        if response.instances:
            for instance in response.instances:
                machine = {"name": instance.name, "ip": instance.network_interfaces[0].access_configs[0].nat_i_p,
                           "status": instance.status, "zone": zone}
                machines.append(machine)
    return machines


def list_all_zones(projekt:str="prj-kloos"):
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
    return sorted_dict

def start_instance(zone: str, instance_name: str, project_id: str = "prj-kloos"):
    """Funktion zum Starten einer Instanz
       Parameter:
            zone: String, die zone in der sich die Instanz befindet
            instance_name: String, der Name der Instanz
            projekt: String der Name des Projektes
            """
    instance_client = compute_v1.InstancesClient()

    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.zone = zone.split("/")[1]

    start_request = compute_v1.types.StartInstanceRequest()
    start_request.instance = instance.name
    start_request.project = project_id
    start_request.zone = instance.zone

    instance_client.start_unary(
        request=start_request
    )

    return redirect("/mashines")


def stop_instance(zone: str, instance_name: str, project_id: str = "prj-kloos"):
    """Funktion zum Stoppen einer Instanz
       Parameter:
            zone: String, die zone in der sich die Instanz befindet
            instance_name: String, der Name der Instanz
            projekt: String der Name des Projektes
            """

    instance_client = compute_v1.InstancesClient()

    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.zone = zone.split("/")[1]

    stopp_request = compute_v1.types.StopInstanceRequest()
    stopp_request.instance = instance.name
    stopp_request.project = project_id
    stopp_request.zone = instance.zone

    instance_client.stop_unary(
        request=stopp_request
    )
    return redirect("/mashines")


def delete_instance(zone: str, instance_name: str, project_id: str = "prj-kloos"):
    """Funktion zum Löschen einer Instanz
       Parameter:
            zone: String, die zone in der sich die Instanz befindet
            instance_name: String, der Name der Instanz
            projekt: String der Name des Projektes
            """

    instance_client = compute_v1.InstancesClient()

    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.zone = zone.split("/")[1]

    delete_request = compute_v1.types.DeleteInstanceRequest()
    delete_request.instance = instance.name
    delete_request.project = project_id
    delete_request.zone = instance.zone

    instance_client.delete_unary(
        request=delete_request
    )
    return redirect("/mashines")


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
    """Funktion zum finden aller Machin-Templates.
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


def create_instance_form_template(name: str, template: str, zone: str="europe-west3-b", projekt="prj-kloos"):
    """Funktion zum erstellen einer Instanz.
       Parameter:
            name: Name der zuerstellenden Instanz
            template: String, der Name der Vorlage, die verwendet werden soll
            zone: Die gewünschte zone
            projekt: String, der Name des Projektes in dem erstellt werden soll(default: prj-kloos)
       Return: Die erstellte instanz
       """

    instance_client = compute_v1.InstancesClient()
    operation_client = compute_v1.ZoneOperationsClient()

    template_str = "projects/prj-kloos/global/instanceTemplates/" + template

    instance = compute_v1.Instance()

    name = name + "-" + flask_login.current_user.id

    for machine in list_all_instance():
        if machine["name"] == name:
            return "existiert bereits"

    instance.name = name
    create_request = compute_v1.InsertInstanceRequest()
    create_request.instance_resource = instance
    create_request.project = projekt
    create_request.source_instance_template = template_str
    create_request.zone = zone

    operation = instance_client.insert_unary(request=create_request)
    while operation.status != compute_v1.Operation.Status.DONE:
        operation = operation_client.wait(
            operation=operation.name, zone=zone, project="prj-kloos"
        )
    if operation.error:
        print("Error during creation:", operation.error, file=sys.stderr)
    if operation.warnings:
        print("Warning during creation:", operation.warnings, file=sys.stderr)
    print(f"Instance {instance.name} created.")
    return instance


app.run(debug=True)
