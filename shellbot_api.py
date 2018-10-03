from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from json import dumps
from shellbot_persisters import JsonFilePersister

def main():
    print """The Shellbot API defines a RESTful interface for interacting
with Shellbot tools such as Gmail Helper."""


class ShellbotAPI():
    def __init__(self, port='5000'):
        app = Flask(__name__)
        api = Api(app)
        api.add_resource(Config, '/config', '/config/<name>') # Route_1
        app.run(port=port)


class Config(Resource):
    def get(self, name=''):
        config_persister = JsonFilePersister('config',
                                             {'limit': 0,
                                              'cache_maxage': 60 * 60 * 6})
        config = config_persister.get()
        if name == '':
            result = config
        else:
            result = config[name]
        return jsonify(result)

    def put(self, name=''):
        config_persister = JsonFilePersister('config',
                                             {'limit': 0,
                                              'cache_maxage': 60 * 60 * 6})
        config = config_persister.get()
        if name == '':
            config = request.form
            result = config
        else:
            config[name] = request.form['value']
            result = config[name]
        config_persister.set(config)
        return jsonify(result)

    def delete(self, name=''):
        config_persister = JsonFilePersister('config',
                                             {'limit': 0,
                                              'cache_maxage': 60 * 60 * 6})
        config = config_persister.get()
        if name == '':
            config = {}
        else:
            config.pop(name, None)
        config_persister.set(config)
        return jsonify(config)


if __name__ == '__main__':
    main()
