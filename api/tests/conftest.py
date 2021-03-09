import os
import pytest
import tempfile
from ...app import app
from dotenv import load_dotenv
from os import environ


# .env読み込み
load_dotenv(verbose=True, override=True)

# テスト用データ
with open("test_data.sql", "r", encoding="utf-8") as f:
    TEST_DATA = f.read()


# テスト用のクライアント生成
@pytest.fixture
def client():
    db_fd, app.app.config['DATABASE'] = tempfile.mkstemp()
    app.app.config['TESTING'] = True
    TOKEN = environ.get('TEST_TOKEN')
    with app.app.test_client() as client:
        with app.app.app_context():
            app.init_db()
            app.g.db.edit(TEST_DATA)
        yield client, {"Authorization": f"Bearer {TOKEN}"}
    os.close(db_fd)
    os.unlink(app.app.config['DATABASE'])
