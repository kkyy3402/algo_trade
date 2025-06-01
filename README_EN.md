[한글 버전 (Korean Version)](README.md)

# Algorithmic Trading Bot (algo_trade)

This project is a Python-based algorithmic trading bot developed with the assistance of Google's AI, Jules.
It uses Bollinger Bands and Williams %R indicators for trading signals and is designed to interact with the Korea Investment & Securities (KIS) API. The bot features a FastAPI backend and a Streamlit-based user interface.

## Features

*   **Trading Strategy**: Based on Bollinger Bands and Williams %R.
*   **KIS API Integration**: For fetching market data, account information, and placing orders (requires user's KIS API keys).
*   **FastAPI Backend**: Provides API endpoints for:
    *   Scanning stocks for trading signals.
    *   Executing trades.
    *   Viewing portfolio and account balance.
*   **Streamlit UI**: A web-based interface to:
    *   Monitor portfolio.
    *   Scan stocks on demand.
    *   Manually execute trades.
*   **Scheduled Jobs**: Automated periodic scanning of predefined stocks using APScheduler.
*   **Extensible Design**: Structured for easier modifications and additions (e.g., new trading strategies).

## Project Structure

```
algo_trade/
├── backend/                  # Contains all backend code, including FastAPI app
│   ├── api/                  # API endpoint definitions (trading.py)
│   ├── core/                 # Core logic (KIS API, indicators, config)
│   ├── models/               # Pydantic data models (trade.py)
│   ├── services/             # Business logic services (trading_service.py)
│   ├── scheduler/            # APScheduler jobs (jobs.py)
│   ├── ui/                   # Streamlit UI application (app_ui.py)
│   ├── main.py               # FastAPI application entry point
│   ├── utils.py              # Utility functions
│   ├── requirements.txt      # Python dependencies for backend
│   ├── requirements-dev.txt  # Development dependencies
│   └── .env                  # For API keys and other environment variables (user-created from .env.example or instructions)
├── PLAN.txt                  # Development plan and progress.
└── README.md                 # This file.
```
*(Note: The .env file should be created by the user and not committed to version control.)*

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd algo_trade
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Navigate to the `backend` directory and install the required packages:
    ```bash
    cd backend
    pip install -r requirements.txt
    pip install -r requirements-dev.txt # For development tools like pytest
    ```
    *   **TA-Lib Note**: The `ta` library is used. If you encounter issues with its dependencies (like TA-Lib itself), you might need to install the TA-Lib C library separately on your system. Refer to the `ta` library's documentation or [TA-Lib's official page](https://ta-lib.org/hdr_dw.html) for installation instructions.

4.  **Configure Environment Variables:**
    *   In the `backend` directory, create a file named `.env`.
    *   Add your Korea Investment & Securities API keys and account details to this file. You can use the existing `.env` file (which was created with placeholders) as a template:
        ```env
        KIS_APP_KEY="YOUR_KIS_APP_KEY"
        KIS_APP_SECRET="YOUR_KIS_APP_SECRET"

        # For KIS API functions requiring account number (e.g., balance, orders)
        # These are examples; obtain the correct values from your KIS account details.
        KIS_ACCOUNT_CANO="YOUR_ACCOUNT_NUMBER_FIRST_8_DIGITS"
        KIS_ACCOUNT_ACNT_PRDT_CD="YOUR_ACCOUNT_PRODUCT_CODE_LAST_2_DIGITS"
        ```
    *   **Important**: Replace placeholder values with your actual KIS API credentials and account information. Ensure the account numbers are for a **virtual/mock trading account** if you are testing, especially for order placement.

## Running the Application

The application consists of two main parts: the FastAPI backend and the Streamlit UI.

1.  **Start the FastAPI Backend:**
    *   Navigate to the `backend` directory.
    *   Run Uvicorn:
        ```bash
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   The backend API will be accessible at `http://localhost:8000`.
    *   The API documentation (Swagger UI) will be at `http://localhost:8000/docs`.

2.  **Start the Streamlit UI:**
    *   Open a **new terminal** window/tab.
    *   Activate the virtual environment (if not already active).
    *   Navigate to the `backend` directory (where `ui/app_ui.py` is located relative to the project root, or adjust path if running Streamlit from root).
    *   Run Streamlit:
        ```bash
        streamlit run ui/app_ui.py
        ```
    *   The Streamlit UI will typically open in your web browser automatically, usually at `http://localhost:8501`.

## Usage

*   **Backend API**: You can interact with the API endpoints directly using tools like Postman or curl, or view the interactive documentation at `/docs`.
*   **Streamlit UI**:
    *   **Portfolio**: View your current account balance and holdings. Click "Refresh Portfolio" to update.
    *   **Stock Scanner**: Enter comma-separated stock codes to get trading signals based on the implemented strategy.
    *   **Manual Trade Execution**: Place buy or sell orders. Ensure you understand the order types and conditions. **Use with extreme caution, preferably with a virtual trading account.**
*   **Scheduled Jobs**: The backend runs a scheduled job (default: hourly) to scan a predefined list of stocks. Check the backend logs for output from these scans.

## Disclaimer

*   This is a software development project and not financial advice.
*   Automated trading systems carry significant risks.
*   **Always test thoroughly with a virtual/paper trading account before considering any real-money trading.**
*   The developers are not responsible for any financial losses incurred.
*   Ensure your KIS API usage complies with their terms of service.

## Future Enhancements (from PLAN.txt)

*   Full implementation of the Strategy pattern for easily swappable trading algorithms.
*   Database integration for storing trade history, signals, and configurations.
*   More sophisticated error handling and notifications.
*   Comprehensive unit and integration tests.
*   Configuration options for scheduler frequency and stock lists via UI or config files.
