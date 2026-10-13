# Generative AI Usage
Answers are generated with Amazon Bedrock using retrieval-augmented generation: the system first retrieves relevant document passages, then asks the model to answer only from those passages.
Responses must cite their sources so users can verify them.
If the retrieved passages do not contain the answer, the assistant must say it does not know rather than guess.
Temperature is kept low (0.1) to reduce variation between answers.
Model access must be enabled per account and region in the Bedrock console before the model can be invoked.
