from yars import YARS
from yars import media_scraping_utils
from yars import utils
import pathlib


miner = YARS()
reddit_type = "user"
is_user_flag = reddit_type == "user"

subreddit_posts = miner.fetch_subreddit_post_image_metadata(
    "FrostGlistenss",
    subreddit_is_a_user_profile=is_user_flag,
    limit=1000,
    category="new",
    time_filter="all",
)

utils.download_video(subreddit_posts[0]["url"], pathlib.Path("test.mp4"))
breakpoint()