from api_scraper import ApiScraper
import argparse

parser = argparse.ArgumentParser(description="Chương trình lấy FACEBOOK API")
parser.add_argument("type_api", choices=["post_api", "comment_api"], help="Chọn loại Facebook API cần lấy\n post_api: Lấy api để lấy bài post\n comment_api: Lấy api để lấy bình luận")

agrs = parser.parse_args()
type_api = agrs.type_api

cookie_path = "./chrome_profile/cookies/cookies.json"
api_path = "./api_info/api_info.json"

api_scraper = ApiScraper(cookie_path, api_path) 

post_url_path = "./facebook_urls/post_urls.txt"
page_url_path = "./facebook_urls/page_urls.txt"

if type_api == "post_api":
    api_scraper._get_post_api(page_url_path)
elif type_api == "comment_api":
    api_scraper._get_comment_api(post_url_path)
