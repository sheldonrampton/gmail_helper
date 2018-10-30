import json
import time
import os
import stat
import db


class DBPersister():
    """The DBPersister class implements getting and setting persistent
    attributes saved in a MySQL database.
    """

    def __init__(self, name, default_value = {}, uid=1):
        """Initializes the DBFilePersister object
        """
        self.name = name
        self.default_value = default_value
        db_config = JsonFilePersister('db', {}).get()
        host=db_config['host']
        user=db_config['user']
        passwd=db_config['passwd']
        portnum=int(db_config['portnum'])
        if self.name == 'config':
            self.db = db.ConfigDB(host, user, passwd, portnum=portnum)
        elif self.name == 'rules':
            self.db = db.RulesDB(host, user, passwd, portnum=portnum)
        elif self.name == 'cache':
            self.db = db.CacheDB(host, user, passwd, portnum=portnum)
        elif self.name == 'log':
            self.db = db.LogDB(host, user, passwd, portnum=portnum)
        self.uid = uid

    def get(self):
        return self.db.get(uid=self.uid)

    def set(self, value):
        self.db.set(value, uid=self.uid)

    def delete(self):
        self.db.delete(uid=self.uid)

    def age_in_seconds(self):
        return 1


class JsonFilePersister():
    """The JsonFilePersister class implements getting and setting persistent
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

    def age_in_seconds(self):
        if os.path.isfile(self.name + '.json'):
            return time.time() - os.stat(self.name + '.json')[stat.ST_MTIME]
        return 0


def main():
    print """Persisters support data persistence.
  * The JsonFilePersister class saves data in a .json file.
  * A MysqlPersister class will save data in a mySQL database."""

if __name__ == '__main__':
    main()
