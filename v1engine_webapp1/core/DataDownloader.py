import os
import time
import pandas as pd
import requests

# Import the API key from the configuration file.
# This file must be in the same directory and named 'config_api.py'.
try:
    from configuration.config_api import ALPHA_VANTAGE_API_KEY
except ImportError:
    print("Error: A 'config_api.py' file with your ALPHA_VANTAGE_API_KEY is required.")
    ALPHA_VANTAGE_API_KEY = None

class DataDownloader:
    """
    A component for downloading historical stock data from the Alpha Vantage API
    and saving it to CSV files.
    """
    def __init__(self, api_key, output_dir='data'):
        """
        Initializes the DataDownloader.

        Args:
            api_key (str): Your Alpha Vantage API key.
            output_dir (str): The directory where CSV files will be saved.
        """
        self.api_key = api_key
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def download_and_save_data(self, tickers, start_date, end_date):
        """
        Downloads and saves historical data for a list of tickers within a date range.

        Args:
            tickers (list): A list of stock ticker symbols (e.g., ['AAPL', 'GOOG']).
            start_date (str): The start date for the data in 'YYYY-MM-DD' format.
            end_date (str): The end date for the data in 'YYYY-MM-DD' format.
        """
        if not self.api_key:
            print("Cannot download data without an API key.")
            return

        for ticker in tickers:
            print(f"Downloading data for {ticker}...")
            
            # Construct the API request URL
            url = (
                f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED'
                f'&symbol={ticker}&outputsize=full&apikey={self.api_key}'
            )
            
            # Make the API request
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()  # Raise an exception for bad status codes
                data = response.json()

                if "Time Series (Daily)" not in data:
                    print(f"Could not retrieve 'Time Series (Daily)' for {ticker}. "
                          f"Response: {data.get('Note', data)}")
                    time.sleep(1) 
                    continue

                # Convert the data into a pandas DataFrame
                df = pd.DataFrame.from_dict(data['Time Series (Daily)'], orient='index')
                
                # Format the DataFrame
                df.index = pd.to_datetime(df.index)
                df = df.sort_index(ascending=True)
                
                # Rename columns to a standard format for consistency
                df.rename(columns={
                    '1. open': 'open',
                    '2. high': 'high',
                    '3. low': 'low',
                    '4. close': 'close',
                    '5. adjusted close': 'adjusted_close',
                    '6. volume': 'volume',
                    '7. dividend amount': 'dividend_amount',
                    '8. split coefficient': 'split_coefficient'
                }, inplace=True)
                
                # Convert columns to numeric types
                for col in ['open', 'high', 'low', 'close', 'adjusted_close', 'volume']:
                    df[col] = pd.to_numeric(df[col])

                # Filter the DataFrame by the specified date range
                df = df.loc[start_date:end_date]
                
                # Fulfills the requirement to get Open, High, Low, Close, Volume
                final_df = df[['open', 'high', 'low', 'close', 'volume']]
                
                # --- MODIFICATION START ---
                # Per user request, convert the date index into a regular column
                final_df = final_df.reset_index()
                final_df.rename(columns={'index': 'date'}, inplace=True)
                # --- MODIFICATION END ---

                # Save the data to a dedicated CSV file
                file_path = os.path.join(self.output_dir, f"daily_{ticker}.csv")
                
                # --- MODIFICATION ---
                # Save the CSV without the pandas index column
                final_df.to_csv(file_path, index=False)
                
                print(f"Successfully saved data for {ticker} to {file_path}")

            except requests.exceptions.RequestException as e:
                print(f"An error occurred while downloading data for {ticker}: {e}")
            except Exception as e:
                print(f"An error occurred during data processing for {ticker}: {e}")
            
            time.sleep(2)

if __name__ == '__main__':
    # --- Example Usage ---
    
    # This block checks if the API key was successfully imported before trying to run.
    if ALPHA_VANTAGE_API_KEY:
        print("API Key found. Starting downloader...")
        
        # 1. Define the list of tickers and the date range
        tickers_to_download = ['AAPL', 'GOOG']
        start = '2020-01-01'
        end = '2023-12-31'
        
        # 2. Create an instance of the DataDownloader
        downloader = DataDownloader(api_key=ALPHA_VANTAGE_API_KEY, output_dir='data')
        
        # 3. Run the download process
        downloader.download_and_save_data(tickers_to_download, start, end)
    else:
        # This message will ONLY print if the import from config_api.py failed.
        print("\nCould not import API Key. Please ensure 'config_api.py' is in the correct directory and has no errors.")