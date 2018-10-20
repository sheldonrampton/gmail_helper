import sys
from shellbot_api import ShellbotAPI

# Tests the Shellbot API in a local environment.
#
# Usage: python_api.py <persistence>
# where
# <persistence> is an optional argument. If the argument is 'mysql' or omitted,
#   the API test uses a database connection using the connection settings
#   defined in file db.json. (See db.example.json for an example file.)
#   Other, the API test uses a file-based approach to data persistence, storing
#   the data in files config.json, cache.json and rules.json

if __name__ == '__main__':
    try:
        persistence = sys.argv[1]
    except IndexError:
        persistence = 'mysql'

    if  persistence == 'mysql':
        api_test = ShellbotAPI().app.run(port='5000')
    else:
        api_test = ShellbotAPI(False).app.run(port='5000')
