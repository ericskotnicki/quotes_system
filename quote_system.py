# Import the necessary libraries
import sqlite3
import schedule
import time
import os
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database setup
def setup_database():
    """Create the SQLite database and a table for storing quotes if they don't already exist."""
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS quotes
                 (id INTEGER PRIMARY KEY, quote TEXT UNIQUE, author TEXT, used BOOLEAN)""")
    conn.commit()
    conn.close()
    print("\nDatabase setup complete.")

# Function to remove duplicates from the database
def remove_duplicates():
    """Remove any duplicate quotes in the database."""
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()

    # Remove duplicates by keeping only the first occurrence of each quote
    c.execute("""DELETE FROM quotes
                 WHERE rowid NOT IN (SELECT MIN(rowid) 
                                     FROM quotes
                                     GROUP BY quote)""")

    conn.commit()
    conn.close()
    
    # If duplicates were removed, print a message
    if c.rowcount > 0:
        print(f"Removed {c.rowcount} duplicate quotes from the database.")

# Function to add new quotes to the database
def update_database():
    """Read quotes from a text file and add new quotes to the database, ignoring duplicates."""
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()
    
    with open('quotes.txt', 'r') as file:
        quotes = file.readlines()
    
    new_quotes = 0
    errors = 0
    
    for row_number, quote in enumerate(quotes, start=1):
        try:
            quote_text, author = quote.strip().rsplit(' - ', 1)
            # Strip both styles of quotations
            quote_text = quote_text.strip('“”""')
            # Check if the quote is already in the database
            c.execute("SELECT COUNT(*) FROM quotes WHERE quote = ? AND author = ?", (quote_text, author))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO quotes (quote, author, used) VALUES (?, ?, ?)", 
                          (quote_text, author, False))
                new_quotes += 1
        except ValueError:
            errors += 1
            print(f"Error in row {row_number}: {quote.strip()}")
    
    conn.commit()
    
    # Get total quote count
    c.execute("SELECT COUNT(*) FROM quotes")
    total_quotes = c.fetchone()[0]
    
    conn.close()
    
    # Print summary of update
    print(f"Database update completed.")
    print(f"New quotes added: {new_quotes}")
    print(f"Errors: {errors}")
    print(f"Total quotes: {total_quotes}\n")
    
    # Update summary file
    with open('summary.txt', 'a') as summary:
        summary.write(f"Update Date: {datetime.now()}\n")
        summary.write(f"Total Quotes: {total_quotes}\n")
        summary.write(f"New Quotes Added: {new_quotes}\n")
        summary.write(f"Errors: {errors}\n\n")

# Function to retrieve a random unused quote from the database
def get_random_quote():
    """Select a random unused quote from the database."""
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()
    c.execute("SELECT quote, author FROM quotes WHERE used = 0 ORDER BY RANDOM() LIMIT 1")
    result = c.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return None, None

# Function to send an SMS via email
def send_sms_via_email(quote, author):
    """Send a quote via email to SMS gateway."""
    sender_email = "eric.skotnicki@gmail.com"
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    if not sender_email or not sender_password:
        raise ValueError("GMAIL_USER or GMAIL_APP_PASSWORD not set in .env file")
    
    recipients = [
        "3046851372@txt.att.net",
        "8324193684@tmomail.net"
    ]
    
    # subject = "Quote of the Day"
    body = f'Quote of the Day:\n"{quote}" - {author}'
    
    # MIMEText: For plain text or HTML content.
    # MIMEImage: For image attachments.
    # MIMEAudio: For audio attachments.
    # MIMEMultipart: For emails with multiple parts (e.g., text and attachments).
    
    msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = sender_email
    # msg['To'] = ', '.join(recipients)
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(sender_email, sender_password)
            smtp_server.sendmail(sender_email, recipients, msg.as_string())
        print("SMS sent successfully")
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")

# Function to send daily quote
def send_daily_quote():
    """Gets a random quote and sends it to the recipients via email-to-SMS gateways."""
    quote, author = get_random_quote()
    if quote and author:
        send_sms_via_email(quote, author)
    else:
        print("No unused quotes available to send.")

# Schedule tasks
schedule.every().monday.at("00:00").do(update_database)   # Updates the database every Monday at midnight
schedule.every().day.at("09:00").do(send_daily_quote)   # Sends the daily quote every day at 9:00 AM

# Quick test schedule
schedule.every(1).minutes.do(send_daily_quote)   # Sends the daily quote every minute for testing

# Main loop
if __name__ == "__main__":
    setup_database()
    remove_duplicates()  # Ensure duplicates are removed initially
    update_database()  # Ensure the database is updated with quotes initially
    while True:
        schedule.run_pending()
        time.sleep(60)
