# gmail_helper
Tools that use the Gmail API to categorize and organize Gmail messages. Presently it is a command-line utility that lets you identify email addresses that send you a lot of messages and define rules for classifying them by adding tags, e.g., "Friends," "Bills," "Jobs," etc. Another command will apply those rules to all messages in your inbox.

## Usage

### To test locally

```
python gmail_helper.py

```

This will store persistent information in .json files named config.json, rules.json, cache.json, dialog.json, credentials.json and token.json.

```
python test_api.py
```

This will spin up a local HTTP server at http://127.0.0.1:5002 where you can try the Shellbot API at endpoints including:

* http://127.0.0.1:5002/rules
* http://127.0.0.1:5002/cache
* http://127.0.0.1:5002/config


### To test with a MySQL database

* Create a MySQL database.
* Copy ```db.example.json``` to ```db.json``` and edit it with the host, user, password and port information.
* Run ```python db.py``` to set up the config, rules and cache tables in the database and populate them with data from the .json files.
* Run ```python test_db.py```


```
python test_db.py

```

### To deploy on Google Cloud Platform

* Create a MySQL database in your Google project.
* Update app.yaml with your database connection information
* Deploy!

Currently this is a very basic tool. Use at your own risk!

Future roadmap:
* Add Bayesian analysis capability so categorized messages can be used as training datasets to identify other messages that should be similarly classified.
* Add the ability to analyze and classify messages based on other metadata besides the From address.
* Create a chatbot UI
* Create a web UI
* Integrate with other Google services, e.g., Google Drive documents, images, calendar, contacts
* Integrate with non-Google services. For example, once the Bayesian capability exists,  it could be used to apply the same classifications to Facebook conversations.
