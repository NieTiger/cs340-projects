from typing import Dict, List, NamedTuple, Set, Tuple
from abc import ABC
from collections import defaultdict
import math
import heapq
import unittest

__all__ = ("Neighbor", "Edge", "Graph", "dijkstra")


class Neighbor(NamedTuple):
    id: int
    weight: int

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
    weight: int
    node1: int
    node2: int


class _Graph(ABC):
    """Currently not used"""

    def new_vertex(self, u):
        raise NotImplementedError

    def add_edge(self, u: int, v: int, weight: int) -> None:
        raise NotImplementedError

    def has_edge(self, u: int, v: int) -> bool:
        raise NotImplementedError

    def get_vertices(self) -> Set[int]:
        raise NotImplementedError

    def get_neighbors(self, v: int) -> Set[int]:
        raise NotImplementedError


class Graph:
    """
    Graph ADT
    """

    def __init__(self):
        self.adj: Dict[int, List[Neighbor]] = defaultdict(list)

    def _find_neighbor(self, root, neighbor):
        "If yes, return index of the neighbor in root's adj list, else return None"
        neighbors = self.adj[root]
        try:
            i = neighbors.index(Neighbor(id=neighbor, weight=-1))
        except ValueError:
            return None
        else:
            return i

    def get_vertices(self) -> Set[int]:
        return set(self.adj.keys())

    def get_neighbors(self, node: int) -> List[Neighbor]:
        return self.adj[node]

    def has_edge(self, n1: int, n2: int) -> bool:
        i = self._find_neighbor(n1, n2)
        return i is not None

    def get_edge(self, n1: int, n2: int) -> Edge:
        i2 = self._find_neighbor(n1, n2)
        if i2 is not None:
            return Edge(
                node1=n1,
                node2=n2,
                weight=self.adj[n1][i2].weight,
            )
        else:
            raise ValueError

    def add_edge(self, n1: int, n2: int, weight: int):
        neighbor2 = Neighbor(id=n2, weight=weight)
        neighbor1 = Neighbor(id=n1, weight=weight)

        self.adj[n1].append(neighbor2)
        self.adj[n2].append(neighbor1)

    def update_edge(self, n1, n2, weight):
        i2 = self._find_neighbor(n1, n2)

        neighbor2 = Neighbor(id=n2, weight=weight)
        neighbor1 = Neighbor(id=n1, weight=weight)

        i1 = self._find_neighbor(n2, n1)

        self.adj[n1][i2] = neighbor2
        self.adj[n2][i1] = neighbor1

    def remove_edge(self, n1, n2):
        i2 = self._find_neighbor(n1, n2)
        if i2 is not None:
            # edge exists
            i1 = self._find_neighbor(n2, n1)
            del self.adj[n1][i2], self.adj[n2][i1]


def dijkstra(g: Graph, start: int) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Run Dijkstra's shortest path algorithm on `g` from `start`
    Returns two dictionaries, pred and dist
    """
    vertices = g.get_vertices()
    dist: Dict[int, int] = {v: math.inf for v in vertices}
    pred: Dict[int, int] = {v: None for v in vertices}
    dist[start] = 0
    done: Set[int] = set()
    todo: List[Tuple[int, int]] = [(0, start)]  # priority queue of (distance, vertex)

    while todo:
        _, v = heapq.heappop(todo)
        if v not in done:
            done.add(v)
            for edge in g.get_neighbors(v):
                u = edge.id
                if dist[v] + edge.weight <= dist[u]:
                    dist[u] = dist[v] + edge.weight
                    pred[u] = v
                    heapq.heappush(todo, (dist[u], u))

    return pred, dist


def _make_test_graph():
    g = Graph()
    g.add_edge(1, 2, 1)
    g.add_edge(2, 3, 5)
    g.add_edge(3, 1, 2)

    g.add_edge(3, 4, 2)
    g.add_edge(3, 5, 1)
    g.add_edge(4, 5, 2)
    return g


def _make_test_graph2():
    g = Graph()
    g.add_edge(1, 2, 1)
    g.add_edge(1, 3, 2)
    g.add_edge(2, 4, 3)
    g.add_edge(2, 5, 6)
    g.add_edge(3, 4, 5)
    g.add_edge(3, 5, 4)
    g.add_edge(4, 6, 6)
    g.add_edge(5, 6, 3)
    return g


class TestGraph(unittest.TestCase):
    def test_remove_edge(self):
        g = _make_test_graph()
        g.remove_edge(1, 2)
        try:
            g.get_edge(1, 2)
        except ValueError:
            pass
        else:
            self.assertTrue(False)

    def test_update_edge(self):
        g = _make_test_graph()
        g.update_edge(1, 2, 10)
        e = g.get_edge(1, 2)
        self.assertEqual(e.weight, 10)
        g.update_edge(1, 2, 20)
        e = g.get_edge(1, 2)
        self.assertEqual(e.weight, 20)

    def test_has_edge(self):
        g = _make_test_graph()
        self.assertTrue(g.has_edge(1, 2))
        self.assertTrue(g.has_edge(1, 3))
        self.assertTrue(g.has_edge(2, 3))

    def test_get_vertices(self):
        g = _make_test_graph()
        vset = g.get_vertices()
        self.assertIn(1, vset)
        self.assertIn(2, vset)
        self.assertIn(3, vset)

    def test_get_neighbors(self):
        g = _make_test_graph()
        nbors = g.get_neighbors(1)
        self.assertIn(Neighbor(id=2, weight=0), nbors)
        self.assertIn(Neighbor(id=3, weight=0), nbors)


class TestDijkstra(unittest.TestCase):
    def test1(self):
        g = _make_test_graph()
        pred, dist = dijkstra(g, 1)
        self.assertEqual(dist[1], 0)
        self.assertEqual(dist[4], 4)
        self.assertEqual(dist[5], 3)

    def test2(self):
        g = _make_test_graph2()
        pred, dist = dijkstra(g, 1)
        self.assertEqual(pred[6], 5)
        self.assertEqual(pred[5], 3)
        self.assertEqual(pred[4], 2)
        self.assertEqual(pred[2], 1)
        self.assertEqual(pred[3], 1)

        self.assertEqual(dist[6], 9)
        self.assertEqual(dist[5], 6)
        self.assertEqual(dist[3], 2)
        self.assertEqual(dist[2], 1)
        self.assertEqual(dist[4], 4)


if __name__ == "__main__":
    unittest.main()