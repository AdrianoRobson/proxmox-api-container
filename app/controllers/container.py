
from app.utils.authorization import token_required
from flask_restplus import Resource, Namespace, fields
from flask import request, jsonify
import requests
import time
from flask_restx import fields
from functools import wraps
import os
from dotenv import load_dotenv
load_dotenv()


api = Namespace('Container', description='Containers creation and manager')

API_BASE_URL = f'https://{os.getenv("PROXMOX_NODE_IP")}:8006/api2/json/nodes/{os.getenv("PROXMOX_NODE_NAME")}/lxc'
API_AUTH = f'https://{os.getenv("PROXMOX_NODE_IP")}:8006/api2/json/access/ticket'
CREDENTIAL = {
    "username": f"{os.getenv('API_USER')}@{os.getenv('PROXMOX_NODE_NAME')}", "password": os.getenv("API_USER_PASSWORD")}


def get_data(endpoint, data):
    response = requests.post(endpoint, data=data, verify=False)
    response.raise_for_status()
    return response.json()["data"]


# Get ticket and CSRFPreventionToken
ticket = get_data(API_AUTH, CREDENTIAL)["ticket"]
csrf_token = get_data(API_AUTH, CREDENTIAL)["CSRFPreventionToken"]


# Function to retrieve information about all containers
def list_all_containers():
    endpoint = f"{API_BASE_URL}"
    response = requests.get(
        endpoint, cookies={"PVEAuthCookie": ticket}, verify=False)
    response.raise_for_status()

    containers = response.json()["data"]
    return containers


# Function to retrieve information about a specific container by ID
def get_container_info(container_id):
    endpoint = f"{API_BASE_URL}/{container_id}/config"
    response = requests.get(
        endpoint, cookies={"PVEAuthCookie": ticket}, verify=False)
    response.raise_for_status()
    is_container_locked(container_id)
    container_info = response.json()["data"]

    return container_info


# Function to check if a container is locked
def is_container_locked(container_id):
    endpoint = f"{API_BASE_URL}/{container_id}/status/current"
    response = requests.get(
        endpoint, cookies={"PVEAuthCookie": ticket}, verify=False)
    response.raise_for_status()
    if 'lock' in response.json()["data"]:
        return {"locked": True}
    else:
        return {"locked": False}


# Decorator for handling exceptions in routes
def handle_exceptions(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.HTTPError as e:
            return {"error": f"HTTP error occurred: {str(e)}"}, e.response.status_code
        except requests.RequestException as e:
            return {"error": f"Request error occurred: {str(e)}"}, 500
        except Exception as e:
            return {"error": f"Internal server error occurred: {str(e)}"}, 500
    return decorated_function


@api.route('/')
class ContainerListAll(Resource):
    @api.response(200, "Success")
    @api.doc('some operation', security='apikey')
    @token_required
    @handle_exceptions
    def get(self):
        return list_all_containers(), 200


@api.route('/<id>')
class ContainerIdInfo(Resource):
    @api.response(200, "Success")
    @api.doc('some operation', security='apikey')
    @token_required
    @api.doc(params={'id': 'The container id'},)
    @handle_exceptions
    def get(self, id):
        return get_container_info(id), 200


@api.route('/<id>/<command>')
class ContainerId(Resource):
    @api.response(200, "Success")
    @api.doc('some operation', security='apikey')
    @token_required
    @api.doc(params={'id': 'The container id'},)
    @api.doc(params={'command': 'start, stop, delete'},)
    @handle_exceptions
    def get(self, id: int, command: str):

        commands = ['start', 'stop', 'delete']

        if (command not in commands):
            return {"error": f"Bad Request: Invalid command passed in your route'{command}'. Valid commands are {', '.join(commands)}"}, 400

        if command in ["start", "stop"]:
            endpoint = f"{API_BASE_URL}/{id}/status/{command}"
            response = requests.post(endpoint, cookies={"PVEAuthCookie": ticket}, headers={
                "CSRFPreventionToken": csrf_token}, verify=False)
            response.raise_for_status()

        elif command == "delete":
            endpoint = f"{API_BASE_URL}/{id}"
            response = requests.delete(endpoint, cookies={"PVEAuthCookie": ticket}, headers={
                "CSRFPreventionToken": csrf_token}, verify=False)
            response.raise_for_status()

        return {'message': 'success'}, 200


@api.route('/<id>/edit')
class ContainerIdEdit(Resource):

    payload_model = api.model('ContainerEditModel', {
        "nameserver": fields.String(example="8.8.8.8,4.4.4.4"),
        "searchdomain": fields.String(example="hittelco.com.br"),
    })

    @api.response(200, "Success")
    @api.doc('some operation', security='apikey')
    @token_required
    @api.doc(params={'id': 'The container id'},)
    @api.expect(payload_model, validate=True)
    @handle_exceptions
    def put(self, id: int):
        data = request.json
        endpoint = f"{API_BASE_URL}/{id}/config"
        response = requests.put(endpoint, cookies={"PVEAuthCookie": ticket}, headers={
                                "CSRFPreventionToken": csrf_token}, data=data, verify=False)
        response.raise_for_status()

        return {'message': 'success'}, 200


@api.route('/create/up')
class ContainerCreateUp(Resource):

    payload_model = api.model('ContainerCreateUpModel', {
        "net0": fields.String(example="name=tnetVM_ID,bridge=vmbr0"),
        "ostemplate": fields.String(example="local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"),
        "storage": fields.String(example="local"),
        "cores": fields.String(example="1"),
        "cpuunits": fields.String(example="512"),
        "memory": fields.String(example="512"),
        "swap": fields.String(example="0"),
        "password": fields.String(example="91472432"),
        "hostname": fields.String(example="ctnodeapi"),
        "nameserver": fields.String(example="8.8.8.8,4.4.4.4"),
        "searchdomain": fields.String(example="hittelco.com.br"),
    })

    @api.response(201, "Success") 

    @api.doc('some operation', security='apikey')
    @token_required
    @api.expect(payload_model, validate=True)
    @handle_exceptions
    def post(self,):
        data = request.json

        vm_id = 1

        vm_id_list = sorted(
            list(map(lambda x: int(x.get("vmid")), list_all_containers())))
        print('vm_id_list: ', vm_id_list)

        if (len(vm_id_list) > 0):
            vm_id = vm_id_list[-1] + 1

        for key, value in data.items():
            if key == 'vmid':
                return {"error": f'Bad Request: The "vmid" property is automatically setting'}, 400

            if key in ["cores", "cpuunits", "memory", "swap"]:
                data[key] = int(value)

            if key == 'hostname':
                data[key] = value+f'{vm_id}'

            if 'VM_ID' in value:
                data[key] = value.replace('VM_ID', f'{vm_id}')

        aux_data = {
            "vmid": vm_id
        }

        data = {**data, **aux_data}

        # Create container
        endpoint = f"{API_BASE_URL}"
        response = requests.post(endpoint, cookies={"PVEAuthCookie": ticket}, headers={
            "CSRFPreventionToken": csrf_token}, data=data, verify=False)
        response.raise_for_status()
        print(f'Container id {vm_id} created!')

        # Check each 3 seconds if the container is locked before start
        while is_container_locked(vm_id)['locked']:
            print('*********** LOCKED ************')
            time.sleep(5)

        # Start container
        endpoint = f"{API_BASE_URL}/{vm_id}/status/start"
        response = requests.post(endpoint, cookies={"PVEAuthCookie": ticket}, headers={
            "CSRFPreventionToken": csrf_token}, verify=False)
        response.raise_for_status()
        print(f'Container id {vm_id} started!')

        return {'message': 'success', 'id': vm_id}, 201


@api.route('/create')
class ContainerCreate(Resource):

    payload_model = api.model('ContainerCreateModel',  {
        "net0": fields.String(example="name=tnet538,bridge=vmbr0"),
        "ostemplate": fields.String(example="local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"),
        "storage": fields.String(example="local"),
        "vmid": fields.String(example="538"),
        "cores": fields.String(example="1"),
        "cpuunits": fields.String(example="512"),
        "memory": fields.String(example="512"),
        "swap": fields.String(example="0"),
        "password": fields.String(example="988325936"),
        "hostname": fields.String(example="ctnodeapi538"),
        "nameserver": fields.String(example="8.8.8.8,4.4.4.4"),
        "searchdomain": fields.String(example="hittelco.com.br"),
    })

    @api.response(201, "Success")
    @api.doc('some operation', security='apikey')
    @token_required
    @api.expect(payload_model, validate=True)
    @handle_exceptions
    def post(self,):
        data = request.json

        for key, value in data.items():
            if key in ["cores", "cpuunits", "memory", "swap", "vmid"]:
                data[key] = int(value)

        endpoint = f"{API_BASE_URL}"
        response = requests.post(endpoint, cookies={"PVEAuthCookie": ticket}, headers={
            "CSRFPreventionToken": csrf_token}, data=data, verify=False)
        response.raise_for_status()
        return {'message': 'success'}, 201
