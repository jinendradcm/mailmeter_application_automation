# Mail Meter Application Automation 🚀

High-performance, multi-threaded email discovery automation script using Playwright and Python. This tool automates the process of finding professional email addresses via Mailmeteor's email finder tool.

## ✨ Key Features

- **Parallel Processing**: Supports multiple browser instances (Workers) and multiple tabs per instance for maximum throughput.
- **Persistent Sessions**: Uses persistent Chrome profiles to maintain state and avoid detection.
- **Smart Column Detection**: Automatically identifies name and domain columns in input files using advanced heuristics.
- **Resumable Operations**: Checks for existing results to avoid duplicate work and allow resuming after interruptions.
- **Flexible Data Support**: Handles both CSV and Excel (`.xlsx`, `.xls`) input formats.
- **Dual Output**: Saves results in both CSV and JSON formats in real-time.

## 🛠️ Tech Stack

- **Language**: Python 3.8+
- **Automation**: Playwright (Async API)
- **Data Handling**: Pandas, JSON
- **Environment**: Virtualenv / Chrome Profiles

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- [Playwright](https://playwright.dev/python/docs/intro)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jinendradcm/mailmeter_application_automation.git
   cd mailmeter_application_automation
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv myenv
   myenv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install pandas playwright openpyxl
   ```

4. **Install Playwright Browsers**:
   ```bash
   playwright install chromium
   ```

## 📖 Usage

1. **Prepare Input**: Ensure your input CSV or Excel file is in the project directory. The script defaults to `hospitality 10k ift 3.csv`.
2. **Configure Constants**: Edit `test_meter.py` to adjust:
   - `INPUT_FILE`: Path to your source file.
   - `WORKERS`: Number of browser instances.
   - `TABS_PER_WORKER`: Number of concurrent tabs per browser.
3. **Run the Script**:
   ```bash
   python test_meter.py
   ```

## 📁 Project Structure

```text
mailmeter_application_automation/
├── test_meter.py        # Main execution script
├── chrome_profile/      # Base directory for persistent profiles
├── chrome_profile_N/    # Individual worker profiles
├── hospitality...csv   # Input data (example)
├── output_...csv       # Generated results (CSV)
└── output_...json      # Generated results (JSON)
```

## ⚙️ Configuration

The following parameters can be tuned in `test_meter.py`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `WORKERS` | Number of separate browser processes | `5` |
| `TABS_PER_WORKER` | Concurrent tabs within each browser | `4` |
| `MAX_RETRIES` | Number of attempts for failed searches | `1` |
| `BASE_URL` | Target tool URL | `mailmeteor.com/...` |

## 👤 Chrome Profiles & Session Management

The script uses **Persistent Contexts** to manage browser sessions. You do not need to create these folders manually; the script handles everything:

1.  **Automatic Creation**: When you run the script, Playwright automatically creates directories named `chrome_profile_1`, `chrome_profile_2`, etc., in the project root.
2.  **State Persistence**: These folders store cookies, local storage, and browser cache. This allows the script to "remember" sessions and helps in bypassing common bot detection mechanisms.
3.  **Isolation**: Each worker uses its own unique profile directory, ensuring that concurrent searches do not interfere with each other's session data.

> [!TIP]
> If you encounter issues with a specific worker, you can safely delete its `chrome_profile_N` folder. The script will recreate a fresh one on the next run.

### 🛠️ Manual Profile Initialization (Optional)

If you need to manually log in or solve a captcha to "seed" a profile before running the automation:

1.  **Open Chromium with a persistent profile directory**:
    ```bash
    playwright open --user-data-dir=chrome_profile_1 https://mailmeteor.com/tools/email-finder
    ```
    *(Wait for the browser to open, perform your actions, and then close it. The state will be saved in `chrome_profile_1`.)*

2.  **Using a custom directory**:
    If you want to create a base profile to copy elsewhere:
    ```bash
    mkdir chrome_profile
    ```

## 🛡️ License

This project is licensed under the MIT License.

---
Built with ❤️ for High-Performance Automation
