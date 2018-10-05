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
        json_persister = JsonFilePersister('config',
                                      {'limit': 0,
                                       'cache_maxage': 60 * 60 * 6})
        api.add_resource(Config, '/config', '/config/<name>',
                         resource_class_kwargs={'persister': json_persister})

        rules_persister = JsonFilePersister('rules', {})
        api.add_resource(Rules, '/rules', '/rules/<name>',
                         resource_class_kwargs={'persister': rules_persister})
        app.run(port=port)


class PersistentResource(Resource):
    def __init__(self, **kwargs):
        self.persister = kwargs['persister']

    def get(self, name=''):
        values = self.persister.get()
        if name == '':
            result = values
        else:
            result = values[name]
        return jsonify(result)

    def put(self, name=''):
        values = self.persister.get()
        if name == '':
            values = request.form
            result = values
        else:
            values[name] = request.form['value']
            result = values[name]
        self.persister.set(values)
        return jsonify(result)

    def delete(self, name=''):
        values = self.persister.get()
        if name == '':
            values = {}
        else:
            values.pop(name, None)
        self.persister.set(values)
        return jsonify(values)


class Config(PersistentResource):
    def __init__(self, **kwargs):
        self.persister = kwargs['persister']


class Rules(PersistentResource):
    def __init__(self, **kwargs):
        self.persister = kwargs['persister']



if __name__ == '__main__':
    main()
