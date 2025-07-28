import os
import pymongo

from flask import Flask
from logging import Logger

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.logger.info("Creating app")
    
    # load the config info
    from .config import config
    config(app)
    app.logger.info("Configuring app")

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # initialize routes
    from . import api
    app.register_blueprint(api.bp)
    app.logger.info("Registering routes")

    return app