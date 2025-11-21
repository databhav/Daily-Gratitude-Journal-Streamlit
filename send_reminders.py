import os
import sys
import requests
from supabase import create_client, Client
import pandas as pd
import time 
import json # Added to handle JSON response

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
MAILJET_PUBLIC_KEY = os.environ.get("MAILJET_PUBLIC_KEY")
MAILJET_SECRET_KEY = os.environ.get("MAILJET_SECRET_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL") 
USERS_TABLE = "user_data" 

if not all([SUPABASE_URL, SUPABASE_KEY, MAILJET_PUBLIC_KEY, MAILJET_SECRET_KEY, SENDER_EMAIL]):
    print("FATAL: Required environment variables are missing (Supabase keys, Mailjet keys, or SENDER_EMAIL).")
    sys.exit(1)

# --- Supabase Functions (Unchanged) ---
def get_supabase_client() -> Client:
    """Connects to Supabase."""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        sys.exit(1)

def fetch_users_for_reminder(supabase_client):
    """Fetches user_id and email for all users who registered and have an email."""
    try:
        response = supabase_client.table(USERS_TABLE).select("user_id, email").not_eq("email", "null").execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        print(f"Error fetching users from {USERS_TABLE}: {e}")
        return pd.DataFrame()

# --- Email Function (Uses Mailjet API) ---

def send_reminder_email(recipient_email, username):
    """Sends a personalized gratitude journal reminder using Mailjet API."""
    
    subject = f"IMPORTANT: Daily Gratitude Form Fill Reminder for {username}"
    
    # Customized HTML Body (Formatted for readability and delivery)
    html_content = f"""
    <html>
    <body style="font-family: sans-serif; padding: 20px; background-color: #f4f4f9;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h2 style="color: #333;">Dear {username},</h2>
            
            <p style="line-height: 1.5; margin-bottom: 25px;">
                If you have forgotten to fill the form today, please access your journal here:
            </p>
            
            <p style="text-align: center; margin: 25px 0;">
                <a href="https://dailygratitude.streamlit.app/" 
                   style="background-color: #4CAF50; color: white; padding: 12px 25px; text-align: center; text-decoration: none; display: inline-block; border-radius: 8px; font-weight: bold; font-size: 16px;">
                   Fill the Gratitude Form
                </a>
            </p>
            
            <p style="line-height: 1.5; margin-top: 25px;">
                Hope you had a day full of Gratitude.
            </p>
            
            <p style="margin-top: 30px;">
                Grateful regards,<br>
                <strong>Sneha</strong>
            </p>
        </div>
    </body>
    </html>
    """
    
    data = {
        'Messages': [{
            'From': {'Email': SENDER_EMAIL, 'Name': 'Sneha | Gratitude App'},
            'To': [{'Email': recipient_email}],
            'Subject': subject,
            'HTMLPart': html_content,
            'CustomID': f'GratitudeReminder_{username}_{time.strftime("%Y%m%d")}'
        }]
    }

    try:
        response = requests.post(
            'https://api.mailjet.com/v3.1/send',
            auth=(MAILJET_PUBLIC_KEY, MAILJET_SECRET_KEY),
            json=data
        )
        
        response_json = response.json()

        if response.status_code == 200:
            # Print the JSON response to confirm Mailjet acceptance details
            print(f"SUCCESS: Email accepted for {recipient_email}. Mailjet Response: {json.dumps(response_json, indent=2)}")
        else:
            # Print full response text on error
            print(f"ERROR: Email failed for {recipient_email}. Status: {response.status_code}. Mailjet Error: {response.text}")
            
    except Exception as e:
        print(f"FATAL API ERROR for {recipient_email}: {e}")

# --- Main Execution (Unchanged) ---
def main():
    print("Starting daily reminder script...")
    supabase_client = get_supabase_client()
    user_df = fetch_users_for_reminder(supabase_client)

    if user_df.empty:
        print("No users found to send reminders to.")
        return

    print(f"Found {len(user_df)} users for reminders.")
    
    for index, row in user_df.iterrows():
        if 'email' in row and pd.notna(row['email']) and 'user_id' in row and pd.notna(row['user_id']):
            username = row['user_id']
            send_reminder_email(row['email'], username)
            time.sleep(0.5) 
        else:
            print(f"Skipping row {index}: missing email or user_id.")


    print("Daily reminder script finished.")

if __name__ == "__main__":
    main()
