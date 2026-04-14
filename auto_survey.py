"""
McDonald's Auto Survey Master Bot
Combines techniques from happymeal, mcd-voice-bot, and Mcdonalds-Survey-Automation
into one unified, robust survey automation tool.

⚠️ For educational purposes only.
"""

import json
import time
import random
import os
import re
import sys
import traceback
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    # Stub colorama if not installed
    class _Stub:
        def __getattr__(self, _):
            return ""
    Fore = _Stub()
    Style = _Stub()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "2.0.0"
CWD = os.path.dirname(os.path.abspath(__file__))
REVIEWS_PATH = os.path.join(CWD, "reviews.json")
RESULTS_PATH = os.path.join(CWD, "results.json")
MCDVOICE_URL = "https://www.mcdvoice.com"
MCDVOICE_PIECEMEAL_URL = "https://www.mcdvoice.com/Index.aspx?POSType=PieceMeal"

# ---------------------------------------------------------------------------
# Survey status callback (used by web server)
# ---------------------------------------------------------------------------
_status_callback = None

def set_status_callback(cb):
    global _status_callback
    _status_callback = cb

def _update_status(message, progress=None, code=None, error=None):
    """Push status to callback (for web UI) and print to console."""
    print(f"{Fore.CYAN}[STATUS]{Style.RESET_ALL} {message}")
    if _status_callback:
        _status_callback({
            "message": message,
            "progress": progress,
            "code": code,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
def load_reviews():
    """Load the review pool from reviews.json."""
    try:
        with open(REVIEWS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["reviews"]
    except Exception as e:
        print(f"{Fore.RED}Could not load reviews: {e}")
        return {
            "general": ["Great experience!"],
            "breakfast": ["Great breakfast!"],
            "lunch": ["Great lunch!"],
        }

# ---------------------------------------------------------------------------
# Result logging
# ---------------------------------------------------------------------------
def save_result(entry_code, validation_code, mode, extra=None):
    """Append a result to results.json."""
    result = {
        "entry_code": entry_code,
        "validation_code": validation_code,
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
    }
    if extra:
        result.update(extra)

    results = []
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            results = []

    results.append(result)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return result

# ---------------------------------------------------------------------------
# WebDriver setup
# ---------------------------------------------------------------------------
def create_driver(headless=True):
    """Create a Chrome WebDriver instance."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        if USE_WDM:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=chrome_options)
        else:
            return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"{Fore.RED}Failed to create WebDriver: {e}")
        raise

# ---------------------------------------------------------------------------
# Helper: safe interactions
# ---------------------------------------------------------------------------
def safe_click(driver, element_id, retries=3, delay=1):
    """Safely click an element by ID, with retries."""
    for attempt in range(retries):
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            elem = driver.find_element(By.ID, element_id)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
            time.sleep(0.2)
            try:
                elem.click()
            except (ElementClickInterceptedException, ElementNotInteractableException):
                driver.execute_script("arguments[0].click();", elem)
            return True
        except (NoSuchElementException, TimeoutException):
            if attempt < retries - 1:
                time.sleep(delay)
            continue
        except StaleElementReferenceException:
            time.sleep(delay)
            continue
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"{Fore.YELLOW}Could not click #{element_id}: {e}")
    return False


def safe_click_css(driver, selector, retries=3, delay=1):
    """Safely click an element by CSS selector."""
    for attempt in range(retries):
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            elem = driver.find_element(By.CSS_SELECTOR, selector)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
            time.sleep(0.2)
            try:
                elem.click()
            except (ElementClickInterceptedException, ElementNotInteractableException):
                driver.execute_script("arguments[0].click();", elem)
            return True
        except (NoSuchElementException, TimeoutException):
            if attempt < retries - 1:
                time.sleep(delay)
            continue
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
    return False


def click_next(driver):
    """Click the Next button."""
    return safe_click(driver, "NextButton")


def weighted_choice(choices=None, weights=None):
    """Pick a weighted random option (biased towards positive)."""
    if choices is None:
        choices = ["Opt5", "Opt4", "Opt3", "Opt2", "Opt1"]
    if weights is None:
        weights = (45, 30, 15, 7, 3)
    return random.choices(choices, weights=weights, k=1)[0]

# ---------------------------------------------------------------------------
# Brute-force page solvers (from mcd-voice-bot, improved)
# ---------------------------------------------------------------------------
def solve_radio_tables(driver):
    """Solve pages with tables of radio-button rows."""
    try:
        table = driver.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.CSS_SELECTOR, ".InputRowOdd, .InputRowEven")
        if not rows:
            return False
        for row in rows:
            opt = weighted_choice()
            try:
                cell = row.find_element(By.CLASS_NAME, opt)
                radio = cell.find_element(By.CSS_SELECTOR, "input[type='radio'], .radioSimpleInput, .radioBranded")
                driver.execute_script("arguments[0].click();", radio)
            except NoSuchElementException:
                # Fallback: click highest available option
                for fallback in ["Opt5", "Opt4", "Opt3", "Opt2", "Opt1"]:
                    try:
                        cell = row.find_element(By.CLASS_NAME, fallback)
                        radio = cell.find_element(By.CSS_SELECTOR, "input[type='radio'], .radioSimpleInput, .radioBranded")
                        driver.execute_script("arguments[0].click();", radio)
                        break
                    except NoSuchElementException:
                        continue
        return True
    except NoSuchElementException:
        return False


def solve_radio_pattern(driver):
    """Click all elements matching the 'Highly Satisfied' pattern (R*.5)."""
    elements = driver.find_elements(By.CSS_SELECTOR, '[id^="R"][id$=".5"]')
    if not elements:
        return False
    for elem in elements:
        try:
            driver.execute_script("arguments[0].click();", elem)
        except Exception:
            pass
    return True


def solve_single_radio(driver):
    """Solve pages with a single radio-button list."""
    try:
        container = driver.find_element(By.CLASS_NAME, "rbListContainer")
        options = container.find_elements(By.CLASS_NAME, "rbList")
        if options:
            # Pick the first option (usually "Highly Satisfied" or best option)
            choice = options[0]
            radio = choice.find_element(By.CSS_SELECTOR, "input[type='radio'], .radioSimpleInput, .radioBranded")
            driver.execute_script("arguments[0].click();", radio)
            return True
    except NoSuchElementException:
        pass
    return False


def solve_yes_no(driver):
    """Solve yes/no questions (favor 'no problem')."""
    page_src = driver.page_source
    try:
        if "experience a problem" in page_src or "problem" in page_src.lower():
            # Usually Opt2 = "No" (no problem)
            opt = weighted_choice(["Opt1", "Opt2"], (10, 90))
            table = driver.find_element(By.TAG_NAME, "table")
            cell = table.find_element(By.CLASS_NAME, opt)
            radio = cell.find_element(By.CSS_SELECTOR, "input[type='radio'], .radioSimpleInput, .radioBranded")
            driver.execute_script("arguments[0].click();", radio)
            return opt == "Opt1"  # True if problem occurred
        elif "kiosk" in page_src.lower():
            cell = driver.find_element(By.CLASS_NAME, "Opt2")
            radio = cell.find_element(By.CSS_SELECTOR, "input[type='radio'], .radioSimpleInput, .radioBranded")
            driver.execute_script("arguments[0].click();", radio)
            return False
    except NoSuchElementException:
        pass
    return False


def solve_checkboxes(driver):
    """Solve checkbox pages (check a random subset)."""
    try:
        container = driver.find_element(By.CLASS_NAME, "cataListContainer")
        boxes = container.find_elements(By.CLASS_NAME, "cataOption")
        if not boxes:
            return False
        # Don't check "Other" (usually last)
        selectable = boxes[:-1] if len(boxes) > 1 else boxes
        count = random.randint(1, max(1, len(selectable) // 2))
        random.shuffle(selectable)
        for i in range(min(count, len(selectable))):
            try:
                cb = selectable[i].find_element(By.CSS_SELECTOR, "input[type='checkbox'], .checkboxSimpleInput, .checkboxBranded")
                driver.execute_script("arguments[0].click();", cb)
            except Exception:
                pass
        return True
    except NoSuchElementException:
        return False


def solve_textarea(driver, reviews):
    """Fill in comment/review textareas."""
    try:
        textarea = driver.find_element(By.TAG_NAME, "textarea")
        if textarea.is_displayed():
            # Pick a random review
            all_reviews = reviews.get("general", []) + reviews.get("lunch", []) + reviews.get("breakfast", [])
            if all_reviews:
                review = random.choice(all_reviews)
                textarea.clear()
                textarea.send_keys(review)
                return True
    except NoSuchElementException:
        pass
    return False


def solve_branded_radios(driver):
    """Click radioBranded elements on the page (generic solver)."""
    try:
        radios = driver.find_elements(By.CSS_SELECTOR, "span.radioBranded")
        if radios:
            # Try to click the first one on each row
            clicked = set()
            for radio in radios:
                try:
                    parent_row = radio.find_element(By.XPATH, "./ancestor::tr | ./ancestor::div[contains(@class,'rbList')]")
                    row_id = parent_row.get_attribute("id") or id(parent_row)
                    if row_id not in clicked:
                        driver.execute_script("arguments[0].click();", radio)
                        clicked.add(row_id)
                except Exception:
                    pass
            return bool(clicked)
    except Exception:
        pass
    return False

# ---------------------------------------------------------------------------
# Validation code extraction
# ---------------------------------------------------------------------------
def extract_validation_code(driver, timeout=10):
    """Wait for and extract the validation code from the final page."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ValCode"))
        )
        elem = driver.find_element(By.CLASS_NAME, "ValCode")
        text = elem.text.strip()
        # Parse out just the code if it has a label
        if ":" in text:
            text = text.split(":")[-1].strip()
        return text
    except TimeoutException:
        # Try alternative selectors
        for selector in [".ValCode", "#ValCode", "[class*='validation']", "[class*='Validation']"]:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                return elem.text.strip()
            except NoSuchElementException:
                continue
    return None

# ---------------------------------------------------------------------------
# Entry Mode: Receipt Code (CN1-CN6)
# ---------------------------------------------------------------------------
def enter_receipt_code(driver, code):
    """Enter the 26-digit receipt code into the CN1-CN6 fields."""
    _update_status("Navigating to McDVOICE...", progress=5)

    driver.get(MCDVOICE_URL)
    time.sleep(2)

    # Parse code: handle both "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-X" and raw digits
    code_clean = code.strip()
    if "-" in code_clean:
        parts = code_clean.split("-")
    else:
        # Try to split into standard format
        digits = re.sub(r"[^0-9]", "", code_clean)
        if len(digits) >= 26:
            parts = [digits[0:5], digits[5:10], digits[10:15], digits[15:20], digits[20:25], digits[25:]]
        else:
            raise ValueError(f"Invalid code length: {len(digits)} digits (expected 26+)")

    if len(parts) != 6:
        raise ValueError(f"Expected 6 code parts, got {len(parts)}")

    _update_status("Entering receipt code...", progress=10)

    field_ids = ["CN1", "CN2", "CN3", "CN4", "CN5", "CN6"]
    for field_id, part in zip(field_ids, parts):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, field_id))
            )
            elem = driver.find_element(By.ID, field_id)
            elem.clear()
            elem.send_keys(part)
        except Exception as e:
            raise RuntimeError(f"Could not fill {field_id}: {e}")

    _update_status("Submitting receipt code...", progress=15)
    click_next(driver)
    time.sleep(2)

    # Check for error
    if "Error" in driver.page_source and "unable to continue" in driver.page_source.lower():
        raise ValueError("Invalid receipt code — the survey site rejected it.")

    return code_clean

# ---------------------------------------------------------------------------
# Entry Mode: Store Info (Piecemeal)
# ---------------------------------------------------------------------------
def enter_store_info(driver, store_number, ks_number="01", auto_date=True,
                     date_str=None, time_str=None, trans_num=None, amount=None):
    """Enter store info for piecemeal survey entry."""
    _update_status("Navigating to McDVOICE (piecemeal)...", progress=5)

    driver.get(MCDVOICE_PIECEMEAL_URL)
    time.sleep(2)

    # Generate or use provided date/time
    if auto_date:
        now = datetime.now()
        day_offset = random.randint(0, 5)
        visit_date = now - timedelta(days=day_offset)
        month = str(visit_date.month).zfill(2)
        day = str(visit_date.day).zfill(2)
        hour = str(random.randint(6, 22)).zfill(2)
        minute = str(random.randint(0, 59)).zfill(2)
    else:
        m, d = date_str.split("/")
        month, day = m.zfill(2), d.zfill(2)
        h, mi = time_str.split(":")
        hour, minute = h.zfill(2), mi.zfill(2)

    # Generate transaction data
    if trans_num is None:
        trans_num = f"{ks_number}{random.randint(0, 99):02}"
    if amount is None:
        dollars = str(random.randint(3, 25))
        cents = str(random.randint(0, 99)).zfill(2)
    else:
        dollars, cents = amount.split(".")

    _update_status("Filling in store information...", progress=10)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "InputStoreID"))
        )
        driver.find_element(By.ID, "InputStoreID").send_keys(store_number)
        driver.find_element(By.ID, "InputRegisterNum").send_keys(ks_number)
        Select(driver.find_element(By.ID, "InputMonth")).select_by_value(month)
        Select(driver.find_element(By.ID, "InputDay")).select_by_value(day)
        Select(driver.find_element(By.ID, "InputHour")).select_by_value(hour)
        Select(driver.find_element(By.ID, "InputMinute")).select_by_value(minute)
        driver.find_element(By.ID, "InputTransactionNum").send_keys(trans_num)
        driver.find_element(By.ID, "AmountSpent1").send_keys(dollars)
        driver.find_element(By.ID, "AmountSpent2").send_keys(cents)
    except Exception as e:
        raise RuntimeError(f"Failed to fill store info: {e}")

    _update_status("Submitting store information...", progress=15)
    click_next(driver)
    time.sleep(2)

    return f"Store#{store_number} KS#{ks_number} {month}/{day} {hour}:{minute}"

# ---------------------------------------------------------------------------
# Main survey solver (brute-force with smart detection)
# ---------------------------------------------------------------------------
def solve_survey(driver, reviews, max_pages=30):
    """
    Brute-force through the survey pages until we reach the validation code.
    Handles dynamic page variations by trying multiple solving strategies.
    """
    _update_status("Starting survey...", progress=20)

    page_count = 0
    progress_per_page = 70 / max_pages  # Spread progress from 20% to 90%

    for page_num in range(max_pages):
        page_count += 1
        current_progress = min(20 + int(page_num * progress_per_page), 90)

        # Check if we've reached the validation code
        try:
            code = extract_validation_code(driver, timeout=2)
            if code:
                _update_status(f"🎉 Validation code found: {code}", progress=100, code=code)
                return code
        except Exception:
            pass

        _update_status(f"Solving page {page_count}...", progress=current_progress)

        solved = False

        # Strategy 1: Try textarea (comment/review page)
        if solve_textarea(driver, reviews):
            solved = True

        # Strategy 2: Try "Highly Satisfied" radio pattern (R*.5)
        if solve_radio_pattern(driver):
            solved = True

        # Strategy 3: Try table-based radio buttons
        if not solved:
            if solve_radio_tables(driver):
                solved = True

        # Strategy 4: Try yes/no questions
        if not solved:
            solve_yes_no(driver)

        # Strategy 5: Try checkboxes
        if not solved:
            if solve_checkboxes(driver):
                solved = True

        # Strategy 6: Try single radio option
        if not solved:
            if solve_single_radio(driver):
                solved = True

        # Strategy 7: Try generic branded radios
        if not solved:
            solve_branded_radios(driver)

        # Click Next
        time.sleep(0.5)
        click_next(driver)
        time.sleep(1.5)

    # Final check for validation code
    code = extract_validation_code(driver, timeout=5)
    if code:
        _update_status(f"🎉 Validation code found: {code}", progress=100, code=code)
        return code

    _update_status("Could not find validation code after all pages.", progress=100, error="No validation code found")
    return None

# ---------------------------------------------------------------------------
# High-level run functions
# ---------------------------------------------------------------------------
def run_with_receipt_code(code, headless=True):
    """Run the full survey using a receipt code."""
    driver = None
    try:
        driver = create_driver(headless=headless)
        reviews = load_reviews()

        entry_info = enter_receipt_code(driver, code)

        # First page after code entry: how did you order?
        # Usually Drive-Thru = Opt2
        _update_status("Selecting order type (Drive-Thru)...", progress=18)
        time.sleep(1)
        safe_click_css(driver, ".Opt2 .radioSimpleInput, .Opt2 .radioBranded, .Opt2 input[type='radio']")
        if not safe_click_css(driver, ".Opt2 .radioSimpleInput, .Opt2 .radioBranded"):
            # Try alternative: click first radio on page
            solve_single_radio(driver)
        click_next(driver)
        time.sleep(1)

        # Solve the rest
        validation_code = solve_survey(driver, reviews)

        if validation_code:
            result = save_result(entry_info, validation_code, "receipt_code")
            return {"success": True, "validation_code": validation_code, "result": result}
        else:
            return {"success": False, "error": "Could not extract validation code"}

    except Exception as e:
        tb = traceback.format_exc()
        _update_status(f"Error: {str(e)}", error=str(e))
        return {"success": False, "error": str(e), "traceback": tb}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def run_with_store_info(store_number, ks_number="01", headless=True, **kwargs):
    """Run the full survey using store info (piecemeal mode)."""
    driver = None
    try:
        driver = create_driver(headless=headless)
        reviews = load_reviews()

        entry_info = enter_store_info(driver, store_number, ks_number, **kwargs)

        # Solve the survey
        validation_code = solve_survey(driver, reviews)

        if validation_code:
            result = save_result(entry_info, validation_code, "store_info")
            return {"success": True, "validation_code": validation_code, "result": result}
        else:
            return {"success": False, "error": "Could not extract validation code"}

    except Exception as e:
        tb = traceback.format_exc()
        _update_status(f"Error: {str(e)}", error=str(e))
        return {"success": False, "error": str(e), "traceback": tb}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def print_banner():
    print(f"""{Fore.YELLOW}
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║        🍔  McDVOICE Auto Survey Bot  🍔          ║
    ║              v{VERSION}                              ║
    ║                                                   ║
    ║   Combined from happymeal + mcd-voice-bot         ║
    ║   ⚠️  Educational purposes only                   ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
    {Style.RESET_ALL}""")


def cli_main():
    """Interactive CLI mode."""
    print_banner()

    print(f"\n{Fore.GREEN}Choose entry mode:{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}1{Style.RESET_ALL} - Receipt Code (26-digit code from receipt)")
    print(f"  {Fore.CYAN}2{Style.RESET_ALL} - Store Info (auto-generate transaction data)")
    print()

    mode = input("Enter choice (1 or 2): ").strip()

    if mode == "1":
        code = input(f"\n{Fore.GREEN}Enter receipt code (XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-X):{Style.RESET_ALL}\n> ").strip()
        headless_input = input(f"{Fore.GREEN}Run headless? (y/n, default y):{Style.RESET_ALL} ").strip().lower()
        headless = headless_input != "n"

        print(f"\n{Fore.YELLOW}Starting survey...{Style.RESET_ALL}\n")
        result = run_with_receipt_code(code, headless=headless)

    elif mode == "2":
        store = input(f"\n{Fore.GREEN}Enter store number:{Style.RESET_ALL} ").strip()
        ks = input(f"{Fore.GREEN}Enter KS/register number (default 01):{Style.RESET_ALL} ").strip() or "01"
        count = int(input(f"{Fore.GREEN}How many surveys? (default 1):{Style.RESET_ALL} ").strip() or "1")
        headless_input = input(f"{Fore.GREEN}Run headless? (y/n, default y):{Style.RESET_ALL} ").strip().lower()
        headless = headless_input != "n"

        for i in range(count):
            print(f"\n{Fore.YELLOW}--- Survey {i+1}/{count} ---{Style.RESET_ALL}\n")
            result = run_with_store_info(store, ks, headless=headless)
            if result["success"]:
                print(f"\n{Fore.GREEN}✅ Validation Code: {result['validation_code']}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}❌ Failed: {result['error']}{Style.RESET_ALL}")
            if i < count - 1:
                time.sleep(2)
        return

    else:
        print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
        return

    if result["success"]:
        print(f"\n{Fore.GREEN}✅ Validation Code: {result['validation_code']}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}❌ Failed: {result['error']}{Style.RESET_ALL}")


if __name__ == "__main__":
    cli_main()
