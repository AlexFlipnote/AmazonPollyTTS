# AmazonPollyTTS
The TTS API that xelA will probably use

## Requirements
- Python 3.6 or higher
- PostgreSQL 9.6 or higher
- Amazon AWS account

# Amazon Polly Pricing
If you're wondering how much you can use for free, you can check [here](https://aws.amazon.com/polly/pricing/) and see if you wish to continue using this.

## Amazon setup
[Have a user account with admin permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/getting-started_create-admin-group.html), then get the access and secret key.

## Creation steps
PostgreSQL commands:
```sql
CREATE ROLE amazonpolly WITH LOGIN PASSWORD 'whateverthefuckyouwant';
CREATE DATABASE amazonpolly OWNER amazonpolly;
```

config.json PostgreSQL:
```json
{
  "postgresql": "postgresql://DATABASENAME:DATABASEPASSWORD@localhost/DATABASENAME"
}
```
