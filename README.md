# Car Assistant Buyer

Car Assistant Buyer is a Python-based project designed to scrape car data from various brands and provide insights through a Streamlit web application. It uses Playwright for web scraping and Streamlit for visualization.

## Features

- **Web Scraping**: Collects car data from multiple brands using custom scrapers.
- **Streamlit Integration**: Displays scraped data in an interactive web application.
- **Efficient Resource Management**: Reuses a single browser instance for all scraping tasks to improve performance.
- **Customizable**: Easily extendable to support additional car brands.

## Installation

### Prerequisites

- Python 3.10 or higher
- Docker (optional, for containerized deployment)

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Car_Assistant_Buyer.git
   cd Car_Assistant_Buyer
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright:
   ```bash
   pip install playwright
   playwright install
   ```

5. Run the scraper:
   ```bash
   python -m src.scraper.main_scraper
   ```

6. Run the Streamlit app:
   ```bash
   python -m streamlit run app/app.py  
   ```

### Docker Setup

1. Build the Docker image:
   ```bash
   docker build -t car_assistant_buyer .
   ```

2. Run the container:
   ```bash
   docker run -p 8501:8501 --rm car_assistant_buyer
   ```

3. Access the Streamlit app at `http://localhost:8501`.

## Project Structure

```
Car_Assistant_Buyer/
├── src/
│   ├── scraper/
│   │   ├── main_scraper.py
│   │   ├── config.py
│   │   ├── car_brands/
│   │   │   ├── kia_scraper.py
│   │   │   ├── toyota_scraper.py
│   │   │   └── ...
│   ├── streamlit_app.py
├── requirements.txt
├── Dockerfile
├── README.md
└── .gitignore
```

## Technologies Used

- **Python**: Core programming language.
- **Playwright**: For web scraping.
- **Streamlit**: For building the web application.
- **Docker**: For containerized deployment.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request.


