from utils import Utils
from driver_manager import ControllerDriver
import time
from logger import setup_logger
from selenium.webdriver.common.by import By

logger = setup_logger(__name__)

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
                logger.info(f"Đang truy cập url {url}")
                driver.go_to_url(url)

                driver.add_cookie(self.cookies)
                logger.info("Thêm cookie thành công")
                driver.refresh()
                driver.is_page_loaded()

                driver.random_scroll(5)
                
                # comment_button_elem = '//div[@aria-label="Leave a comment"]'
                # comment_button = driver.find_element_by_xpath(comment_button_elem)
                # if comment_button is not None:
                #     driver.scroll_into_view(comment_button)
                #     time.sleep(2)
                #     if driver.is_clickable(comment_button):
                #         comment_button.click()
        
        driver.stop_controller()
        if Utils.is_apis_in_source(self.api_path, [post_api_key]) == False:
            logger.info(f"Lấy {post_api_key} thất bại")
        else:
            logger.info(f"Lấy {post_api_key} thành công")

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
                logger.info(f"Đang truy cập url {url}")
                driver.go_to_url(url)
                driver.add_cookie(self.cookies)
                logger.info("Thêm cookie thành công")
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

                # script = '''
                #     const allElements = document.querySelectorAll("*");
                #     const visibleScrollables = [];

                #     for (const el of allElements) {
                #         const style = getComputedStyle(el);
                #         const canScrollY = el.scrollHeight > el.clientHeight && (style.overflowY === "auto" || style.overflowY === "scroll");

                #         if (canScrollY) {
                #             const rect = el.getBoundingClientRect();
                #             const centerX = rect.left + rect.width / 2;
                #             const centerY = rect.top + rect.height / 2;
                #             const topEl = document.elementFromPoint(centerX, centerY);

                #             if (topEl === el || el.contains(topEl)) {
                #             console.log("✅ Scrollable và hiển thị ở phía trước:", el);
                #             visibleScrollables.push(el);
                #             } else {
                #             console.log("🚫 Scrollable nhưng bị che:", el);
                #             }
                #         }
                #     }
                #     // 👉 Trả về phần tử đầu tiên cuộn được và không bị che (nếu có)
                #     return visibleScrollables[0];
                # '''
                # scrollable_element = driver.driver.execute_script(script)

                scrollable_element = driver.get_first_scrollable_element()

                logger.info(f"Phần tử cuộn được {scrollable_element}")

                for _ in range(2):
                    if Utils.is_apis_in_source(self.api_path, [comment_apis[1]]) == False:
                        if scrollable_element is not None:
                            driver.scroll_element(scrollable_element, repeat=10) 

        if Utils.is_apis_in_source(self.api_path, comment_apis) == False:
            logger.info(f"Lấy {comment_apis} thất bại")
        else:
            logger.info(f"Lấy {comment_apis} thành công")
            comment_api_path = "./api_info/comment_api.json"
            Utils.export_api2json(self.api_path, comment_api_path, comment_apis)

        driver.stop_controller()
