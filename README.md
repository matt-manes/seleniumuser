# Seleniumuser
A module that sits ontop of Selenium to streamline scraping and automation workflows.<br>
Install with:
<pre>pip install seleniumuser</pre>
Currently supports using firefox or chrome.<br>
You will need to have the appropriate web driver executable for the browser and your system in either the system PATH or a location passed to the User class constructor.<br>
They can be found here:<br>
[Firefox](https://github.com/mozilla/geckodriver/releases)<br>
[Chrome](https://chromedriver.chromium.org/downloads)

### Basic usage: 

#####  Submitting a generic form with fields for first name, last name, email address, and phone number:

<pre>
from seleniumuser import User
user = User(browser_type="firefox")
user.get('https://somewebsite.com')
user.send_keys('//input[@id="first-name"]', 'Bill')
user.fill_next(['Billson', 'bill@bill.com', '5345548486'])
user.click('//button[@id="submit"]')
try:
    user.wait_until(lambda: 'Submission Received' in user.text('//p[@id="confirmation-message"]'))
    print('Submission success.')
except TimeoutError:
    print('Submission failed.')
user.close_browser()
</pre>

The User class supports being used with a context manager if you'd rather not worry about closing the browser before exiting the script:

<pre>
from seleniumUser import User
with User(browser_type="firefox") as user:
    user.get('https://somewebsite.com')
    user.send_keys('//input[@id="first-name"]', 'Bill')
    user.fill_next(['Billson', 'bill@bill.com', '5345548486'])
    user.click('//button[@id="submit"]')
    try:
        user.wait_until(lambda: 'Submission Received' in user.text('//p[@id="confirmation-message"]'))
        print('Submission success.')
    except TimeoutError:
        print('Submission failed.')
</pre>
