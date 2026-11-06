import unittest

from hayes.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.s = Store(force_memory=True)

    def test_dedupe(self):
        self.assertTrue(self.s.is_empty())
        self.assertTrue(self.s.add_if_new("a"))
        self.assertFalse(self.s.add_if_new("a"))
        self.assertFalse(self.s.is_empty())

    def test_order_and_cap(self):
        for n in range(5):
            self.s.push_item({"n": n}, keep=3)
        self.assertEqual([i["n"] for i in self.s.list_items(10)], [4, 3, 2])

    def test_lock(self):
        self.assertTrue(self.s.acquire_lock(30))
        self.assertFalse(self.s.acquire_lock(30))
        self.s.release_lock()
        self.assertTrue(self.s.acquire_lock(30))


if __name__ == "__main__":
    unittest.main()
