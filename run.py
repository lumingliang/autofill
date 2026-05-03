import uvicorn

if __name__ == "__main__":
    # 使用 uvicorn 的默认日志配置，但禁用访问日志（我们在中间件中处理）
    # 日志配置已在 app/__init__.py 中初始化
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9999,
        reload=True,
        access_log=False,  # 禁用默认访问日志，由我们的中间件处理
        log_level="info",
    )
