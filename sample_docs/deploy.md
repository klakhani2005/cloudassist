# Deployment Process
Infrastructure is defined as code with AWS SAM and deployed through a CI pipeline; manual console changes are not allowed in production.
Every change goes to the staging environment first and must pass automated tests before promotion.
Production deploys use gradual traffic shifting: 10 percent of traffic for ten minutes, then all traffic if CloudWatch alarms stay quiet.
If an alarm fires during the rollout, the deployment rolls back automatically.
