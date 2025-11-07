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

weather_map = {
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

try:
  res = requests.get(url, params=params, timeout=5)
  res.raise_for_status()
  data = res.json()

  temp = data["current_weather"]["temperature"]
  wind = data["current_weather"]["windspeed"]
  code = data["current_weather"]["weathercode"]
  j_weather = weather_map.get(code, "不明")

  print("=== 現在の福岡の天気 ===")
  print(f"気温: {temp}℃")
  print(f"風速: {wind} m/s")
  print(f"天気: {j_weather}")

except requests.exceptions.RequestException as e:
  print("通信エラー:", e)
