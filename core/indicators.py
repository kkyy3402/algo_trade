import pandas as pd
from ta.volatility import BollingerBands
from ta.momentum import WilliamsRIndicator

def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20, window_dev: int = 2, column_name: str = "close"):
    """
    Calculates Bollinger Bands.
    Assumes 'data' is a Pandas DataFrame with a column specified by 'column_name' (e.g., 'close').
    Returns the DataFrame with new columns: 'bb_mavg', 'bb_hband', 'bb_lband', 'bb_pband', 'bb_wband'.
    """
    if column_name not in data.columns:
        raise ValueError(f"Column '{column_name}' not found in DataFrame for Bollinger Bands calculation.")
    if len(data) < window:
        # Not enough data to calculate; return DataFrame with empty BB columns or handle as appropriate
        data['bb_mavg'] = pd.NA
        data['bb_hband'] = pd.NA
        data['bb_lband'] = pd.NA
        data['bb_pband'] = pd.NA
        data['bb_wband'] = pd.NA
        return data

    indicator_bb = BollingerBands(close=data[column_name], window=window, window_dev=window_dev)

    data['bb_mavg'] = indicator_bb.bollinger_mavg()        # Middle Band
    data['bb_hband'] = indicator_bb.bollinger_hband()      # Upper Band
    data['bb_lband'] = indicator_bb.bollinger_lband()      # Lower Band
    data['bb_pband'] = indicator_bb.bollinger_pband()      # Percentage Band (%B)
    data['bb_wband'] = indicator_bb.bollinger_wband()      # Bandwidth

    return data

def calculate_williams_r(data: pd.DataFrame, period: int = 14):
    """
    Calculates Williams %R.
    Assumes 'data' is a Pandas DataFrame with 'high', 'low', and 'close' columns.
    Returns the DataFrame with a new column: 'wr'.
    """
    required_cols = ["high", "low", "close"]
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain {required_cols} columns for Williams %R calculation.")
    if len(data) < period:
        # Not enough data
        data['wr'] = pd.NA
        return data

    indicator_wr = WilliamsRIndicator(high=data['high'], low=data['low'], close=data['close'], lbp=period)

    data['wr'] = indicator_wr.williams_r() # Williams %R

    return data

if __name__ == '__main__':
    # Create a sample DataFrame for testing
    sample_data = {
        'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                                      '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                                      '2023-01-11', '2023-01-12', '2023-01-13', '2023-01-14', '2023-01-15',
                                      '2023-01-16', '2023-01-17', '2023-01-18', '2023-01-19', '2023-01-20',
                                      '2023-01-21', '2023-01-22', '2023-01-23', '2023-01-24', '2023-01-25']),
        'open': [10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 19, 18, 17, 16],
        'high': [11, 12, 13, 14, 15, 16, 15, 14, 13, 12, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 20, 19, 18, 17],
        'low':  [9, 10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 18, 17, 16, 15],
        'close':[10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 14.5, 13.5, 12.5, 11.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 19.5, 18.5, 17.5, 16.5],
        'volume':[100, 110, 120, 130, 140, 150, 140, 130, 120, 110, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 190, 180, 170, 160]
    }
    df = pd.DataFrame(sample_data)
    df.set_index('timestamp', inplace=True)

    print("Original DataFrame:")
    print(df.head())

    # Test Bollinger Bands
    df_bb = calculate_bollinger_bands(df.copy(), window=5, window_dev=2) # Using smaller window for small dataset
    print("\nDataFrame with Bollinger Bands (window=5):")
    print(df_bb[['close', 'bb_mavg', 'bb_hband', 'bb_lband']].tail())

    # Test Williams %R
    df_wr = calculate_williams_r(df.copy(), period=7) # Using smaller period for small dataset
    print("\nDataFrame with Williams %R (period=7):")
    print(df_wr[['high', 'low', 'close', 'wr']].tail())

    # Test with insufficient data
    print("\nTesting with insufficient data for BB (window=30):")
    df_short = df.head(3).copy()
    df_short_bb = calculate_bollinger_bands(df_short, window=30)
    print(df_short_bb[['close', 'bb_mavg', 'bb_hband', 'bb_lband']].tail())

    print("\nTesting with insufficient data for WR (period=30):")
    df_short_wr = calculate_williams_r(df_short, period=30)
    print(df_short_wr[['high', 'low', 'close', 'wr']].tail())
