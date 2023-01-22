import pytest

import seleniumuser


def test_start_up():
    user = seleniumuser.User(headless=True)
    user.close_browser()
    user = seleniumuser.User(headless=True, browser_type="chrome")
    user.close_browser()


def test_seleniumuser___enter__():
    ...


def test_seleniumuser___exit__():
    ...


def test_seleniumuser_configure_firefox():
    ...


def test_seleniumuser_configure_chrome():
    ...


def test_seleniumuser_search_for_driver():
    ...


def test_seleniumuser_set_implicit_wait():
    ...


def test_seleniumuser_open_browser():
    ...


def test_seleniumuser_close_browser():
    ...


def test_seleniumuser_open_tab():
    ...


def test_seleniumuser_switch_to_tab():
    ...


def test_seleniumuser_get_num_tabs():
    ...


def test_seleniumuser_close_tab():
    ...


def test_seleniumuser_get_soup():
    ...


def test_seleniumuser_current_url():
    ...


def test_seleniumuser_delete_cookies():
    ...


def test_seleniumuser_turbo():
    ...


def test_seleniumuser_chill():
    ...


def test_seleniumuser_script():
    ...


def test_seleniumuser_remove():
    ...


def test_seleniumuser_get_length():
    ...


def test_seleniumuser_find():
    ...


def test_seleniumuser_find_children():
    ...


def test_seleniumuser_scroll():
    ...


def test_seleniumuser_scroll_into_view():
    ...


def test_seleniumuser_text():
    ...


def test_seleniumuser_click():
    ...


def test_seleniumuser_clear():
    ...


def test_seleniumuser_switch_to_iframe():
    ...


def test_seleniumuser_switch_to_parent_frame():
    ...


def test_seleniumuser_select():
    ...


def test_seleniumuser_click_elements():
    ...


def test_seleniumuser_get_click_list():
    ...


def test_seleniumuser_send_keys():
    ...


def test_seleniumuser_fill_next():
    ...


def test_seleniumuser_wait_until():
    ...


def test_seleniumuser_dismiss_alert():
    ...


def test_seleniumuser_solve_recaptcha_v3():
    ...
