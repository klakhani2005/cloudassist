# Logging Standard
All services write structured JSON logs to standard output. Lambda forwards stdout to CloudWatch Logs automatically.
Every log line includes a request ID, the service name, and a severity level.
Log groups keep data for 14 days in development and 90 days in production; set retention explicitly so logs do not accumulate forever.
Never log secrets, access keys, passwords, or full credit card numbers. Mask customer email addresses before logging them.
Use CloudWatch Logs Insights to search logs, for example to find every ERROR line for one request ID.
