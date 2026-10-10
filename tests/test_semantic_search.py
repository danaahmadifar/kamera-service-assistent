"""Mathematische Vergleichsfälle und Zuordnung der API-Vektoren prüfen."""

import unittest

from camera_service.semantic_search import cosine_similarity, read_embeddings


class SemanticSearchTests(unittest.TestCase):
    def test_same_direction_is_one_even_with_different_lengths(self):
        self.assertAlmostEqual(cosine_similarity([1, 2], [3, 6]), 1.0)

    def test_perpendicular_and_opposite_directions(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)

    def test_zero_vector_and_dimension_mismatch_are_rejected(self):
        for left, right in [([0, 0], [1, 0]), ([1], [1, 2])]:
            with self.subTest(left=left, right=right):
                with self.assertRaises(ValueError):
                    cosine_similarity(left, right)

    def test_response_order_does_not_change_text_assignment(self):
        response = {"data": [
            {"index": 1, "embedding": [0, 1]},
            {"index": 0, "embedding": [1, 0]},
        ]}
        self.assertEqual(read_embeddings(response, 2), [[1, 0], [0, 1]])

    def test_incomplete_duplicate_and_invalid_vectors_are_rejected(self):
        entries = [
            [{"index": 0, "embedding": [1, 0]}],
            [{"index": 0, "embedding": [1]}, {"index": 0, "embedding": [2]}],
            [{"index": 0, "embedding": [float("nan")]}, {"index": 1, "embedding": [1]}],
        ]
        for data in entries:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    read_embeddings({"data": data}, 2)
