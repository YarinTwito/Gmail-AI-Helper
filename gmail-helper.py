from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

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


if __name__ == "__main__":
    service = connect_to_gmail()
    print("Connected to Gmail!")