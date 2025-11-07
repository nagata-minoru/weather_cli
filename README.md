# weather_cli

`weather_cli` は Open-Meteo の無料 API を利用して、
指定した地域（デフォルトは福岡市）の現在の天気を取得する
シンプルな Python コマンドラインツールです。

学習目的:
- requests を使った API 通信
- uv による仮想環境管理
- JSON の扱い

---

## ✅ 必要環境

- Python 3.10 以上
- uv（高速パッケージ管理ツール）

uv が未インストールの場合:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## ✅ プロジェクトのセットアップ

このプロジェクトは uv を使って構築しています。

```bash
uv venv
uv init
uv add requests
```

---

## ✅ 使い方

仮想環境内の Python で `weather.py` を実行します。

```bash
uv run python weather.py
```

実行例:

```
=== 現在の福岡の天気 ===
気温: 15.8℃
風速: 6.1 m/s
天気: 快晴
```

---

## ✅ コマンドライン引数（新機能）

`weather.py` はコマンドライン引数に対応し、より柔軟に天気情報を取得できます。

- 都市名指定例:

```bash
uv run python weather.py tokyo
```

- 緯度経度指定:

```bash
uv run python weather.py --lat 35.6895 --lon 139.6917
```

- 温度単位切替（摂氏または華氏）:

```bash
uv run python weather.py --units f
```

- 時間ごとの予報表示（直近N時間）:

```bash
uv run python weather.py --hourly 5
```

これらのオプションを組み合わせて使うことも可能です。

---

## ✅ 天気情報の取得方法について

Open-Meteo API を使用しています：

https://open-meteo.com/en/docs

さらに、都市名から緯度経度を取得するためにジオコーディング API も利用しています：

https://geocoding-api.open-meteo.com/v1/search

送信する主なパラメータ:
- latitude（緯度）
- longitude（経度）
- current_weather=True

レスポンスは JSON 形式で返され、気温・風速・天気コードなどが含まれます。

---

## ✅ 天気コード（weathercode）について

API から返される `weathercode` を日本語表記に変換するための辞書例:

```python
weather_map = {
  0: "快晴",
  1: "晴れ",
  2: "薄曇り",
  3: "曇り",
  45: "霧",
  48: "霧雨（霧氷）",
  51: "小雨（弱）",
  61: "雨（弱）",
  71: "雪（弱）",
  80: "にわか雨",
  95: "雷雨",
  # 必要に応じて追加してください
}
```

---

## ✅ ファイル構成

```
weather_cli/
├── weather.py       # メインスクリプト
├── pyproject.toml   # uv のプロジェクト設定
├── uv.lock          # 依存関係ロック
└── README.md        # このファイル
```

---

## ✅ ライセンス

MIT License
著者: 永田（個人学習用プロジェクト）
