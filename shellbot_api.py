from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from json import dumps
from shellbot_persisters import DBPersister, JsonFilePersister

def main():
    print """The Shellbot API defines a RESTful interface for interacting
with Shellbot tools such as Gmail Helper."""


class ShellbotAPI():
    def __init__(self, use_db=True):
        app = Flask(__name__)
        api = Api(app)
        if use_db:
            config_persister = DBPersister('config',
                                           {'limit': 0,
                                           'cache_maxage': 60 * 60 * 6})
            rules_persister = DBPersister('rules', {})
            cache_persister = DBPersister('cache', {})
        else:
            config_persister = JsonFilePersister('config',
                                                 {'limit': 0,
                                                 'cache_maxage': 60 * 60 * 6})
            rules_persister = JsonFilePersister('rules', {})
            cache_persister = JsonFilePersister('cache', {})
        api.add_resource(Config, '/config', '/config/<name>',
                         resource_class_kwargs={'persister': config_persister})

        api.add_resource(Rules, '/rules', '/rules/<name>',
                         resource_class_kwargs={'persister': rules_persister})
        api.add_resource(PersistentResource, '/cache', '/cache/<name>',
                         resource_class_kwargs={'persister': cache_persister})
        self.app = app


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

    def post(self, name=''):
        values = self.persister.get()
        if name == '':
            json_values = request.get_json()['queryResult']['parameters']
            values.update(json_values)
            result = values
        else:
            values[name] = request.form['value']
            result = values[name]
#        self.persister.set(values)
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
