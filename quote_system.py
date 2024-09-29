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
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS quotes
                 (id INTEGER PRIMARY KEY, quote TEXT, author TEXT, used BOOLEAN)''')
    conn.commit()
    conn.close()

# Function to add new quotes to the database
def update_database():
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()
    
    with open('quotes.txt', 'r') as file:
        quotes = file.readlines()
    
    new_quotes = 0
    errors = 0
    
    for quote in quotes:
        try:
            quote_text, author = quote.strip().split('" - ')
            quote_text = quote_text.strip('"')
            c.execute("INSERT OR IGNORE INTO quotes (quote, author, used) VALUES (?, ?, ?)", 
                      (quote_text, author, False))
            if c.rowcount > 0:
                new_quotes += 1
        except ValueError:
            errors += 1
    
    conn.commit()
    
    # Get total quote count
    c.execute("SELECT COUNT(*) FROM quotes")
    total_quotes = c.fetchone()[0]
    
    conn.close()
    
    # Update summary file
    with open('summary.txt', 'a') as summary:
        summary.write(f"Update Date: {datetime.now()}\n")
        summary.write(f"Total Quotes: {total_quotes}\n")
        summary.write(f"New Quotes Added: {new_quotes}\n")
        summary.write(f"Errors: {errors}\n\n")

# Function to get a random unused quote
def get_random_quote():
    conn = sqlite3.connect('quotes.db')
    c = conn.cursor()
    c.execute("SELECT id, quote, author FROM quotes WHERE used = 0 ORDER BY RANDOM() LIMIT 1")
    result = c.fetchone()
    if result:
        quote_id, quote, author = result
        c.execute("UPDATE quotes SET used = 1 WHERE id = ?", (quote_id,))
        conn.commit()
    conn.close()
    return quote, author if result else (None, None)

# Function to send SMS via email
def send_sms_via_email(quote, author):
    # Email configuration
    sender_email = "eric.skotnicki@gmail.com"
    sender_password = os.getenv('GMAIL_APP_PASSWORD')
    
    if sender_password is None:
        raise ValueError("GMAIL_APP_PASSWORD not set in .env file")
    
    # List of phone numbers and their corresponding email-to-SMS gateways
    recipients = [
        "3046851372@txt.att.net",        # AT&T
        "8324193684@tmomail.net",        # T-Mobile
        # "3456789012@vtext.com",          # Verizon
        # "4567890123@messaging.sprintpcs.com",  # Sprint
        # "5678901234@msg.fi.google.com"   # Google Fi
    ]
    
    # Prepare the message
    subject = "Quote of the Day"
    body = f"Quote of the Day: \"{quote}\" - {author}"
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    
    # Send the email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(sender_email, sender_password)
            smtp_server.sendmail(sender_email, recipients, msg.as_string())
        print("SMS sent successfully")
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")

# Function to send daily quote
def send_daily_quote():
    quote, author = get_random_quote()
    if quote and author:
        send_sms_via_email(quote, author)

# Schedule tasks
schedule.every().monday.at("00:00").do(update_database)
schedule.every().day.at("09:00").do(send_daily_quote)

# Main loop
if __name__ == "__main__":
    setup_database()
    while True:
        schedule.run_pending()
        time.sleep(60)