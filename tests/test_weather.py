import sys

import pytest
import requests

import weather

class FakeResponse:
  """requests.get が返すレスポンスの代わりに使うクラス。"""

  def __init__(self, data: dict, status_error: Exception | None = None) -> None:
    """レスポンスを作る。

    Args:
      data (dict): json() が返すデータ
      status_error (Exception | None): raise_for_status() で投げる例外。None なら投げない
    """
    self.data = data
    self.status_error = status_error

  def raise_for_status(self) -> None:
    """status_error が設定されていれば投げる。

    Returns:
      None
    """
    if self.status_error:
      raise self.status_error

  def json(self) -> dict:
    """設定されたデータを返す。

    Returns:
      dict: コンストラクタで渡したデータ
    """
    return self.data

class FakeGet:
  """requests.get の代わりに使い、呼ばれたときの引数を記録するクラス。"""

  def __init__(self, *responses: FakeResponse | Exception) -> None:
    """呼ばれた順に返すレスポンスを設定する。

    Args:
      *responses (FakeResponse | Exception): 返すレスポンス。例外なら投げる
    """
    self.responses = list(responses)
    self.calls = []

  def __call__(self, url: str, params: dict, timeout: float) -> FakeResponse:
    """引数を記録し、次のレスポンスを返す。

    Args:
      url (str): リクエスト先の URL
      params (dict): クエリパラメータ
      timeout (float): タイムアウト秒数

    Returns:
      FakeResponse: 設定されたレスポンス
    """
    self.calls.append({"url": url, "params": params, "timeout": timeout})
    res = self.responses.pop(0)
    if isinstance(res, Exception):
      raise res
    return res

def weather_data(code: int = 0, daily: bool = True) -> dict:
  """天気 API のレスポンスに似たデータを作る。

  Args:
    code (int): 天気コード
    daily (bool): daily（最小/最大気温）を含めるか

  Returns:
    dict: 天気 API のレスポンスに似たデータ
  """
  data = {
    "current_weather": {
      "time": "2026-10-25T18:00",
      "temperature": 19.2,
      "windspeed": 0.58,
      "weathercode": code,
    },
    "hourly": {
      "time": ["2026-10-25T17:00", "2026-10-25T18:00", "2026-10-25T19:00", "2026-10-25T20:00"],
      "temperature_2m": [19.5, 19.2, 19.1, 18.8],
    },
  }
  if daily:
    data["daily"] = {"temperature_2m_min": [16.1], "temperature_2m_max": [27.2]}
  return data

def run_main(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
  """コマンドライン引数を設定して main() を実行する。

  Args:
    monkeypatch (pytest.MonkeyPatch): pytest の monkeypatch
    *args (str): コマンドライン引数

  Returns:
    None
  """
  monkeypatch.setattr(sys, "argv", ["weather.py", *args])
  weather.main()

@pytest.mark.parametrize("units, expected", [("c", "°C"), ("f", "°F")])
def test_format_unit(units, expected):
  assert weather.format_unit(units) == expected

class TestPickNextHours:
  """pick_next_hours のテスト。"""

  times = ["2026-10-25T17:00", "2026-10-25T18:00", "2026-10-25T19:00", "2026-10-25T20:00"]
  temps = [19.5, 19.2, 19.1, 18.8]

  def test_returns_n_hours_from_now(self):
    rows = weather.pick_next_hours(self.times, self.temps, "2026-10-25T18:00", 2)
    assert rows == [("2026-10-25T18:00", 19.2), ("2026-10-25T19:00", 19.1)]

  def test_truncates_minutes(self):
    rows = weather.pick_next_hours(self.times, self.temps, "2026-10-25T18:45", 1)
    assert rows == [("2026-10-25T18:00", 19.2)]

  def test_stops_at_end_of_data(self):
    rows = weather.pick_next_hours(self.times, self.temps, "2026-10-25T19:00", 10)
    assert rows == [("2026-10-25T19:00", 19.1), ("2026-10-25T20:00", 18.8)]

  def test_returns_empty_after_last_hour(self):
    assert weather.pick_next_hours(self.times, self.temps, "2026-10-25T21:00", 3) == []

  def test_zero_hours(self):
    assert weather.pick_next_hours(self.times, self.temps, "2026-10-25T18:00", 0) == []

class TestGeocode:
  """geocode のテスト。"""

  def test_returns_lat_lon_label(self, monkeypatch):
    fake = FakeGet(FakeResponse({
      "results": [{
        "name": "東京都", "country_code": "JP", "latitude": "35.69", "longitude": "139.69",
      }, {
        "name": "Tokyo", "country_code": "US", "latitude": "0", "longitude": "0",
      }],
    }))
    monkeypatch.setattr(weather.requests, "get", fake)

    assert weather.geocode("tokyo", lang="en") == (35.69, 139.69, "東京都, JP")
    assert fake.calls[0]["params"] == {"name": "tokyo", "count": 1, "language": "en"}

  @pytest.mark.parametrize("data", [{"results": []}, {}])
  def test_returns_none_when_not_found(self, monkeypatch, data):
    monkeypatch.setattr(weather.requests, "get", FakeGet(FakeResponse(data)))
    assert weather.geocode("nowhere") is None

  def test_returns_none_on_request_error(self, monkeypatch, capsys):
    monkeypatch.setattr(weather.requests, "get", FakeGet(requests.exceptions.ConnectionError("down")))

    assert weather.geocode("tokyo") is None
    assert "ジオコーディング失敗" in capsys.readouterr().out

  def test_returns_none_on_http_error(self, monkeypatch):
    res = FakeResponse({}, status_error=requests.exceptions.HTTPError("500"))
    monkeypatch.setattr(weather.requests, "get", FakeGet(res))
    assert weather.geocode("tokyo") is None

class TestFetchWeather:
  """fetch_weather のテスト。"""

  def test_requests_celsius_and_meters_per_second(self, monkeypatch):
    fake = FakeGet(FakeResponse({"ok": True}))
    monkeypatch.setattr(weather.requests, "get", fake)

    assert weather.fetch_weather(33.5, 130.4, "c", 0) == {"ok": True}
    params = fake.calls[0]["params"]
    assert params["latitude"] == 33.5
    assert params["longitude"] == 130.4
    assert params["windspeed_unit"] == "ms"
    assert "temperature_unit" not in params

  def test_requests_fahrenheit(self, monkeypatch):
    fake = FakeGet(FakeResponse({}))
    monkeypatch.setattr(weather.requests, "get", fake)

    weather.fetch_weather(33.5, 130.4, "f", 0)
    assert fake.calls[0]["params"]["temperature_unit"] == "fahrenheit"

  def test_exits_on_request_error(self, monkeypatch, capsys):
    monkeypatch.setattr(weather.requests, "get", FakeGet(requests.exceptions.Timeout("slow")))

    with pytest.raises(SystemExit) as e:
      weather.fetch_weather(33.5, 130.4, "c", 0)
    assert e.value.code == 1
    assert "天気取得に失敗" in capsys.readouterr().out

class TestMain:
  """main のテスト。"""

  def test_uses_lat_lon_without_geocoding(self, monkeypatch, capsys):
    fake = FakeGet(FakeResponse(weather_data(code=55)))
    monkeypatch.setattr(weather.requests, "get", fake)

    run_main(monkeypatch, "--lat", "33.59", "--lon", "130.4")

    assert len(fake.calls) == 1
    assert fake.calls[0]["url"] == "https://api.open-meteo.com/v1/forecast"
    out = capsys.readouterr().out
    assert "=== (33.59, 130.4) の現在の天気 ===" in out
    assert "時刻: 2026-10-25T18:00" in out
    assert "気温: 19.2°C" in out
    assert "風速: 0.58 m/s" in out
    assert "今日の最小/最大: 16.1°C / 27.2°C" in out
    assert "天気: 霧雨（強）" in out
    assert "時間予報" not in out

  def test_geocodes_city_name(self, monkeypatch, capsys):
    geo = FakeResponse({
      "results": [{"name": "東京都", "country_code": "JP", "latitude": 35.69, "longitude": 139.69}],
    })
    fake = FakeGet(geo, FakeResponse(weather_data()))
    monkeypatch.setattr(weather.requests, "get", fake)

    run_main(monkeypatch, "tokyo")

    assert fake.calls[1]["params"]["latitude"] == 35.69
    assert fake.calls[1]["params"]["longitude"] == 139.69
    assert "=== 東京都, JP の現在の天気 ===" in capsys.readouterr().out

  def test_exits_when_city_not_found(self, monkeypatch, capsys):
    monkeypatch.setattr(weather.requests, "get", FakeGet(FakeResponse({"results": []})))

    with pytest.raises(SystemExit) as e:
      run_main(monkeypatch, "nowhere")
    assert e.value.code == 1
    assert "都市が見つかりませんでした: nowhere" in capsys.readouterr().out

  def test_shows_hourly_forecast(self, monkeypatch, capsys):
    monkeypatch.setattr(weather.requests, "get", FakeGet(FakeResponse(weather_data())))

    run_main(monkeypatch, "--lat", "1", "--lon", "2", "--hourly", "2", "--units", "f")

    out = capsys.readouterr().out
    assert "気温: 19.2°F" in out
    assert "--- 時間予報(気温) ---\n2026-10-25 18:00: 19.2°F\n2026-10-25 19:00: 19.1°F\n" in out

  def test_unknown_code_and_missing_daily(self, monkeypatch, capsys):
    monkeypatch.setattr(weather.requests, "get", FakeGet(FakeResponse(weather_data(code=999, daily=False))))

    run_main(monkeypatch, "--lat", "1", "--lon", "2")

    out = capsys.readouterr().out
    assert "天気: 不明" in out
    assert "今日の最小/最大" not in out
