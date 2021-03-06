from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from json import dumps
from shellbot_persisters import DBPersister, JsonFilePersister
from gmail_helper import GmailHelper

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
            log_persister = DBPersister('log', {})
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
        api.add_resource(CacheQueueResource, '/update_sender_count_cache',
                         resource_class_kwargs={'log': log_persister,
                                                'config': config_persister,
                                                'rules': rules_persister,
                                                'cache': cache_persister
                                                  })
        api.add_resource(DialogFlowResource, '/dialog',
                         resource_class_kwargs={'config': config_persister,
                                                'rules': rules_persister,
                                                'cache': cache_persister
                                                  })
        self.app = app


class CacheQueueResource(Resource):
    def __init__(self, **kwargs):
        self.log_persister = kwargs['log']
        persisters = {}
        persisters['config'] = DBPersister('config',
                                                 {'limit': 0,
                                                  'cache_maxage': 60 * 60 * 6})
        persisters['rules'] = DBPersister('rules', {})
        persisters['cache'] = DBPersister('cache',
                                                {'sorted_domain_counts': [],
                                                 'sorted_address_counts': []})
        self.gmail_helper = GmailHelper(persisters)


    def post(self):
        """Log the request payload."""
        payload = request.get_data(as_text=True) or '(empty payload)'
        value = {'log_key': payload, 'message': 'Received task with payload: {}'.format(payload)}
        self.log_persister.set(value)
        messages = self.gmail_helper.collect_messages_list()
        i = 1
        for message in messages:
            if i < 10:
                value = {'log_key': str(i), 'message': dumps(message.keys())}
                self.log_persister.set(value)
            i = i + 1
        return 'Printed task payload: {}'.format(payload)


class DialogFlowResource(Resource):
    def __init__(self, **kwargs):
        self.config_persister = kwargs['config']
        self.rules_persister = kwargs['rules']
        self.cache_persister = kwargs['cache']

    def set_limit(self):
        parameters = request.get_json()['queryResult']['parameters']
        values = self.config_persister.get()
        values.update(parameters)
        self.config_persister.set(values)
        if int(parameters['limit']) == 0:
            phrase = "OK, I won't limit the number of messages I process each time I review your emails."
        else:
            phrase = "I've set the email processing limit to {} as you requested.".format(int(values['limit']))
        return self.define_response(parameters, phrase)

    def set_cache_limit(self):
        parameters = request.get_json()['queryResult']['parameters']
        values = self.config_persister.get()
        duration_amount = parameters['duration']['amount']
        seconds = duration_amount
        duration_unit = parameters['duration']['unit']
        if duration_unit == 's':
            duration_unit = 'second'
            seconds = duration_amount
        elif duration_unit == 'min':
            duration_unit = 'minute'
            seconds = duration_amount * 60
        elif duration_unit == 'h':
            duration_unit = 'hour'
            seconds = duration_amount * 3600
        elif duration_unit == 'day':
            seconds = duration_amount * 3600 * 24
        elif duration_unit == 'wk':
            duration_unit = 'week'
            seconds = duration_amount * 3600 * 24 * 7
        elif duration_unit == 'mo':
            duration_unit = 'month'
            seconds = duration_amount * 3600 * 30
        elif duration_unit == 'yr':
            duration_unit = 'year'
            seconds = duration_amount * 3600 * 365
        if duration_amount != 1:
            duration_unit = duration_unit + "s"
        values.update({'cache_maxage': seconds})
        self.config_persister.set(values)
        if int(duration_amount) == duration_amount:
            phrase = "OK, I've set the maximum cache age to {} {}.".format(int(duration_amount), duration_unit)
        else:
            phrase = "OK, I've set the maximum cache age to {} {}.".format(duration_amount, duration_unit)
        return self.define_response(parameters, phrase)

    def post(self):
        intent_display_name = request.get_json()['queryResult']['intent']['displayName']
        if intent_display_name == "Set limit":
            result = self.set_limit()
        elif intent_display_name == "Set cache limit":
            result = self.set_cache_limit()
        else:
            parameters = request.get_json()['queryResult']['parameters']
            result = self.define_response(parameters, phrase="The Shellbot API doesn't handle that.")
        return jsonify(result)

    def define_response(self, values, phrase):
        return {
            "fulfillmentText": self.fulfillment_text(values, phrase),
            "outputContexts": request.get_json()['queryResult']['outputContexts']
        }
        # "fulfillmentMessages": self.fulfillment_messages(values, phrase),
        # "source": self.source(values, phrase),
        # "payload": self.payload(values, phrase),
        # "followupEventInput": self.followup_event_input(values, phrase)

    def fulfillment_text(self, values, phrase):
        return phrase

    def fulfillment_messages(self, values, phrase):
        return [
          {
            "card": {
              "title": phrase,
              "subtitle": "card text",
              "imageUri": "https://assistant.google.com/static/images/molecule/Molecule-Formation-stop.png",
              "buttons": [
                {
                  "text": "button text",
                  "postback": "https://assistant.google.com/"
                }
              ]
            }
          }
        ]

    def source(self, values, phrase):
        return "nudistrobot.appspot.com"

    def payload(self, values, phrase):
        return {
          "google": self.google_payload(values, phrase),
          "facebook": self.facebook_payload(values, phrase),
          "slack": self.slack_payload(values, phrase)
        }

    def google_payload(self, values, phrase):
        return {
          "expectUserResponse": True,
          "richResponse": {
            "items": [
              {
                "simpleResponse": {
                  "textToSpeech": phrase
                }
              }
            ]
          }
        }

    def facebook_payload(self, values, phrase):
        return {
          "text": phrase
        }

    def slack_payload(self, values, phrase):
        return {
          "expectUserResponse": True,
          "richResponse": {
            "items": [
              {
                "simpleResponse": {
                  "textToSpeech": phrase
                }
              }
            ]
          }
        }

    def output_contexts(self, values, phrase):
        return [
          {
            "name": "projects/<<PROJECT_ID>>/agent/sessions/<<SESSION_ID>>/contexts/<<CONTEXT_NAME>>",
            "lifespanCount": 5,
            "parameters": values
          }
        ]

    def followup_event_input(self, values, phrase):
        return {
          "name": "event name",
          "languageCode": "en-US",
          "parameters": values
        }


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
