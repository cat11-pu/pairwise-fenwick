"""排行榜索引内核（纯标准库，行为完全确定）。

榜面按分数档位维护：每个分数占树状数组的一个 1 基下标，下标上记这个分数有
多少人，前缀和就是“分数不超过它的玩家数”。名次、区间统计与按名次取人都从
这棵树上取数。模块不使用真实时钟、线程、网络与随机数，同一串提交与退榜操作
永远得到同样的榜单。

约定：

* 名次从 1 开始，分数最高者第 1 名，名次不超过榜上总人数；
* 同分并列：分数相同的玩家名次相同，名次等于“分数严格高于自己的人数十 1”；
* 同分取人：先提交的排在前面；
* 退榜与改分后其余玩家的名次立刻前移，名次之间不留空档。

对外接口：

* FenwickTree —— 1 基树状数组：单点加减、前缀和、区间和、按升序序号定位；
* Leaderboard —— 榜单：登记与改分、退榜、查分数、计数、区间统计、名次、
                  按名次取人、取前若干名。
"""

__all__ = ["FenwickTree", "Leaderboard"]


def _require_int(value, label):
    """确认参数是非布尔的整数。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("%s 必须是整数: %r" % (label, value))
    return value


def _require_player(player):
    """确认玩家标识是非空字符串。"""
    if not isinstance(player, str) or not player:
        raise TypeError("玩家标识必须是非空字符串: %r" % (player,))
    return player


class FenwickTree:
    """下标 1..size 的树状数组，槽位里放整数计数。"""

    __slots__ = ("_size", "_tree")

    def __init__(self, size):
        _require_int(size, "下标上界")
        if size < 1:
            raise ValueError("下标上界必须为正: %r" % (size,))
        self._size = size
        self._tree = [0] * (size + 1)

    @property
    def size(self):
        return self._size

    def __len__(self):
        return self._size

    def __repr__(self):
        return "FenwickTree(size=%d, total=%d)" % (self._size, self.total())

    def add(self, index, delta):
        """把下标 index 上的计数加上 delta，delta 可以为负。"""
        _require_int(index, "下标")
        _require_int(delta, "增量")
        if index < 1 or index > self._size:
            raise ValueError("下标越界: %r" % (index,))
        while index <= self._size:
            self._tree[index] += delta
            index += index & (-index)

    def prefix(self, index):
        """下标 1..index 上的计数之和，index 为 0 时表示空前缀。"""
        _require_int(index, "下标")
        if index < 0 or index > self._size:
            raise ValueError("下标越界: %r" % (index,))
        total = 0
        while index > 0:
            total += self._tree[index]
            index -= index & (-index)
        return total

    def total(self):
        """树内所有计数之和。"""
        return self.prefix(self._size)

    def range_sum(self, low, high):
        """闭区间 [low, high] 上的计数之和，low 大于 high 时为 0。"""
        _require_int(low, "区间下界")
        _require_int(high, "区间上界")
        if low > high:
            return 0
        low = max(low, 1)
        return self.prefix(high) - self.prefix(low - 1)

    def select(self, order):
        """返回最小的下标 index 使 prefix(index) 不小于 order。

        order 超过树内计数之和时返回 size + 1，表示没有这样的下标。
        """
        _require_int(order, "次序")
        index = 0
        step = 1 << (self._size.bit_length() - 1)
        while step:
            nxt = index + step
            if nxt <= self._size and self._tree[nxt] < order:
                index = nxt
                order -= self._tree[nxt]
            step >>= 1
        return index + 1


class Leaderboard:
    """按分数档位维护名次的榜单。"""

    __slots__ = ("_min_score", "_max_score", "_tree", "_scores",
                 "_order", "_roster", "_next_order")

    def __init__(self, min_score, max_score):
        _require_int(min_score, "分数下界")
        _require_int(max_score, "分数上界")
        if min_score > max_score:
            raise ValueError("分数下界不能高于上界: %r > %r"
                             % (min_score, max_score))
        self._min_score = min_score
        self._max_score = max_score
        self._tree = FenwickTree(max_score - min_score + 1)
        self._scores = {}
        self._order = {}
        self._roster = {}
        self._next_order = 0

    # ---- 只读视图 -------------------------------------------------

    @property
    def min_score(self):
        return self._min_score

    @property
    def max_score(self):
        return self._max_score

    def __repr__(self):
        return "Leaderboard(min_score=%d, max_score=%d, players=%d)" % (
            self._min_score, self._max_score, self.player_count())

    def is_empty(self):
        """榜上是否一个人都没有。"""
        return not self._scores

    def player_count(self):
        """榜上玩家数。"""
        return len(self._scores)

    def players(self):
        """榜上玩家标识，按提交次序排列。"""
        return sorted(self._scores, key=lambda name: self._order[name])

    def score_of(self, player):
        """玩家当前分数；没上过榜的返回 None。"""
        _require_player(player)
        return self._scores.get(player)

    def count_at(self, score):
        """分数正好是 score 的玩家数。"""
        self._require_score(score)
        return len(self._roster.get(score, ()))

    def count_between(self, low, high):
        """分数落在闭区间 [low, high] 内的玩家数，越出榜面的边界按榜面裁剪。"""
        _require_int(low, "区间下界")
        _require_int(high, "区间上界")
        if low > high:
            return 0
        first = max(low, self._min_score)
        last = min(high, self._max_score)
        if first > last:
            return 0
        return self._tree.range_sum(self._index_of(first),
                                    self._index_of(last))

    def rank(self, player):
        """玩家当前名次；不在榜上的返回 None。"""
        _require_player(player)
        if player not in self._scores:
            return None
        score = self._scores[player]
        index = self._index_of(score)
        above = self.player_count() - self._tree.prefix(index)
        return above + 1

    def player_at_rank(self, rank):
        """名次 rank 上的 (玩家, 分数)；名次从 1 开始，越界返回 None。"""
        _require_int(rank, "名次")
        if rank < 1 or rank > self.player_count():
            return None
        total = self.player_count()
        index = self._tree.select(total - rank + 1)
        if index > self._tree.size:
            return None
        score = self._min_score + index - 1
        above = total - self._tree.prefix(index)
        peers = sorted(self._roster.get(score, ()),
                       key=lambda name: self._order[name])
        seat = rank - above - 1
        if seat < 0 or seat >= len(peers):
            return None
        return (peers[seat], score)

    def top(self, count):
        """按名次顺序取前 count 名，元素是 (玩家, 分数)；不为正时返回空表。"""
        _require_int(count, "数量")
        if count <= 0:
            return []
        return self._ordered()[:count]

    # ---- 写入 -----------------------------------------------------

    def submit(self, player, score):
        """登记或改分，返回此前的分数；首次登记返回 None。"""
        _require_player(player)
        self._require_score(score)
        previous = self._scores.get(player)
        if previous == score:
            return previous
        self._scores[player] = score
        if previous is not None:
            self._roster[previous].discard(player)
            self._tree.add(self._index_of(previous), -1)
        self._roster.setdefault(score, set()).add(player)
        if previous is None:
            self._next_order += 1
            self._order[player] = self._next_order
        self._tree.add(self._index_of(score), 1)
        return previous

    def remove(self, player):
        """把玩家退榜，返回是否真的退掉了。"""
        _require_player(player)
        if player not in self._scores:
            return False
        score = self._scores.pop(player)
        self._roster[score].discard(player)
        del self._order[player]
        self._tree.add(self._index_of(score), -1)
        return True

    # ---- 内部结构 -------------------------------------------------

    def _require_score(self, score):
        """确认分数是非布尔整数且落在榜面范围内。"""
        _require_int(score, "分数")
        if score < self._min_score or score > self._max_score:
            raise ValueError("分数越出榜面范围: %r" % (score,))
        return score

    def _index_of(self, score):
        """分数对应的 1 基下标。"""
        return score - self._min_score + 1

    def _ordered(self):
        """全部玩家按名次顺序排列：分数从高到低，同分按提交次序。"""
        return sorted(self._scores.items(),
                      key=lambda item: (-item[1], self._order[item[0]]))
