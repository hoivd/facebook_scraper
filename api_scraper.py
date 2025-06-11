from utils import Utils
from driver_manager import ControllerDriver
import time
from logger import setup_logger
from selenium.webdriver.common.by import By
import argparse
from enum import Enum
import logging

logger = setup_logger(__name__, logging.DEBUG)
class ApiScraper():
    def __init__(self, cookies_path: str, api_path: str):
        cookies_data = Utils.load_cookies(cookies_path)
        self.cookies = cookies_data["cookies"]
        self.api_path = api_path
    
    def _get_post_api(self, page_url_path: str) -> None:
        post_api_key = "ProfileCometTimelineFeedRefetchQuery"

        driver = ControllerDriver()
        driver.start_controller()

        for _ in range(2):
            if Utils.is_apis_in_source(self.api_path, [post_api_key]) == False:
                url = Utils.get_random_url(page_url_path)
                logger.debug(f"Đang truy cập url {url}")
                driver.go_to_url(url)

                driver.add_cookie(self.cookies)
                logger.debug("Thêm cookie thành công")
                driver.refresh()
                driver.is_page_loaded()

                driver.random_scroll(5)
                
        driver.stop_controller()
        if Utils.is_apis_in_source(self.api_path, [post_api_key]) == False:
            logger.debug(f"Lấy {post_api_key} thất bại")
        else:
            logger.debug(f"Lấy {post_api_key} thành công")

            post_api_path = "./api_info/post_api.json"
            Utils.export_api2json(self.api_path, post_api_path, [post_api_key])


    def _get_comment_api(self, post_url_path: str) -> None:
        # Khởi tạo driver
        comment_apis = [
            "CommentListComponentsRootQuery",
            "CommentsListComponentsPaginationQuery"    
        ]

        driver = ControllerDriver()
        driver.start_controller()

        for _ in range(2):
            if Utils.is_apis_in_source(self.api_path, comment_apis) == False:
                url = Utils.get_random_url(post_url_path)
                logger.debug(f"Đang truy cập url {url}")
                driver.go_to_url(url)
                driver.add_cookie(self.cookies)
                logger.debug("Thêm cookie thành công")
                driver.refresh()
                driver.is_page_loaded()

                choice_comment_element = [
                    {"by": By.XPATH, "selector": '//div[@role="button"]//span[text()="Phù hợp nhất"]'},
                    {"by": By.XPATH, "selector": '//div[@role="button" and .//span[contains(text(), "Most relevant")]]'}
                ]
                choice_comment_button = driver.find_first_match(choice_comment_element)
                if choice_comment_button is not None and driver.is_clickable(choice_comment_button):
                    choice_comment_button.click()
                
                time.sleep(1)

                choice_rank_element = [
                    {"by": By.XPATH, "selector": '//div[@role="menuitem" and .//span[text()="All comments"]]'}
                ]
                choice_rank_button = driver.find_first_match(choice_rank_element)
                if choice_rank_button is not None and driver.is_clickable(choice_rank_button):
                    choice_rank_button.click()

                scrollable_element = driver.get_first_scrollable_element()

                logger.debug(f"Phần tử cuộn được {scrollable_element}")

                for _ in range(2):
                    if Utils.is_apis_in_source(self.api_path, [comment_apis[1]]) == False:
                        if scrollable_element is not None:
                            driver.scroll_element(scrollable_element, repeat=10) 

        if Utils.is_apis_in_source(self.api_path, comment_apis) == False:
            logger.debug(f"Lấy {comment_apis} thất bại")
        else:
            logger.debug(f"Lấy {comment_apis} thành công")
            comment_api_path = "./api_info/comment_api.json"
            Utils.export_api2json(self.api_path, comment_api_path, comment_apis)

        driver.stop_controller()

if __name__ == "__main__":
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
