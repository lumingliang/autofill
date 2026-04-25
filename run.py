import uvicorn

# 先初始化项目日志配置
from app.log import logger

if __name__ == "__main__":
    # 使用 uvicorn 的默认日志配置，但禁用访问日志（我们在中间件中处理）
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9999,
        reload=True,
        access_log=False,  # 禁用默认访问日志，由我们的中间件处理
        log_level="info",
    )
