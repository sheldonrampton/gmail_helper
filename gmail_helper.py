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

# If modifying these scopes, delete the file token.json.
# SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'

def main():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('gmail', 'v1', http=creds.authorize(Http()))

    print("I can do several things:")
    print("* Define new email rules based on sender domains (domains)")
    print("* Define new email rules based on sender email addresses (addresses)")
    print("* Clean up duplicate rules (dedupe)")
    print("* Backup rules (backup)")
    print("* Apply the rules (apply)")
    handling = raw_input("What would you like me to do? ")
    if "senders" in handling.lower():
        ask_for_sender_rules(service, full_address=False)
    elif "addresses" in handling.lower():
        ask_for_sender_rules(service, full_address=True)
    elif "dedupe" in handling.lower():
        rules = get_email_rules()
        new_rules = {}
        senders = rules.keys()
        for sender in senders:
            rule = get_email_rule(sender, rules)
            new_rule = dedupe_rule(rule)
            set_email_rule(sender, new_rule, rules)
            # pprint.pprint(rules)
        set_email_rules(rules)
        # pprint.pprint(rules)
    elif "apply" in handling.lower():
        messages = collect_messages_list(service)
        define_rule_tags(service)
        tag_messages(messages, service)
    elif "backup" in handling.lower():
        backup_rules()


def backup_rules():
    copyfile("rules.json", "rules.json.backup")


def dedupe_rule(rule):
    adds = rule['add_tags']
    # pprint.pprint(adds)
    new_adds = {tag.lower(): tag for tag in adds}
    # pprint.pprint(new_adds)
    return {'add_tags': new_adds, 'remove_tags': {}, 'set_status': {}}


def collect_messages_list(service):
    # Call the Gmail API
    # api = service.users().messages()
    # results = api.list(userId='me', q='is:unread').execute()
    # messages=ListMessagesMatchingQuery(service, 'me', query='label:INBOX is:unread')
    messages=ListMessagesMatchingQuery(service, 'me', query='label:INBOX')

    if not messages:
        print('No messages found.')
        return messages
    else:
        message_count = len(messages)
        print(str(message_count) + ' Messages:')
        return messages


def ask_for_sender_rules(service, full_address=False):
    """Asks the user to specify rules for handling Gmail messages.
    """
    messages = collect_messages_list(service)
    sender_counts = defaultdict(int)
    count = 1
    for message in messages:
        sender = get_from_sender(message, service, full_address=full_address)
        if sender:
            sender_counts[sender] += 1
        count += 1
        # if count > 50:
        #     break
    sorted_counts = sorted(sender_counts.iteritems(),
                           key=lambda (k,v): (v,k),
                           reverse=True)
    print("""For each sender, tell me how you want it handled, as follows:
  * Enter [return] if you want it tagged with its sender.
  * Enter a word or phrase if you want it tagged with that word or phrase.
  * Enter SKIP (in all caps) if you don't want to do anything.
  * Enter END (in all caps) if you don't want to do anything with this sender
    or any subsequent senders in the list.
  * Enter CANCEL (all caps) to cancel all of the processing you've specified.

OK? Let's get started...""")
    rules = get_email_rules()
    for count_item in sorted_counts:
        (sender, count) = count_item
        print("sender " + sender + " has " + str(count) + " messages.")
        handling = raw_input("How do you want it handled? ")
        if handling.lower() == "cancel":
            print("Your will be done, my liege. I will do nothing.")
            break
        elif handling.lower() == "end":
            set_email_rules(rules)
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
    # return messages


def get_from_sender(message, service, full_address=False):
    api = service.users().messages()
    mess = api.get(userId='me', id=message['id'], format='metadata').execute()
    headers = mess['payload']['headers']
    temp_dict = {}
    for header in headers:
        if header['name'] == 'Subject':
            temp_dict['Subject'] = header['value']
        # elif header['name'] == 'Date':
        #     msg_date = header['value']
        #     date_parse = (parser.parse(msg_date))
        #     temp_dict['Date'] = str(date_parse.date())
        elif header['name'] == 'From':
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


def get_from_email(message, service):
    api = service.users().messages()
    mess = api.get(userId='me', id=message['id'], format='metadata').execute()
    headers = mess['payload']['headers']
    temp_dict = {}
    for header in headers:
        if header['name'] == 'Subject':
            temp_dict['Subject'] = header['value']
        # elif header['name'] == 'Date':
        #     msg_date = header['value']
        #     date_parse = (parser.parse(msg_date))
        #     temp_dict['Date'] = str(date_parse.date())
        elif header['name'] == 'From':
            temp_dict['From'] = header['value']
    if 'From' in temp_dict:
        (name, email_address) = parseaddr(temp_dict['From'])
        return email_address.lower()
    else:
        return False


def tag_messages(messages, service):
    print("Filing messages. This may take awhile...")
    api = service.users().messages()
    response = service.users().labels().list(userId='me').execute()
    labels = response['labels']
    label_map = {l.get('name').lower(): l.get('id') for l in labels}
    rules = get_email_rules()
    count = 1
    for message in messages:
        domain = get_from_sender(message, service, False)
        email = get_from_sender(message, service, True)
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
        # if count > 5:
        #     exit()


def define_rule_tags(service):
    """Applies user-specified rules to emails in the inbox.
    """
    rules = get_email_rules()
    try:
        response = service.users().labels().list(userId='me').execute()
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
                CreateLabel(service, 'me', label)


def get_email_rules():
    """Retrieves email rules from file rules.json."""
    try:
        with open('rules.json') as json_file:
            rules = json.load(json_file)
            return rules
    except IOError:
        return {}


def set_email_rules(rules):
    """Saves email rules to file rules.json."""
    with open('rules.json', 'w') as outfile:
        json.dump(rules, outfile)


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



if __name__ == '__main__':
    main()
