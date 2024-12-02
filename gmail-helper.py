from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from gpt4all import GPT4All
import redis
import hashlib
import json
from collections import Counter
from colorama import Fore, Style
import matplotlib.pyplot as plt

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


def fetch_latest_emails(service, max_results=100):
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
            (header['value'] for header in headers
             if header['name'] == 'Subject'),
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
        return json.loads(cached_response)  # Deserialize the cached response

    # Create the LLM prompt
    prompt = (
        f"Analyze the following email details:\n"
        f"Sender: {sender}\n"
        f"Subject: {subject}\n\n"
        f"Decide the following:\n"
        f"1. Category (e.g., Work, School, Shopping, etc.).\n"
        f"2. Priority (e.g., Urgent, Important, Normal).\n"
        f"3. Does it require a response? (Yes/No).\n"
        f"Output format: Category: [Category], Priority: [Priority], "
        f"Response: [Yes/No]"
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


def plot_all_graphs(categories, priorities, responses):
    """
    Plots all the graphs (categories, priorities, responses) in one figure.
    """
    # Count data for the graphs
    category_counts = Counter(categories)
    priority_counts = Counter(priorities)
    response_counts = Counter(responses)

    # Prepare data for plotting
    category_labels = list(category_counts.keys())
    category_values = list(category_counts.values())

    priority_labels = list(priority_counts.keys())
    priority_sizes = list(priority_counts.values())

    response_labels = ['Yes', 'No']
    response_values = [
        response_counts.get('Yes', 0), response_counts.get('No', 0)
    ]

    # Create subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Email Analysis', fontsize=16)

    # Graph 1: Number of Emails per Category (Bar Chart)
    axes[0].bar(
        category_labels, category_values, color='skyblue', edgecolor='black'
    )
    axes[0].set_title('Number of Emails per Category', fontsize=12)
    axes[0].set_xlabel('Categories', fontsize=10)
    axes[0].set_ylabel('Number of Emails', fontsize=10)
    axes[0].tick_params(axis='x', rotation=45)

    # Graph 2: Email Priorities Distribution (Pie Chart)
    axes[1].pie(
        priority_sizes,
        labels=priority_labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=plt.cm.tab20c.colors[:len(priority_labels)],
        textprops={'fontsize': 9}
    )
    axes[1].set_title('Email Priorities Distribution', fontsize=12)

    # Graph 3: Emails Requiring Response (Bar Chart)
    axes[2].bar(
        response_labels, response_values,
        color=['green', 'red'], edgecolor='black'
    )
    axes[2].set_title('Emails Requiring Response (Yes/No)', fontsize=12)
    axes[2].set_xlabel('Response Required', fontsize=10)
    axes[2].set_ylabel('Number of Emails', fontsize=10)
    for i, value in enumerate(response_values):
        axes[2].text(i, value + 1, str(value), ha='center', fontsize=10)

    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()


if __name__ == "__main__":
    service = connect_to_gmail()
    print("Connected to Gmail!")

    # Fetch the latest emails
    emails = fetch_latest_emails(service)

    # Initialize GPT4All model
    llm_model = GPT4All("gpt4all-13b-snoozy-q4_0.gguf")

    # Analyze and display results
    categories = []
    priorities = []
    responses = []
    for idx, email in enumerate(emails, start=1):
        analysis = analyze_email_with_llm(
            email['subject'], email['sender'], llm_model)
        print(f"{idx}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   Category: {analysis.get('Category', 'N/A')}")
        print(f"   Priority: {analysis.get('Priority', 'N/A')}")
        print(f"   Response: {analysis.get('Response', 'N/A')}\n")
        # Collect data for visualizations
        categories.append(analysis.get('Category', 'N/A'))
        priorities.append(analysis.get('Priority', 'Normal'))
        responses.append(analysis.get('Response', 'No'))

    # Count the frequency of each category
    category_counts = Counter(categories)
    most_frequent_category, frequency = category_counts.most_common(1)[0]

    # Print the most frequent category in blue
    print(Fore.BLUE +
          f"The most frequent category is '{most_frequent_category}' - " +
          f"{frequency} times" +
          Style.RESET_ALL)

    # Generate all graphs in one figure
    plot_all_graphs(categories, priorities, responses)
