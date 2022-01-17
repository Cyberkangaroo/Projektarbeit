from flask import Flask, render_template, request, redirect
from google.cloud import compute_v1
import sys


app = Flask("prj-kloos")

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


def create_instance_form_template(template:str, projekt="prj-kloos"):
    instance_client = compute_v1.InstancesClient()
    operation_client = compute_v1.ZoneOperationsClient()

    template_str = "projects/prj-kloos/global/instanceTemplates/" + template

    instance = compute_v1.Instance()
    name = ""
    for i in template.split("-")[1:]:
        name += i

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

#create_instance_form_template(template="template-prj-kloos-jupyter-spark", projekt="prj-kloos")

app.run(debug=True)