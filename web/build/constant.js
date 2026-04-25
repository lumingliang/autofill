export const OUTPUT_DIR = 'dist'

export const PROXY_CONFIG = {
  // /**
  //  * @desc    替换匹配值
  //  * @请求路径  http://localhost:3100/api/user
  //  * @转发路径  http://localhost:9999/api/v1 +/user
  //  */
  // '/api': {
  //   target: 'http://localhost:9999/api/v1',
  //   changeOrigin: true,
  //   rewrite: (path) => path.replace(new RegExp('^/api'), ''),
  // },
  /**
   * @desc    不替换匹配值
   * @请求路径  http://localhost:3100/api/v1/user
   * @转发路径  http://localhost:9999/api/v1/user
   */
  '/api/v1': {
    target: 'http://127.0.0.1:9999',
    changeOrigin: true,
  },
  /**
   * @desc    上传文件访问代理
   * @请求路径  http://localhost:3100/uploads/xxx
   * @转发路径  http://localhost:9999/uploads/xxx
   */
  '/uploads': {
    target: 'http://127.0.0.1:9999',
    changeOrigin: true,
  },
}
