from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from gpt4all import GPT4All
import redis
import hashlib
import json

# Define the scope for the Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Connect to Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


def connect_to_gmail():
    # Always go through the authorization flow
    flow = InstalledAppFlow.from_client_secrets_file(
        'emails.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Build the Gmail service
    service = build('gmail', 'v1', credentials=creds)
    return service


def fetch_latest_emails(service, max_results=10):
    # Fetch the latest emails
    results = service.users().messages().list(
        userId='me', maxResults=max_results
    ).execute()
    messages = results.get('messages', [])

    email_data = []
    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me', id=msg['id']).execute()
        payload = msg_data['payload']
        headers = payload['headers']

        # Extract sender and subject
        sender = next(
            header['value'] for header in headers if header['name'] == 'From'
        )
        subject = next(
            (header['value'] for header in headers if header['name'] == 'Subject'),
            "(No Subject)"
        )

        email_data.append({'sender': sender, 'subject': subject})
    return email_data


def get_cache_key(subject, sender):
    """Generate a unique cache key based on email subject and sender."""
    data = f"{subject}|{sender}"
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def analyze_email_with_llm(subject, sender, llm_model):
    # Generate a cache key
    cache_key = get_cache_key(subject, sender)

    # Check if the response is already in Redis
    cached_response = redis_client.get(cache_key)
    if cached_response:
        print(f"Cache hit for: {subject}")
        return json.loads(cached_response)  # Deserialize the cached response

    print(f"Cache miss for: {subject}. Calling LLM...")

    # Create the LLM prompt
    prompt = (
        f"Analyze the following email details:\n"
        f"Sender: {sender}\n"
        f"Subject: {subject}\n\n"
        f"Decide the following:\n"
        f"1. Category (e.g., Work, School, Shopping, etc.).\n"
        f"2. Priority (e.g., Urgent, Important, Normal).\n"
        f"3. Does it require a response? (Yes/No).\n"
        f"Output format: Category: [Category], Priority: [Priority], Response: [Yes/No]"
    )

    # Run the prompt through the LLM
    response = llm_model.generate(prompt)

    # Clean up the response to remove numerical prefixes
    response_lines = response.strip().split('\n')
    cleaned_response = {}
    for line in response_lines:
        if "Category:" in line:
            cleaned_response["Category"] = (
                line.replace("Category:", "")
                .replace("1.", "")
                .strip()
            )
        elif "Priority:" in line:
            cleaned_response["Priority"] = (
                line.replace("Priority:", "")
                .replace("2.", "")
                .strip()
            )
        elif "Response:" in line:
            cleaned_response["Response"] = (
                line.replace("Response:", "")
                .replace("3.", "")
                .strip()
            )

    # Cache the response in Redis with a 4-hour expiration
    redis_client.setex(cache_key, 4 * 3600, json.dumps(cleaned_response))

    return cleaned_response


if __name__ == "__main__":
    service = connect_to_gmail()
    print("Connected to Gmail!")

    # Fetch the latest emails
    emails = fetch_latest_emails(service)

    # Initialize GPT4All model
    llm_model = GPT4All("gpt4all-13b-snoozy-q4_0.gguf")

    # Analyze and display results
    for idx, email in enumerate(emails, start=1):
        analysis = analyze_email_with_llm(
            email['subject'], email['sender'], llm_model
        )
        print(f"{idx}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   Category: {analysis.get('Category', 'N/A')}")
        print(f"   Priority: {analysis.get('Priority', 'N/A')}")
        print(f"   Response: {analysis.get('Response', 'N/A')}\n")
