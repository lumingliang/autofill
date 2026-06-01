import os
import sys
import warnings

# 在导入其他模块前设置环境变量
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# 抑制 Python 默认的 traceback 输出（避免控制台打印完整堆栈）
# 异常已由我们的全局异常处理器记录到日志文件
sys.tracebacklimit = 0

# 忽略 multiprocessing resource_tracker 警告
warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")

import uvicorn

if __name__ == "__main__":
    # 完全禁用 Uvicorn 日志，全部使用我们自己的日志组件
    # 日志配置已在 app/log/log.py 中初始化
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9999,
        reload=False,
        access_log=False,  # 禁用默认访问日志，由我们的中间件处理
        log_config=None,   # 禁用 Uvicorn 的日志配置，完全使用我们自己的日志
    )
