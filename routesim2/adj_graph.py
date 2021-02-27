import unittest
from typing import Dict, NamedTuple, List
from collections import defaultdict


class Neighbor(NamedTuple):
    id: int
    seq_n: int
    latency: int

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __le__(self, other):
        return self.id <= other.id

    def __ge__(self, other):
        return self.id >= other.id

    def __eq__(self, other):
        return self.id == other.id


class Edge(NamedTuple):
    seq_n: int
    latency: int
    node1: int
    node2: int


class Graph:
    def __init__(self):
        self.adj: Dict[int, List[Neighbors]] = defaultdict(list)

    def _find_neighbor(self, root, neighbor):
        "If yes, return index of the neighbor in root's adj list, else return None"
        neighbors = self.adj[root]
        try:
            i = neighbors.index(Neighbor(id=neighbor, seq_n=-1, latency=-1))
        except ValueError:
            return None
        else:
            return i

    def has_edge(self, n1: int, n2: int) -> bool:
        i = self._find_neighbor(n1, n2)
        return i is not None

    def get_edge(self, n1: int, n2: int) -> Edge:
        i2 = self._find_neighbor(n1, n2)
        if i2 is not None:
            return Edge(
                node1=n1,
                node2=n2,
                latency=self.adj[n1][i2].latency,
                seq_n=self.adj[n1][i2].seq_n,
            )
        else:
            raise ValueError

    def add_edge(self, n1: int, n2: int, latency: int, seq_n: int):
        neighbor2 = Neighbor(id=n2, latency=latency, seq_n=seq_n)
        neighbor1 = Neighbor(id=n1, latency=latency, seq_n=seq_n)

        self.adj[n1].append(neighbor2)
        self.adj[n2].append(neighbor1)

    def update_edge(self, n1, n2, latency, seq_n):
        i2 = self._find_neighbor(n1, n2)

        if self.adj[n1][i2].seq_n < seq_n:
            neighbor2 = Neighbor(id=n2, latency=latency, seq_n=seq_n)
            neighbor1 = Neighbor(id=n1, latency=latency, seq_n=seq_n)

            i1 = self._find_neighbor(n2, n1)

            self.adj[n1][i2] = neighbor2
            self.adj[n2][i1] = neighbor1

    def remove_edge(self, n1, n2):
        i2 = self._find_neighbor(n1, n2)
        if i2 is not None:
            # edge exists
            i1 = self._find_neighbor(n2, n1)
            del self.adj[n1][i2], self.adj[n2][i1]


def _make_test_graph():
    g = Graph()
    g.add_edge(1, 2, 1, 1)
    g.add_edge(2, 3, 5, 1)
    g.add_edge(3, 1, 2, 1)
    return g


class TestGraph(unittest.TestCase):
    def test1(self):
        g = _make_test_graph()
        g.remove_edge(1, 2)
        try:
            g.get_edge(1, 2)
        except ValueError:
            pass
        else:
            self.assertTrue(False)

    def test2(self):
        g = _make_test_graph()
        g.update_edge(1, 2, 10, 2)
        e = g.get_edge(1, 2)
        self.assertEqual(e.latency, 10)
        g.update_edge(1, 2, 20, 0)
        e = g.get_edge(1, 2)
        self.assertEqual(e.latency, 10)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    pass