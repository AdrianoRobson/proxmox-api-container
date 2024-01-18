from flask import Flask, Blueprint
from flask_restplus import Api
from werkzeug.middleware.proxy_fix import ProxyFix 
from app.controllers.container import api as home_ns 
from app.utils.authorization import token_required 

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
blueprint = Blueprint('api', __name__)
app.register_blueprint(blueprint)

authorizations = {
    'apikey': {
        'name': "X-API-KEY",
        'in': "header",
        'type': "apiKey",
        'description': "Insert your Token here!"
    }
}
api = Api(app,
          title='Proxmox container rest API',
          version='1.0',
          description='The Proxmox Container Management API allows users to interact with Proxmox using its REST API for container management. Key functionalities include creating, updating, editing and retrieving information about containers.',
          prefix='/api',
          authorizations=authorizations,
          security='apiKey')


api.add_namespace(home_ns, path='/container')
