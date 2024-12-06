from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from gpt4all import GPT4All
import redis
import json
from collections import Counter
from colorama import Fore, Style
import matplotlib.pyplot as plt

# Define the scope for the Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Connect to Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Predefined categories, priorities, and responses
MAIL_CATEGORIES = {
    "Work": [],
    "Personal": [],
    "Updates/Notifications": [],
    "Promotions/Marketing": [],
    "Finance/Bills": [],
    "Shopping": [],
    "Social": [],
    "Health/Wellness": [],
    "Travel": [],
    "Education": [],
    "Other": []
}

PRIORITIES = {
    "Urgent": [],
    "Important": [],
    "Normal": [],
    "Ignore": []
}

RESPONSES = {"Yes": [], "No": []}

CACHE_EXPIRATION = 4 * 3600  # Cache duration in seconds (4 hours)


def connect_to_gmail():
    """Authenticate and connect to Gmail API."""
    flow = InstalledAppFlow.from_client_secrets_file('emails.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('gmail', 'v1', credentials=creds)
    return service


def fetch_latest_emails(service, max_results=100):
    """Fetch the latest emails from Gmail."""
    results = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = results.get('messages', [])
    email_data = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        payload = msg_data['payload']
        headers = payload['headers']

        # Extract sender and subject
        sender = next((header['value'] for header in headers if header['name'] == 'From'), "Unknown Sender")
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "(No Subject)")

        email_data.append({'sender': sender, 'subject': subject})
    return email_data


def ask_llm(question):
    """Query the LLM with caching using Redis."""
    cache_key = f"llm:{question}"
    cached_response = redis_client.get(cache_key)

    if cached_response:
        return json.loads(cached_response)  # Deserialize cached response

    response = ""
    with llm_model.chat_session():
        response = llm_model.generate(question, max_tokens=6)

    # Cache the response in Redis
    redis_client.setex(cache_key, CACHE_EXPIRATION, json.dumps(response))
    return response


def analyze_email_with_llm(subject, sender):
    """Analyze an email using the LLM and Redis caching."""
    # Create the LLM prompt
    prompt = (
        f"Analyze the following email details:\n"
        f"Sender: {sender}\n"
        f"Subject: {subject}\n\n"
        f"Decide the following:\n"
        f"1. Category (e.g., Work, Personal, Updates/Notifications, Promotions/Marketing, "
        f"Finance/Bills, Shopping, Social, Health/Wellness, Travel, Education, Other).\n"
        f"2. Priority (e.g., Urgent, Important, Normal, Ignore).\n"
        f"3. Does it require a response? (Yes/No).\n"
        f"Output format: Category: [Category], Priority: [Priority], Response: [Yes/No]"
    )

    response = ask_llm(prompt)

    # Parse the response into a structured dictionary
    response_lines = response.strip().split('\n')
    cleaned_response = {}
    for line in response_lines:
        if "Category:" in line:
            cleaned_response["Category"] = line.replace("Category:", "").strip()
        elif "Priority:" in line:
            cleaned_response["Priority"] = line.replace("Priority:", "").strip()
        elif "Response:" in line:
            cleaned_response["Response"] = line.replace("Response:", "").strip()
    return cleaned_response


def categorize_emails(email, analysis):
    """Categorize emails based on predefined categories, priorities, and responses."""
    # Add email to the appropriate category
    category = analysis.get("Category", "Other")
    MAIL_CATEGORIES.setdefault(category, []).append(email)

    # Add email to the appropriate priority
    priority = analysis.get("Priority", "Normal")
    PRIORITIES.setdefault(priority, []).append(email)

    # Add email to the appropriate response
    response = analysis.get("Response", "No")
    RESPONSES.setdefault(response, []).append(email)


def plot_all_graphs():
    """Plot graphs based on categorized email data."""
    # Count data for the graphs
    category_counts = {k: len(v) for k, v in MAIL_CATEGORIES.items()}
    priority_counts = {k.replace("2.", "").replace("1.", "").strip(): len(v) for k, v in PRIORITIES.items()}
    response_counts = {
        "Yes": sum(len(RESPONSES[key]) for key in RESPONSES if "Yes" in key),
        "No": sum(len(RESPONSES[key]) for key in RESPONSES if "No" in key),
    }

    # Prepare data for plotting
    category_labels, category_values = zip(*category_counts.items())
    priority_labels, priority_sizes = zip(*priority_counts.items())
    response_labels, response_values = zip(*response_counts.items())

    # Create subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Email Analysis', fontsize=16)

    # Graph 1: Number of Emails per Category (Bar Chart)
    cleaned_category_labels = [label.replace("1.", "").strip() for label in category_labels]
    axes[0].bar(cleaned_category_labels, category_values, color='skyblue', edgecolor='black')
    axes[0].set_title('Number of Emails per Category', fontsize=12)
    axes[0].set_xlabel('Categories', fontsize=10)
    axes[0].set_ylabel('Number of Emails', fontsize=10)
    axes[0].tick_params(axis='x', rotation=45, labelsize=9)
    axes[0].set_xticks(range(len(cleaned_category_labels)))
    axes[0].set_xticklabels(cleaned_category_labels, fontsize=9, rotation=45, ha='right')

    # Graph 2: Email Priorities Distribution (Pie Chart)
    wedges, texts, autotexts = axes[1].pie(
        priority_sizes,
        labels=priority_labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=plt.cm.tab20c.colors[:len(priority_labels)],
        textprops={'fontsize': 9}
    )
    axes[1].set_title('Email Priorities Distribution', fontsize=12)

    # Adjust the text appearance for better readability
    for text in texts:
        text.set_fontsize(9)
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color('white')

    # Graph 3: Emails Requiring Response (Bar Chart)
    axes[2].bar(response_labels, response_values, color=['green', 'red'], edgecolor='black')
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
    llm_model = GPT4All("Llama-3.2-3B-Instruct-Q4_0.gguf")

    # Analyze and display results
    for idx, email in enumerate(emails, start=1):
        analysis = analyze_email_with_llm(email['subject'], email['sender'])
        print(f"{idx}. From: {email['sender']}")
        print(f"   Subject: {email['subject']}")
        print(f"   Category: {analysis.get('Category', 'N/A')}")
        print(f"   Priority: {analysis.get('Priority', 'N/A')}")
        print(f"   Response: {analysis.get('Response', 'N/A')}\n")
        categorize_emails(email, analysis)

    # Count the frequency of each category
    category_counts = {k: len(v) for k, v in MAIL_CATEGORIES.items()}
    most_frequent_category = max(category_counts, key=category_counts.get)
    frequency = category_counts[most_frequent_category]

    # Print the most frequent category in blue
    print(Fore.BLUE + f"The most frequent category is '{most_frequent_category}' - {frequency} times" + Style.RESET_ALL)

    # Generate all graphs in one figure
    plot_all_graphs()