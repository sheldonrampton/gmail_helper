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
            "KEY `uid` (`uid`))"
        )

        # Create gmail_rules table
        # Example: 1, 'facebook.com', 'add_tag', 'facebook', Facebook'
        self.cursor.execute("CREATE TABLE shellbot_gmail_rules (" +
            "uid INT, " +
            "sender VARCHAR(255)," +
            "action VARCHAR(255), " +
            "rule_key VARCHAR(255), " +
            "rule_value VARCHAR(255), " +
            "KEY `uid` (`uid`))"
        )

        # Create cache table
        # Example: 1, 'facebook.com', 'domain', '4'
        # Example: 1, 'sheldon@gmail.com', 'address', '7'
        self.cursor.execute("CREATE TABLE shellbot_cache (uid INT, " +
            "sender VARCHAR(255) PRIMARY KEY," +
            "type VARCHAR(16), " +
            "message_count INT, " +
            "KEY `uid` (`uid`))"
        )


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


if __name__ == '__main__':
    main()
