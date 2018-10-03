from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import pprint
import dateutil.parser as parser
from parse import *
from collections import defaultdict
from apiclient import errors
import re
from email.utils import parseaddr
import json
from shutil import copyfile
import time
import os
import stat
import shellbot_persisters

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'

main_responses = {}
main_responses['intro'] = """I can do several things:
* Define new email rules based on sender domains (domains)
* Define new email rules based on sender email addresses (addresses)
* Backup rules (backup)
* Apply the rules (apply)
* Set a limit on the number of messages to process (limit)
* Set the number of seconds to cache sender counts (cache)
"""
main_responses['questions'] = "What would you like me to do?"
main_responses['conclusion'] = "OK, done."


class GmailHelper():
    """The GmailHelper object implements defining and apply rules for
    managing messages in a Gmail account.

    This requires using a token in file token.json with a valid
    token key to establish access to a gmail service.

    Attributes:
        service (object): the gmail service
    """

    persist = False

    def __init__(self, persisters={}):
        """Initializes the GmailHelper object
        """
        if persisters:
            self.persist = True
            self.config_persister = persisters['config']
            self.rules_persister = persisters['rules']
            self.cache_persister = persisters['cache']
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('gmail', 'v1', http=creds.authorize(Http()))

    def ask_for_sender_rules(self, full_address=False):
        """Asks the user to specify rules for handling Gmail messages.
        """
        messages = self.collect_messages_list()
        cache_maxage = self.config_persister.get()['cache_maxage']
        age = self.cache_persister.file_age_in_seconds()
        print("The cache is " + str(age) + " seconds old.")
        if age > cache_maxage:
            self.cache_persister.delete()
            print("Deleting cache.")
        cache = self.cache_persister.get()
        if full_address:
            print("FULL ADDRESS")
            sorted_counts = cache['sorted_address_counts']
        else:
            sorted_counts = cache['sorted_domain_counts']
        if len(sorted_counts) == 0:
            sender_counts = defaultdict(int)
            count = 1
            limit = self.config_persister.get()['limit']
            for message in messages:
                sender = self.get_from_sender(message, full_address=full_address)
                if sender:
                    sender_counts[sender] += 1
                count += 1
                if count % 100 == 0:
                    print(str(count) + " messages inspected.")
                if limit > 0 and count > limit:
                    break
            sorted_counts = sorted(sender_counts.iteritems(),
                                   key=lambda (k,v): (v,k),
                                   reverse=True)
            if full_address:
                cache['sorted_address_counts'] = sorted_counts
            else:
                cache['sorted_domain_counts'] = sorted_counts
            self.cache_persister.set(cache)

        print("""For each sender, tell me how you want it handled, as follows:
  * Enter [return] if you want it tagged with its sender.
  * Enter a word or phrase if you want it tagged with that word or phrase.
  * Enter SKIP if you don't want to do anything.
  * Enter END if you don't want to do anything with this sender
    or any subsequent senders in the list.
  * Enter CANCEL to cancel all of the processing you've specified.

OK? Let's get started...""")
        rules = self.rules_persister.get()
        for count_item in sorted_counts:
            (sender, count) = count_item
            print("sender " + sender + " has " + str(count) + " messages.")
            handling = raw_input("How do you want it handled? ")
            if handling.lower() == "cancel":
                print("Your will be done, my liege. I will do nothing.")
                break
            elif handling.lower() == "end":
                self.rules_persister.set(rules)
                print("Sounds like a plan, Stan. Let me get to work.")
                break
            elif handling.lower() == "skip":
                print("Gotcha. OK, let's look at the next one.")
            elif handling == "":
                print("OK, we'll tag all of these emails with \"" + sender + "\".")
                rule = get_email_rule(sender, rules)
                rule['add_tags'].append(sender)
                set_email_rule(sender, rule, rules)
            else:
                rule = get_email_rule(sender, rules)
                rule['add_tags'][handling.lower()] = handling
                set_email_rule(sender, rule, rules)
                print("OK, we'll tag all of these emails with \"" + handling + "\".")

    def collect_messages_list(self):
        # messages=ListMessagesMatchingQuery(service, 'me', query='label:INBOX is:unread')
        messages=ListMessagesMatchingQuery(self.service, 'me', query='label:INBOX')
        if not messages:
            print('No messages found.')
        else:
            message_count = len(messages)
            print(str(message_count) + ' Messages:')
        return messages

    def define_rule_tags(self):
        """Applies user-specified rules to emails in the inbox.
        """
        rules = self.rules_persister.get()
        try:
            response = self.service.users().labels().list(userId='me').execute()
            labels = response['labels']
            label_tags = [l.get('name').lower() for l in labels]
        except errors.HttpError, error:
            print('An error occurred: %s' % error)
        for sender in rules.keys():
            # print("sender " + sender + " has the following tags:")
            for key in rules[sender]['add_tags'].keys():
                # print("* " + tag)
                if not key.lower() in label_tags:
                    label = MakeLabel(rules[sender]['add_tags'][key])
                    CreateLabel(self.service, 'me', label)

    def tag_messages(self, messages):
        print("Filing messages. This may take awhile...")
        limit = self.config_persister.get()['limit']
        api = self.service.users().messages()
        response = self.service.users().labels().list(userId='me').execute()
        labels = response['labels']
        label_map = {l.get('name').lower(): l.get('id') for l in labels}
        rules = self.rules_persister.get()
        count = 1
        for message in messages:
            domain = self.get_from_sender(message, False)
            email = self.get_from_sender(message, True)
            for sender in [domain,email]:
                rule = get_email_rule(sender, rules)
                if len(rule['add_tags'].keys()) > 0:
                    add_rule = [label_map[key] for key in rule['add_tags'].keys()]
                    request_body = {'addLabelIds': add_rule,
                                    'removeLabelIds': ['INBOX']}
                    message = api.modify(userId='me', id=message['id'],
                                         body=request_body).execute()
            count += 1
            if count % 100 == 0:
                print(str(count) + " messages processed.")
            if limit != 0 and count > limit:
                exit()

    def get_from_sender(self, message, full_address=False):
        api = self.service.users().messages()
        mess = api.get(userId='me', id=message['id'], format='metadata').execute()
        headers = mess['payload']['headers']
        temp_dict = {}
        for header in headers:
            # if header['name'] == 'Subject':
            #     temp_dict['Subject'] = header['value']
            # elif header['name'] == 'Date':
            #     msg_date = header['value']
            #     date_parse = (parser.parse(msg_date))
            #     temp_dict['Date'] = str(date_parse.date())
            if header['name'] == 'From':
                temp_dict['From'] = header['value']
        if 'From' in temp_dict:
            (name, email_address) = parseaddr(temp_dict['From'])
            if full_address:
                return email_address
            else:
                (username, domain) = parse("{}@{}", email_address)
                return domain
            return sender.lower()
        else:
            return False


class JsonFilePersister():
    """The Persister class implements getting and setting persistent
    attributes saved in a Json file.
    """

    def __init__(self, name, default_value = {}):
        """Initializes the JsonFilePersister object
        """
        self.name = name
        self.default_value = default_value

    def get(self):
        """Retrieves info settings from file self.name + '.json'.
        """
        try:
            with open(self.name + '.json') as json_file:
                return json.load(json_file)
        except IOError:
            return self.default_value

    def set(self, value):
        """Saves configuration settings to file config.json."""
        with open(self.name + '.json', 'w') as outfile:
            json.dump(value, outfile)

    def delete(self):
        ## If file exists, delete it ##
        if os.path.isfile(self.name + '.json'):
            os.remove(self.name + '.json')

    def file_age_in_seconds(self):
        if os.path.isfile(self.name + '.json'):
            return time.time() - os.stat(self.name + '.json')[stat.ST_MTIME]
        return 0


class Dialog():
    """The Dialog object defines a sequence of steps that can take actions
    and return values and text within a context.

    This requires using a token in file token.json with a valid
    token key to establish access to a gmail service.

    Attributes:
        service (object): the gmail service
    """

    context = {}
    persist = False
    response = {}

    def __init__(self, name,
                 intro="Let's start",
                 questions=[],
                 conclusion="OK, thanks.",
                 persisters={}):
        """Initializes the Dialog object
        """
        self.response['intro'] = intro
        self.response['questions'] = questions
        self.response['conclusion'] = conclusion
        if persisters:
            self.persist = True
            self.dialog_persister = persisters['dialog']
            self.dialog_persister.set(self.response)

    def intro(self):
        return self.dialog_persister.get()['intro']

    def questions(self):
        return self.dialog_persister.get()['questions']

    def conclusion(self):
        return self.dialog_persister.get()['conclusion']

    def set(self, attr, value):
        self.response['attr'] = value
        self.dialog_persister.set(self.response)


def backup_rules():
    copyfile("rules.json", "rules.json.backup")
    copyfile("config.json", "config.json.backup")


def get_email_rule(sender, rules):
    """Retrieves the email rule for a single sender."""
    if sender in rules.keys():
        return rules[sender]
    else:
        return {'add_tags': {}, 'remove_tags': {}, 'set_status': {}}


def set_email_rule(sender, rule, rules):
    rules[sender] = rule


def ListMessagesMatchingQuery(service, user_id, query=''):
  """List all Messages of the user's mailbox matching the query.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    query: String used to filter messages returned.
    Eg.- 'from:user@some_sender.com' for Messages from a particular email address.

  Returns:
    List of Messages that match the criteria of the query. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate ID to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id,
                                               q=query).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = service.users().messages().list(userId=user_id, q=query,
                                         pageToken=page_token).execute()
      messages.extend(response['messages'])

    return messages
  except errors.HttpError, error:
    print('An error occurred: ' + str(error))


def ListMessagesWithLabels(service, user_id, label_ids=[]):
  """List all Messages of the user's mailbox with label_ids applied.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_ids: Only return Messages with these labelIds applied.

  Returns:
    List of Messages that have all required Labels applied. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate id to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id,
                                               labelIds=label_ids).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = service.users().messages().list(userId=user_id,
                                                 labelIds=label_ids,
                                                 pageToken=page_token).execute()
      messages.extend(response['messages'])

    return messages
  except errors.HttpError, error:
    print('An error occurred: ' + str(error))


def CreateLabel(service, user_id, label_object):
  """Creates a new label within user's mailbox, also prints Label ID.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_object: label to be added.

  Returns:
    Created Label.
  """
  try:
    label = service.users().labels().create(userId=user_id,
                                            body=label_object).execute()
    print(label['id'])
    return label
  except errors.HttpError, error:
    print('An error occurred: %s' % error)


def MakeLabel(label_name, mlv='show', llv='labelShow'):
  """Create Label object.

  Args:
    label_name: The name of the Label.
    mlv: Message list visibility, show/hide.
    llv: Label list visibility, labelShow/labelHide.

  Returns:
    Created Label.
  """
  label = {'messageListVisibility': mlv,
           'name': label_name,
           'labelListVisibility': llv}
  return label


def main():
    persisters = {}
    persisters['config'] = JsonFilePersister('config',
                                             {'limit': 0,
                                              'cache_maxage': 60 * 60 * 6})
    persisters['rules'] = JsonFilePersister('rules', {})
    persisters['cache'] = JsonFilePersister('cache',
                                            {'sorted_domain_counts': [],
                                             'sorted_address_counts': []})

    gmail_helper = GmailHelper(persisters)
    service = gmail_helper.service

    persisters = {}
    persisters['dialog'] = JsonFilePersister('dialog', main_responses)

    main_dialog = Dialog('main_dialog', intro = main_responses['intro'],
                         questions = main_responses['questions'],
                         conclusion = main_responses['conclusion'],
                         persisters = persisters)
    print(main_dialog.intro())
    handling = raw_input(main_dialog.questions() + " ")
    if "domains" in handling.lower():
        gmail_helper.ask_for_sender_rules(full_address=False)
    elif "addresses" in handling.lower():
        gmail_helper.ask_for_sender_rules(full_address=True)
    elif "apply" in handling.lower():
        messages = gmail_helper.collect_messages_list()
        gmail_helper.define_rule_tags()
        gmail_helper.tag_messages(messages)
    elif "backup" in handling.lower():
        backup_rules()
    elif "limit" in handling.lower():
        config = gmail_helper.config_persister.get()
        print("Limit was previously " + str(config['limit']) + ".")
        m = re.search(r'(\d*)\s*$',handling.lower())
        limit = m.group(0)
        if limit == '':
            config['limit'] = 0
        else:
            config['limit'] = int(limit)
        gmail_helper.config_persister.set(config)
        print("I've changed the limit to " + str(config['limit']) + ".")
    elif "cache" in handling.lower():
        config = gmail_helper.config_persister.get()
        print("Cache was previously " + str(config['cache_maxage']) + " seconds.")
        m = re.search(r'(\d*)\s*$',handling.lower())
        cache = m.group(0)
        if cache == '':
            config['cache_maxage'] = 0
        else:
            config['cache_maxage'] = int(cache)
        gmail_helper.config_persister.set(config)
        print("I've set caching to " + str(config['cache_maxage']) + " seconds.")
    print(main_dialog.conclusion())


if __name__ == '__main__':
    main()
