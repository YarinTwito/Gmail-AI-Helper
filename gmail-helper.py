from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from gpt4all import GPT4All

# Define the scope for the Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


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
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
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


def analyze_email_with_llm(subject, sender, llm_model):
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
    return response.strip()


if __name__ == "__main__":
    service = connect_to_gmail()
    print("Connected to Gmail!")

    # Fetch the latest emails
    emails = fetch_latest_emails(service)

    # Initialize GPT4All model
    llm_model = GPT4All("gpt4all-13b-snoozy-q4_0.gguf")

    # Analyze and display results
    for idx, email in enumerate(emails, start=1):
        analysis = analyze_email_with_llm(email['subject'], email['sender'], llm_model)
        # Parse analysis result into structured lines
        analysis_lines = analysis.split('\n')
        category = analysis_lines[0].replace("Category:", "").strip()
        priority = analysis_lines[1].replace("Priority:", "").strip()
        response = analysis_lines[2].replace("Response:", "").strip()

        print(f"{idx}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   Category: {category}")
        print(f"   Priority: {priority}")
        print(f"   Response: {response}\n")
