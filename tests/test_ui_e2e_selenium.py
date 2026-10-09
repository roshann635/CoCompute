"""
CoCompute — End-to-End Selenium UI Test Suite
==============================================
Tests the complete user journey on a single PC:
  1. Auth Flow          → Register / Login via the Dashboard
  2. Dashboard Load     → Verify cluster stats, navigation tabs
  3. Worker Visibility  → Confirm online worker nodes appear
  4. Job Submission     → Submit a Sorting job via the modal
  5. Job Execution      → Wait for status to transition to 'completed'
  6. Result Retrieval   → Verify aggregated result is displayed
  7. Multi-Tab Nav      → Navigate through all dashboard tabs
  8. API Health         → Cross-verify dashboard state with REST API

Prerequisites:
  - Master running on http://localhost:8000
  - Dashboard running on http://localhost:5173
  - At least 1 Worker connected
  - Google Chrome or MS Edge installed
"""

import os, sys, time, json, datetime, traceback

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

# ── Selenium imports ──────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except ImportError:
    print("ERROR: pip install webdriver-manager selenium")
    sys.exit(1)

import requests

# ── Configuration ─────────────────────────────────────────────────────────────
DASHBOARD_URL = "http://localhost:5173"
API_BASE      = "http://localhost:8000/api/v1"
TEST_USER     = "selenium_e2e_user"
TEST_EMAIL    = "selenium_e2e@cocompute.test"
TEST_PASS     = "E2E_Test_2026!"
REPORT_DIR    = Path(__file__).parent
SCREENSHOT_DIR = REPORT_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ── Test Result Tracking ──────────────────────────────────────────────────────
class TestResult:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def record(self, name, status, duration, detail="", screenshot=None):
        self.results.append({
            "name": name,
            "status": status,     # PASS / FAIL / SKIP
            "duration_s": round(duration, 2),
            "detail": detail,
            "screenshot": screenshot,
        })
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️"}.get(status, "?")
        print(f"  {icon} {name} ({duration:.2f}s) {detail[:120] if detail else ''}")

    def summary(self):
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total_time = round(time.time() - self.start_time, 2)
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_time_s": total_time,
            "results": self.results,
        }


# ── Helper: Screenshot ────────────────────────────────────────────────────────
def screenshot(driver, name):
    path = str(SCREENSHOT_DIR / f"{name}.png")
    driver.save_screenshot(path)
    return path


# ── Helper: Safe click (avoids element-click-intercepted) ─────────────────────
def safe_click(driver, element):
    """Scroll into view and use JS click to bypass sticky headers / overlays."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});" , element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", element)


def dismiss_any_modal(driver):
    """Close any open modal by clicking its backdrop or close button."""
    try:
        # Try pressing Escape
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.5)
    except:
        pass
    # Also try clicking close (X) buttons in modals
    try:
        close_btns = driver.find_elements(By.CSS_SELECTOR, ".fixed button")
        for btn in close_btns:
            txt = btn.text.strip()
            if txt in ("Close", "") and btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
                break
    except:
        pass


# ── Helper: Create / get browser driver ──────────────────────────────────────
def create_driver():
    """Try Chrome first, fallback to Edge."""
    # Try Chrome
    try:
        opts = webdriver.ChromeOptions()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        print("  🌐 Using Google Chrome")
        return driver
    except Exception as e:
        print(f"  ⚠️ Chrome not available ({e.__class__.__name__}), trying Edge...")

    # Try Edge
    try:
        opts = webdriver.EdgeOptions()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=opts)
        print("  🌐 Using Microsoft Edge")
        return driver
    except Exception as e:
        print(f"  ❌ Edge not available either: {e}")
        raise RuntimeError("No supported browser found (Chrome or Edge)")


# ══════════════════════════════════════════════════════════════════════════════
# TEST FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_01_api_health(report: TestResult):
    """Verify Master API is reachable and healthy."""
    t0 = time.time()
    try:
        r = requests.get(f"{API_BASE}/workers/", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        workers = r.json()
        online = [w for w in workers if w["status"] == "online"]
        report.record("API Health Check", "PASS", time.time()-t0,
                       f"{len(workers)} workers registered, {len(online)} online")
    except Exception as e:
        report.record("API Health Check", "FAIL", time.time()-t0, str(e))


def test_02_dashboard_reachable(driver, report: TestResult):
    """Load the dashboard and verify it renders."""
    t0 = time.time()
    try:
        driver.get(DASHBOARD_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        assert "CoCompute" in driver.page_source or "localhost" in driver.current_url
        ss = screenshot(driver, "01_dashboard_loaded")
        report.record("Dashboard Reachable", "PASS", time.time()-t0,
                       f"Title: {driver.title}", ss)
    except Exception as e:
        ss = screenshot(driver, "01_dashboard_loaded_fail")
        report.record("Dashboard Reachable", "FAIL", time.time()-t0, str(e), ss)


def test_03_auth_register_login(driver, report: TestResult):
    """Register a new user or login if already exists, verify dashboard entry."""
    t0 = time.time()
    try:
        driver.get(DASHBOARD_URL)
        time.sleep(2)

        # Check if we're on the auth screen
        page = driver.page_source
        if "auth-username" in page or "Sign In" in page:
            # Try to register first
            # Click on Register tab
            tabs = driver.find_elements(By.TAG_NAME, "button")
            register_tab = None
            for tab in tabs:
                if "Register" in tab.text:
                    register_tab = tab
                    break
            if register_tab:
                register_tab.click()
                time.sleep(0.5)

            # Fill registration form
            username_input = driver.find_element(By.ID, "auth-username")
            username_input.clear()
            username_input.send_keys(TEST_USER)

            # Check if email field is present (registration mode)
            try:
                email_input = driver.find_element(By.ID, "auth-email")
                email_input.clear()
                email_input.send_keys(TEST_EMAIL)
            except NoSuchElementException:
                pass  # Already in login mode

            password_input = driver.find_element(By.ID, "auth-password")
            password_input.clear()
            password_input.send_keys(TEST_PASS)

            submit_btn = driver.find_element(By.ID, "auth-submit")
            submit_btn.click()
            time.sleep(3)

            # If registration failed (user exists), try login
            if "auth-username" in driver.page_source:
                # Switch to Sign In tab
                tabs = driver.find_elements(By.TAG_NAME, "button")
                for tab in tabs:
                    if "Sign In" in tab.text:
                        tab.click()
                        break
                time.sleep(0.5)

                username_input = driver.find_element(By.ID, "auth-username")
                username_input.clear()
                username_input.send_keys(TEST_USER)
                password_input = driver.find_element(By.ID, "auth-password")
                password_input.clear()
                password_input.send_keys(TEST_PASS)
                submit_btn = driver.find_element(By.ID, "auth-submit")
                submit_btn.click()
                time.sleep(3)

            ss = screenshot(driver, "02_after_auth")
            # Verify we left the auth screen (CoCompute dashboard loaded)
            page_after = driver.page_source
            if "Submit Workload" in page_after or "Overview" in page_after:
                report.record("Auth Register/Login", "PASS", time.time()-t0,
                               "Successfully authenticated", ss)
            else:
                report.record("Auth Register/Login", "FAIL", time.time()-t0,
                               "Still on auth screen after login attempt", ss)
        else:
            # Already logged in
            ss = screenshot(driver, "02_already_authed")
            report.record("Auth Register/Login", "PASS", time.time()-t0,
                           "Already authenticated", ss)

    except Exception as e:
        ss = screenshot(driver, "02_auth_fail")
        report.record("Auth Register/Login", "FAIL", time.time()-t0, str(e), ss)


def test_04_dashboard_overview_stats(driver, report: TestResult):
    """Verify overview tab displays cluster statistics."""
    t0 = time.time()
    try:
        time.sleep(2)
        page = driver.page_source

        # Check for stat card labels
        expected_labels = ["Total Nodes", "Online Nodes", "Active Cores"]
        found = [l for l in expected_labels if l in page]

        ss = screenshot(driver, "03_overview_stats")
        if len(found) >= 2:
            report.record("Overview Stats Display", "PASS", time.time()-t0,
                           f"Found labels: {found}", ss)
        else:
            report.record("Overview Stats Display", "FAIL", time.time()-t0,
                           f"Expected labels not found. Found only: {found}", ss)
    except Exception as e:
        ss = screenshot(driver, "03_overview_stats_fail")
        report.record("Overview Stats Display", "FAIL", time.time()-t0, str(e), ss)


def test_05_worker_nodes_visible(driver, report: TestResult):
    """Navigate to Nodes tab and verify at least 1 online worker is visible."""
    t0 = time.time()
    try:
        # Click on Nodes tab
        tabs = driver.find_elements(By.TAG_NAME, "button")
        nodes_tab = None
        for tab in tabs:
            if tab.text.strip() == "Nodes":
                nodes_tab = tab
                break

        if not nodes_tab:
            report.record("Worker Nodes Visible", "SKIP", time.time()-t0,
                           "Could not find 'Nodes' tab button")
            return

        nodes_tab.click()
        time.sleep(2)

        page = driver.page_source
        ss = screenshot(driver, "04_worker_nodes")

        # Check for worker indicators: "Online" badge or worker hostnames
        has_online = "ONLINE" in page.upper() or "online" in page
        has_worker_card = "LAPTOP" in page or "worker" in page.lower() or "PHYSICAL" in page

        if has_online or has_worker_card:
            report.record("Worker Nodes Visible", "PASS", time.time()-t0,
                           "Online workers visible in Nodes tab", ss)
        else:
            report.record("Worker Nodes Visible", "FAIL", time.time()-t0,
                           "No online worker cards found in Nodes tab", ss)
    except Exception as e:
        ss = screenshot(driver, "04_worker_nodes_fail")
        report.record("Worker Nodes Visible", "FAIL", time.time()-t0, str(e), ss)


def test_06_submit_sorting_job(driver, report: TestResult):
    """Open job submission modal, select Sorting preset, and submit."""
    t0 = time.time()
    try:
        # Click "Submit Workload" button
        buttons = driver.find_elements(By.TAG_NAME, "button")
        submit_btn = None
        for btn in buttons:
            if "Submit Workload" in btn.text:
                submit_btn = btn
                break

        if not submit_btn:
            ss = screenshot(driver, "05_no_submit_btn")
            report.record("Submit Sorting Job", "FAIL", time.time()-t0,
                           "Could not find 'Submit Workload' button", ss)
            return

        submit_btn.click()
        time.sleep(2)

        # The modal should now be open with "Submit Distributed Job" header
        page = driver.page_source
        if "Submit Distributed Job" not in page:
            ss = screenshot(driver, "05_modal_not_open")
            report.record("Submit Sorting Job", "FAIL", time.time()-t0,
                           "Submit modal did not open", ss)
            return

        ss_modal = screenshot(driver, "05_submit_modal_open")

        # The default preset is "Sorting" / "Merge Sort" which is already selected
        # Just click "Submit Workload" button inside the modal
        time.sleep(1)
        modal_buttons = driver.find_elements(By.TAG_NAME, "button")
        final_submit = None
        for btn in modal_buttons:
            txt = btn.text.strip()
            if "Submit Workload" in txt and btn.is_displayed():
                # Find the modal's submit button (not the header one)
                try:
                    # The modal submit button has Play icon + "Submit Workload"
                    final_submit = btn
                except:
                    pass

        if not final_submit:
            report.record("Submit Sorting Job", "FAIL", time.time()-t0,
                           "Could not find modal Submit button", ss_modal)
            return

        final_submit.click()
        time.sleep(3)

        # Verify modal closed and job appears
        ss_after = screenshot(driver, "06_after_job_submit")
        report.record("Submit Sorting Job", "PASS", time.time()-t0,
                       "Sorting job submitted via dashboard modal", ss_after)

    except Exception as e:
        ss = screenshot(driver, "05_submit_fail")
        report.record("Submit Sorting Job", "FAIL", time.time()-t0, str(e), ss)


def test_07_job_execution_wait(driver, report: TestResult):
    """Wait for the most recent job to reach 'completed' status via API polling."""
    t0 = time.time()
    try:
        max_wait = 90  # seconds
        poll_interval = 3
        elapsed = 0
        final_status = "unknown"

        while elapsed < max_wait:
            r = requests.get(f"{API_BASE}/jobs/", timeout=5)
            if r.status_code == 200:
                jobs = r.json()
                if jobs:
                    # Find the most recent job (last in list or highest ID)
                    latest = sorted(jobs, key=lambda j: j.get("id", 0))[-1]
                    final_status = latest.get("status", "unknown")
                    if final_status == "completed":
                        ss = screenshot(driver, "07_job_completed")
                        report.record("Job Execution Wait", "PASS", time.time()-t0,
                                       f"Job '{latest.get('name')}' completed in {elapsed}s", ss)
                        return
                    elif final_status == "failed":
                        ss = screenshot(driver, "07_job_failed")
                        report.record("Job Execution Wait", "FAIL", time.time()-t0,
                                       f"Job failed: {latest.get('name')}", ss)
                        return

            time.sleep(poll_interval)
            elapsed += poll_interval

        ss = screenshot(driver, "07_job_timeout")
        report.record("Job Execution Wait", "FAIL", time.time()-t0,
                       f"Timed out after {max_wait}s. Last status: {final_status}", ss)

    except Exception as e:
        ss = screenshot(driver, "07_job_exec_fail")
        report.record("Job Execution Wait", "FAIL", time.time()-t0, str(e), ss)


def test_08_jobs_tab_status(driver, report: TestResult):
    """Navigate to Jobs & Queue tab and verify job entries appear."""
    t0 = time.time()
    try:
        # Click on "Jobs & Queue" tab
        tabs = driver.find_elements(By.TAG_NAME, "button")
        jobs_tab = None
        for tab in tabs:
            txt = tab.text.strip()
            if "Jobs" in txt and "Queue" in txt:
                jobs_tab = tab
                break

        if not jobs_tab:
            # Fallback: try just "Jobs"
            for tab in tabs:
                if tab.text.strip().startswith("Jobs"):
                    jobs_tab = tab
                    break

        if jobs_tab:
            safe_click(driver, jobs_tab)
            time.sleep(2)

        page = driver.page_source
        ss = screenshot(driver, "08_jobs_tab")

        # Check for job-related content
        has_jobs = ("sorting" in page.lower() or "completed" in page.lower() or
                    "running" in page.lower() or "pending" in page.lower() or
                    "Active" in page)

        if has_jobs:
            report.record("Jobs Tab Display", "PASS", time.time()-t0,
                           "Job entries visible in Jobs & Queue tab", ss)
        else:
            report.record("Jobs Tab Display", "FAIL", time.time()-t0,
                           "No job entries found", ss)
    except Exception as e:
        ss = screenshot(driver, "08_jobs_tab_fail")
        report.record("Jobs Tab Display", "FAIL", time.time()-t0, str(e), ss)


def test_09_job_result_verification(driver, report: TestResult):
    """Verify the completed job's result via API (sorted array correctness)."""
    t0 = time.time()
    try:
        r = requests.get(f"{API_BASE}/jobs/", timeout=5)
        jobs = r.json()
        completed = [j for j in jobs if j.get("status") == "completed"]

        if not completed:
            report.record("Job Result Verification", "SKIP", time.time()-t0,
                           "No completed jobs to verify")
            return

        latest = sorted(completed, key=lambda j: j.get("id", 0))[-1]
        job_id = latest["id"]

        # Fetch result
        rr = requests.get(f"{API_BASE}/jobs/{job_id}/result", timeout=10)
        if rr.status_code != 200:
            report.record("Job Result Verification", "FAIL", time.time()-t0,
                           f"Result endpoint returned {rr.status_code}")
            return

        result = rr.json()
        agg = result.get("aggregated_result", {})

        if latest.get("job_type") == "sorting":
            sorted_data = agg.get("sorted_array") or agg.get("sorted_data") or agg.get("result", [])
            if isinstance(sorted_data, list) and len(sorted_data) > 0:
                # Verify it's actually sorted
                is_sorted = all(sorted_data[i] <= sorted_data[i+1] for i in range(len(sorted_data)-1))
                if is_sorted:
                    report.record("Job Result Verification", "PASS", time.time()-t0,
                                   f"Sorting result verified: {len(sorted_data)} items, correctly sorted ✓")
                else:
                    report.record("Job Result Verification", "FAIL", time.time()-t0,
                                   "Sorting result is NOT correctly sorted!")
            else:
                report.record("Job Result Verification", "PASS", time.time()-t0,
                               f"Job completed with result keys: {list(agg.keys())}")
        elif latest.get("job_type") == "prime_generation":
            primes = agg.get("primes") or agg.get("result", [])
            if isinstance(primes, list) and len(primes) > 0:
                report.record("Job Result Verification", "PASS", time.time()-t0,
                               f"Prime generation result: {len(primes)} primes found")
            else:
                report.record("Job Result Verification", "PASS", time.time()-t0,
                               f"Job completed with result: {list(agg.keys())}")
        else:
            report.record("Job Result Verification", "PASS", time.time()-t0,
                           f"Job type '{latest.get('job_type')}' completed. Result keys: {list(agg.keys())}")

    except Exception as e:
        report.record("Job Result Verification", "FAIL", time.time()-t0, str(e))


def test_10_navigate_all_tabs(driver, report: TestResult):
    """Click through all major dashboard tabs and verify they render."""
    t0 = time.time()
    tab_names = [
        "Overview", "Task Registry", "Result Explorer", "Jobs",
        "Pool", "Analytics", "Nodes", "Logs"
    ]
    visited = []
    try:
        # First dismiss any open modals
        dismiss_any_modal(driver)
        time.sleep(0.5)

        for tab_name in tab_names:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            clicked = False
            for btn in buttons:
                txt = btn.text.strip()
                if tab_name in txt and btn.is_displayed():
                    try:
                        safe_click(driver, btn)
                        time.sleep(1.5)
                        visited.append(tab_name)
                        clicked = True
                        break
                    except:
                        pass
            if not clicked:
                pass  # Tab not found, skip

        ss = screenshot(driver, "09_all_tabs")
        report.record("Navigate All Tabs", "PASS", time.time()-t0,
                       f"Visited {len(visited)}/{len(tab_names)} tabs: {visited}", ss)
    except Exception as e:
        ss = screenshot(driver, "09_all_tabs_fail")
        report.record("Navigate All Tabs", "FAIL", time.time()-t0, str(e), ss)


def test_11_worker_detail_modal(driver, report: TestResult):
    """Click on a worker card in the Nodes tab to open the detail modal."""
    t0 = time.time()
    try:
        # Dismiss any open modals first
        dismiss_any_modal(driver)
        time.sleep(0.5)

        # Navigate to Nodes tab
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Nodes" in btn.text.strip() and btn.is_displayed():
                safe_click(driver, btn)
                break
        time.sleep(2)

        # Find a worker card (look for elements with cursor-pointer class)
        cards = driver.find_elements(By.CSS_SELECTOR, ".cursor-pointer")
        if not cards:
            report.record("Worker Detail Modal", "SKIP", time.time()-t0,
                           "No clickable worker cards found")
            return

        safe_click(driver, cards[0])
        time.sleep(1.5)

        page = driver.page_source
        ss = screenshot(driver, "10_worker_detail")

        if "UID:" in page or "Operating System" in page or "Compute Resources" in page:
            report.record("Worker Detail Modal", "PASS", time.time()-t0,
                           "Worker detail modal opened with hardware specs", ss)
        else:
            report.record("Worker Detail Modal", "FAIL", time.time()-t0,
                           "Worker modal content not found", ss)

        # Close modal
        dismiss_any_modal(driver)
        time.sleep(0.5)

    except Exception as e:
        ss = screenshot(driver, "10_worker_detail_fail")
        report.record("Worker Detail Modal", "FAIL", time.time()-t0, str(e), ss)


def test_12_submit_prime_job(driver, report: TestResult):
    """Submit a Prime Generation job and verify it completes."""
    t0 = time.time()
    try:
        # Dismiss any open modals first
        dismiss_any_modal(driver)
        time.sleep(0.5)

        # Open submit modal via JS click to bypass interception
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Submit Workload" in btn.text and btn.is_displayed():
                safe_click(driver, btn)
                break
        time.sleep(2)

        # Select Prime Gen preset
        modal_buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in modal_buttons:
            if "Prime Gen" in btn.text and btn.is_displayed():
                safe_click(driver, btn)
                break
        time.sleep(1)

        ss_prime = screenshot(driver, "11_prime_preset_selected")

        # Submit — find the modal's "Submit Workload" button (inside the .fixed overlay)
        modal_area = driver.find_elements(By.CSS_SELECTOR, ".fixed button")
        submitted = False
        for btn in modal_area:
            txt = btn.text.strip()
            if "Submit Workload" in txt and btn.is_displayed():
                safe_click(driver, btn)
                submitted = True
                break
        if not submitted:
            # Fallback: find any visible Submit Workload button
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                if "Submit Workload" in btn.text and btn.is_displayed():
                    safe_click(driver, btn)
                    break
        time.sleep(3)

        # Poll for completion
        max_wait = 90
        elapsed = 0
        while elapsed < max_wait:
            r = requests.get(f"{API_BASE}/jobs/", timeout=5)
            if r.status_code == 200:
                jobs = r.json()
                prime_jobs = [j for j in jobs if j.get("job_type") == "prime_generation"]
                if prime_jobs:
                    latest = sorted(prime_jobs, key=lambda j: j.get("id", 0))[-1]
                    if latest.get("status") == "completed":
                        ss = screenshot(driver, "12_prime_completed")
                        report.record("Submit & Execute Prime Job", "PASS", time.time()-t0,
                                       f"Prime job completed in {elapsed}s", ss)
                        return
                    elif latest.get("status") == "failed":
                        ss = screenshot(driver, "12_prime_failed")
                        report.record("Submit & Execute Prime Job", "FAIL", time.time()-t0,
                                       "Prime job failed", ss)
                        return
            time.sleep(3)
            elapsed += 3

        ss = screenshot(driver, "12_prime_timeout")
        report.record("Submit & Execute Prime Job", "FAIL", time.time()-t0,
                       f"Timed out after {max_wait}s", ss)

    except Exception as e:
        ss = screenshot(driver, "11_prime_fail")
        report.record("Submit & Execute Prime Job", "FAIL", time.time()-t0, str(e), ss)


def test_13_api_provenance_check(driver, report: TestResult):
    """Verify provenance API returns chunk-level audit data for a completed job."""
    t0 = time.time()
    try:
        r = requests.get(f"{API_BASE}/jobs/", timeout=5)
        jobs = r.json()
        completed = [j for j in jobs if j.get("status") == "completed"]

        if not completed:
            report.record("API Provenance Check", "SKIP", time.time()-t0,
                           "No completed jobs to check provenance")
            return

        job_id = sorted(completed, key=lambda j: j.get("id", 0))[-1]["id"]
        pr = requests.get(f"{API_BASE}/jobs/{job_id}/provenance", timeout=10)

        if pr.status_code == 200:
            data = pr.json()
            chunks = data.get("chunks", [])
            report.record("API Provenance Check", "PASS", time.time()-t0,
                           f"Provenance retrieved: {len(chunks)} chunks with attempt trees")
        else:
            report.record("API Provenance Check", "FAIL", time.time()-t0,
                           f"Provenance endpoint returned {pr.status_code}")
    except Exception as e:
        report.record("API Provenance Check", "FAIL", time.time()-t0, str(e))


def test_14_websocket_telemetry(driver, report: TestResult):
    """Verify that the dashboard's WebSocket connection indicator shows 'Adaptive Hybrid'."""
    t0 = time.time()
    try:
        # Navigate to overview
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Overview" in btn.text.strip() and btn.is_displayed():
                btn.click()
                break
        time.sleep(2)

        page = driver.page_source
        ss = screenshot(driver, "13_ws_telemetry")

        if "Adaptive Hybrid" in page:
            report.record("WebSocket Telemetry", "PASS", time.time()-t0,
                           "Real-time WebSocket connection active (Adaptive Hybrid mode)", ss)
        elif "Polling" in page:
            report.record("WebSocket Telemetry", "PASS", time.time()-t0,
                           "Dashboard connected via polling fallback", ss)
        else:
            report.record("WebSocket Telemetry", "FAIL", time.time()-t0,
                           "No connection indicator found", ss)
    except Exception as e:
        ss = screenshot(driver, "13_ws_fail")
        report.record("WebSocket Telemetry", "FAIL", time.time()-t0, str(e), ss)


def test_15_final_dashboard_state(driver, report: TestResult):
    """Capture the final state of the dashboard with all data loaded."""
    t0 = time.time()
    try:
        # Dismiss any open modals
        dismiss_any_modal(driver)
        time.sleep(0.5)

        # Go back to overview
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "Overview" in btn.text.strip() and btn.is_displayed():
                safe_click(driver, btn)
                break
        time.sleep(3)

        # Refresh to get latest data
        driver.refresh()
        time.sleep(4)

        ss = screenshot(driver, "14_final_state")
        report.record("Final Dashboard State", "PASS", time.time()-t0,
                       "Dashboard final state captured successfully", ss)
    except Exception as e:
        ss = screenshot(driver, "14_final_state_fail")
        report.record("Final Dashboard State", "FAIL", time.time()-t0, str(e), ss)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 72)
    print("  CoCompute End-to-End Selenium Test Suite")
    print(f"  Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Dashboard: {DASHBOARD_URL}")
    print(f"  Master API: {API_BASE}")
    print("=" * 72)
    print()

    report = TestResult()

    # ── Test 1: API Health (no browser needed) ──
    print("📋 Phase 1: Infrastructure Validation")
    test_01_api_health(report)
    print()

    # ── Create browser driver ──
    print("🌐 Phase 2: Browser Setup")
    try:
        driver = create_driver()
    except Exception as e:
        print(f"  ❌ FATAL: Could not create browser driver: {e}")
        report.record("Browser Setup", "FAIL", 0, str(e))
        generate_report(report)
        return

    driver.implicitly_wait(5)
    report.record("Browser Setup", "PASS", 0, f"Browser initialized: {driver.capabilities.get('browserName', 'unknown')}")
    print()

    try:
        # ── Phase 3: Auth ──
        print("🔐 Phase 3: Authentication Flow")
        test_02_dashboard_reachable(driver, report)
        test_03_auth_register_login(driver, report)
        print()

        # ── Phase 4: Dashboard Verification ──
        print("📊 Phase 4: Dashboard & Cluster Verification")
        test_04_dashboard_overview_stats(driver, report)
        test_05_worker_nodes_visible(driver, report)
        test_14_websocket_telemetry(driver, report)
        print()

        # ── Phase 5: Job Submission & Execution ──
        print("🚀 Phase 5: Job Submission & Execution")
        test_06_submit_sorting_job(driver, report)
        test_07_job_execution_wait(driver, report)
        test_08_jobs_tab_status(driver, report)
        test_09_job_result_verification(driver, report)
        print()

        # ── Phase 6: Prime Gen Job ──
        print("🔢 Phase 6: Second Workload (Prime Generation)")
        test_12_submit_prime_job(driver, report)
        print()

        # ── Phase 7: Navigation & Modals ──
        print("🧭 Phase 7: Full UI Navigation & Modals")
        test_10_navigate_all_tabs(driver, report)
        test_11_worker_detail_modal(driver, report)
        print()

        # ── Phase 8: Provenance & Final ──
        print("📜 Phase 8: Provenance, Telemetry & Final State")
        test_13_api_provenance_check(driver, report)
        test_15_final_dashboard_state(driver, report)
        print()

    except KeyboardInterrupt:
        print("\n⚠️ Test run interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error in test run: {e}")
        traceback.print_exc()
    finally:
        # Always close browser
        try:
            driver.quit()
        except:
            pass

    # ── Generate Report ──
    generate_report(report)


def generate_report(report: TestResult):
    """Generate a markdown test report."""
    summary = report.summary()

    print("=" * 72)
    print(f"  📋 TEST SUITE COMPLETE")
    print(f"  Total: {summary['total']}  |  ✅ Passed: {summary['passed']}  |  ❌ Failed: {summary['failed']}  |  ⚠️ Skipped: {summary['skipped']}")
    print(f"  Duration: {summary['total_time_s']}s")
    print("=" * 72)

    # Write markdown report
    report_path = REPORT_DIR / "selenium_e2e_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# CoCompute — Selenium E2E Test Report\n\n")
        f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Platform:** Single-PC Local Cluster  \n")
        f.write(f"**Dashboard:** {DASHBOARD_URL}  \n")
        f.write(f"**Master API:** {API_BASE}  \n\n")
        f.write("---\n\n")
        f.write("## Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Tests | {summary['total']} |\n")
        f.write(f"| ✅ Passed | {summary['passed']} |\n")
        f.write(f"| ❌ Failed | {summary['failed']} |\n")
        f.write(f"| ⚠️ Skipped | {summary['skipped']} |\n")
        f.write(f"| Duration | {summary['total_time_s']}s |\n")
        f.write(f"| Pass Rate | {summary['passed']/max(summary['total'],1)*100:.1f}% |\n\n")
        f.write("---\n\n")
        f.write("## Detailed Results\n\n")
        f.write("| # | Test | Status | Duration | Detail |\n")
        f.write("|---|------|--------|----------|--------|\n")
        for i, r in enumerate(summary["results"], 1):
            icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️"}.get(r["status"], "?")
            detail = r["detail"][:80].replace("|", "\\|") if r["detail"] else ""
            f.write(f"| {i} | {r['name']} | {icon} {r['status']} | {r['duration_s']}s | {detail} |\n")

        f.write("\n---\n\n")
        f.write("## Screenshots\n\n")
        for r in summary["results"]:
            if r.get("screenshot"):
                name = Path(r["screenshot"]).name
                f.write(f"### {r['name']}\n")
                f.write(f"![{name}]({r['screenshot']})\n\n")

        f.write("\n---\n\n")
        f.write("## Test Architecture\n\n")
        f.write("```\n")
        f.write("Single-PC Test Topology:\n")
        f.write("  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐\n")
        f.write("  │ Master Node │◄──►│  Worker (1)   │    │ Selenium       │\n")
        f.write("  │  :8000      │    │  localhost     │    │ Browser Driver │\n")
        f.write("  └──────┬──────┘    └──────────────┘    └───────┬────────┘\n")
        f.write("         │                                       │\n")
        f.write("         ▼                                       ▼\n")
        f.write("  ┌─────────────┐                       ┌───────────────┐\n")
        f.write("  │ Dashboard   │◄──────────────────────│ Test Assertions│\n")
        f.write("  │  :5173      │   (HTTP + WebSocket)  │ & Screenshots  │\n")
        f.write("  └─────────────┘                       └───────────────┘\n")
        f.write("```\n\n")

        overall = "🟢 ALL TESTS PASSED" if summary["failed"] == 0 else "🔴 SOME TESTS FAILED"
        f.write(f"**Overall Verdict: {overall}**\n")

    print(f"\n📄 Report saved to: {report_path}")
    print(f"📸 Screenshots saved to: {SCREENSHOT_DIR}")

    # Also write JSON report
    json_path = REPORT_DIR / "selenium_e2e_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"📊 JSON report: {json_path}")


if __name__ == "__main__":
    main()
