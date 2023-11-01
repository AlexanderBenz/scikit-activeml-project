import unittest

import numpy as np
from sklearn.datasets import make_classification
from sklearn.naive_bayes import GaussianNB
from skactiveml.utils import MISSING_LABEL
from skactiveml.classifier import ParzenWindowClassifier, SklearnClassifier
from skactiveml.stream import StreamProbabilisticAL
from skactiveml.tests.template_query_strategy import (
    TemplateSingleAnnotatorStreamQueryStrategy,
)
from sklearn.svm import SVC


class TestStreamProbabilisticAL(
    TemplateSingleAnnotatorStreamQueryStrategy, unittest.TestCase
):
    def setUp(self):
        self.classes = [0, 1]
        X = np.array([[1, 2], [5, 8], [8, 4], [5, 4]])
        y = np.array([0, 0, MISSING_LABEL, MISSING_LABEL])
        clf = ParzenWindowClassifier(random_state=0, classes=self.classes).fit(
            X, y
        )
        query_default_params_clf = {
            "candidates": np.array([[1, 2]]),
            "X": X,
            "clf": clf,
            "y": y,
        }
        super().setUp(
            qs_class=StreamProbabilisticAL,
            init_default_params={},
            query_default_params_clf=query_default_params_clf,
        )
        self.update_params = {
            "candidates": [[]],
            "queried_indices": [],
            "budget_manager_dict": {"utilities": 0.0},
        }

    def test_query_param_clf(self):
        add_test_cases = [
            (GaussianNB(), TypeError),
            (SklearnClassifier(SVC()), TypeError),
            (ParzenWindowClassifier(), None),
        ]
        super().test_query_param_clf(test_cases=add_test_cases)

    def test_query(self):
        expected_output = []
        expected_utilities = [0.0170216]
        budget_manager_param_dict = {"utilities": [0.5, 0.5, 0.5, 0.5, 0.5]}
        return super().test_query(
            expected_output, expected_utilities, budget_manager_param_dict
        )

    def test_query_param_utility_weight(self):
        test_cases = []
        test_cases += [
            ([1, 1], ValueError),
            ("string", ValueError),
            (["string", "string"], ValueError),
            (0.5, TypeError),
        ]
        self._test_param("query", "utility_weight", test_cases)

    def test_init_param_prior(self):
        test_cases = []
        test_cases += [
            ("string", TypeError),
            (0.0, ValueError),
            (-1.0, ValueError),
            (0.5, None),
        ]
        self._test_param("init", "prior", test_cases)

    def test_init_param_m_max(self):
        test_cases = []
        test_cases += [
            (0.1, TypeError),
            (0, ValueError),
            (-1, ValueError),
            (2, None),
        ]
        self._test_param("init", "m_max", test_cases)

    def test_init_param_metric(self):
        test_cases = []
        test_cases += [("rbf", None), ("", ValueError), (0.5, ValueError)]
        self._test_param("init", "metric", test_cases)

    def test_init_param_metric_dict(self):
        test_cases = []
        test_cases += [
            ({"gamma": "mean"}, None),
            (["gamma"], TypeError),
            ({"test": 0}, TypeError),
        ]
        replace_init_params = {"metric": "rbf"}
        self._test_param(
            "init",
            "metric_dict",
            test_cases,
            replace_init_params=replace_init_params,
        )
