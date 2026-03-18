from gs2c_base import GameServiceInterceptor

addons = [GameServiceInterceptor(
    target_path="/gs2c/ge/v4/gameService",
    target_symbol="vs20olympgold",
    db_conf={
        "host": "127.0.0.1",
        "port": "3306",
        "user": "root",
        "password": "12345678",
        "database": "ks-pp",
        "mysql_bin": "/opt/homebrew/opt/mysql@8.0/bin/mysql",
    },
)]
