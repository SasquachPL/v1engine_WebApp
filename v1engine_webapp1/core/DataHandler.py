import os
import re
import pandas as pd

class DataHandler:
    """
    Handles loading and providing historical stock data from CSV files.
    This component can now either load a specific list of tickers or
    auto-discover all available tickers in the directory.
    """
    def __init__(self, csv_dir, ticker_list=None):
        """
        Initializes the DataHandler.

        Args:
            csv_dir (str): The directory where the CSV data files are stored.
            ticker_list (list, optional): A specific list of tickers to load.
                                          If None, it will discover all tickers.
        """
        self.csv_dir = csv_dir
        
        if ticker_list:
            print(f"DataHandler: Initializing with a specific list of {len(ticker_list)} tickers.")
            self.tickers = sorted([t.lower() for t in ticker_list])
        else:
            print("DataHandler: No ticker list provided, discovering all tickers in the directory.")
            self.tickers = self._discover_tickers()
            
        self.data = {}
        
        if self.tickers:
            self._load_data()
        else:
            print(f"Warning: No data files found or specified in '{self.csv_dir}'.")

    def _discover_tickers(self):
        """
        Scans the csv_dir to find all available ticker CSV files.
        """
        tickers = []
        # This pattern correctly looks for .csv files
        pattern = re.compile(r"daily_(\w+).csv", re.IGNORECASE)

        if not os.path.exists(self.csv_dir):
            return []

        for filename in os.listdir(self.csv_dir):
            match = pattern.match(filename)
            if match:
                tickers.append(match.group(1).lower())

        print(f"DataHandler: Discovered tickers: {sorted(tickers)}")
        return sorted(tickers)

    def _load_data(self):
        """
        Loads the historical data for each ticker in self.tickers from its CSV file.
        """
        print("DataHandler: Loading historical data from CSV files...")
        for ticker in self.tickers:
            file_path = os.path.join(self.csv_dir, f"daily_{ticker}.csv")
            
            if not os.path.exists(file_path):
                print(f"Warning: Data file not found for ticker '{ticker}' at {file_path}. Skipping.")
                continue

            try:
                # This correctly uses pd.read_csv for .csv files
                df = pd.read_csv(file_path, parse_dates=['date'], index_col='date')
                self.data[ticker] = df
            except Exception as e:
                raise e 
        print("DataHandler: Finished loading data.")


    def get_latest_data(self, date):
        """
        Retrieves the market data for all tickers on a specific date.
        """
        latest_data_for_date = {}
        date_ts = pd.to_datetime(date)

        for ticker in self.tickers:
            if ticker in self.data:
                try:
                    daily_data = self.data[ticker].loc[date_ts]
                    latest_data_for_date[ticker] = daily_data.to_dict()
                except KeyError:
                    pass
        
        return latest_data_for_date