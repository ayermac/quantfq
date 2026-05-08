"""Akshare-based data provider for fast A-share screening."""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class AkshareDataProvider:
    """Batch data provider using akshare APIs.

    Replaces per-stock yfinance calls with akshare batch endpoints
    for 10x+ speed improvement on A-share screening.
    """

    def get_snapshot(self) -> pd.DataFrame:
        """Fetch full A-share market real-time snapshot.

        Returns DataFrame with columns including:
        symbol, name, price, change_pct, volume, amount, market_cap.
        """
        import akshare as ak

        try:
            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                logger.warning("akshare stock_zh_a_spot_em returned empty")
                return pd.DataFrame()

            col_map = {}
            for col in df.columns:
                if col == "代码":
                    col_map[col] = "symbol"
                elif col == "名称":
                    col_map[col] = "name"
                elif col == "最新价":
                    col_map[col] = "price"
                elif col == "涨跌幅":
                    col_map[col] = "change_pct"
                elif col == "成交量":
                    col_map[col] = "volume"
                elif col == "成交额":
                    col_map[col] = "amount"
                elif col == "总市值":
                    col_map[col] = "market_cap"
            df = df.rename(columns=col_map)

            for col in ["price", "change_pct", "volume", "amount", "market_cap"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.info(f"Fetched snapshot: {len(df)} stocks")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch snapshot: {e}")
            return pd.DataFrame()

    def get_ohlcv(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data for a single stock via akshare.

        Args:
            symbol: Stock code, e.g. "000001"
            start_date: Start date "YYYY-MM-DD" or "YYYYMMDD"
            end_date: End date "YYYY-MM-DD" or "YYYYMMDD"
            adjust: Price adjustment - "qfq"(forward), "hfq"(backward), ""(none)

        Returns DataFrame with columns: Open, High, Low, Close, Volume
        """
        import akshare as ak

        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust=adjust,
            )
            if df is None or df.empty:
                return pd.DataFrame()

            col_map = {}
            for col in df.columns:
                cl = col.lower()
                if "日期" in col or cl == "date":
                    col_map[col] = "Date"
                elif "开盘" in col or cl == "open":
                    col_map[col] = "Open"
                elif "最高" in col or cl == "high":
                    col_map[col] = "High"
                elif "最低" in col or cl == "low":
                    col_map[col] = "Low"
                elif "收盘" in col or cl == "close":
                    col_map[col] = "Close"
                elif "成交量" in col or cl == "volume":
                    col_map[col] = "Volume"
            df = df.rename(columns=col_map)

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.set_index("Date")

            for col in ["Open", "High", "Low", "Close", "Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df
        except Exception as e:
            logger.debug(f"Failed to fetch OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    def get_money_flow(self, symbol: str) -> pd.DataFrame:
        """Fetch money flow data for a single stock.

        Returns DataFrame with daily fund flow including
        super_large_net, large_net columns (unit: wan yuan).
        """
        import akshare as ak

        try:
            market = "sh" if symbol.startswith("6") else "sz"
            df = ak.stock_individual_fund_flow(
                stock=symbol, market=market
            )
            if df is None or df.empty:
                return pd.DataFrame()

            col_map = {}
            for col in df.columns:
                if "日期" in col:
                    col_map[col] = "date"
                elif "超大单" in col and "净额" in col:
                    col_map[col] = "super_large_net"
                elif "大单" in col and "净额" in col and "超" not in col:
                    col_map[col] = "large_net"
                elif "中单" in col and "净额" in col:
                    col_map[col] = "medium_net"
                elif "小单" in col and "净额" in col:
                    col_map[col] = "small_net"
            df = df.rename(columns=col_map)

            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)

            for col in ["super_large_net", "large_net", "medium_net", "small_net"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df
        except Exception as e:
            logger.debug(f"Failed to fetch money flow for {symbol}: {e}")
            return pd.DataFrame()
