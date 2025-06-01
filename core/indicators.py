import pandas as pd
from ta.volatility import BollingerBands
from ta.momentum import WilliamsRIndicator

def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20, window_dev: int = 2, column_name: str = "close"):
    """
    볼린저 밴드를 계산합니다.
    데이터프레임 'data'에 'column_name'으로 지정된 열(예: 'close')이 있다고 가정합니다.
    새로운 열('bb_mavg', 'bb_hband', 'bb_lband', 'bb_pband', 'bb_wband')이 추가된 데이터프레임을 반환합니다.
    """
    if column_name not in data.columns:
        raise ValueError(f"볼린저 밴드 계산을 위해 데이터프레임에 '{column_name}' 열이 없습니다.")
    if len(data) < window:
        # 계산할 데이터 부족; BB 열이 비어있는 데이터프레임 반환 또는 적절히 처리
        data['bb_mavg'] = pd.NA
        data['bb_hband'] = pd.NA
        data['bb_lband'] = pd.NA
        data['bb_pband'] = pd.NA
        data['bb_wband'] = pd.NA
        return data

    indicator_bb = BollingerBands(close=data[column_name], window=window, window_dev=window_dev)

    data['bb_mavg'] = indicator_bb.bollinger_mavg()        # 중간 밴드
    data['bb_hband'] = indicator_bb.bollinger_hband()      # 상단 밴드
    data['bb_lband'] = indicator_bb.bollinger_lband()      # 하단 밴드
    data['bb_pband'] = indicator_bb.bollinger_pband()      # 퍼센트 밴드 (%B)
    data['bb_wband'] = indicator_bb.bollinger_wband()      # 밴드폭

    return data

def calculate_williams_r(data: pd.DataFrame, period: int = 14):
    """
    Williams %R을 계산합니다.
    데이터프레임 'data'에 'high', 'low', 'close' 열이 있다고 가정합니다.
    새로운 열 'wr'이 추가된 데이터프레임을 반환합니다.
    """
    required_cols = ["high", "low", "close"]
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"Williams %R 계산을 위해 데이터프레임에 {required_cols} 열이 있어야 합니다.")
    if len(data) < period:
        # 데이터 부족
        data['wr'] = pd.NA
        return data

    indicator_wr = WilliamsRIndicator(high=data['high'], low=data['low'], close=data['close'], lbp=period)

    data['wr'] = indicator_wr.williams_r() # Williams %R 지표

    return data

if __name__ == '__main__':
    # 테스트용 샘플 데이터프레임 생성
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

    print("원본 데이터프레임:")
    print(df.head())

    # 볼린저 밴드 테스트
    df_bb = calculate_bollinger_bands(df.copy(), window=5, window_dev=2) # 작은 데이터셋을 위해 작은 윈도우 사용
    print("\n볼린저 밴드 추가된 데이터프레임 (윈도우=5):")
    print(df_bb[['close', 'bb_mavg', 'bb_hband', 'bb_lband']].tail())

    # Williams %R 테스트
    df_wr = calculate_williams_r(df.copy(), period=7) # 작은 데이터셋을 위해 작은 기간 사용
    print("\nWilliams %R 추가된 데이터프레임 (기간=7):")
    print(df_wr[['high', 'low', 'close', 'wr']].tail())

    # 불충분한 데이터로 테스트
    print("\nBB 불충분한 데이터로 테스트 (윈도우=30):")
    df_short = df.head(3).copy()
    df_short_bb = calculate_bollinger_bands(df_short, window=30)
    print(df_short_bb[['close', 'bb_mavg', 'bb_hband', 'bb_lband']].tail())

    print("\nWR 불충분한 데이터로 테스트 (기간=30):")
    df_short_wr = calculate_williams_r(df_short, period=30)
    print(df_short_wr[['high', 'low', 'close', 'wr']].tail())
