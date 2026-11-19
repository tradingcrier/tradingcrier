# Методичка: свой источник данных в TradingCrier (режим разработчика)

> **Служебный документ.** Не входит в сборку приложения (не объявлен в `assets`), в приложении и в `store/` на него нет ссылок. Распространяется владельцем вручную.
> Схема конфига — `tradingcrier.source/2` (см. `PLAN_V1_3_FOR_SONNET.md`, раздел 2; файлы `/1` читаются, экспорт всегда `/2`). Эталонные файлы спек лежат в `sources/` вне сборки. При изменении схемы обновить этот файл.
> Черновик от 14.11.2026. Рецепты собраны по публичной документации; пометка **[сверить]** — поле не проверено живым запросом, перед раздачей пользователям проверить через «Проверить подключение».

---

## 1. Как это работает

Приложение — HTTP-клиент. Вы описываете в JSON, **куда** слать запрос, **как** приложить ключ и **где** в ответе лежат свечи и цена. Приложение подставляет символ, таймфрейм и окно времени, отправляет запрос со своего телефона напрямую на API и разбирает ответ.

- Ключ хранится только на телефоне (Android Keystore), не попадает в экспорт конфига и в резервные копии.
- Выполняются только запросы рыночных данных; адреса с `order`, `account`, `portfolio`, `withdraw`, `transfer`, `cancel`, `operation` и т. п. приложение не сохранит.
- Свой источник доступен в пробном периоде.

## 2. Безопасность ключа — прочитать до начала

1. **Выпускайте ключ только для чтения** (read-only). У всех описанных ниже API такой тип есть.
2. Никогда не вставляйте значение ключа в JSON — только в поле «Ключ доступа» на вкладке «Поля». В JSON ключ обозначается плейсхолдером `{{secret:имя}}`.
3. Если ключ мог утечь — отзовите его в личном кабинете и выпустите новый.
4. Срок жизни ключей ограничен (от месяца до года) — поставьте себе напоминание.

## 3. Пошагово

1. «Настройки» → «Источник данных» → «Добавить свой источник» → принять условия.
2. Вкладка «JSON» → «Вставить из буфера» → вставить рецепт из раздела 5.
3. Вкладка «Поля» → «Доступ» → вписать значение ключа.
4. «Инструменты» — добавить нужные бумаги/пары (символ + название; параметры — если требует рецепт).
5. «Проверить подключение» — все шаги должны быть ✓. Если ✗ — см. раздел 6.
6. «Сохранить» → выбрать источник → закрепить инструменты через поиск.

## 4. Справочник плейсхолдеров (кратко)

| Плейсхолдер | Что подставится |
|---|---|
| `{{symbol}}` / `{{symbol:raw}}` | символ инструмента (URL-кодированный / как есть) |
| `{{param:NAME}}` | параметр инструмента из `instruments[].params` |
| `{{interval}}` | значение из `timeframes` для текущего таймфрейма |
| `{{limit}}` / `"{{limit:int}}"` | число свечей (строкой / числом в JSON-теле) |
| `{{from:ms\|s\|iso\|date}}`, `{{to:…}}` | границы окна, UTC |
| `{{secret:KEY}}` | ваш ключ из защищённого хранилища |
| `{{auth:token}}` | временный токен, полученный обменом |

Пустое значение таймфрейма (`""`) = таймфрейм на этом источнике недоступен.
Для рынков с торговыми сессиями и выходными ставьте `window.sessionFactor` 3–4 (иначе окно `from..to` вернёт меньше свечей, чем нужно графику).

---

## 5. Рецепты

### 5.1. T-Invest API (Т-Банк), REST

- Документация: `https://developer.tbank.ru/invest/` (REST-прокси над gRPC).
- Ключ: Т-Инвестиции → Настройки → Токены → **«Только для чтения»**. Живёт 3 месяца с последнего использования.
- Символ: `instrumentId` — FIGI, `instrument_uid` или `ТИКЕР_КЛАСС` (например `SBER_TQBR`).
- Цены приходят как `Quotation {units, nano}` — разбираются автоматически.
- Изменения за день в ответе нет — считается из дневных свечей.

```json
{
  "schema": "tradingcrier.source/2",
  "name": "Мой брокер",
  "version": "1.0.0",
  "minEngine": "1.3.0",
  "capabilities": { "candles": true, "quotes": "rest", "stream": false, "instruments": true },
  "identity": {
    "userAgentField": "",
    "appNameField": "appname",
    "appNameHeader": "x-app-name",
    "requiresAppName": ["sandbox"]
  },
  "environments": {
    "prod": { "baseUrl": "https://invest-public-api.tbank.ru/rest" },
    "sandbox": { "baseUrl": "https://sandbox-invest-public-api.tbank.ru/rest" }
  },
  "plugin": "",
  "baseUrl": "https://invest-public-api.tbank.ru/rest",
  "secrets": [
    { "key": "token", "label": "Токен только для чтения" },
    { "key": "appname", "label": "Название приложения (своя метка)" }
  ],
  "auth": {
    "type": "header",
    "header": { "name": "Authorization", "value": "Bearer {{secret:token}}" }
  },
  "headers": { "Content-Type": "application/json" },
  "timeframes": {
    "m1": "CANDLE_INTERVAL_1_MIN", "m5": "CANDLE_INTERVAL_5_MIN", "m15": "CANDLE_INTERVAL_15_MIN",
    "h1": "CANDLE_INTERVAL_HOUR", "h4": "CANDLE_INTERVAL_4_HOUR", "d1": "CANDLE_INTERVAL_DAY"
  },
  "candles": {
    "request": {
      "method": "POST",
      "path": "/tinkoff.public.invest.api.contract.v1.MarketDataService/GetCandles",
      "bodyType": "json",
      "body": {
        "instrumentId": "{{symbol:raw}}",
        "from": "{{from:iso}}",
        "to": "{{to:iso}}",
        "interval": "{{interval}}"
      }
    },
    "window": { "mode": "range", "sessionFactor": 3, "maxCandles": 2400 },
    "pagination": { "type": "none" },
    "response": {
      "itemsPath": "candles",
      "rowFormat": "object",
      "fields": { "time": "time", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume" },
      "time": { "format": "iso8601" },
      "price": { "format": "units_nano" }
    }
  },
  "ticker": {
    "mode": "request",
    "request": {
      "method": "POST",
      "path": "/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices",
      "bodyType": "json",
      "body": { "instrumentId": ["{{symbol:raw}}"] }
    },
    "response": { "itemPath": "lastPrices.0", "lastPrice": "price" }
  },
  "instruments": {
    "request": {
      "method": "POST",
      "path": "/tinkoff.public.invest.api.contract.v1.InstrumentsService/Shares",
      "bodyType": "json",
      "body": { "instrumentStatus": "INSTRUMENT_STATUS_BASE" }
    },
    "response": {
      "itemsPath": "instruments",
      "fields": {
        "symbol": "figi", "name": "name", "isin": "isin", "figi": "figi",
        "type": "", "lot": "lot", "currency": "currency", "board": "classCode"
      }
    },
    "refreshPolicy": "weekly",
    "items": []
  },
  "errors": { "okPath": "", "okValues": [] },
  "limits": {
    "minIntervalMs": 250,
    "maxConcurrent": 2,
    "retry": { "maxAttempts": 3, "baseDelayMs": 500, "factor": 2 }
  }
}
```

Песочница: `https://sandbox-invest-public-api.tbank.ru/rest` (нужен sandbox-токен). Ошибка `40003` — токен неверный или истёк.

### 5.2. Finam Trade API, REST

- Документация: `https://api.finam.ru/docs/rest/`.
- Ключ: портал Trade API → Токены → secret-ключ (**режим readonly**). Из него запросом `POST /v1/sessions` получается временный токен (JWT).
- Временный токен прикладывается в заголовок `Authorization` **без** `Bearer`.
- Символ: `ТИКЕР@MIC`, например `SBER@MISX`. Символ содержит `@` — используем `{{symbol:raw}}` в пути **[сверить]**, принимает ли сервер `%40`.
- Числа приходят как `{"value": "…"}` — разбираются автоматически.
- Глубина истории: M1 — 7 дней, M5…H4 — 30 дней, D — 365 дней.

```json
{
  "schema": "tradingcrier.source/2",
  "name": "Мой брокер",
  "baseUrl": "https://api.finam.ru",
  "secrets": [{ "key": "secret", "label": "Secret-ключ (readonly)" }],
  "auth": {
    "type": "exchange",
    "exchange": {
      "request": { "method": "POST", "url": "/v1/sessions", "bodyType": "json", "body": { "secret": "{{secret:secret}}" } },
      "tokenPath": "token",
      "ttlSeconds": 600,
      "apply": { "name": "Authorization", "value": "{{auth:token}}" }
    }
  },
  "headers": {},
  "timeframes": {
    "m1": "TIME_FRAME_M1", "m5": "TIME_FRAME_M5", "m15": "TIME_FRAME_M15",
    "h1": "TIME_FRAME_H1", "h4": "TIME_FRAME_H4", "d1": "TIME_FRAME_D"
  },
  "candles": {
    "request": {
      "method": "GET",
      "path": "/v1/instruments/{{symbol:raw}}/bars",
      "query": {
        "timeframe": "{{interval}}",
        "interval.start_time": "{{from:iso}}",
        "interval.end_time": "{{to:iso}}"
      }
    },
    "window": { "mode": "range", "sessionFactor": 3 },
    "response": {
      "itemsPath": "bars",
      "rowFormat": "object",
      "fields": { "time": "timestamp", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume" },
      "time": { "format": "iso8601" }
    }
  },
  "ticker": {
    "mode": "request",
    "request": { "method": "GET", "path": "/v1/instruments/{{symbol:raw}}/quotes/latest" },
    "response": { "itemPath": "quote", "lastPrice": "last" }
  },
  "instruments": [{ "symbol": "SBER@MISX", "display": "SBER", "params": {} }],
  "limits": { "minIntervalMs": 300, "maxConcurrent": 2 }
}
```

**[сверить]:** срок жизни временного токена (ориентироваться на `expires_at` из `POST /v1/sessions/details`; если поле появится в ответе `/v1/sessions` — указать `expiresInPath`); имя поля процента изменения в котировке (если есть — добавить `changePct`).

### 5.3. ALOR OpenAPI

- Документация: `https://alor.dev/docs`.
- Ключ: портал разработчика → «Токены для доступа к API» → refresh-токен. **Внимание: у ALOR refresh-токен даёт полный доступ к счёту** (отдельного read-only токена на момент написания нет **[сверить]**). Рекомендуйте пользователям вариант без ключа ниже.
- Без авторизации `/md/v2/history` тоже отвечает, но с задержкой 15 минут — для алертов «по закрытию» на ТФ ≥ 1ч этого часто достаточно. **Безопасный вариант — `auth.type: "none"`.**
- Время в ответе — секунды Unix. Ответ котировок — массив в корне.

Вариант без ключа (данные с задержкой):

```json
{
  "schema": "tradingcrier.source/2",
  "name": "Мой брокер (с задержкой)",
  "baseUrl": "https://api.alor.ru",
  "secrets": [],
  "auth": { "type": "none" },
  "headers": {},
  "timeframes": { "m1": "60", "m5": "300", "m15": "900", "h1": "3600", "h4": "14400", "d1": "D" },
  "candles": {
    "request": {
      "method": "GET",
      "path": "/md/v2/history",
      "query": {
        "symbol": "{{symbol}}",
        "exchange": "{{param:exchange}}",
        "tf": "{{interval}}",
        "from": "{{from:s}}",
        "to": "{{to:s}}"
      }
    },
    "window": { "mode": "range", "sessionFactor": 3 },
    "response": {
      "itemsPath": "history",
      "rowFormat": "object",
      "fields": { "time": "time", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume" },
      "time": { "format": "s" }
    }
  },
  "ticker": { "mode": "fromCandles" },
  "instruments": [{ "symbol": "SBER", "display": "SBER", "params": { "exchange": "MOEX" } }],
  "limits": { "minIntervalMs": 200, "maxConcurrent": 2 }
}
```

Вариант с ключом (данные без задержки) — заменить `secrets`, `auth`, `ticker`:

```json
{
  "secrets": [{ "key": "refresh", "label": "Refresh-токен" }],
  "auth": {
    "type": "exchange",
    "exchange": {
      "request": { "method": "POST", "url": "https://oauth.alor.ru/refresh", "bodyType": "none", "body": null,
                   "headers": {}, "query": { "token": "{{secret:refresh}}" } },
      "tokenPath": "AccessToken",
      "ttlSeconds": 1500,
      "apply": { "name": "Authorization", "value": "Bearer {{auth:token}}" }
    }
  },
  "ticker": {
    "mode": "request",
    "request": { "method": "GET", "path": "/md/v2/Securities/{{param:exchange}}:{{symbol}}/quotes" },
    "response": { "itemPath": "0", "lastPrice": "last_price", "changePct": "change_percent" }
  }
}
```

**[сверить]:** значение `d1` для `tf` (`D` или `86400`); срок жизни access-токена (указан 1500 с с запасом).

### 5.4. БКС Trade API

- Документация: `https://trade-api.bcs.ru`.
- Ключ: БКС Мир инвестиций (веб) → Профиль → счёт → «Токены API» → **«Только для чтения»**. Refresh-токен живёт 90 суток, access-токен — 24 часа.
- Обмен: форма `application/x-www-form-urlencoded`, `client_id=trade-api-read`.
- Инструмент задаётся парой «код класса + тикер» → `classCode` в `params`.
- До 1440 свечей за запрос.

```json
{
  "schema": "tradingcrier.source/2",
  "name": "Мой брокер",
  "baseUrl": "https://be.broker.ru/trade-api-market-data-connector/api/v1",
  "secrets": [{ "key": "refresh", "label": "Refresh-токен (только чтение)" }],
  "auth": {
    "type": "exchange",
    "exchange": {
      "request": {
        "method": "POST",
        "url": "https://be.broker.ru/trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token",
        "bodyType": "form",
        "body": { "client_id": "trade-api-read", "grant_type": "refresh_token", "refresh_token": "{{secret:refresh}}" }
      },
      "tokenPath": "access_token",
      "expiresInPath": "expires_in",
      "apply": { "name": "Authorization", "value": "Bearer {{auth:token}}" }
    }
  },
  "headers": {},
  "timeframes": { "m1": "M1", "m5": "M5", "m15": "M15", "h1": "H1", "h4": "H4", "d1": "D" },
  "candles": {
    "request": {
      "method": "GET",
      "path": "/candles-chart",
      "query": {
        "classCode": "{{param:classCode}}",
        "ticker": "{{symbol}}",
        "startDate": "{{from:iso}}",
        "endDate": "{{to:iso}}",
        "timeFrame": "{{interval}}"
      }
    },
    "window": { "mode": "range", "sessionFactor": 3, "maxCandles": 1440 },
    "response": {
      "itemsPath": "bars",
      "rowFormat": "object",
      "fields": { "time": "time", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume" },
      "time": { "format": "iso8601" }
    }
  },
  "ticker": { "mode": "fromCandles" },
  "instruments": [{ "symbol": "SBER", "display": "SBER", "params": { "classCode": "TQBR" } }],
  "limits": { "minIntervalMs": 350, "maxConcurrent": 2 }
}
```

**[сверить]:** имена полей внутри `bars[]` (`time`/`dateTime`), точное значение `timeFrame` для дня; REST-метод котировки (если есть — перевести `ticker.mode` в `request`).

### 5.5. Московская биржа — ISS (публичный, с задержкой) и ALGOPACK (с ключом)

- Документация: `https://iss.moex.com/iss/reference/`, ALGOPACK — `https://moexalgo.github.io/`.
- Без ключа: `https://iss.moex.com/iss` — данные с задержкой 15 минут.
- С ключом ALGOPACK: `https://apim.moex.com/iss` + `Authorization: Bearer <APIKEY>` (тариф «Стартовый» бесплатный, но тоже с задержкой; онлайн — платные тарифы).
- Формат **columnar**: `{"candles": {"columns": [...], "data": [[...], ...]}}`.
- Время — московское строкой `yyyy-MM-dd HH:mm:ss` → `pattern` + `utcOffset: +03:00`.
- Интервалы ISS: `1`, `10`, `60`, `24` (день), `7`, `31`, `4`. **5м, 15м и 4ч нет** → оставить пустыми.
- ISS отдаёт до 500 строк **от начала окна** — поэтому окно должно быть узким: `window.mode: range`, `sessionFactor` 2–3 (не больше).

```json
{
  "schema": "tradingcrier.source/2",
  "name": "Биржевые данные (с задержкой)",
  "version": "1.0.0",
  "minEngine": "1.3.0",
  "capabilities": { "candles": true, "quotes": "rest", "stream": false, "instruments": true },
  "identity": { "userAgentField": "", "appNameField": "", "requiresAppName": [] },
  "environments": {},
  "plugin": "",
  "baseUrl": "https://iss.moex.com/iss",
  "secrets": [],
  "auth": { "type": "none" },
  "headers": {},
  "timeframes": { "m1": "1", "m5": "", "m15": "", "h1": "60", "h4": "", "d1": "24" },
  "candles": {
    "request": {
      "method": "GET",
      "path": "/engines/stock/markets/shares/boards/TQBR/securities/{{symbol}}/candles.json",
      "query": {
        "interval": "{{interval}}",
        "from": "{{from:date}}",
        "iss.meta": "off",
        "iss.only": "candles"
      }
    },
    "window": { "mode": "range", "sessionFactor": 3, "maxCandles": 500 },
    "pagination": { "type": "offset", "offsetParam": "start", "maxPages": 10 },
    "response": {
      "itemsPath": "candles.data",
      "rowFormat": "columnar",
      "columnsPath": "candles.columns",
      "fields": { "time": "begin", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume" },
      "time": { "format": "pattern", "pattern": "yyyy-MM-dd HH:mm:ss", "utcOffset": "+03:00" },
      "price": { "format": "raw" }
    }
  },
  "ticker": {
    "mode": "request",
    "request": {
      "method": "GET",
      "path": "/engines/stock/markets/shares/boards/TQBR/securities/{{symbol}}.json",
      "query": { "iss.meta": "off", "iss.only": "marketdata", "marketdata.columns": "LAST,LASTTOPREVPRICE" }
    },
    "response": { "itemPath": "marketdata.data.0", "columnsPath": "marketdata.columns", "lastPrice": "LAST", "changePct": "LASTTOPREVPRICE" }
  },
  "tickers": {
    "request": {
      "method": "GET",
      "path": "/engines/stock/markets/shares/boards/TQBR/securities.json",
      "query": { "iss.meta": "off", "iss.only": "marketdata", "marketdata.columns": "SECID,LAST,LASTTOPREVPRICE,VALTODAY,HIGH,LOW" }
    },
    "response": {
      "itemsPath": "marketdata.data",
      "columnsPath": "marketdata.columns",
      "fields": { "symbol": "SECID", "lastPrice": "LAST", "changePct": "LASTTOPREVPRICE", "prevClose": "", "volume24h": "VALTODAY", "high24h": "HIGH", "low24h": "LOW" }
    }
  },
  "instruments": {
    "request": {
      "method": "GET",
      "path": "/engines/stock/markets/shares/boards/TQBR/securities.json",
      "query": {
        "iss.meta": "off",
        "iss.only": "securities",
        "securities.columns": "SECID,SHORTNAME,ISIN,LOTSIZE,CURRENCYID"
      }
    },
    "response": {
      "itemsPath": "securities.data",
      "columnsPath": "securities.columns",
      "fields": {
        "symbol": "SECID", "name": "SHORTNAME", "isin": "ISIN", "figi": "",
        "type": "", "lot": "LOTSIZE", "currency": "CURRENCYID"
      }
    },
    "refreshPolicy": "daily",
    "items": []
  },
  "errors": { "okPath": "", "okValues": [] },
  "limits": {
    "minIntervalMs": 300,
    "maxConcurrent": 2,
    "retry": { "maxAttempts": 2, "baseDelayMs": 500, "factor": 2 }
  }
}
```

Для ALGOPACK: `baseUrl` → `https://apim.moex.com/iss`, добавить
`"secrets": [{"key":"apikey","label":"APIKEY"}]`, `"auth": {"type":"header","header":{"name":"Authorization","value":"Bearer {{secret:apikey}}"}}`.

Площадки: акции — `stock/shares/TQBR`, фьючерсы — `futures/forts/RFUD`, валюта — `currency/selt/CETS`, индексы — `stock/index/SNDX`.
**[сверить]:** `LAST` вне торговой сессии бывает `null` — тогда тикер берётся из свечей (движок должен переходить на `fromCandles` при `null`).

### 5.6. Любой другой REST API — как составить конфиг самому

1. Найдите в документации метод **исторических свечей** и метод **последней цены** (если нет — `ticker.mode: fromCandles`).
2. Выполните запрос в Postman/curl, сохраните пример ответа.
3. `itemsPath` — путь до массива свечей; `rowFormat` — что внутри массива (массивы / объекты / колонки отдельно).
4. `fields` — индексы (`"0"`, `"1"`…) или имена полей; `time.format` — по виду времени (13 цифр — `ms`, 10 — `s`, `2024-01-01T…Z` — `iso8601`, иное — `pattern`).
5. Таймфреймы — значения параметра интервала из документации; чего нет — `""`.
6. Окно: если API принимает `limit` — `mode: limit`; если только даты — `mode: range`.
7. Признак ошибки в теле (если API всегда отвечает 200) — `errors.okPath`/`okValues`.

---

## 6. Частые ошибки (экран «Проверить подключение»)

| Симптом | Причина / что сделать |
|---|---|
| «Адрес похож на операцию со счётом» | В пути есть `order`/`account`/… — используйте только методы рыночных данных |
| Шаг «Токен» ✗, HTTP 401 | Неверный или истёкший ключ; ключ выпущен для песочницы, а адрес боевой (или наоборот) |
| Шаг «Свечи» ✗, HTTP 400/404 | Неверный символ или параметр инструмента; таймфрейм записан не в том формате |
| Свечей 0 | Окно `from..to` попало на выходные/ночь — увеличьте `sessionFactor`; инструмент не торгуется |
| Свечей меньше, чем нужно графику | Увеличьте `sessionFactor`; проверьте `maxCandles` |
| Время свечей сдвинуто на 3 часа | Время в ответе местное — укажите `utcOffset` |
| «Ошибка разбора» | Неверный `itemsPath`/`fields`; посмотрите сниппет ответа внизу экрана проверки |
| HTTP 429 | Слишком частые запросы — увеличьте `limits.minIntervalMs`, закрепите меньше инструментов |
| После переустановки «Введите ключ заново» | Ключи намеренно не восстанавливаются из резервной копии |

## 7. Что приложение НЕ делает

- Не выставляет и не отменяет заявки, не читает счёт и портфель.
- Не отправляет ваш ключ, адрес API и конфиг разработчику.
- Не проверяет и не гарантирует данные подключённого источника.

## 8. Схема `/2`: что добавилось

| Поле | Назначение |
|---|---|
| `version`, `minEngine` | версия спеки; минимальная версия движка (если приложение старее — установка блокируется) |
| `capabilities` | `candles`, `quotes` (`rest` / `none`), `stream` (спекой не поддерживается — `false`), `instruments` |
| `candles.pagination` | `type`: `none` / `offset` / `cursor`; `limitParam`, `offsetParam`, `cursorParam`, `cursorPath`, `maxPages`. Плейсхолдеры `{{page:offset}}`, `{{page:cursor}}`. Для `offset` размер порции — `window.maxCandles` (или число свечей окна); стоп — короткая страница, `maxPages` или покрытое окно |
| `candles.response.price` | `format`: `raw` / `units_nano` / `value` / `scaled`; для `scaled` — `scale` или `scalePath` (множитель, который приходит в ответе); пустой `format` — автоопределение, как в `/1` |
| `limits.retry` | `maxAttempts`, `baseDelayMs`, `factor`: повтор только при сетевых ошибках и 5xx (не при 4xx и ошибках разбора); по умолчанию один запрос |
| `instruments` (объект) | endpoint справочника: `request`, `response.itemsPath` / `columnsPath` / `fields` (`symbol`, `name`, `isin`, `figi`, `type`, `lot`, `currency`; любые другие имена полей попадают в `params` инструмента и доступны как `{{param:…}}`), `refreshPolicy`: `manual` / `daily` / `weekly`. Массив `instruments[]` по-прежнему допустим |
| `tickers` (необязательно) | массовые котировки одним запросом (включают топ-листы и быстрые фильтры в поиске): `request`, `response.itemsPath` / `columnsPath` (для колоночных ответов) / `fields`: `symbol`, `lastPrice` (обязательны), `changePct`, `prevClose`, `volume24h`, `high24h`, `low24h`. Запрос без `{{symbol}}` — один на весь каталог. Если API требует перечислять символы в запросе, секцию не задавайте |
| `ticker.response.volume24h` / `high24h` / `low24h` | необязательные поля оборота и диапазона за 24 ч |
| `environments` | `prod` / `sandbox` со своим `baseUrl` (и `exchangeUrl` для обмена ключа); режим выбирается в проверке подключения |
| `identity` | `userAgentField`, `appNameField` — имена ключей из `secrets[]`, значения которых уходят в `User-Agent` и в заголовок `appNameHeader`; `requiresAppName` — режимы, где метка обязательна |
| `plugin` | имя встроенного адаптера (только из сборки приложения; пусто — чистая спека) |

**Метки.** Значение метки не должно быть похоже на служебное имя приложения — приложение такие значения не принимает. Указывайте собственную метку (например, название своей стратегии) или оставьте поле пустым.

**Установка.** Файл спеки (`.json`) загружается через «Источник данных» → «Загрузить файл спеки»: валидация → обязательная проверка подключения → сохранение. Спека с тем же `name` обновляет существующий источник (ключи и алерты сохраняются). Адрес каталога спек в настройках пуст по умолчанию; пока он пуст, приложение к каталогу не обращается.

**Данные.** История свечей и справочники хранятся на телефоне (SQLite); окно запроса строится от последней сохранённой свечи. Пустой ответ при успешном статусе — «Нет данных (вне сессии/выходной)», а не сбой источника. Корректировки на корпоративные действия в этой версии не выполняются.
