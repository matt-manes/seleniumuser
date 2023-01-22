import os
import random
import sys
import time
from pathlib import Path
from types import LambdaType
from typing import Any
from warnings import warn

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from noiftimer import Timer
from voxscribe import get_text_from_url
from whosyouragent import get_agent


class User:
    """Sits on top of selenium to streamline
    automation and scraping tasks."""

    def __init__(
        self,
        headless: bool = False,
        browser_type: str = "firefox",
        implicit_wait: int = 10,
        page_load_timeout: int = 60,
        open_browser: bool = True,
        locator_method: str = "xpath",
        randomize_user_agent: bool = True,
        user_agent_rotation_period: int = None,
        move_window_by: tuple[int, int] = (0, -1000),
        download_dir: str | Path = None,
        driver_path: str | Path = None,
    ):
        """
        :param headless: If True, browser window will not be visible.

        :param browser_type: Which browser to use. Can be 'firefox' or 'chrome'.

        :param implicit_wait: Number of seconds to look for a specified element before
        selenium considers it missing and throws an exception.

        :param page_load_timeout: Time in seconds for selenium to wait for a page to load
        before throwing an exception.

        :param open_browser: If True, opens a browser window when a User object is created.
        If False, a manual call to self.open_browser() must be made.

        :param locator_method: The locator type User should expect to be given.
        Can be 'xpath', 'id', 'className', 'name', or 'cssSelector'.
        Every member function with a 'locator' argument refers to a string matching
        the current locator_method.

        :param randomize_user_agent: If True, a random useragent will be used whenever
        the browser is opened. If False, the native useragent will be used.

        :param user_agent_rotation_period: If not None, the browser window will be closed
        and reopened with a new useragent every user_agent_rotation_period number of minutes.
        Rotation occurs on the first call to self.get() after the time period has elapsed.
        Ignored if randomize_user_agent is False.

        :param move_window_by: The x and y amount of pixels to move the browser window by after opening.

        :param download_dir: The download folder to use. If None, the default folder will be used.

        :param driver_path: The path to the webdriver executable selenium should use.
        If None, the system PATH will be checked for the executable.
        If the executable isn't found, the parent directories and the immediate child directories
        of the current working directory will be searched.
        """
        self.headless = headless
        browser_type = browser_type.lower()
        if browser_type in ["firefox", "chrome"]:
            self.browser_type = browser_type
        else:
            raise ValueError("'browser_type' parameter must be 'firefox' or 'chrome'")
        self.browser_open = False
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.rotation_timer = Timer()
        self.timer = Timer()
        self.timer.start()
        self.randomize_user_agent = randomize_user_agent
        self.user_agent_rotation_period = user_agent_rotation_period
        self.locator_method = locator_method
        self.turbo()
        self.keys = Keys
        self.move_window_by = move_window_by
        self.download_dir = download_dir
        self.driver_path = driver_path
        if not self.driver_path:
            self.search_for_driver()
        if open_browser:
            self.open_browser()
        else:
            self.browser = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close_browser()

    def configure_firefox(self) -> FirefoxService:
        """Configure options and profile for firefox."""
        self.options = FirefoxOptions()
        self.options.headless = self.headless
        self.options.set_preference(
            "widget.windows.window_occlusion_tracking.enabled", False
        )
        self.options.set_preference("dom.webaudio.enabled", False)
        if self.randomize_user_agent:
            self.options.set_preference("general.useragent.override", get_agent())
        if self.download_dir:
            Path(self.download_dir).mkdir(parents=True, exist_ok=True)
            self.profile = FirefoxProfile()
            self.profile.set_preference("browser.download.dir", str(self.download_dir))
            self.profile.set_preference("browser.download.folderList", 2)
        else:
            self.profile = None
        self.service = FirefoxService(
            executable_path=str(self.driver_path), log_path=os.devnull
        )

    def configure_chrome(self) -> ChromeService:
        """Configure options and profile for chrome."""
        self.options = ChromeOptions()
        self.options.headless = self.headless
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("--mute-audio")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--log-level=3")
        if self.randomize_user_agent:
            self.options.add_argument(f"--user-agent={get_agent()}")
        self.options.add_experimental_option("useAutomationExtension", False)
        if self.download_dir:
            Path(self.download_dir).mkdir(parents=True, exist_ok=True)
            self.options.add_experimental_option(
                "prefs", {"download.default_directory": str(self.download_dir)}
            )
        self.service = ChromeService(
            executable_path=str(self.driver_path), log_path=os.devnull
        )

    def search_for_driver(self):
        """Searches for the webdriver executable."""
        cwd = Path.cwd()
        found = False
        match self.browser_type:
            case "firefox":
                driver = "geckodriver.exe"
            case "chrome":
                driver = "chromedriver.exe"
        # search PATH
        env_path = os.environ["PATH"]
        if sys.platform == "win32":
            env_paths = env_path.split(";")
        else:
            env_paths = env_path.split(":")
            driver = driver[: driver.find(".")]
        for path in env_paths:
            if (Path(path) / driver).exists():
                self.driver_path = Path(path) / driver
                found = True
                break
        # check current working directory and parent folders
        if not found:
            while cwd != cwd.parent:
                if (cwd / driver).exists():
                    self.driver_path = cwd / driver
                    found = True
                    break
                cwd = cwd.parent
            # check top most level
            if not found and (cwd / driver).exists():
                self.driver_path = cwd / driver
                found = True
        # check child folders (only 1 level down)
        if not found:
            for child in Path.cwd().iterdir():
                if child.is_dir() and (child / driver).exists():
                    self.driver_path = child / driver
                    found = True
        if not found:
            warn(f"Could not find {driver}")

    def set_implicit_wait(self, wait_time: int = None):
        """Sets to default time if no arg given."""
        if not wait_time:
            self.browser.implicitly_wait(self.implicit_wait)
        else:
            self.browser.implicitly_wait(wait_time)

    def open_browser(self):
        """Configures and opens selenium browser."""
        if not self.browser_open:
            match self.browser_type:
                case "firefox":
                    self.configure_firefox()
                    self.browser = webdriver.Firefox(
                        options=self.options,
                        service=self.service,
                        firefox_profile=self.profile,
                    )
                case "chrome":
                    self.configure_chrome()
                    self.browser = webdriver.Chrome(
                        options=self.options, service=self.service
                    )
            self.set_implicit_wait()
            self.browser.maximize_window()
            self.browser.set_window_position(
                self.move_window_by[0], self.move_window_by[1]
            )
            self.browser.maximize_window()
            self.browser.set_page_load_timeout(self.page_load_timeout)
            self.browser_open = True
            self.tab_index = 0
            self.rotation_timer.start()
        else:
            warn("Browser already open.")

    def close_browser(self):
        """Close browser window."""
        self.browser_open = False
        self.browser.quit()

    def open_tab(self, url: str = "", switch_to_tab: bool = True):
        """Opens new tab and, if provided, goes to url.

        New tab is inserted after currently active tab."""
        self.script("window.open(arguments[0]);", url)
        if switch_to_tab:
            self.switch_to_tab(self.tab_index + 1)

    def switch_to_tab(self, tab_index: int):
        """Switch to a tab in browser, zero indexed."""
        self.browser.switch_to.window(self.browser.window_handles[tab_index])
        self.tab_index = tab_index

    def get_num_tabs(self) -> int:
        """Returns number of tabs open."""
        return len(self.browser.window_handles)

    def close_tab(self, tab_index: int = 1):
        """Close specified tab and
        switches to tab index 0."""
        self.switch_to_tab(tab_index)
        self.browser.close()
        self.switch_to_tab(0)

    def get(self, url: str):
        """Requests webpage at given url and rotates userAgent if necessary."""
        if not self.browser_open:
            self.open_browser()
        if (
            self.randomize_user_agent
            and self.user_agent_rotation_period is not None
            and self.rotation_timer.check(format=False)
            > (60 * self.user_agent_rotation_period)
        ):
            self.rotation_timer.stop()
            self.close_browser()
            self.open_browser()
        self.browser.get(url)
        self.script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
        self.chill(self.arrival_wait)

    def get_soup(self) -> BeautifulSoup:
        """Returns a BeautifulSoup object
        of the current page source."""
        return BeautifulSoup(self.browser.page_source, "html.parser")

    def current_url(self) -> str:
        """Returns current url of active tab."""
        return self.browser.current_url

    def delete_cookies(self):
        """Delete all cookies for
        this browser instance."""
        self.browser.delete_all_cookies()

    def turbo(self, engage: bool = True):
        """When engaged, strings will be sent
        to elements all at once and there will be
        no waiting after actions.

        When disengaged, strings will be sent to elements
        'one key at a time' with randomized amounts of
        time between successive keys and after actions."""
        if engage:
            self.after_key_wait = (0, 0)
            self.after_field_wait = (0, 0)
            self.after_click_wait = (0, 0)
            self.arrival_wait = (1, 1)
            self.one_key_at_a_time = False
            self.turbo_engaged = True
        else:
            self.after_key_wait = (0.1, 0.5)
            self.after_field_wait = (1, 2)
            self.after_click_wait = (0.25, 1.5)
            self.arrival_wait = (4, 10)
            self.one_key_at_a_time = True
            self.turbo_engaged = False

    def chill(self, min_max: tuple[float, float]):
        """Sleeps a random amount
        between min_max[0] and min_max[1]."""
        time.sleep(random.uniform(min_max[0], min_max[1]))

    def script(self, script: str, args: Any = None) -> Any:
        """Execute javascript code and returns result."""
        return self.browser.execute_script(script, args)

    def remove(self, locator: str):
        """Removes element from DOM."""
        self.script("arguments[0].remove();", self.find(locator))

    def get_length(self, locator: str) -> int:
        """Returns number of child elements for a given element."""
        return int(self.script("return arguments[0].length;", self.find(locator)))

    def find(self, locator: str) -> WebElement:
        """Finds and returns a WebElement."""
        match self.locator_method:
            case "xpath":
                return self.browser.find_element(By.XPATH, locator)
            case "id":
                return self.browser.find_element(By.ID, locator)
            case "className":
                return self.browser.find_element(By.CLASS_NAME, locator)
            case "name":
                return self.browser.find_element(By.NAME, locator)
            case "cssSelector":
                return self.browser.find_element(By.CSS_SELECTOR, locator)

    def find_children(self, locator: str) -> list[WebElement]:
        """Returns a list of child WebElements
        for given locator arg."""
        element = self.find(locator)
        return element.find_elements("xpath", "./*")

    def scroll(self, amount: int = None, fraction: float = None):
        """Scroll web page.
        :param amount: The number of lines to scroll if not None.

        :param fraction: The amount between 0.0 and 1.0
        of the page height to scroll.

        If values are provided for both arguments,
        amount will be used.

        If values are provided for neither argument,
        the entire page length will be scrolled.

        Scrolls one line at a time if self.turbo is False."""
        if amount:
            amount_to_scroll = amount
        elif fraction:
            amount_to_scroll = int(
                fraction
                * (
                    int(self.script("return document.body.scrollHeight;"))
                    - int(self.script("return window.pageYOffset;"))
                )
            )
        else:
            amount_to_scroll = int(self.script("return document.body.scrollHeight;"))
        if self.turbo_engaged:
            self.script("window.scrollBy(0,arguments[0]);", amount_to_scroll)
        else:
            for _ in range(abs(amount_to_scroll)):
                if amount_to_scroll >= 0:
                    self.script("window.scrollBy(0,1);")
                else:
                    self.script("window.scrollBy(0,-1);")
        self.chill(self.after_click_wait)

    def scroll_into_view(self, locator: str) -> WebElement:
        """Scrolls to a given element and returns the element."""
        element = self.find(locator)
        self.script("arguments[0].scroll_into_view();", element)
        self.chill(self.after_click_wait)
        return element

    def text(self, locator: str) -> str:
        """Returns text of WebElement."""
        return self.find(locator).text

    def click(self, locator: str) -> WebElement:
        """Clicks on and returns WebElement."""
        element = self.find(locator)
        element.click()
        self.chill(self.after_click_wait)
        return element

    def clear(self, locator: str) -> WebElement:
        """Clears content of WebElement if able
        and then returns WebElement."""
        element = self.find(locator)
        element.clear()
        self.chill(self.after_click_wait)
        return element

    def switch_to_iframe(self, locator: str):
        """Switch to an iframe from given locator."""
        self.browser.switch_to.frame(self.find(locator))

    def switch_to_parent_frame(self):
        """Move up a frame level from current frame."""
        self.browser.switch_to.parent_frame()

    def select(
        self, locator: str, method: str, choice: str | int | tuple
    ) -> WebElement:
        """Select a choice from Select element.
        Returns the Select element from the locator string,
        not the option element that is selected.

        :param method: Can be 'value' or 'index'

        :param choice: The option to select.

        If method is 'value', then choice should be
        the html 'value' attribute of the desired option.

        If method is 'index', choice can either be a single
        int for the desired option or it can be a two-tuple.
        If the tuple is provided, a random option between the
        two indicies (inclusive) will be selected."""
        element = self.click(locator)
        match method:
            case "value":
                Select(element).select_by_value(choice)
            case "index":
                if type(choice) == tuple:
                    choice = random.randint(choice[0], choice[1])
                Select(element).select_by_index(choice)
        self.chill(self.after_field_wait)
        return element

    def click_elements(
        self, locators: list[str], max_selections: int = None, min_selections: int = 1
    ) -> WebElement:
        """Click a random number of WebElements
        and return the last WebElement clicked.

        :param locators: A list of element locators to choose from.

        :param max_selections: The maximum number of elements to click.
        If None, the maximum will be the length of the locators list.

        :param min_selections: The minimum number of elements to click.

        e.g. self.click_elements([xpath1, xpath2, xpath3, xpath4], max_selections=3)
        will click between 1 and 3 random elements from the list.
        """
        if not max_selections:
            max_selections = len(locators)
        for option in random.sample(
            locators, k=random.randint(min_selections, max_selections)
        ):
            element = self.click(option)
        return element

    def get_click_list(
        self, num_options: int, max_choices: int = 1, min_choices: int = 1
    ) -> list[str]:
        """Similar to self.click_elements(), but for use with the self.fill_next() method.

        Creates a list of length 'num_options' where every element is 'skip'.

        A random number of elements in the list between 'min_choices' and 'max_choices' are
        replaced with 'keys.SPACE' (interpreted as a click by almost all web forms)."""
        click_list = ["skip"] * num_options
        selected_indexes = []
        for i in range(random.randint(min_choices, max_choices)):
            index = random.randint(0, num_options - 1)
            while index in selected_indexes:
                index = random.randint(0, num_options - 1)
            selected_indexes.append(index)
            click_list[index] = self.keys.SPACE
        return click_list

    def send_keys(
        self,
        locator: str,
        data: str,
        click_first: bool = True,
        clear_first: bool = False,
    ) -> WebElement:
        """Types data into element and returns the element.

        :param data: The string to send to the element.

        :param click_first: If True, the element is clicked on
        before the data is sent.

        :param clear_first: If True, the current text of the element
        is cleared before the data is sent."""
        element = self.click(locator) if click_first else self.find(locator)
        if clear_first:
            element.clear()
            self.chill(self.after_click_wait)
        if self.one_key_at_a_time:
            for ch in str(data):
                element.send_keys(ch)
                self.chill(self.after_key_wait)
        else:
            element.send_keys(str(data))
        self.chill(self.after_field_wait)
        return element

    def fill_next(
        self, data: list[str | tuple], start_element: WebElement = None
    ) -> WebElement:
        """Fills a form by tabbing from the current WebElement
        to the next one and using the corresponding item in data.
        Returns the last WebElement.

        :param data: A list of form data. If an item is a string (except for 'skip')
        it will be typed into the current WebElement.

        An item in data can be a two-tuple of the form
        ('downArrow', numberOfPresses:int|tuple[int, int]).

        If numberOfPresses is a single int, Keys.ARROW_DOWN will be sent
        that many times to the WebElement.

        If numberOfPresses is a tuple, Keys.ARROW_DOWN will be sent a random
        number of times between numberOfPresses[0] and numberOfPresses[1] inclusive.
        This is typically for use with Select elements.

        An item in data can also be 'skip', which will perform no action on the current
        WebElement and will continue to the next one.

        :param start_element: The WebElement to start tabbing from.
        The currently active element will be used if start_element is None.

        Note: The function tabs to the next element before sending data,
        so the start_element should the WebElement before the one
        that should receive data[0].
        """
        element = (
            self.browser.switch_to.active_element
            if not start_element
            else start_element
        )
        for datum in data:
            element.send_keys(Keys.TAB)
            element = self.browser.switch_to.active_element
            self.chill(self.after_key_wait)
            if datum[0] == "downArrow":
                if type(datum[1]) == tuple:
                    times = random.randint(datum[1][0], datum[1][1])
                else:
                    times = datum[1]
                for _ in range(times):
                    element.send_keys(Keys.ARROW_DOWN)
                    self.chill(self.after_key_wait)
            elif datum == "skip":
                self.chill(self.after_key_wait)
            else:
                if self.turbo_engaged:
                    element.send_keys(str(datum))
                else:
                    for ch in str(datum):
                        element.send_keys(ch)
                        self.chill(self.after_key_wait)
            self.chill(self.after_field_wait)
        return element

    def wait_until(
        self, condition: LambdaType, max_wait: float = 10, polling_interval: float = 0.1
    ):
        """Checks condition repeatedly until either it is true,
        or the max_wait is exceeded.

        Raises a TimeoutError if the condition doesn't success within max_wait.

        Useful for determing whether a form has been successfully submitted.

        :param condition: The condition function to check.

        :param max_wait: Number of seconds to continue checking condition
        before throwing a TimeoutError.

        :param polling_interval: The number of seconds to sleep before
        checking the condition function again after it fails.

        e.g. self.wait_until(lambda: 'Successfully Submitted' in self.text('//p[@id="form-output"]))"""
        start_time = time.time()
        while True:
            try:
                if condition():
                    time.sleep(1)
                    break
                elif (time.time() - start_time) > max_wait:
                    raise TimeoutError(f"max_wait exceeded in wait_until({condition})")
                else:
                    time.sleep(polling_interval)
            except:
                if (time.time() - start_time) > max_wait:
                    raise TimeoutError(f"max_wait exceeded in wait_until({condition})")
                else:
                    time.sleep(polling_interval)

    def dismiss_alert(self):
        """Dismiss alert dialog."""
        self.browser.switch_to.alert.dismiss()

    def solve_recaptcha_v3(
        self,
        outer_iframe_xpath: str = '//iframe[@title="reCAPTCHA"]',
        inner_iframe_xpath: str = '//iframe[@title="recaptcha challenge expires in two minutes"]',
    ):
        """Pass google recaptcha v3 by solving an audio puzzle.

        :param outer_iframe_xpath: Xpath to the iframe containing the recaptcha checkbox.
        If it's the recaptcha without the initial checkbox that just shows the image puzzle,
        pass None to this argument.

        """
        locator_method = self.locator_method
        self.locator_method = "xpath"
        try:
            if outer_iframe_xpath:
                self.switch_to_iframe(outer_iframe_xpath)
                self.click('//*[@id="recaptcha-anchor"]')
                self.switch_to_parent_frame()
            self.switch_to_iframe(inner_iframe_xpath)
            self.click('//*[@id="recaptcha-audio-button"]')
            mp3_url = self.find(
                '//a[@class="rc-audiochallenge-tdownload-link"]'
            ).get_attribute("href")
            text = get_text_from_url(mp3_url, ".mp3")
            self.send_keys('//*[@id="audio-response"]', text)
            self.click('//*[@id="recaptcha-verify-button"]')
        except Exception as e:
            print(e)
            raise Exception("Could not solve captcha")
        finally:
            self.switch_to_parent_frame()
            self.locator_method = locator_method
