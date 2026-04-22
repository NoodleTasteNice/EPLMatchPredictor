import os
import praw
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)

subreddit = reddit.subreddit("soccer")
for submission in subreddit.search("Match Thread", limit=1):
    print(f"Connection Successful! Found match: {submission.title}")
