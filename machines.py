from google.cloud import compute_v1
import flask_login
import sys
from flask import redirect


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


def create_instance_form_template(name: str, template: str, zone: str = "europe-west3-b", projekt="prj-kloos"):
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
