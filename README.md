# Hayes Signal Monitor

Captura publicações **oficiais** de Arthur Hayes (CIO da Maelstrom, cofundador da BitMEX) e as transforma em sinais estruturados para robôs de trading quantitativo. Roda na **Vercel** (Python/Flask).

## Fontes
| Fonte | Como | Latência |
|---|---|---|
| X/Twitter `@CryptoHayes` | API oficial v2 (`X_BEARER_TOKEN`, opcional) | segundos–minutos |
| Substack "Crypto Trader Digest" (`cryptohayes.substack.com`) | RSS `/feed` | minutos |
| Substack da Maelstrom (`maelstromfund.substack.com`) | RSS `/feed` | minutos |
| Qualquer outra (ex.: sua própria ponte RSS do X) | `EXTRA_FEEDS` | depende |

## Melhorias em relação a `the-convocation/twitter-scraper` e `TreasureProject/twitter-scraper-v2`
Esses dois são bibliotecas Node/TypeScript que usam a API interna do site do X e exigem **login com conta real** (os próprios READMEs avisam do risco de banimento, de limites dinâmicos e de quebras frequentes). Aqui:
- **Sem login, cookie ou senha**: API oficial do X + RSS. Nada de conta que pode ser banida.
- **Incremental**: `since_id` busca (e cobra) só posts novos.
- **Dedupe atômico** (Redis `SADD`) e **trava** contra execuções simultâneas.
- **Bootstrap seguro**: a 1ª execução carrega o histórico sem disparar o robô.
- **Falha isolada**: uma fonte fora do ar não derruba as outras (coleta em paralelo).
- **Análise por ativo** (BTC, ETH, HYPE, ZEC, USD, JPY…) e por tema (liquidez, Fed, tesouro, iene…), com score agregado e decaimento no tempo.
- **Webhook assinado (HMAC)** para o robô, **XML seguro** (`defusedxml`), endpoint de coleta **fechado por padrão**, testes e CI.

## Deploy (GitHub + Vercel)
1. Suba esta pasta para um repositório no GitHub.
2. Na Vercel: *Add New → Project* e importe o repositório.
3. Em *Storage/Marketplace*, adicione **Upstash Redis** (preenche as variáveis sozinho). Sem isso os dados ficam só em memória e se perdem.
4. Em *Settings → Environment Variables*, defina `CRON_SECRET` (valor longo e aleatório). Opcionais: `X_BEARER_TOKEN`, `WEBHOOK_URL`, `WEBHOOK_SECRET`, `EXTRA_FEEDS`.
5. Faça o deploy e confira `https://SEU-APP.vercel.app/api/health`.

### Agendamento (a cada 1–5 min)
- **Grátis**: o workflow `poll.yml` chama `/api/poll` a cada ~5 min. Em *Settings → Secrets → Actions* crie `CRON_SECRET` (o mesmo valor) e `APP_URL` (`https://SEU-APP.vercel.app`).
- **Vercel Pro**: acrescente ao `vercel.json` `"crons": [{ "path": "/api/poll", "schedule": "* * * * *" }]`. A Vercel envia `Authorization: Bearer $CRON_SECRET` automaticamente. No plano Hobby, crons só podem rodar 1x/dia e um cron mais frequente **falha o deploy**; por isso ele não vem ativado.

## API
- `GET /api/items?limit=50&source=x` — itens novos primeiro, cada um com `analysis`.
- `GET /api/signals?hours=48` — score por ativo: `{"BTC": {"score": 0.6, "label": "bullish", "mentions": 4, ...}}`.
- `GET /api/health` — estado da configuração.
- `POST /api/poll` — coleta agora (`Authorization: Bearer $CRON_SECRET`).

## Webhook para o robô
`POST` com `{"event":"hayes.new_items","count":N,"items":[...]}` e cabeçalhos `X-Hayes-Timestamp` e `X-Hayes-Signature: sha256=<hmac>`. Verificação:
```python
import hashlib, hmac, time
def valid(body: bytes, ts: str, sig: str, secret: str) -> bool:
    if abs(time.time() - int(ts)) > 300:  # rejeita replays
        return False
    expected = "sha256=" + hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
```

## Rodar local / testes
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
CRON_SECRET=teste flask --app api/index run
curl -X POST -H "Authorization: Bearer teste" localhost:5000/api/poll
```

## Limites e avisos
- O X cobra/limita a API oficial; `since_id` e o intervalo de 5 min ajudam a controlar custo. Confira seu plano.
- A análise é heurística (palavras-chave): serve como variável de entrada, não como decisão. Ensaios longos são resumidos por frases; ironia e contexto escapam.
- Este projeto **não executa ordens**. Qualquer negociação é por sua conta e risco; isto não é recomendação financeira.
- Respeite os termos de uso de cada fonte.
