import mysql.connector
from shellbot_persisters import JsonFilePersister


class ShellbotDB():
    def __init__(self, hostname, username, password, dbasename='shellbot'):
        self.db = mysql.connector.connect(
            host=hostname,
            user=username,
            passwd=password
        )
        self.cursor = self.db.cursor()
        self.dbname = dbasename

    def create_database(self):
        self.cursor.execute("CREATE DATABASE " + self.dbname)

    def destroy_database(self):
        self.cursor.execute("DROP DATABASE " + self.dbname)

    def open_database(self):
        try:
            self.cursor.execute("USE {}".format(self.dbname))
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                self.create_database(self.dbname)

    def create_tables(self):
        # Create user table
        self.open_database()
        self.cursor.execute("CREATE TABLE shellbot_user (" +
            "uid INT AUTO_INCREMENT PRIMARY KEY, " +
            "username VARCHAR(255))")

        # Create config table
        # Example: 3, 'limit', '200'
        # No table needed for credentials. Store them in shellbot_config.
        self.cursor.execute("CREATE TABLE shellbot_config (" +
            "uid INT, " +
            "config_name VARCHAR(255), config_value TEXT, " +
            "PRIMARY KEY(uid, config_name))"
        )

        # Create gmail_rules table
        # Example: 1, 'facebook.com', 'add_tag', 'facebook', Facebook'
        self.cursor.execute("CREATE TABLE shellbot_gmail_rules (" +
            "uid INT, " +
            "sender VARCHAR(255)," +
            "action VARCHAR(255), " +
            "rule_key VARCHAR(255), " +
            "rule_value VARCHAR(255), " +
            "PRIMARY KEY(uid, sender, action, rule_key))"
        )

        # Create cache table
        # Example: 1, 'facebook.com', 'domain', '4'
        # Example: 1, 'sheldon@gmail.com', 'address', '7'
        self.cursor.execute("CREATE TABLE shellbot_cache (uid INT, " +
            "sender VARCHAR(255)," +
            "type VARCHAR(16), " +
            "message_count INT, " +
            "PRIMARY KEY(uid, sender, type))"
        )

    def get_config(self, uid=1):
        query = "SELECT config_name, config_value FROM shellbot_config WHERE uid = %s"
        self.cursor.execute(query, (uid, ))
        result = self.cursor.fetchall()
        return {k: v for k, v in result}

    def set_config(self, config, uid=1):
        rows = [(uid, k, v) for k, v in config.iteritems()]
        query = ("INSERT INTO shellbot_config (uid, config_name, config_value) " +
                 "VALUES (%s, %s, %s) " +
                 "ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)")
        self.cursor.executemany(query, rows)
        self.db.commit()

    def get_rules(self, uid=1):
        query = ("SELECT sender, action, rule_key, rule_value " +
                 "FROM shellbot_gmail_rules WHERE uid = %s")
        self.cursor.execute(query, (uid, ))
        result = self.cursor.fetchall()
        rules = {}
        for sender, action, rule_key, rule_value in result:
            print "Sender: " + sender + "; Action: " + action + "; rule_key: " + rule_key + "; rule_value: " + rule_value
            if not sender in rules:
                rules[sender] = {"set_status": {}, "remove_tags": {}, "add_tags": {}}
            rules[sender][action][rule_key] = rule_value
        return rules

    def set_rules(self, rules, uid=1):
        rows = []
        for sender, actions in rules.iteritems():
            set_status = [(uid, sender, 'set_status', k, v)
                          for k,v in actions['set_status'].iteritems()]
            remove_tags = [(uid, sender, 'remove_tags', k, v)
                           for k,v in actions['remove_tags'].iteritems()]
            add_tags = [(uid, sender, 'add_tags', k, v)
                        for k,v in actions['add_tags'].iteritems()]
            rows.extend(set_status)
            rows.extend(remove_tags)
            rows.extend(add_tags)
        query = ("INSERT INTO shellbot_gmail_rules (uid, sender, action, rule_key, rule_value) " +
                 "VALUES (%s, %s, %s, %s, %s) " +
                 "ON DUPLICATE KEY UPDATE rule_value = VALUES(rule_value)")
        self.cursor.executemany(query, rows)
        self.db.commit()

    def get_cache(self, uid=1):
        cache = {'sorted_domain_counts': [], 'sorted_address_counts': []}
        query = ('SELECT sender, message_count ' +
                 'FROM shellbot_cache WHERE uid = %s AND type = "domain"')
        self.cursor.execute(query, (uid, ))
        result = self.cursor.fetchall()
        cache['sorted_domain_counts'] = [[s, c] for s, c in result]
        query = ('SELECT sender, message_count ' +
                 'FROM shellbot_cache WHERE uid = %s AND type = "address"')
        self.cursor.execute(query, (uid, ))
        result = self.cursor.fetchall()
        cache['sorted_address_counts'] = [[s, c] for s, c in result]
        return cache

    def set_cache(self, cache, uid=1):
        rows = []
        sorted_domain_counts = [(uid, x[0], 'domain', x[1]) for x in cache['sorted_domain_counts']]
        sorted_address_counts = [(uid, x[0], 'address', x[1]) for x in cache['sorted_address_counts']]
        rows.extend(sorted_domain_counts)
        rows.extend(sorted_address_counts)
        query = ("INSERT INTO shellbot_cache (uid, sender, type, message_count) " +
                 "VALUES (%s, %s, %s, %s) " +
                 "ON DUPLICATE KEY UPDATE message_count = VALUES(message_count)")
        self.cursor.executemany(query, rows)
        self.db.commit()

    def delete_config(self, uid=1):
        query = "DELETE FROM shellbot_config WHERE uid = %s"
        param = (uid,)
        self.cursor.execute(query, param)
        self.db.commit()

    def delete_rules(self, uid=1):
        query = "DELETE FROM shellbot_gmail_rules WHERE uid = %s"
        param = (uid,)
        self.cursor.execute(query, param)
        self.db.commit()

    def delete_cache(self, uid=1):
        query = "DELETE FROM shellbot_cache WHERE uid = %s"
        param = (uid,)
        self.cursor.execute(query, param)
        self.db.commit()


def main():
    db_config = JsonFilePersister('db', {}).get()
    host=db_config['host']
    user=db_config['user']
    passwd=db_config['passwd']
    bot_db = ShellbotDB(host, user, passwd)
    print(bot_db.db)
    bot_db.destroy_database()
    bot_db.create_database()
    bot_db.cursor.execute("SHOW DATABASES")
    for x in bot_db.cursor:
        print(x)
    bot_db.create_tables()
    bot_db.cursor.execute("SHOW TABLES")
    for x in bot_db.cursor:
        print(x)

    config = JsonFilePersister('config', {}).get()
    bot_db.set_config(config)
    bot_db.cursor.execute("SELECT * FROM shellbot_config")
    myresult = bot_db.cursor.fetchall()
    for x in myresult:
        print(x)

    rules = JsonFilePersister('rules', {}).get()
    bot_db.set_rules(rules)
    bot_db.cursor.execute("SELECT * FROM shellbot_gmail_rules")
    myresult = bot_db.cursor.fetchall()
    for x in myresult:
        print(x)

    print "CACHE"
    cache = JsonFilePersister('cache', {}).get()
    bot_db.set_cache(cache)
    bot_db.cursor.execute("SELECT * FROM shellbot_cache")
    myresult = bot_db.cursor.fetchall()
    for x in myresult:
        print(x)

    print bot_db.get_config()
    print bot_db.get_rules()
    print bot_db.get_cache()


if __name__ == '__main__':
    main()
