import streamlit as st
from datetime import date, timedelta # Added timedelta for date arithmetic
import pandas as pd
from supabase import create_client, Client
import time
import re # Added for email validation

# --- Streamlit App Layout ---
# MUST be the first Streamlit command executed
st.set_page_config(page_title="Gratitude & Letters App", layout="wide")

# --- Configuration & Initialization ---
# This code requires the 'supabase' Python package (pip install supabase)
# and a .streamlit/secrets.toml file with [supabase] and [admin] configurations.

if 'supabase' not in st.secrets or 'url' not in st.secrets['supabase']:
    st.error("Supabase secrets not configured. Please set up .streamlit/secrets.toml.")
    st.stop()
    
# Tables (Collections) in Supabase
DAILY_TABLE = "daily_gratitude"
WEEKLY_TABLE = "weekly_letters"
USERS_TABLE = "user_data" # Table for storing user IDs and emails

if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- Supabase Connection and Data Handling ---

@st.cache_resource(ttl=3600)
def get_supabase_client() -> Client:
    """Connects to Supabase using the configured secrets."""
    try:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"Error connecting to Supabase. Check your secrets.toml: {e}")
        st.stop()

supabase = get_supabase_client()

@st.cache_data(ttl=60) 
def load_all_data(table_name):
    """Loads ALL data from a specific table (used by Superuser)."""
    try:
        # Fetches all data using the anonymous key
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.warning(f"Could not load data from {table_name}. Error: {e}")
        return pd.DataFrame()

# --- Check if user already exists in user_data table ---
def check_user_exists(username):
    """Checks if a username already exists in the USERS_TABLE."""
    try:
        # Query the users table specifically
        response = supabase.table(USERS_TABLE).select("user_id", count="exact").eq("user_id", username).execute()
        return response.count > 0
    except Exception as e:
        print(f"Error checking user existence in {USERS_TABLE}: {e}")
        return False

# --- Function to save new user registration details ---
def register_new_user(username, email):
    """Saves the new user's username and email to the user_data table."""
    data_to_save = {
        'user_id': username,
        'email': email,
    }
    
    try:
        supabase.table(USERS_TABLE).insert(data_to_save).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Critical error during user registration to '{USERS_TABLE}'. See below for details:")
        st.exception(e)
        return False

# --- Email Validation ---
def is_valid_email(email):
    """Basic email format validation."""
    # Simple regex for structure check
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


@st.cache_data(ttl=60) 
def load_user_data(table_name, user_id):
    """Loads ONLY data linked to the current user_id (for privacy)."""
    try:
        # Filter query: ONLY return rows where user_id matches the logged-in user
        response = supabase.table(table_name).select("*").eq("user_id", user_id).execute()
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.warning(f"Could not load user data from {table_name}. Error: {e}")
        return pd.DataFrame()

def insert_to_supabase(table_name, data):
    """Inserts a new row of data and clears cache to force data reload."""
    try:
        supabase.table(table_name).insert(data).execute()
        st.cache_data.clear() # Invalidate cache 
        return True
    except Exception as e:
        # --- MODIFIED FOR DEBUGGING ---
        st.error(f"Critical error during database write (Table: {table_name}). See below for details:")
        st.exception(e) # Displays the full traceback and error message
        # --- END MODIFIED BLOCK ---
        return False

# --- Helper for weekly date calculation ---
def get_week_start(d: date) -> str:
    """Returns the ISO-formatted date for the Monday of the given date's week."""
    # isoweekday() returns 1 for Monday, 7 for Sunday. Subtract (weekday - 1) days.
    start_of_week = d - timedelta(days=d.isoweekday() - 1)
    return start_of_week.isoformat()

# --- App Logic Functions (Supabase-integrated) ---

def save_daily_entry(username, entry):
    """Saves the daily entry to the daily_gratitude table."""
    data_to_save = {
        'user_id': username, # Crucial for identification and filtering
        'date': entry['date'],
        'g1': entry['gratitude_1'], 'r1': entry['reason_1'],
        'g2': entry['gratitude_2'], 'r2': entry['reason_2'],
        'g3': entry['gratitude_3'], 'r3': entry['reason_3'],
    }
    if insert_to_supabase(DAILY_TABLE, data_to_save):
        st.success(f"Daily Gratitude saved for **{username}** on **{entry['date']}**!")

def save_weekly_letter(username, week_start, letter_content):
    """Saves the weekly letter to the weekly_letters table."""
    data_to_save = {
        'user_id': username, # Crucial for identification and filtering
        'week_start': week_start,
        'letter_content': letter_content,
    }
    if insert_to_supabase(WEEKLY_TABLE, data_to_save):
        st.success(f"Weekly Letter saved for the week starting **{week_start}**!")


# --- Email Reminder Placeholder Function ---
def schedule_email_reminder(username):
    """Placeholder for scheduling an email."""
    # Note: This app-side reminder is just a UI message.
    # The actual scheduling/sending happens in the external send_reminders.py script.
    st.info(f"Email reminder preference saved for **{username}** (Check {USERS_TABLE} table).")
    pass


## 🔑 User Login Flow
if st.session_state.logged_in_user is None:
    st.title("Welcome to Your Daily Gratitude App")
    st.markdown("---")
    
    col_login, col_reg = st.columns(2)

    # --- LOGIN FORM (Existing User) ---
    with col_login:
        st.subheader("Existing User Login")
        with st.form("login_form"):
            login_username = st.text_input("Enter Your Username (e.g., Alex2331)", key="login_username_input")
            
            if st.form_submit_button("Log In"):
                if not login_username:
                    st.error("Please enter your username.")
                elif check_user_exists(login_username):
                    # Existing user: Log in immediately
                    st.session_state.logged_in_user = login_username
                    st.success(f"Welcome back, **{login_username}**!")
                    st.rerun()
                else:
                    st.warning("Username not found in our records. Please register on the right.")

    # --- REGISTRATION FORM (New User) ---
    with col_reg:
        st.subheader("New User Registration")
        with st.form("registration_form"):
            reg_username = st.text_input("Choose Username (Name + 4 digits, e.g., Sarah9012)", key="reg_username_input")
            reg_email = st.text_input("Your Email (for daily reminders)", key="reg_email_input")
            
            # The enable_reminders checkbox controls whether the email is saved/used, 
            # though here we save the email regardless, assuming the external script handles preferences.
            st.checkbox("Enable daily email reminders", key="reg_enable_reminders", value=True) 
            
            if st.form_submit_button("Register & Log In"):
                # 1. Basic Validation
                if not reg_username or not reg_email:
                    st.error("Both Username and Email are required.")
                elif not is_valid_email(reg_email):
                    st.error("Please enter a valid email address.")
                # 2. Check for Username Duplication
                elif check_user_exists(reg_username):
                    st.error(f"The username '{reg_username}' is already taken. Please choose another.")
                # 3. Register and Log In
                else:
                    if register_new_user(reg_username, reg_email):
                        st.session_state.logged_in_user = reg_username
                        if st.session_state.reg_enable_reminders:
                            schedule_email_reminder(reg_username) 
                        st.rerun()

else:
    user = st.session_state.logged_in_user
    today_str = date.today().isoformat()
    
    # Check if current user is the Superuser based on secrets.toml
    # Safely handle missing admin key
    if 'admin' in st.secrets and 'superuser_name' in st.secrets.admin:
        is_superuser = user == st.secrets.admin.superuser_name
    else:
        is_superuser = False

    # Load data based on user type (Privacy check)
    df_daily_entries = load_user_data(DAILY_TABLE, user) # Loads only user's data
    df_weekly_letters = load_user_data(WEEKLY_TABLE, user) # Loads only user's data
    
    # --- Sidebar for Navigation and History ---
    with st.sidebar:
        st.title(f"👋 {user}'s Journal")
        st.header("Navigation & History")
        
        # Logout Button in Sidebar
        if st.button("Logout", key="sidebar_logout"):
            st.session_state.logged_in_user = None
            st.cache_data.clear() # Clear cache on logout
            st.rerun()
            
        st.markdown("---")
        
        # Previous Entries Dropdown
        st.subheader("🗓️ Previous Daily Entries")
        # FIX: Check if DataFrame is empty before trying to access the 'date' column
        if not df_daily_entries.empty:
            daily_dates = sorted(df_daily_entries['date'].unique(), reverse=True)
        
            if daily_dates:
                # Drop the user_id column for non-superusers in history view
                history_df = df_daily_entries if is_superuser else df_daily_entries.drop(columns=['user_id'], errors='ignore')
                
                selected_date = st.selectbox("Select a date to view:", daily_dates)
                
                if selected_date:
                    entry = history_df[history_df['date'] == selected_date].iloc[0]
                    # Column names g1, r1, etc., match your Supabase table schema
                    st.markdown(f"**Gratitude 1:** {entry['g1']}")
                    st.markdown(f"**Reason 1:** {entry['r1']}")
            else:
                st.info("No daily entries yet.")
        else:
            st.info("No daily entries yet.") # Display if the initial DataFrame load was empty
        
        if is_superuser:
            st.markdown("---")
            st.subheader("👑 Superuser Tools")
            st.info("Viewing all data via the tabs.")


    # --- Main Content: Tabs ---
    st.title(f"🙏 Your Gratitude Journal")
    tab1, tab2 = st.tabs(["✨ Daily Gratitude", "📝 Weekly Letter/Reflection"]) 

    # ===============================================
    # TAB 1: Daily Gratitude Submission / View
    # ===============================================
    with tab1:
        
        if is_superuser:
            # Superuser view
            st.header("👑 Daily Gratitude - ALL DATA")
            # Only load all data here if user is superuser to avoid loading all data upfront
            df_all_daily_entries = load_all_data(DAILY_TABLE)
            st.dataframe(df_all_daily_entries) # Shows user_id column
            
        else:
            st.subheader(f"What 3 things are you grateful for today ({today_str})?")
            # Check if the user already submitted today
            # Use the daily_dates list from the sidebar setup
            has_submitted_today = today_str in daily_dates if 'daily_dates' in locals() and daily_dates else False
            
            if has_submitted_today:
                st.warning("You've already submitted your gratitude for today!")
                entry = df_daily_entries[df_daily_entries['date'] == today_str].iloc[0]
                # Show only the gratitude columns to the user
                st.dataframe(entry[['g1', 'r1', 'g2', 'r2', 'g3', 'r3']].to_frame().T)
                
            else:
                with st.form("gratitude_form"):
                    
                    # --- Single-Row Gratitude Inputs ---
                    # Keep the header columns for desktop layout clarity
                    col_h1, col_h2 = st.columns([1, 1.5])
                    col_h1.markdown("**I am grateful for...**")
                    col_h2.markdown("**Why?**")
                    
                    # Row 1
                    col1_1, col1_2 = st.columns([1, 1.5])
                    # FIX: Removed label_visibility="collapsed" and made labels unique for mobile
                    g1 = col1_1.text_input("1. I am grateful for...", key="g1", placeholder="Example: The hot cup of tea this morning") 
                    r1 = col1_2.text_input("1. Reason (Why?):", key="r1", placeholder="Example: It helped me wake up and focus")
                    
                    # Row 2
                    col2_1, col2_2 = st.columns([1, 1.5])
                    # FIX: Removed label_visibility="collapsed" and made labels unique for mobile
                    g2 = col2_1.text_input("2. I am grateful for...", key="g2", placeholder="Example: A positive comment from a friend")
                    r2 = col2_2.text_input("2. Reason (Why?):", key="r2", placeholder="Example: It boosted my confidence for the day")

                    # Row 3
                    col3_1, col3_2 = st.columns([1, 1.5])
                    # FIX: Removed label_visibility="collapsed" and made labels unique for mobile
                    g3 = col3_1.text_input("3. I am grateful for...", key="g3", placeholder="Example: Finishing a challenging task")
                    r3 = col3_2.text_input("3. Reason (Why?):", key="r3", placeholder="Example: It cleared my schedule for fun activities")
                    
                    st.markdown("---")
                    
                    submit_button = st.form_submit_button("✨ Submit My Daily Gratitude ✨")

                    if submit_button:
                        if all([g1, r1, g2, r2, g3, r3]):
                            entry = {
                                'date': today_str,
                                'gratitude_1': g1, 'reason_1': r1,
                                'gratitude_2': g2, 'reason_2': r2,
                                'gratitude_3': g3, 'reason_3': r3,
                            }
                            save_daily_entry(user, entry)
                            st.balloons()
                            st.rerun() 
                        else:
                            st.error("Please fill in all 3 gratitude items and their reasons.")

    # ===============================================
    # TAB 2: Weekly Letter Submission / View
    # ===============================================
    with tab2:
        
        if is_superuser:
            # Superuser view
            st.header("👑 Weekly Letters - ALL DATA")
            # Only load all data here if user is superuser
            df_all_weekly_letters = load_all_data(WEEKLY_TABLE)
            st.dataframe(df_all_weekly_letters)
            
        else:
            st.header("Weekly Reflection")
            
            # Calculate current week start (Monday)
            current_week_start_str = get_week_start(date.today()) 
            
            # --- FIX FOR KEYERROR: Check if DataFrame is populated before accessing columns ---
            if not df_weekly_letters.empty:
                weekly_dates = df_weekly_letters['week_start'].unique().tolist()
                has_submitted_this_week = current_week_start_str in weekly_dates
            else:
                weekly_dates = []
                has_submitted_this_week = False
            # --- END FIX ---
            
            st.info(f"Writing reflection for the week starting: **{current_week_start_str}**")
            
            if has_submitted_this_week:
                st.warning(f"You have already submitted a weekly letter for the week starting {current_week_start_str}. You can only submit one per week.")
                
                # Show the submitted content for confirmation
                try:
                    submitted_entry = df_weekly_letters[df_weekly_letters['week_start'] == current_week_start_str].iloc[0]
                    st.subheader("Your Submission:")
                    st.markdown(f"***{submitted_entry['letter_content']}***")
                except IndexError:
                    st.info("Submitted letter content could not be retrieved.")
                
            else:
                with st.form("weekly_letter_form"):
                    weekly_letter_content = st.text_area(
                        "Write your longer weekly letter or reflection here:",
                        height=400,
                        key="weekly_letter_content"
                    )
                    submit_weekly = st.form_submit_button("Save Weekly Letter")

                    if submit_weekly:
                        if weekly_letter_content:
                            # Use the calculated week start date for saving
                            save_weekly_letter(user, current_week_start_str, weekly_letter_content)
                            st.rerun()
                        else:
                            st.error("Please write something for your weekly letter.")
                        
            st.markdown("---")
            
            # Display Weekly Letter History for the user
            st.subheader("Weekly Letter History")
            if not df_weekly_letters.empty:
                # Dropping the user_id column for display to non-superusers
                display_df = df_weekly_letters.drop(columns=['user_id'], errors='ignore')
                st.dataframe(display_df)
            else:
                st.info("No weekly letters saved yet.")
