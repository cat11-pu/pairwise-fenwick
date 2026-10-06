"""fenwick.core 的验收测试。

只断言期望的榜面结果与不变量：名次口径与同分并列、区间统计与逐点求和
一致、按名次取人与取前若干名、退榜与改分后的名次修正、空榜与非法输入。
"""

import unittest

from fenwick import FenwickTree, Leaderboard


def seed(board, entries):
    """按顺序把 (玩家, 分数) 登记进榜单。"""
    for name, score in entries:
        board.submit(name, score)


class BasicTests(unittest.TestCase):

    def test_basic_board_after_a_few_submissions(self):
        board = Leaderboard(0, 100)
        self.assertTrue(board.is_empty())
        self.assertEqual(board.min_score, 0)
        self.assertEqual(board.max_score, 100)
        self.assertIsNone(board.submit("ann", 64))
        self.assertIsNone(board.submit("bo", 31))
        board.submit("cy", 88)
        self.assertFalse(board.is_empty())
        self.assertEqual(board.player_count(), 3)
        self.assertEqual(board.players(), ["ann", "bo", "cy"])
        self.assertEqual(board.score_of("ann"), 64)
        self.assertEqual(board.score_of("cy"), 88)
        self.assertEqual(board.count_at(64), 1)
        self.assertEqual(board.count_at(90), 0)
        self.assertEqual(board.rank("cy"), 1)
        self.assertEqual(board.rank("ann"), 2)
        self.assertEqual(board.rank("bo"), 3)
        self.assertEqual(board.top(2), [("cy", 88), ("ann", 64)])
        self.assertEqual(board.top(3), [("cy", 88), ("ann", 64), ("bo", 31)])

    def test_empty_board_and_absent_players(self):
        board = Leaderboard(10, 40)
        self.assertTrue(board.is_empty())
        self.assertEqual(board.player_count(), 0)
        self.assertEqual(board.players(), [])
        self.assertIsNone(board.score_of("ghost"))
        self.assertIsNone(board.rank("ghost"))
        self.assertIsNone(board.player_at_rank(1))
        self.assertIsNone(board.player_at_rank(0))
        self.assertEqual(board.top(3), [])
        self.assertEqual(board.count_between(0, 99), 0)
        self.assertFalse(board.remove("ghost"))
        board.submit("ann", 20)
        self.assertIsNone(board.score_of("nobody"))
        self.assertIsNone(board.rank("nobody"))
        self.assertFalse(board.remove("nobody"))
        self.assertTrue(board.remove("ann"))
        self.assertTrue(board.is_empty())


class RankTests(unittest.TestCase):

    def test_tied_scores_share_one_rank(self):
        board = Leaderboard(0, 100)
        seed(board, [("ann", 100), ("bo", 90), ("cy", 90),
                     ("di", 90), ("eve", 70)])
        names = ("ann", "bo", "cy", "di", "eve")
        self.assertEqual([board.rank(name) for name in names],
                         [1, 2, 2, 2, 5])
        scores = {name: board.score_of(name) for name in names}
        ranks = {name: board.rank(name) for name in names}
        for name in names:
            higher = sum(1 for other in scores.values() if other > scores[name])
            self.assertEqual(ranks[name], higher + 1)
            self.assertLessEqual(ranks[name], board.player_count())
            self.assertGreaterEqual(ranks[name], 1)
        seen = {}
        for name in names:
            seen.setdefault(scores[name], set()).add(ranks[name])
        for score, tied in seen.items():
            self.assertEqual(len(tied), 1, score)

    def test_rank_lookup_returns_the_matching_player(self):
        board = Leaderboard(0, 100)
        seed(board, [("ann", 90), ("bo", 70), ("cy", 70),
                     ("di", 20), ("eve", 20)])
        expected = [("ann", 90), ("bo", 70), ("cy", 70),
                    ("di", 20), ("eve", 20)]
        for rank, entry in enumerate(expected, start=1):
            self.assertEqual(board.player_at_rank(rank), entry)
        self.assertIsNone(board.player_at_rank(0))
        self.assertIsNone(board.player_at_rank(6))
        self.assertIsNone(board.player_at_rank(-2))
        self.assertEqual([board.player_at_rank(rank) for rank in range(1, 6)],
                         board.top(5))


class IntervalTests(unittest.TestCase):

    def test_interval_counts_cover_every_bucket(self):
        board = Leaderboard(0, 20)
        seed(board, [("ann", 4), ("bo", 9), ("cy", 9), ("di", 17)])
        self.assertEqual(board.count_between(9, 9), 2)
        self.assertEqual(board.count_between(4, 4), 1)
        self.assertEqual(board.count_between(4, 17), 4)
        self.assertEqual(board.count_between(17, 99), 1)
        self.assertEqual(board.count_between(-5, 4), 1)
        self.assertEqual(board.count_between(18, 20), 0)
        self.assertEqual(board.count_between(-5, 3), 0)
        self.assertEqual(board.count_between(9, 4), 0)

        tree = FenwickTree(6)
        for index, delta in ((1, 2), (3, 1), (5, 2), (6, 1)):
            tree.add(index, delta)
        self.assertEqual(tree.total(), 6)
        self.assertEqual([tree.prefix(index) for index in range(7)],
                         [0, 2, 2, 3, 3, 5, 6])
        self.assertEqual(tree.range_sum(1, 3), 3)

    def test_interval_counts_match_pointwise_sums(self):
        board = Leaderboard(0, 20)
        seed(board, [("ann", 3), ("bo", 5), ("cy", 7), ("cy", 7),
                     ("di", 9), ("eve", 14)])
        self.assertEqual(board.player_count(), 5)
        for low, high in ((3, 20), (5, 20), (3, 14), (5, 7), (3, 7)):
            expected = sum(board.count_at(score)
                           for score in range(low, high + 1))
            self.assertEqual(board.count_between(low, high), expected,
                             (low, high))


class LookupTests(unittest.TestCase):

    def test_top_lists_players_in_rank_order(self):
        board = Leaderboard(0, 100)
        seed(board, [("ann", 90), ("bo", 70), ("cy", 70), ("di", 40)])
        full = [("ann", 90), ("bo", 70), ("cy", 70), ("di", 40)]
        self.assertEqual(board.top(1), [("ann", 90)])
        self.assertEqual(board.top(2), [("ann", 90), ("bo", 70)])
        self.assertEqual(board.top(4), full)
        self.assertEqual(board.top(9), full)
        self.assertEqual(board.top(0), [])
        self.assertEqual(board.top(-1), [])
        self.assertEqual(board.top(-2), [])


class MutationTests(unittest.TestCase):

    def test_repeated_submission_of_the_same_score_takes_one_seat(self):
        board = Leaderboard(0, 100)
        seed(board, [("ann", 90), ("bo", 70), ("cy", 50)])
        self.assertEqual(board.submit("bo", 70), 70)
        self.assertEqual(board.player_count(), 3)
        self.assertEqual(board.count_at(70), 1)
        self.assertEqual(board.rank("ann"), 1)
        self.assertEqual(board.rank("bo"), 2)
        self.assertEqual(board.rank("cy"), 3)
        self.assertEqual(board.top(3),
                         [("ann", 90), ("bo", 70), ("cy", 50)])
        board.submit("cy", 95)
        self.assertEqual(board.count_at(50), 0)
        self.assertEqual(board.count_at(95), 1)
        self.assertEqual(board.rank("cy"), 1)
        self.assertEqual(board.rank("ann"), 2)
        self.assertEqual(board.count_between(50, 100), 3)

    def test_removing_a_player_shifts_the_ranks_below(self):
        board = Leaderboard(0, 100)
        seed(board, [("ann", 80), ("bo", 60), ("cy", 40), ("di", 20)])
        self.assertEqual([board.rank(name) for name in ("ann", "bo", "cy", "di")],
                         [1, 2, 3, 4])
        self.assertTrue(board.remove("ann"))
        self.assertFalse(board.remove("ann"))
        self.assertEqual(board.player_count(), 3)
        self.assertEqual(board.players(), ["bo", "cy", "di"])
        self.assertIsNone(board.rank("ann"))
        self.assertEqual([board.rank(name) for name in ("bo", "cy", "di")],
                         [1, 2, 3])
        self.assertEqual(board.top(3),
                         [("bo", 60), ("cy", 40), ("di", 20)])
        self.assertEqual(board.count_at(80), 0)
        self.assertEqual(board.count_between(0, 100), 3)
        for name in ("bo", "cy", "di"):
            self.assertTrue(board.remove(name))
        self.assertTrue(board.is_empty())
        self.assertEqual(board.player_count(), 0)
        self.assertEqual(board.count_at(80), 0)
        self.assertEqual(board.count_at(40), 0)
        self.assertEqual(board.count_between(0, 100), 0)


class InputTests(unittest.TestCase):

    def test_invalid_inputs_are_rejected(self):
        self.assertRaises(ValueError, Leaderboard, 60, 10)
        self.assertRaises(TypeError, Leaderboard, 1.5, 10)
        self.assertRaises(TypeError, Leaderboard, 1, True)
        self.assertRaises(ValueError, FenwickTree, 0)
        self.assertRaises(TypeError, FenwickTree, 2.5)

        board = Leaderboard(10, 40)
        self.assertRaises(TypeError, board.submit, 7, 20)
        self.assertRaises(TypeError, board.submit, "", 20)
        self.assertRaises(TypeError, board.submit, "ann", 20.5)
        self.assertRaises(TypeError, board.submit, "ann", True)
        self.assertRaises(ValueError, board.submit, "ann", 9)
        self.assertRaises(ValueError, board.submit, "ann", 41)
        self.assertRaises(TypeError, board.remove, None)
        self.assertRaises(TypeError, board.score_of, 3)
        self.assertRaises(TypeError, board.rank, None)
        self.assertRaises(TypeError, board.player_at_rank, 1.5)
        self.assertRaises(TypeError, board.top, "2")
        self.assertRaises(TypeError, board.count_at, 20.5)
        self.assertRaises(ValueError, board.count_at, 5)
        self.assertRaises(TypeError, board.count_between, 10.5, 20)
        self.assertRaises(TypeError, board.count_between, 10, "20")

        tree = FenwickTree(4)
        self.assertRaises(ValueError, tree.add, 0, 1)
        self.assertRaises(ValueError, tree.add, 5, 1)
        self.assertRaises(TypeError, tree.add, 1, 1.5)
        self.assertRaises(ValueError, tree.prefix, 5)
        self.assertRaises(TypeError, tree.prefix, True)
        self.assertRaises(TypeError, tree.select, 1.5)

        board.submit("ann", 20)
        self.assertEqual(board.rank("ann"), 1)
        self.assertEqual(board.count_at(20), 1)


if __name__ == "__main__":
    unittest.main()
