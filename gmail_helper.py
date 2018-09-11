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

# If modifying these scopes, delete the file token.json.
# SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
SCOPES = 'https://www.googleapis.com/auth/gmail.modify'

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('gmail', 'v1', http=creds.authorize(Http()))

    # Call the Gmail API
    api = service.users().messages()
    results = api.list(userId='me',
                       q='is:unread',
                       maxResults=50).execute()
    messages=ListMessagesMatchingQuery(service, 'me', query='is:unread')

    if not messages:
        print('No messages found.')
    else:
        message_count = len(messages)
        print(str(message_count) + ' Messages:')

        domain_counts = defaultdict(int)
        count = 1
        for message in messages:
            # print(message['id'])
            #messages_call = service.users().messages()
            mess = api.get(
                                        userId='me', id=message['id'],
                                        format='metadata').execute()
            headers = mess['payload']['headers']
            temp_dict = { }
            for header in headers:
                if header['name'] == 'Subject':
                    temp_dict['Subject'] = header['value']
                elif header['name'] == 'Date':
                    msg_date = header['value']
                    date_parse = (parser.parse(msg_date))
                    temp_dict['Date'] = str(date_parse.date())
                elif header['name'] == 'From':
                    temp_dict['From'] = header['value']

            print(temp_dict['From'])
            (name, email_address) = parseaddr(temp_dict['From'])
            print(email_address)
            (username, domain) = parse("{}@{}", email_address)
            # print(domain)
            domain_counts[domain] += 1
            count += 1
            if count > 50:
                break
        sorted_counts = sorted(domain_counts.iteritems(),
                               key=lambda (k,v): (v,k),
                               reverse=True)
        print("""For each domain, tell me how you want it handled, as follows:
  * Enter [return] if you want it tagged with its domain.
  * Enter a word or phrase if you want it tagged with that word or phrase.
  * Enter SKIP (in all caps) if you don't want to do anything.
  * Enter END (in all caps) if you don't want to do anything with this domain
    or any subsequent domains in the list.
  * Enter CANCEL (all caps) to cancel all of the processing you've specified.

OK? Let's get started...""")
        rules = get_email_rules()
        for count_item in sorted_counts:
            (domain, count) = count_item
            print("Domain " + domain + " has " + str(count) + " messages.")
            handling = raw_input("How do you want it handled? ")
            if handling == "CANCEL":
                print("Your will be done, my liege. I will do nothing.")
                exit()
            elif handling == "END":
                set_email_rules(rules)
                print("Sounds like a plan, Stan. Let me get to work.")
                exit()
            elif handling == "SKIP":
                print("Gotcha. OK, let's look at the next one.")
            elif handling == "":
                print("OK, we'll tag all of these emails with \"" + domain + "\".")
                rule = get_email_rule(domain, rules)
                rule['add_tags'].append(domain)
                rules[domain] = rule
                pprint.pprint(rules)
            else:
                rule = get_email_rule(domain, rules)
                rule['add_tags'].append(handling)
                rules[domain] = rule
                pprint.pprint(rules)
                print("OK, we'll tag all of these emails with \"" + handling + "\".")


def get_email_rules():
    try:
        with open('rules.json') as json_file:
            rules = json.load(json_file)
            return rules
    except IOError:
        return {}


def set_email_rules(rules):
    with open('rules.json', 'w') as outfile:
        json.dump(rules, outfile)


def get_email_rule(domain, rules):
    if domain in rules.keys():
        return rules[domain]
    else:
        return {'add_tags': [], 'remove_tags': [], 'set_status': []}


def set_email_rule(domain, rule):
    return ""


def ListMessagesMatchingQuery(service, user_id, query=''):
  """List all Messages of the user's mailbox matching the query.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    query: String used to filter messages returned.
    Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

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
    print label['id']
    return label
  except errors.HttpError, error:
    print 'An error occurred: %s' % error


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
