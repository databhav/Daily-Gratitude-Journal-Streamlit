import os
from supabase import create_client, Client
from datetime import date
import sys 
# import requests # <-- Uncomment this line if you integrate with a real email API (SendGrid, Mailgun, etc.)

# --- Configuration (Assumes Environment Variables are Set) ---
# The scheduler (e.g., cron, cloud function) running this script MUST
# set these environment variables securely.

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

DAILY_TABLE = "daily_gratitude"
USERS_TABLE = "user_data"

# NOTE: REPLACE THIS WITH YOUR DEPLOYED APP LINK
APP_LINK = "https://YOUR-DEPLOYED-APP-LINK.streamlit.app" 

# --- Supabase Connection ---

def get_supabase_client() -> Client:
    """Connects to Supabase using environment variables."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        # We use sys.exit(1) to stop the script if environment variables are missing
        print("FATAL: SUPABASE_URL or SUPABASE_KEY environment variables not set.")
        sys.exit(1)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        sys.exit(1)

supabase = get_supabase_client()

# --- Email Sending Blueprint ---
def send_real_email(recipient_email: str, recipient_user_id: str, email_body: str):
    """
    Blueprint for sending a real email using an external API (e.g., SendGrid, Mailgun).
    
    You would replace this function with an actual API call. 
    A quick search for "Python SendGrid API" will give you the necessary setup.
    """
    subject = f"Friendly Reminder: Time for your Gratitude, {recipient_user_id}!"
    sender_email = "sneha@gratitudeapp.com" # Example sender address
    
    # Example using a mock log
    print("------------------------------------------------------------------")
    print(f"To: {recipient_email}")
    print(f"From: {sender_email}")
    print(f"Subject: {subject}")
    print("Body:")
    print(email_body)
    print("------------------------------------------------------------------")
    # if requests is imported:
    # try:
    #     requests.post(
    #         "YOUR_EMAIL_API_ENDPOINT",
    #         auth=("api", "YOUR_API_KEY"),
    #         data={
    #             "from": sender_email,
    #             "to": [recipient_email],
    #             "subject": subject,
    #             "text": email_body 
    #         }
    #     )
    # except Exception as e:
    #     print(f"Failed to send email to {recipient_email}: {e}")
    

# --- Core Logic ---

def get_users_needing_reminder(supabase_client: Client) -> list:
    """
    Fetches the list of all users and filters it down to those who 
    have *not* submitted their daily gratitude today.
    """
    today_str = date.today().isoformat()
    print(f"Checking for users who have not submitted their gratitude for: {today_str}")

    # 1. Get all active users (user_id and email)
    try:
        # Selecting email is crucial here
        users_response = supabase_client.table(USERS_TABLE).select("user_id, email").execute()
        all_users = {user['user_id']: user['email'] for user in users_response.data}
    except Exception as e:
        print(f"Error fetching users from {USERS_TABLE}: {e}")
        return []

    # 2. Get the list of users who HAVE submitted today
    try:
        submitted_response = supabase_client.table(DAILY_TABLE).select("user_id").eq("date", today_str).execute()
        # Create a set for fast lookup of users who already submitted
        submitted_user_ids = {entry['user_id'] for entry in submitted_response.data}
    except Exception as e:
        print(f"Error fetching submissions from {DAILY_TABLE}: {e}")
        submitted_user_ids = set() 
        
    # 3. Determine users who NEED a reminder
    users_to_remind = []
    for user_id, email in all_users.items():
        # Only remind if the user hasn't submitted AND they have an email address recorded
        # The app should save an empty string or null if they opt out, but we check for truthiness
        if user_id not in submitted_user_ids and email:
            users_to_remind.append({'user_id': user_id, 'email': email})

    print(f"Total users found: {len(all_users)}")
    print(f"Users who submitted today: {len(submitted_user_ids)}")
    print(f"Users needing reminder: {len(users_to_remind)}")
    
    return users_to_remind

def send_email_reminders(users_to_remind: list):
    """
    Sends email reminders to the list of users with your custom content.
    """
    if not users_to_remind:
        print("No reminders to send.")
        return

    for user in users_to_remind:
        user_id = user['user_id']
        recipient_email = user['email']
        
        # Construct the specific email body you requested
        email_body = f"""
Hey, did you fill the DAILY GRATITUDE FORM today:

Here's the link: {APP_LINK}

Sweet regards,
Sneha
"""
        
        # Replace send_real_email with your actual email sending API integration
        send_real_email(recipient_email, user_id, email_body)
        


def main():
    """Main function to run the daily reminder job."""
    print(f"Starting Daily Reminder Job at: {date.today()}")
    
    users_for_reminder = get_users_needing_reminder(supabase)
    send_email_reminders(users_for_reminder)
    
    print("Daily Reminder Job Finished.")

if __name__ == "__main__":
    main()