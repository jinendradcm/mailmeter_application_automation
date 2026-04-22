import pandas as pd
import json
import asyncio
import os
import time
from playwright.async_api import async_playwright

INPUT_FILE = "hospitality 10k ift 3.csv"
OUTPUT_CSV = "output_hospitality 10k ift 3.csv"
OUTPUT_JSON = "output_hospitality 10k ift 3.json"
PROFILE_DIR = "chrome_profile"


WORKERS = 5  # number of browsers
TABS_PER_WORKER = 4
MAX_RETRIES = 1
BASE_URL = "https://mailmeteor.com/tools/email-finder"

def load_existing_results():
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_files(data):
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    pd.DataFrame(data).to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

def already_done(existing_data, name, domain):
    for row in existing_data:
        if row.get("input_name") == name and row.get("input_domain") == domain:
            return True   # 🔥 treat ALL processed as done
    return False


async def open_clean_page(page):
    # Cache bypass using random query param
    url = f"{BASE_URL}?r={int(time.time() * 1000)}"
    await page.goto(url, wait_until="networkidle", timeout=60000)

    await page.wait_for_selector("form#email-finder-form", timeout=20000)
    await page.wait_for_selector("#fullName", timeout=20000)
    await page.wait_for_selector("#domain", timeout=20000)


async def run_search(page, name, domain):
    # clear inputs fully
    await page.fill("#fullName", "")
    await page.fill("#domain", "")

    await page.click("#fullName")
    await page.keyboard.type(name, delay=50)

    await page.click("#domain")
    await page.keyboard.type(domain, delay=50)

    # click FIND EMAIL button
    async with page.expect_response(lambda r: "email-finder" in r.url or "api" in r.url, timeout=20000):
        await page.click("form#email-finder-form button[type='submit']")

    await page.wait_for_selector("div.email-result-card", timeout=20000)


async def get_state(page):
    """
    Returns:
        FOUND, NOT_FOUND, SEARCHING, UNKNOWN
    """
    try:
        card = page.locator("div.email-result-card").first

        title = ""
        try:
            title = (await card.locator("h5 span").inner_text()).strip().lower()
        except:
            title = ""

        if "no results found" in title:
            return "NOT_FOUND"

        if "searching" in title:
            return "SEARCHING"

        try:
            email_text = (await card.locator("span.email-finder__text.text-secondary").inner_text()).strip()
            if "@" in email_text:
                return "FOUND"
        except:
            pass

        return "UNKNOWN"

    except:
        return "UNKNOWN"


async def extract_email_data(page):
    card = page.locator("div.email-result-card").first

    found_name = None
    email = None
    status = None

    try:
        found_name = (await card.locator("h5 span").inner_text()).strip()
        if found_name.lower() in ["searching...", "no results found"]:
            found_name = None
    except:
        pass

    try:
        email_text = (await card.locator("span.email-finder__text.text-secondary").inner_text()).strip()
        if "@" in email_text:
            email = email_text
    except:
        pass

    try:
        status_text = (await card.locator("div.chip").inner_text()).strip()
        if status_text:
            status = status_text.lower()
    except:
        pass

    return found_name, email, status


async def scrape_one(page, name, domain, worker_id):
    result = {
        "input_name": name,
        "input_domain": domain,
        "url": BASE_URL,
        "found_name": None,
        "email": None,
        "status": None,
        "error": None
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[Worker-{worker_id}] TRY {attempt}/{MAX_RETRIES} -> {name} | {domain}")

            # HARD RESET PAGE EVERY ATTEMPT
            await open_clean_page(page)

            # Submit search
            await run_search(page, name, domain)

            # Wait max 12 seconds for FOUND/NOT_FOUND
            for _ in range(40):  # 40 * 0.3 = 12 sec
                state = await get_state(page)

                if state == "FOUND":
                    found_name, email, status = await extract_email_data(page)

                    result["found_name"] = found_name
                    result["email"] = email
                    result["status"] = status
                    result["error"] = None

                    return result

                if state == "NOT_FOUND":
                    print(f"[Worker-{worker_id}] NOT FOUND -> forcing retry")
                    break

                await asyncio.sleep(0.3)

        except Exception as e:
            print(f"[Worker-{worker_id}] ERROR attempt {attempt}: {str(e)}")

        await asyncio.sleep(0.4)

    result["error"] = f"NOT FOUND after {MAX_RETRIES} retries"
    return result

async def worker_group(worker_id, queue, context, existing_data, output_data, lock):
    pages = []

    # Create multiple tabs
    for i in range(TABS_PER_WORKER):
        page = await context.new_page()
        pages.append(page)

    async def tab_runner(page, tab_id):
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break

            idx, name, domain = item

            if already_done(existing_data, name, domain):
                print(f"[Worker-{worker_id} | Tab-{tab_id}] SKIP: {name} | {domain}")
                queue.task_done()
                continue

            print(f"[Worker-{worker_id} | Tab-{tab_id}] START [{idx}] {name} | {domain}")

            data = await scrape_one(page, name, domain, f"{worker_id}-{tab_id}")

            async with lock:
                output_data.append(data)
                save_files(existing_data + output_data)

            queue.task_done()

    # Run all tabs concurrently
    tasks = []
    for i, page in enumerate(pages):
        tasks.append(asyncio.create_task(tab_runner(page, i + 1)))

    await asyncio.gather(*tasks)

    for page in pages:
        await page.close()

    await context.close()

def detect_columns(df):
    name_candidates = []
    domain_candidates = []

    for col in df.columns:
        col_lower = col.lower().strip()

        # --- Heuristic 1: column name matching ---
        if any(k in col_lower for k in ["name", "full", "person", "contact"]):
            name_candidates.append(col)

        if any(k in col_lower for k in ["domain", "website", "company", "url"]):
            domain_candidates.append(col)

    # --- Heuristic 2: fallback using data pattern ---
    if not name_candidates or not domain_candidates:
        for col in df.columns:
            sample_values = df[col].dropna().astype(str).head(10)

            name_score = 0
            domain_score = 0

            for val in sample_values:
                val = val.strip()

                # Name pattern
                if " " in val and not any(c.isdigit() for c in val):
                    name_score += 1

                # Domain pattern
                if "." in val and " " not in val:
                    domain_score += 1

            if name_score >= 5:
                name_candidates.append(col)

            if domain_score >= 5:
                domain_candidates.append(col)

    if not name_candidates or not domain_candidates:
        raise Exception(f"Could not detect columns automatically. Columns found: {df.columns.tolist()}")

    return name_candidates[0], domain_candidates[0]


async def main():
    if INPUT_FILE.endswith(".csv"):
        df = pd.read_csv(INPUT_FILE, encoding="latin1")
    elif INPUT_FILE.endswith(".xlsx") or INPUT_FILE.endswith(".xls"):
        df = pd.read_excel(INPUT_FILE)
    else:
        raise Exception("Unsupported file format. Use CSV or Excel.")

    name_col, domain_col = detect_columns(df)

    print(f"Detected columns → NAME: {name_col}, DOMAIN: {domain_col}")

    records = df.to_dict(orient="records")

    existing_data = load_existing_results()
    output_data = []
    lock = asyncio.Lock()
    queue = asyncio.Queue()

    idx = 1
    skipped = 0
    queued = 0

    for row in records:
        name = str(row[name_col]).strip()
        domain = str(row[domain_col]).strip()

        if not name or not domain or name.lower() == "nan" or domain.lower() == "nan":
            continue

        # 🔥 SKIP BEFORE QUEUE (THIS IS THE KEY FIX)
        if already_done(existing_data, name, domain):
            skipped += 1
            continue

        await queue.put((idx, name, domain))
        queued += 1
        idx += 1

    print(f"SKIPPED (already done): {skipped}")
    print(f"QUEUED (remaining): {queued}")

    async with async_playwright() as p:
        def get_profile_dir(worker_id):
            return f"{PROFILE_DIR}_{worker_id}"

        #print(f"WORKERS={WORKERS} | MAX_RETRIES={MAX_RETRIES}")

        workers = []

        for i in range(WORKERS):
            context = await p.chromium.launch_persistent_context(
                get_profile_dir(i + 1),  # unique profile per browser
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            workers.append(asyncio.create_task(
                worker_group(i + 1, queue, context, existing_data, output_data, lock)
            ))

        # 1. Wait until all queued jobs are processed
        await queue.join()

        # 2. Now stop all workers (send shutdown signals)
        for _ in range(WORKERS * TABS_PER_WORKER):
            await queue.put(None)

        # 3. Wait for all workers to exit cleanly
        await asyncio.gather(*workers)

        await context.close()

    print("DONE")

if __name__ == "__main__":
    asyncio.run(main())
