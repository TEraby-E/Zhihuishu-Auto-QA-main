# Zhihuishu-Auto-QA

AI-Based Zhihuishu Auto QA Script
referring to https://github.com/Yan233th/Zhihuishu-Auto-QA
A new filter has been added, allowing users to specify a particular name when asking questions.
## Usage Instructions

First, install the required dependencies.
```bash
pip install -r ./requirements.txt
```

Complete the `secret.py.example` file with your API key for the platform you are using for `api_key`.\
Then copy or rename the file to `secret.py`.
```bash
python -u ./main.py
```