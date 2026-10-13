# Access Management Policy
Grant least privilege: each role receives only the actions and resources it needs.
Prefer IAM roles over long-lived access keys. Lambda functions receive temporary credentials through their execution role.
Never commit access keys to Git. If a key is exposed, deactivate it immediately and rotate it.
Review unused permissions every quarter with IAM Access Analyzer and remove them.
Require multi-factor authentication for every human user who can sign in to the console.
