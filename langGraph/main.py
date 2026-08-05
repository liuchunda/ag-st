from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes

from app.controller.add_docs_route import add_docs_route
from app.controller.add_graph_route import add_graph_route

app = FastAPI(
    docs_url=None,  # 禁用默认 Swagger
    redoc_url=None,  # 禁用默认 ReDoc
)
add_docs_route(app)

add_graph_route(app)

@app.get("/")
async def redirect_root_to_docs() -> RedirectResponse:
    return RedirectResponse("/docs")


# Edit this to add the chain you want to add
# add_routes(app, NotImplemented)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)