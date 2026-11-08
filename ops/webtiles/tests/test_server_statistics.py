from pathlib import Path
import importlib.util
import tempfile
import unittest


source = Path(__file__).resolve().parents[3] / 'crawl-ref/source/webserver/webtiles/server_statistics.py'
spec = importlib.util.spec_from_file_location('server_statistics', source)
statistics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(statistics)


def record(index, name='Alice', score=10, duration=60, outcome='mon', extra=''):
    return (f'name={name}:start=20261108{index:06d}S:end=20261108{index + 1:06d}S:'
            f'sc={score}:dur={duration}:ktyp={outcome}:place=D::2{extra}\n')


class ServerStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, player, content, filename='logfile'):
        folder = self.root / player
        folder.mkdir(exist_ok=True)
        (folder / filename).write_text(content, encoding='utf8')

    def test_real_results_count_once_and_only_winning_is_a_victory(self):
        win = record(2, score=250, duration=3600, outcome='winning')
        self.write('Alice', record(1) + win + win + record(3, score=0, duration=0, outcome='leaving'))
        self.assertEqual(statistics.collect_statistics(self.root), dict(
            available=True, completed=3, wins=1, best_score=250, total_seconds=3660))

    def test_training_debug_and_explore_do_not_inflate_results(self):
        self.write('Alice', record(1, extra=':wiz=1') + record(2, extra=':explore=1'))
        for filename in ('logfile-tutorial', 'logfile-sprint', 'scores'):
            self.write('Alice', record(4, score=9999, outcome='winning'), filename)
        result = statistics.collect_statistics(self.root)
        self.assertEqual(result['completed'], 0)
        self.assertIsNone(result['best_score'])

    def test_partial_corrupt_and_negative_records_are_not_reported_as_games(self):
        self.write('Alice', 'broken\n' + record(1, score='bad')
                   + record(2, duration=-1) + record(3, score=0)
                   + record(4, score=999).rstrip('\n'))
        result = statistics.collect_statistics(self.root)
        self.assertEqual((result['completed'], result['best_score']), (1, 0))

    def test_private_or_technical_players_are_excluded_even_from_cached_totals(self):
        self.write('Alice', record(1, score=250))
        self.write('Bob', record(2, name='Bob', score=100))
        self.assertEqual(statistics.cached_statistics(self.root)['completed'], 2)
        result = statistics.cached_statistics(self.root, ['ALICE'])
        self.assertEqual((result['completed'], result['best_score']), (1, 100))

    def test_missing_configuration_is_distinct_from_an_empty_history(self):
        self.assertEqual(statistics.collect_statistics(None), {'available': False})
        self.assertEqual(statistics.collect_statistics(self.root)['completed'], 0)


if __name__ == '__main__':
    unittest.main()
