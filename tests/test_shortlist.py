"""精选漏斗模块测试：过滤与排序逻辑（不依赖网络）。"""

from unittest.mock import patch

from sequoia_x.core.shortlist import ShortlistItem, build_shortlist
import sequoia_x.core.shortlist as shortlist_mod


class FakeEngine:
    """仅提供 get_latest_turnover 的最小 engine 替身。"""

    def __init__(self, turnover: dict[str, float]):
        self._turnover = turnover

    def get_latest_turnover(self) -> dict[str, float]:
        return self._turnover


NAMES = {
    "000001": "平安银行",
    "000002": "ST风险",
    "000003": "退市X",
    "600000": "浦发银行",
    "600001": "红旗连锁",
}


def _run(results, turnover, top_n=5, names=NAMES):
    with patch.object(shortlist_mod, "fetch_all_stock_names", return_value=names):
        return build_shortlist(results, FakeEngine(turnover), top_n=top_n)


def test_excludes_risk_warning_and_illiquid():
    results = {"A": ["000001", "000002", "000003", "600000"]}
    turnover = {
        "000001": 6e8,   # 保留：6亿
        "000002": 9e8,   # ST -> 剔除
        "000003": 9e8,   # 退市 -> 剔除
        "600000": 1e8,   # 成交额不足 -> 剔除
    }
    items = _run(results, turnover)
    assert [it.code for it in items] == ["000001"]


def test_resonance_then_turnover_ranking():
    results = {
        "A": ["000001", "600000", "600001"],
        "B": ["000001", "600001"],
        "C": ["600001"],
    }
    turnover = {"000001": 6e8, "600000": 9e8, "600001": 7e8}
    items = _run(results, turnover)
    # 600001 命中 3 策略排第一；000001 命中 2 策略第二（尽管成交额更低）
    assert [it.code for it in items] == ["600001", "000001", "600000"]
    assert items[0].hits == ["A", "B", "C"]


def test_top_n_limit():
    results = {"A": ["000001", "600000", "600001"]}
    turnover = {"000001": 6e8, "600000": 7e8, "600001": 8e8}
    items = _run(results, turnover, top_n=2)
    assert [it.code for it in items] == ["600001", "600000"]


def test_empty_names_skips_st_filter():
    """名称拉取失败（空 dict）时不误杀，仅按流动性过滤。"""
    results = {"A": ["000002", "600000"]}
    turnover = {"000002": 9e8, "600000": 9e8}
    items = _run(results, turnover, names={})
    assert {it.code for it in items} == {"000002", "600000"}
    # 名称缺失时展示名回退为代码
    assert all(it.name == it.code for it in items)


def test_labels_use_chinese_names():
    item = ShortlistItem(
        code="000001",
        name="平安银行",
        hits=["TurtleTradeStrategy", "RpsBreakoutStrategy"],
        turnover=1e8,
    )
    assert item.labels == "海龟+RPS"


def test_empty_results_returns_empty():
    assert _run({"A": []}, {}) == []
