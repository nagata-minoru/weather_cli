import argparse
import datetime as dt
import sys
import bisect
from typing import Optional
import requests

# 福岡市(博多)の座標
latitude = 33.590355
longitude = 130.401716

url = "https://api.open-meteo.com/v1/forecast"
params = {
  "latitude": latitude,
  "longitude": longitude,
  "current_weather": True,
}

WEATHER_MAP = {
  0: "快晴",
  1: "晴れ",
  2: "薄曇り",
  3: "曇り",
  45: "霧",
  48: "濃霧",
  51: "霧雨（弱）",
  53: "霧雨（中）",
  55: "霧雨（強）",
  61: "雨（弱）",
  62: "雨（中）",
  65: "雨（強）",
  71: "雪（弱）",
  73: "雪（中）",
  75: "雪（強）",
  80: "にわか雨（弱）",
  81: "にわか雨（中）",
  82: "にわか雨（強）",
  95: "雷雨",
}

def geocode(name: str, lang: str = "ja") -> Optional[tuple[float, float, str]]:
  """都市名から緯度経度情報を取得する。

  Args:
    name (str): 検索する都市名
    lang (str, optional): 結果の言語. デフォルトは "ja"

  Returns:
    Optional[tuple[float, float, str]]: (緯度, 経度, 場所のラベル)のタプル。
      見つからない場合はNone
  """
  url = "https://geocoding-api.open-meteo.com/v1/search"
  params = {"name": name, "count": 1, "language": lang}
  try:
    res = requests.get(url, params=params, timeout=6)
    res.raise_for_status()
    data = res.json()
    results = data.get("results") or []
    if not results:
      return
    r = results[0]
    label = f'{r["name"]}, {r["country_code"]}'
    return float(r["latitude"]), float(r["longitude"]), label
  except requests.exceptions.RequestException as e:
    print("ジオコーディング失敗:", e)
    return

def fetch_weather(lat: float, lon: float, units: str, hours: int) -> dict:
  """指定された座標の天気情報をOpen-Meteo APIから取得する。

  Args:
    lat (float): 緯度
    lon (float): 経度
    units (str): 温度単位 ("c" または "f")
    hours (int): 取得する時間予報の時間数

  Returns:
    dict: APIレスポンスの JSON データ

  Raises:
    SystemExit: API リクエストが失敗した場合
  """
  url = "https://api.open-meteo.com/v1/forecast"
  params = {
    "latitude": lat,
    "longitude": lon,
    "current_weather": True,
    "hourly": "temperature_2m",
    "timezone": "auto",
    "daily": "temperature_2m_max,temperature_2m_min",
  }
  if units == "f":
    params["temperature_unit"] = "fahrenheit"
  try:
    res = requests.get(url, params=params, timeout=6)
    res.raise_for_status()
    return res.json()
  except requests.exceptions.RequestException as e:
    print("天気取得に失敗:", e)
    sys.exit(1)

def pick_next_hours(
  hourly_times: list[str],
  hourly_temps: list[float],
  now_iso: str,
  n: int
) -> list[tuple[str, float]]:
  """現在時刻から指定時間数分の気温データを抽出する。

  Args:
    hourly_times (list[str]): 時刻のリスト
    hourly_temps (list[float]): 気温のリスト
    now_iso (str): 現在時刻（ISO形式 例: "2025-11-07T21:00"）
    n (int): 取得する時間数

  Returns:
    list[tuple[str, float]]: (時刻, 気温)のタプルのリスト
  """
  # now_iso 例: "2025-11-07T21:00"
  target = now_iso[:13] + ":00"
  i = bisect.bisect_left(hourly_times, target)
  end = min(i + n, len(hourly_times))
  return list(zip(hourly_times[i:end], hourly_temps[i:end]))

def format_unit(units: str) -> str:
  """温度単位の表示形式を返す。

  Args:
    units (str): 温度単位 ("c" または "f")

  Returns:
    str: 表示用の単位文字列（"°C" または "°F"）
  """
  return "°C" if units == "c" else "°F"

def main() -> None:
  """CLIのメインエントリーポイント。

  コマンドライン引数をパースし、天気情報を取得して表示する。
  都市名または緯度経度から現在の天気と時間予報（オプション）を表示する。
  """
  parser = argparse.ArgumentParser(description="Open-Meteo の現在天気と時間予報を表示するCLI（都市名/緯度経度対応）")
  parser.add_argument("query", nargs="?", default="福岡", help="都市名（例: tokyo, fukuoka）。--lat/--lon 指定時は無視")
  parser.add_argument("--lat", type=float, help="緯度を直接指定")
  parser.add_argument("--lon", type=float, help="経度を直接指定")
  parser.add_argument("--units", choices=["c", "f"], default="c", help="温度単位 c=摂氏, f=華氏（デフォルト: c）")
  parser.add_argument("--hourly", type=int, default=0, help="次のN時間の気温を表示（例: --hourly 12）")
  parser.add_argument("--lang", default="ja", help="ジオコーディング言語（デフォルト: ja）")
  args = parser.parse_args()

  if args.lat is not None and args.lon is not None:
    lat, lon, label = args.lat, args.lon, f"({args.lat}, {args.lon})"
  else:
    geo = geocode(args.query, lang=args.lang)
    if not geo:
      print(f"都市が見つかりませんでした: {args.query}")
      sys.exit(1)
    lat, lon, label = geo

  data = fetch_weather(lat, lon, args.units, args.hourly)

  cw = data["current_weather"]
  unit = format_unit(args.units)
  code = int(cw.get("weathercode", -1))
  now_local = cw["time"]
  j_weather = WEATHER_MAP.get(code, "不明")

  daily = data.get("daily", {})
  tmin = daily.get("temperature_2m_min", [None])[0]
  tmax = daily.get("temperature_2m_max", [None])[0]

  print(f"=== {label} の現在の天気 === ")
  print(f"時刻: {now_local}")
  print(f"気温: {cw['temperature']}{unit}")
  print(f"風速: {cw['windspeed']} m/s")
  if tmin is not None and tmax is not None:
    print(f"今日の最小/最大: {tmin}{unit} / {tmax}{unit}")
  print(f"天気: {j_weather}")
  if args.hourly > 0 and "hourly" in data:
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    # 現地タイムゾーンの現在時刻ISO(分以下切り捨て)
    now_iso = dt.datetime.fromisoformat(now_local).strftime("%Y-%m-%dT%H:%M")
    rows = pick_next_hours(times, temps, now_iso, args.hourly)
    print("\n--- 時間予報(気温) ---")
    for t, v in rows:
      hhmm = t.replace("T", " ")
      print(f"{hhmm}: {v}{unit}")

if __name__ == "__main__":
  main()
