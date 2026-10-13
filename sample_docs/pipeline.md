# Data Ingestion Pipeline
Files uploaded to the docs/ prefix in S3 trigger the ingestion Lambda.
The pipeline accepts only UTF-8 .txt and .md files up to 2 MB; anything else is rejected and logged with the reason.
Documents are split into overlapping chunks of about 900 characters so passages are not cut off at chunk boundaries.
Re-uploading a file replaces its previous chunks instead of creating duplicates.
The ingestion function runs with reserved concurrency of one so two uploads cannot overwrite each other's index update.
