# gmail_helper
Tools that use the Gmail API to categorize and organize Gmail messages. Presently it is a command-line utility that lets you identify email addresses that send you a lot of messages and define rules for classifying them by adding tags, e.g., "Friends," "Bills," "Jobs," etc. Another command will apply those rules to all messages in your inbox.

Usage:

```
python gmail_helper.py
```

Currently this is a very basic tool. Use at your own risk!

Future roadmap:
* Add Bayesian analysis capability so categorized messages can be used as training datasets to identify other messages that should be similarly classified.
* Add the ability to analyze and classify messages based on other metadata besides the From address.
* Create a chatbot UI
* Create a web UI
* Integrate with other Google services, e.g., Google Drive documents, images, calendar, contacts
* Integrate with non-Google services. For example, once the Bayesian capability exists,  it could be used to apply the same classifications to Facebook conversations.
