from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pychrome
from selenium import webdriver
from selenium_stealth import stealth
import undetected_chromedriver as uc
from parser import Parser 
from utils import Utils
from logger import setup_logger
import random
import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement




logger = setup_logger(__name__)

class ControllerDriver:
    def __init__(self):
        self.driver = None
        self.api_info_path = "./api_info/api_info.json"
        if Utils.file_exists(self.api_info_path):
            Utils.del_json(self.api_info_path)
    
    def start_controller(self) -> webdriver.Chrome:
        # Khởi động driver Selenium
        chrome_options = uc.ChromeOptions()

        chrome_options.add_argument("--log-level=3")  # 0 = ALL, 1 = INFO, 2 = WARNING, 3 = ERROR
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # Tắt log thêm

        # Đảm bảo trình duyệt không bị phát hiện là Selenium Bot
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Ẩn các đặc tính kiểm tra tự động
        chrome_options.add_argument('--disable-infobars')  # Tắt thông báo trên trình duyệt (ví dụ: "Chrome đang được điều khiển bởi một chương trình tự động")
        chrome_options.add_argument("--remote-debugging-port=9222")  # Cho phép remote debugging (có thể tắt nếu không cần)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Khởi động chrome driver thành công")

        # Khởi tạo DevTools client
        self.browser = pychrome.Browser(url="http://127.0.0.1:9222")
        self.tab = self.browser.list_tab()[0]
        self.tab.start()
        self.tab.Network.enable(includeResponseBodies=True)
        

        self.tab.Network.requestWillBeSent = self.handle_request
        return self.driver

    def handle_request(self, **kwargs) -> None:
        try:
            request = kwargs.get('request', {})
            url = request.get('url')
            method = request.get('method')
            payload = request.get('postData')
            if "graphql" in url:
                logger.info("Tìm thấy api graphql")
                graphql_api = Parser._get_api_value(payload)
                Utils.check_and_add_api(self.api_info_path, graphql_api)
        except Exception as e:
            if self.is_driver_alive() == False:
                logger.info("Driver đã đóng")
            else:
                raise Exception(f"Lỗi khi lấy api {e}")

    def is_driver_alive(self):
        try:
            _ = self.driver.current_url
            return True
        except Exception as e:
            return False


    def stop_controller(self) -> None:
        """Đóng WebDriver và DevTools client"""
        try:
            # Dừng DevTools client (nếu có)
            if self.tab:
                self.tab.stop()
                logger.info("DevTools client đã dừng.")
            if hasattr(self, 'browser') and self.browser:
                    self.browser.close_tab(self.tab)
                    logger.info("Tab DevTools đã đóng.")
            # Đóng WebDriver
            if self.driver:
                self.driver.quit()
                logger.info("Trình duyệt WebDriver đã đóng.")
        except Exception as e:
            logger.error(f"Đã xảy ra lỗi khi đóng driver và DevTools: {e}")

    def is_page_loaded(self) -> bool:
        """
        Kiểm tra xem trang đã tải xong hay chưa.
        Trả về True nếu trang đã tải xong, False nếu trang vẫn đang tải.
        """
        try:
            # Lấy trạng thái của document.readyState
            ready_state = self.driver.execute_script("return document.readyState;")
            if ready_state == "complete":
                print("✅ Trang đã tải xong!")
                return True
            else:
                print("⏳ Trang vẫn đang tải...")
                return False
        except Exception as e:
            print(f"❌ Lỗi khi kiểm tra trạng thái tải trang: {e}")
            return False

    def wait_for_page_title(self, title: str, timeout: int = 10) -> None:
        """
        Chờ đến khi tiêu đề của trang là một giá trị cụ thể.

        Parameters:
        - driver: Đối tượng WebDriver của Selenium.
        - title: Tiêu đề trang mà bạn muốn kiểm tra.
        - timeout: Thời gian chờ tối đa (theo giây).
        """
        WebDriverWait(self.driver, timeout).until(EC.title_is(title))

    def get_driver(self) -> webdriver.Chrome:
        """Lấy driver hiện tại."""
        return self.driver
    
    def go_to_url(self, url) -> None:
        """Đi đến một URL."""
        if self.driver:
            self.driver.get(url)

    def get_HTML(self) -> str:
        """Lấy mã nguồn HTML của trang hiện tại."""
        if self.driver:
            return self.driver.page_source
        return None
    
    def find_first_match(self, locator_list: list[dict]) -> WebElement:
        """
        Tìm phần tử đầu tiên phù hợp trong danh sách selector.

        Args:
            locator_list: List chứa dict dạng {'by': By.X, 'selector': '...'}
            
        Returns:
            WebElement nếu tìm thấy phần tử đầu tiên phù hợp

        Raises:
            Exception nếu không tìm thấy bất kỳ phần tử nào
        """
        for locator in locator_list:
            by = locator.get("by", By.CSS_SELECTOR)
            selector = locator.get("selector")
            if not selector:
                continue

            try:
                element = self.driver.find_element(by, selector)
                logger.info(f"Tìm thấy phần tử với {by} = {selector}")
                return element
            except NoSuchElementException:
                logger.info(f"Không tìm thấy với {by} = {selector}, thử tiếp...")
                continue

        # Nếu duyệt hết danh sách vẫn không tìm thấy
        logger.warning("Không tìm thấy phần tử nào trong danh sách locator.")
        return None

    def find_element(self, locator: str, by: str = By.CSS_SELECTOR) -> WebElement:
        """
        Tìm phần tử NGAY LẬP TỨC không chờ đợi
        
        Args:
            locator: Giá trị selector (ID, CSS, XPath,...)
            by: Loại selector (mặc định CSS_SELECTOR)
            
        Returns:
            WebElement nếu tìm thấy
            
        Raises:
            Exception: Khi không tìm thấy phần tử
        """
        try:
            element = self.driver.find_element(by, locator)
            logger.info(f"Tìm thấy phần tử {by} = {locator}")
            return element
        except Exception as e:
            logger.warning(f"Không tìm thấy phần tử với {by} = {locator} {e}")
            return None
    
    # Các hàm tiện ích
    def find_element_by_id(self, element_id: str) -> WebElement:
        return self.find_element(element_id, By.ID)
    
    def find_element_by_css(self, css_selector: str) -> WebElement:
        return self.find_element(css_selector, By.CSS_SELECTOR)
    
    def find_element_by_xpath(self, xpath: str) -> WebElement:
        return self.find_element(xpath, By.XPATH)
    
    def find_element_by_class(self, class_name: str) -> WebElement:
        return self.find_element(class_name, By.CLASS_NAME)
    
    def wait_to_switch_by_id(self, element_id: str, timeout: int = 2) -> None:
        """Chờ phần tử xuất hiện và chuyển vào iframe theo ID, raise lỗi nếu không thành công"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, element_id))
            )
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển vào iframe với ID = {element_id}: {e}")

    def wait_to_switch_by_css_selector(self, css_selector: str, timeout: int = 2) -> None:
        """Chờ phần tử xuất hiện và chuyển vào iframe theo CSS Selector, raise lỗi nếu không thành công"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, css_selector))
            )
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển vào iframe với CSS_SELECTOR = {css_selector}: {e}")

    def wait_to_switch_by_xpath(self, xpath: str, timeout: int = 2) -> None:
        """Chờ phần tử xuất hiện và chuyển vào iframe theo XPath, raise lỗi nếu không thành công"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, xpath))
            )
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển vào iframe với XPATH = {xpath}: {e}")
        
    def switch_to_iframe_by_id(self, element_id: str) -> None:
        """Chuyển vào iframe theo ID, raise lỗi nếu không thành công"""
        try:
            self.driver.switch_to.frame(self.driver.find_element(By.ID, element_id))
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển vào iframe với ID = {element_id}: {e}")

    def switch_to_iframe_by_css_selector(self, css_selector: str) -> None:
        """Chuyển vào iframe theo CSS Selector, raise lỗi nếu không thành công"""
        try:
            self.driver.switch_to.frame(self.driver.find_element(By.CSS_SELECTOR, css_selector))
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển vào iframe với CSS_SELECTOR = {css_selector}: {e}")

    def switch_to_iframe_by_xpath(self, xpath: str) -> None:
        """Chuyển vào iframe theo XPath, raise lỗi nếu không thành công"""
        try:
            self.driver.switch_to.frame(self.driver.find_element(By.XPATH, xpath))
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển vào iframe với XPATH = {xpath}: {e}")

    def wait_to_click_by_id(self, element_id: str, timeout: int = 2) -> None:
        """Chờ phần tử có thể click và click vào nút theo ID, raise lỗi nếu không thành công"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.ID, element_id))
            ).click()
            print(f"✅ Đã click vào phần tử với ID = {element_id}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi click vào phần tử với ID = {element_id}: {e}")

    def wait_to_click_by_css_selector(self, css_selector: str, timeout: int = 2) -> None:
        """Chờ phần tử có thể click và click vào nút theo CSS Selector, raise lỗi nếu không thành công"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
            ).click()
            print(f"✅ Đã click vào phần tử với CSS_SELECTOR = {css_selector}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi click vào phần tử với CSS_SELECTOR = {css_selector}: {e}")

    def wait_to_click_by_xpath(self, xpath: str, timeout: int = 2) -> None:
        """Chờ phần tử có thể click và click vào nút theo XPath, raise lỗi nếu không thành công"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            ).click()
            print(f"✅ Đã click vào phần tử với XPATH = {xpath}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi click vào phần tử với XPATH = {xpath}: {e}")

    def wait_to_send_keys_by_id(self, element_id: str, text: str, timeout: int = 2, clear_before: bool = False) -> None:
        """Chờ phần tử với ID và gửi văn bản vào ô nhập liệu, raise lỗi nếu không thành công"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            if clear_before:
                element.clear()
            element.send_keys(text)
            print(f"✅ Đã nhập văn bản vào phần tử với ID = {element_id}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi nhập văn bản vào phần tử với ID = {element_id}: {e}")

    def click_by_id(self, element_id: str) -> None:
        """Click trực tiếp vào phần tử theo ID, raise lỗi nếu không thành công"""
        try:
            element = self.driver.find_element(By.ID, element_id)
            element.click()
            print(f"✅ Đã click vào phần tử với ID = {element_id}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi click vào phần tử với ID = {element_id}: {e}")

    def click_by_css_selector(self, css_selector: str) -> None:
        """Click trực tiếp vào phần tử theo CSS Selector, raise lỗi nếu không thành công"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, css_selector)
            element.click()
            print(f"✅ Đã click vào phần tử với CSS_SELECTOR = {css_selector}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi click vào phần tử với CSS_SELECTOR = {css_selector}: {e}")

    def click_by_xpath(self, xpath: str) -> None:
        """Click trực tiếp vào phần tử theo XPath, raise lỗi nếu không thành công"""
        try:
            element = self.driver.find_element(By.XPATH, xpath)
            element.click()
            print(f"✅ Đã click vào phần tử với XPATH = {xpath}")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi click vào phần tử với XPATH = {xpath}: {e}")

    def switch_to_home(self) -> None:
        """Chuyển về trang gốc (ra khỏi tất cả các iframe), raise lỗi nếu không thành công"""
        try:
            self.driver.switch_to.default_content()
            # print("✅ Đã chuyển về trang gốc (ra khỏi iframe).")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi chuyển về trang gốc: {e}")

    def get_page_title(self) -> None:
        """Lấy tiêu đề của trang web hiện tại, raise lỗi nếu không thành công"""
        try:
            page_title = self.driver.title
            # print(f"Tiêu đề trang hiện tại là: {page_title}")
            return page_title
        except Exception as e:
            raise Exception(f"❌ Lỗi khi lấy tiêu đề trang: {e}")

    def clear_cookies(self) -> None:
        """Xoá tất cả cookies trong trình duyệt, raise lỗi nếu không thành công"""
        try:
            self.driver.delete_all_cookies()
            print("✅ Đã xoá tất cả cookies.")
        except Exception as e:
            raise Exception(f"❌ Lỗi khi xoá cookies: {e}")

    def wait_for_element_by_id(self, element_id: str, timeout: int = 2) -> None:
        """Chờ phần tử xuất hiện theo ID và có thể tương tác được, raise lỗi nếu không tìm thấy"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.ID, element_id))
            )
            print(f"✅ Phần tử với ID '{element_id}' đã xuất hiện.")
            return element
        except Exception as e:
            raise Exception(f"❌ Không tìm thấy phần tử với ID '{element_id}' sau {timeout} giây: {e}")

    def wait_for_element_by_css(self, css_selector: str, timeout: int = 2) -> None:
        """Chờ phần tử xuất hiện theo CSS Selector và có thể tương tác được, raise lỗi nếu không tìm thấy"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            print(f"✅ Phần tử với CSS Selector '{css_selector}' đã xuất hiện.")
            return element
        except Exception as e:
            raise Exception(f"❌ Không tìm thấy phần tử với CSS Selector '{css_selector}' sau {timeout} giây: {e}")

    def wait_for_element_by_xpath(self, xpath: str, timeout: int = 2) -> None:
        """Chờ phần tử xuất hiện theo XPath và có thể tương tác được, raise lỗi nếu không tìm thấy"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
            print(f"✅ Phần tử với XPath '{xpath}' đã xuất hiện.")
            return element
        except Exception as e:
            raise Exception(f"❌ Không tìm thấy phần tử với XPath '{xpath}' sau {timeout} giây: {e}")
        
    def add_cookie(self, cookies: list[dict]) -> None:
        def clean_cookie(raw_cookie):
            if "expirationDate" in raw_cookie:
                raw_cookie["expirationDate"] = int(raw_cookie.pop("expirationDate", None))

            same_site = raw_cookie.get("sameSite", "")
            if same_site.lower() == "lax":
                raw_cookie["sameSite"] = "Lax"
            elif same_site.lower() == "strict":
                raw_cookie["sameSite"] = "Strict"
            elif same_site.lower() == "unspecified":
                raw_cookie.pop("sameSite", None)
            elif same_site.lower() == "no_restriction":
                raw_cookie["sameSite"] = "None"

            allowed_keys = {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}
            return {k: v for k, v in raw_cookie.items() if k in allowed_keys}

        try:
            for cookie in cookies:
                cookie_cleaned = clean_cookie(cookie)
                self.driver.add_cookie(cookie_cleaned)
        except Exception as e:
            raise Exception(f"Lỗi khi add cookie {cookie_cleaned} {e}")

    def refresh(self) -> None:
        try:
            self.driver.refresh()
        except Exception as e:
            raise Exception(f"Lỗi khi refresh {e}")

    def random_scroll(self, max_scrolls: int = 10, min_wait: int = 2, max_wait: int = 2.5) -> None:
        """
        Cuộn trang ngẫu nhiên với Selenium.

        Args:
            driver: Đối tượng Selenium WebDriver.
            max_scrolls: Số lần cuộn tối đa.
            min_wait: Thời gian chờ tối thiểu giữa các lần cuộn (giây).
            max_wait: Thời gian chờ tối đa giữa các lần cuộn (giây).
        """
        logger.info("Tiến hành mô phỏng cuộn trang")
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        for i in range(max_scrolls):
            # Tạo khoảng cách cuộn ngẫu nhiên
            logger.info(f"Thực hiện cuộn trang lần thứ {i + 1}")
            scroll_offset = random.randint(100, 800)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_offset});")

            self.is_page_loaded()
            # Thời gian chờ ngẫu nhiên sau mỗi lần cuộn
            wait_time = random.uniform(min_wait, max_wait)
            time.sleep(wait_time)

        logger.info("Mô phỏng cuộn trang thành công")

    def is_page_loaded(self, timeout: int = 10) -> bool:
        """
        Kiểm tra trang đã load xong chưa bằng cách theo dõi document.readyState == 'complete'.

        Args:
            driver: Đối tượng Selenium WebDriver.
            timeout: Số giây tối đa để chờ trang load xong.

        Returns:
            True nếu trang đã tải xong, False nếu quá thời gian chờ.
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logger.info("Trang đã tải xong")
            return True
        except:
            logger.warning("Đã hết thời gian chờ trang tải chưa xong!!")
            return False

    def is_clickable(self, element: WebElement) -> bool:
        """
        Kiểm tra xem phần tử có thể click được hay không.

        Điều kiện:
        - Hiển thị (`is_displayed`)
        - Không bị vô hiệu hóa (`is_enabled`)

        Args:
            element (WebElement): phần tử cần kiểm tra

        Returns:
            bool: True nếu click được, False nếu không
        """
        try:
            if element.is_displayed() and element.is_enabled():
                logger.info(f"Phần tử {element} có thể click được")
                return True
            else:
                logger.info(f"Phần tử {element} không thể click được")
                return False
        except Exception:
            logger.info(f"Phần tử {element} không thể click được")
            return False

    def scroll_element(self, element: WebElement, pixels: int = 300, delay: float = 0.5, repeat: int = 3):
        """
        Cuộn một phần tử vùng scrollable theo chiều dọc (scrollTop hoặc scrollBy)

        Args:
            driver (WebDriver): Trình điều khiển Selenium
            element (WebElement): Vùng DOM cuộn được (div, section...)
            pixels (int): Số pixel mỗi lần cuộn (âm để cuộn lên)
            delay (float): Thời gian chờ giữa mỗi lần cuộn
            repeat (int): Số lần cuộn lặp lại

        Returns:
            None
        """
        for i in range(repeat):
            logger.info(f"Thực hiện cuộn trang lần {i + 1}")
            self.driver.execute_script("arguments[0].scrollBy(0, arguments[1]);", element, pixels)
            time.sleep(delay)

    def scroll_into_view(self, element: WebElement) -> None:
        try:
            script = '''
                const el = arguments[0];
                const rect = el.getBoundingClientRect();
                const absoluteTop = rect.top + window.pageYOffset;
                const centerY = absoluteTop - (window.innerHeight / 2) + (rect.height / 2);
                window.scrollTo({ top: centerY });
            '''
            self.driver.execute_script(script, element)
            logger.info("Cuộn vào phần tử thành công")
        except Exception as e:
            logger.info(f"Lỗi khi cuộn vào phần tử {e}")

    def get_first_scrollable_element(self) -> WebElement:
        try:
            script = '''
                const allElements = document.querySelectorAll("*");
                const visibleScrollables = [];

                for (const el of allElements) {
                    const style = getComputedStyle(el);
                    const canScrollY = el.scrollHeight > el.clientHeight && (style.overflowY === "auto" || style.overflowY === "scroll");

                    if (canScrollY) {
                        const rect = el.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const centerY = rect.top + rect.height / 2;
                        const topEl = document.elementFromPoint(centerX, centerY);

                        if (topEl === el || el.contains(topEl)) {
                        console.log("✅ Scrollable và hiển thị ở phía trước:", el);
                        visibleScrollables.push(el);
                        } else {
                        console.log("🚫 Scrollable nhưng bị che:", el);
                        }
                    }
                }
                // 👉 Trả về phần tử đầu tiên cuộn được và không bị che (nếu có)
                return visibleScrollables[0];
            '''
            scrollable_element = self.driver.execute_script(script)
            logger.info(f"Phần tử cuộn được {scrollable_element}")
            return scrollable_element
        except Exception as e:
            raise Exception("Lỗi khi lấy phần tử cuộn được")
