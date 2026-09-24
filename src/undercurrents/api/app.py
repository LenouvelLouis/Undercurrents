from fastapi import FastAPI

from undercurrents.api import analysis, predictions, shows, songs, stats

app = FastAPI(title="Undercurrents API")
app.include_router(stats.router)
app.include_router(songs.router)
app.include_router(predictions.router)
app.include_router(analysis.router)
app.include_router(shows.router)
