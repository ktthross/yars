from yars import YARS

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

breakpoint()