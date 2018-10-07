import re
import shellbot_persisters
import gmail_helper

def main():
    persisters = {}
    persisters['config'] = shellbot_persisters.DBPersister('config',
                                             {'limit': 0,
                                              'cache_maxage': 60 * 60 * 6})
    persisters['rules'] = shellbot_persisters.DBPersister('rules', {})
    persisters['cache'] = shellbot_persisters.DBPersister('cache',
                                            {'sorted_domain_counts': [],
                                             'sorted_address_counts': []})

    helper = gmail_helper.GmailHelper(persisters)
    service = helper.service

    persisters = {}
    main_responses = gmail_helper.main_responses
    persisters['dialog'] = shellbot_persisters.JsonFilePersister('dialog', main_responses)
    main_dialog = gmail_helper.Dialog('main_dialog', intro = main_responses['intro'],
                         questions = main_responses['questions'],
                         conclusion = main_responses['conclusion'],
                         persisters = persisters)
    print(main_dialog.intro())
    handling = raw_input(main_dialog.questions() + " ")
    if "domains" in handling.lower():
        helper.ask_for_sender_rules(full_address=False)
    elif "addresses" in handling.lower():
        helper.ask_for_sender_rules(full_address=True)
    elif "apply" in handling.lower():
        messages = helper.collect_messages_list()
        helper.define_rule_tags()
        helper.tag_messages(messages)
    elif "backup" in handling.lower():
        gmail_helper.backup_rules()
    elif "limit" in handling.lower():
        config = helper.config_persister.get()
        print("Limit was previously " + str(config['limit']) + ".")
        m = re.search(r'(\d*)\s*$',handling.lower())
        limit = m.group(0)
        if limit == '':
            config['limit'] = 0
        else:
            config['limit'] = int(limit)
        helper.config_persister.set(config)
        print("I've changed the limit to " + str(config['limit']) + ".")
    elif "cache" in handling.lower():
        config = helper.config_persister.get()
        print("Cache was previously " + str(config['cache_maxage']) + " seconds.")
        m = re.search(r'(\d*)\s*$',handling.lower())
        cache = m.group(0)
        if cache == '':
            config['cache_maxage'] = 0
        else:
            config['cache_maxage'] = int(cache)
        helper.config_persister.set(config)
        print("I've set caching to " + str(config['cache_maxage']) + " seconds.")
    print(main_dialog.conclusion())


if __name__ == '__main__':
    main()
