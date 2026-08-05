from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html, get_redoc_html, get_swagger_ui_html
from fastapi.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parents[2] / "packages" / "static"


def add_docs_route(app: FastAPI):
  """
  专门处理文档静态资源本地代理的接口
  """

  app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

  # 自定义 Swagger 页面（使用本地资源）
  @app.get("/docs", include_in_schema=False)
  async def custom_swagger_ui():
    """
    提供自定义的 Swagger UI 文档页面

    Returns:
        Swagger UI HTML 页面，使用本地静态资源加载
    """
    return get_swagger_ui_html(
      openapi_url=app.openapi_url,
      title=app.title + " - Swagger UI",
      oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
      swagger_js_url="/static/swagger-ui-bundle.js",
      swagger_css_url="/static/swagger-ui.css",
    )

  @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
  async def swagger_ui_redirect():
    """
    处理 Swagger UI 的 OAuth2 重定向回调

    Returns:
        OAuth2 重定向 HTML 响应
    """
    return get_swagger_ui_oauth2_redirect_html()

  @app.get("/redoc", include_in_schema=False)
  async def redoc_html():
    """
    提供自定义的 ReDoc 文档页面

    Returns:
        ReDoc HTML 页面，使用本地静态资源加载
    """
    return get_redoc_html(
      openapi_url=app.openapi_url,
      title=app.title + " - ReDoc",
      redoc_js_url="/static/redoc.standalone.js",
    )

  @app.get("/")
  async def redirect_root_to_docs():
    """
    将根路径请求重定向到 Swagger 文档页面

    Returns:
        重定向响应到 /docs 路径
    """
    return RedirectResponse("/docs")
