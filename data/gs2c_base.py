"""
gs2c_base.py - PP游戏采集公共模块
所有游戏脚本共享此模块，通过构造参数传入游戏配置和数据库配置。
"""
from mitmproxy import http
import json
import hashlib
import subprocess
from decimal import Decimal

TARGET_ACTIONS = ["doSpin", "doBonus"]


def form_to_dict(text: str) -> dict:
    result = {}
    for pair in text.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        result[k] = v
    return result


def dict_to_query(d: dict) -> str:
    return "&".join(f"{k}={v}" for k, v in d.items())


def face_hash(face: str) -> str:
    return hashlib.sha256(face.encode("utf-8")).hexdigest()[:16]


def mysql_escape(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


def insert_to_db(db_conf: dict, db_table: str, row: dict):
    if row["rid"] == 0:
        print(f"  [DB] SKIP  rid=0")
        return

    bonus_val = mysql_escape(row["bonus_script"]) if row["bonus_script"] else "NULL"

    sql = (
        f"INSERT INTO {db_table} (rid, bet, odd, fs_max, pur, script, bonus_script, `hash`) "
        f"VALUES ({row['rid']}, {row['bet']}, {row['odd']}, {row['fs_max']}, {row['pur']}, "
        f"{mysql_escape(row['script'])}, {bonus_val}, {mysql_escape(row['hash'])}) "
        f"ON DUPLICATE KEY UPDATE "
        f"bet=VALUES(bet), odd=VALUES(odd), fs_max=VALUES(fs_max), pur=VALUES(pur), "
        f"script=VALUES(script), bonus_script=VALUES(bonus_script);"
    )

    cmd = [
        db_conf["mysql_bin"],
        f"-h{db_conf['host']}",
        f"-P{db_conf['port']}",
        f"-u{db_conf['user']}",
        f"-p{db_conf['password']}",
        db_conf["database"],
        "-e", sql,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  [DB] INSERT OK  rid={row['rid']}  pur={row['pur']}  hash={row['hash']}")
        else:
            print(f"  [DB] INSERT FAIL  rid={row['rid']}  stderr={result.stderr.strip()}")
    except Exception as e:
        print(f"  [DB] INSERT ERROR  rid={row['rid']}  error={e}")


def print_round(db_conf: dict, db_table: str, rid: str, records: list, bonus: dict, fsmax: str, round_face: str, pur: int):
    if not records:
        return

    first_req = records[0]["req"]
    c = Decimal(first_req.get("c", "0"))
    first_resp = records[0]["resp"]
    l = Decimal(first_resp.get("l", "0"))
    base_bet = c * l

    last_resp = records[-1]["resp"]
    total_win = Decimal(last_resp.get("tw", "0"))
    round_odd = (total_win / base_bet) if base_bet != 0 else Decimal("0")

    cards = []
    for record in records:
        resp = record["resp"]
        w = Decimal(resp.get("w", "0"))
        card_odd = (w / base_bet) if base_bet != 0 else Decimal("0")
        script = dict_to_query(resp)
        cards.append({
            "odd": str(card_odd),
            "script": script,
        })

    bonus_obj = None
    if bonus:
        bonus_resp = bonus["resp"]
        bonus_obj = {
            "is_free": True,
            "ind": bonus["req"].get("ind", "0"),
            "script": dict_to_query(bonus_resp),
        }

    rtp_card = {
        "bet": str(base_bet),
        "odd": str(round_odd),
        "fs_max": int(fsmax) if fsmax else 0,
        "cards": cards,
        "bonus": bonus_obj,
    }

    print(f"\n{'#'*60}")
    print(f"  ROUND : {rid}")
    print(f"  Spins : {len(records)}")
    print(f"  Bet   : {base_bet}")
    print(f"  Odd   : {round_odd}")
    print(f"  Win   : {total_win}")
    print(f"  FsMax : {fsmax if fsmax else '0'}")
    print(f"  Pur   : {pur}")
    print(f"  Face  : {round_face if round_face else 'N/A'}")
    print(f"{'#'*60}")

    for i, record in enumerate(records):
        resp = record["resp"]
        w = resp.get("w", "0")
        tw = resp.get("tw", "0")
        fs = resp.get("fs", "")
        na = resp.get("na", "")
        card_odd = cards[i]["odd"]

        label = f"[{record['action']}]"
        fs_info = f"  fs={fs}" if fs else ""
        print(f"\n  #{i + 1} {label}  w={w}  odd={card_odd}  tw={tw}  na={na}{fs_info}")
        print(f"    [Request]")
        print(f"    {json.dumps(record['req'], indent=4, ensure_ascii=False)}")
        print(f"    [Response]")
        print(f"    {json.dumps(resp, indent=4, ensure_ascii=False)}")

    if bonus:
        print(f"\n  [doBonus]")
        print(f"    [Request]")
        print(f"    {json.dumps(bonus['req'], indent=4, ensure_ascii=False)}")
        print(f"    [Response]")
        print(f"    {json.dumps(bonus['resp'], indent=4, ensure_ascii=False)}")

    print(f"\n  [RtpCard]")
    print(f"  {json.dumps(rtp_card, indent=4, ensure_ascii=False)}")

    hash_val = ""
    if round_face:
        hash_val = face_hash(round_face)
        print(f"\n  [FaceHash]")
        print(f"  face : {round_face}")
        print(f"  hash : {hash_val}")

    print(f"\n{'#'*60}\n")

    db_row = {
        "rid": int(rid) if rid else 0,
        "bet": float(base_bet),
        "odd": float(round_odd),
        "fs_max": int(fsmax) if fsmax else 0,
        "pur": pur,
        "script": json.dumps(rtp_card, ensure_ascii=False),
        "bonus_script": json.dumps(bonus_obj, ensure_ascii=False) if bonus_obj else None,
        "hash": hash_val,
    }

    print(f"  [DB Row]")
    print(f"  {json.dumps(db_row, indent=4, ensure_ascii=False, default=str)}")

    insert_to_db(db_conf, db_table, db_row)


class GameServiceInterceptor:
    """
    通用拦截器。
    用法:
        addons = [GameServiceInterceptor(
            target_path="/gs2c/ge/v4/gameService",
            target_symbol="vs10txbigbass",
            db_conf={
                "host": "127.0.0.1",
                "port": "3306",
                "user": "root",
                "password": "12345678",
                "database": "ks-pp",
                "mysql_bin": "/opt/homebrew/opt/mysql@8.0/bin/mysql",
            },
        )]
    """

    def __init__(self, target_path: str, target_symbol: str, db_conf: dict, is_fsmax_default: bool = False):
        self.target_path = target_path
        self.target_symbol = target_symbol
        self.db_conf = db_conf
        self.is_fsmax_default = is_fsmax_default  # 是否手动推断 fsmax（用于无 fsmax 字段的游戏）
        self.db_table = f"t_logs_{target_symbol}"
        self.current_rid = None
        self.current_round = []
        self.current_bonus = None
        self.current_fsmax = None
        self.current_round_face = None
        self.current_round_pur = 0  # 当局 pur 值，取第一个 spin 响应的 puri 字段，默认 0
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """检查表是否存在，不存在则自动创建"""
        check_sql = (
            f"SELECT COUNT(*) FROM information_schema.tables "
            f"WHERE table_schema='{self.db_conf['database']}' "
            f"AND table_name='{self.db_table}';"
        )
        cmd = [
            self.db_conf["mysql_bin"],
            f"-h{self.db_conf['host']}",
            f"-P{self.db_conf['port']}",
            f"-u{self.db_conf['user']}",
            f"-p{self.db_conf['password']}",
            self.db_conf["database"],
            "-N", "-B",
            "-e", check_sql,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip() == "1":
                print(f"  [DB] Table `{self.db_table}` already exists.")
                return
        except Exception as e:
            print(f"  [DB] CHECK TABLE ERROR: {e}")
            return

        create_sql = (
            f"CREATE TABLE `{self.db_table}` ("
            f"  `rid` bigint NOT NULL COMMENT '局唯一主键',"
            f"  `bet` double NOT NULL DEFAULT '0' COMMENT '基础投注金额',"
            f"  `odd` double NOT NULL DEFAULT '0' COMMENT '中奖倍数',"
            f"  `fs_max` int DEFAULT '0' COMMENT '当局首次免费赠送次数',"
            f"  `pur` tinyint NOT NULL DEFAULT '0' COMMENT 'pur',"
            f"  `script` text NOT NULL COMMENT '牌面脚本',"
            f"  `bonus_script` text,"
            f"  `hash` varchar(255) NOT NULL DEFAULT '' COMMENT '哈希值',"
            f"  PRIMARY KEY (`rid`),"
            f"  UNIQUE KEY `uk_hash` (`hash`)"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci "
            f"COMMENT='{self.target_symbol}游戏日志';"
        )
        cmd[-1] = create_sql
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  [DB] Table `{self.db_table}` created successfully.")
            else:
                print(f"  [DB] CREATE TABLE FAIL: {result.stderr.strip()}")
        except Exception as e:
            print(f"  [DB] CREATE TABLE ERROR: {e}")

    def _flush(self):
        # is_fsmax_default 模式：游戏无 fsmax 字段，根据当局 spin 数量手动推断
        # current_round 长度 > 1 说明有 free spin，fsmax 设为 1；否则为 0
        if self.is_fsmax_default and self.current_fsmax is None:
            self.current_fsmax = 1 if len(self.current_round) > 1 else 0

        print_round(self.db_conf, self.db_table, self.current_rid, self.current_round,
                     self.current_bonus, self.current_fsmax, self.current_round_face, self.current_round_pur)
        self.current_round = []
        self.current_bonus = None
        self.current_fsmax = None
        self.current_round_face = None
        self.current_round_pur = 0  # 重置 pur

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.request.method != "POST":
            return
        if self.target_path not in flow.request.path:
            return
        request_text = flow.request.get_text()
        matched = [a for a in TARGET_ACTIONS if a in request_text]
        if not matched:
            return

        action = matched[0]

        request_body = flow.request.get_text()
        try:
            req_params = json.loads(request_body)
        except (json.JSONDecodeError, TypeError):
            req_params = form_to_dict(request_body)

        if req_params.get("symbol", "") != self.target_symbol:
            print(f"  [WARN] 游戏匹配错误: expected={self.target_symbol}, got={req_params.get('symbol', 'N/A')}")
            return

        response_body = flow.response.get_text()
        try:
            resp_data = json.loads(response_body)
        except (json.JSONDecodeError, TypeError):
            resp_data = form_to_dict(response_body)

        if action == "doBonus":
            self.current_bonus = {
                "action": action,
                "req": req_params,
                "resp": resp_data,
            }
            return

        rid = resp_data.get("rid", "")

        if self.current_rid is not None and rid != self.current_rid:
            self._flush()

        self.current_rid = rid

        if self.current_fsmax is None and "fsmax" in resp_data:
            self.current_fsmax = resp_data["fsmax"]

        if self.current_round_face is None and "s" in resp_data:
            self.current_round_face = resp_data["s"]

        # 取第一个 spin 响应里的 puri 字段作为当局 pur 值
        if not self.current_round and "puri" in resp_data:
            self.current_round_pur = int(resp_data["puri"])

        self.current_round.append({
            "action": action,
            "req": req_params,
            "resp": resp_data,
        })
