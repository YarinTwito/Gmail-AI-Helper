# Gmail AI Helper

## Overview
The **Gmail AI Helper** is a Python-based tool that connects to your Gmail account, analyzes emails using a local Large Language Model (LLM), and categorizes them into predefined groups such as Work, School, or Shopping. It also assigns priority levels (e.g., Urgent, Important, Normal) and determines whether a response is required. The program caches the analysis using Redis for efficient processing.

## Features
- **Email Categorization**: Automatically classifies emails into categories like Work, School, or Shopping.
- **Priority Assignment**: Identifies email priority as Urgent, Important, or Normal.
- **Response Decision**: Determines whether an email requires a response.
- **Caching**: Stores analysis results in Redis for 4 hours to avoid redundant processing.
- **Frequency Analysis**: Identifies the most frequent email category and displays it in a visually appealing format.

## Installation

### Prerequisites
- Python 3.9 or above
- Docker (to run Redis)
- Gmail API credentials (`emails.json`)

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/YarinTwito/gmail-ai-helper.git
   cd gmail-ai-helper
   ```

	2.	Install Dependencies:
Use the requirements.txt file to install all necessary Python packages:
    ```pip install -r requirements.txt```

	3.	Set Up Redis:
    Start a Redis server using Docker:
    ``` docker run -d --name redis -p 6379:6379 redis```

 4.	Set Up Gmail API Credentials:
	•	Go to the Google Cloud Console.
	•	Create a new project or use an existing one.
	•	Enable the Gmail API for the project.
	•	Download the credentials file and save it as emails.json in the project directory.

	5.	Run the Program:
    ```python main.py```

    

