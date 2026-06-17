FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据和上传目录（Fly.io volume 挂载点）
RUN mkdir -p /data /data/uploads

# 使用 gunicorn 运行，$PORT 由 Render 自动设置
EXPOSE 10000
CMD gunicorn server:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120
