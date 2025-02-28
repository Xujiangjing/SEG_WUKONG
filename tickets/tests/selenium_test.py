from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import unittest

class DjangoSeleniumTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize WebDriver"""
        cls.driver = webdriver.Chrome()
        cls.driver.implicitly_wait(10)
        cls.driver.maximize_window()

    def test_home_page_loads(self):
        """Test if the Home page loads correctly"""
        driver = self.driver
        driver.get("http://127.0.0.1:8000/")

        # Get the page title
        new_title = driver.title
        print(f"New page title: {new_title}")

        # Allow case-insensitive matching
        self.assertIn("wukong", new_title.lower())

    def test_css_loaded(self):
        """Test if CSS is loaded correctly"""
        driver = self.driver
        driver.get("http://127.0.0.1:8000/")

        # Ensure the page contains custom CSS styles
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-box"))
        )
        content_element = driver.find_element(By.CLASS_NAME, "container-box")
        self.assertTrue(content_element.is_displayed(), "CSS may not be applied correctly")

        # Get the color of the LOG IN button (verify CSS styles)
        login_button = driver.find_element(By.PARTIAL_LINK_TEXT, "LOG")
        color = login_button.value_of_css_property("color")
        print("LOG IN button color:", color)

    def test_base_template_renders(self):
        """Test if the base.html template renders correctly"""
        driver = self.driver
        driver.get("http://127.0.0.1:8000/")

        # Check if Bootstrap is loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//link[contains(@href, 'bootstrap')]"))
        )
        bootstrap_css = driver.find_element(By.XPATH, "//link[contains(@href, 'bootstrap')]")
        self.assertTrue(bootstrap_css, "Bootstrap CSS is not loaded correctly")

        # Check if jQuery is loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//script[contains(@src, 'jquery')]"))
        )
        jquery_script = driver.find_element(By.XPATH, "//script[contains(@src, 'jquery')]")
        self.assertTrue(jquery_script, "jQuery is not loaded correctly")

    @classmethod
    def tearDownClass(cls):
        """Close the browser after tests are completed"""
        cls.driver.quit()

if __name__ == "__main__":
    unittest.main()



