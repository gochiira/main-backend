# Pythonイメージの取得
FROM ghcr.io/gochiira/main-backend-depends:latest
# モジュールを揃える
WORKDIR /usr/local/app
COPY . .
# 起動環境設定
EXPOSE 5000
ENTRYPOINT [ "gunicorn", "app:app" ]
CMD [ "-c", "gunicorn_config.py" ]