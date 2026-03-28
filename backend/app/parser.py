import json
from datetime import datetime

from openai import OpenAI

from app.config import settings


PROMPT_TEMPLATE = (
    "Analise a seguinte mensagem e extraia informações de compromisso/evento. "
    "Retorne APENAS um JSON válido com os campos: \"titulo\", \"descricao\", \"data\" (YYYY-MM-DD), "
    "\"hora\" (HH:MM:00), \"local\". "
    "REGRAS: Se não for um compromisso, retorne: {\"erro\": \"Nenhum compromisso identificado\"}. "
    "Se a data não for especificada, use a data de amanhã. "
    "Se a hora não for especificada, use \"09:00:00\". "
    "Se o local não for especificado, use \"A definir\". "
    "A descrição pode ser o próprio título se não houver mais detalhes. "
    "Data atual para referência: {hoje}. Mensagem: \"{texto}\". JSON:"
)


def parse_message(texto: str, hoje: datetime) -> dict:
    if not settings.openai_api_key:
        return {"erro": "OPENAI_API_KEY não configurada"}

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = PROMPT_TEMPLATE.format(hoje=hoje.isoformat(), texto=texto)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.1,
        )
    except Exception:
        return {"erro": "Falha ao chamar OpenAI"}

    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"erro": "Falha ao interpretar JSON retornado pela IA"}
