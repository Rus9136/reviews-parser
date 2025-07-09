import glob
import os
from typing import List

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Reviews Parser API",
    description="API для получения отзывов, собранных парсером.",
    version="1.0.0",
)

OUTPUT_DIR = "output"


def get_latest_reviews_file() -> str | None:
    """Находит самый свежий CSV файл с отзывами в директории output."""
    list_of_files = glob.glob(os.path.join(OUTPUT_DIR, "reviews_*.csv"))
    if not list_of_files:
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


@app.get("/reviews",
         summary="Получить список всех отзывов",
         response_description="Список отзывов в формате JSON")
def get_reviews():
    """
    Возвращает содержимое последнего файла с отзывами в формате JSON.
    """
    latest_file = get_latest_reviews_file()

    if latest_file is None:
        raise HTTPException(
            status_code=404,
            detail="Файл с отзывами не найден. Сначала запустите парсер.",
        )

    try:
        df = pd.read_csv(latest_file)
        # Заполняем пустые значения, чтобы они корректно отображались в JSON
        df.fillna("", inplace=True)
        reviews = df.to_dict(orient="records")
        return JSONResponse(content=reviews)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при чтении или обработке файла: {e}",
        )
