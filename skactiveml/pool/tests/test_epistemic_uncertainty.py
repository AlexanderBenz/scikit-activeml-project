import unittest

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from skactiveml.classifier import SklearnClassifier, PWC
from skactiveml.pool import EpistemicUncertainty
from skactiveml.pool._epistemic_uncertainty import _interpolate, \
    _pwc_ml_1, _pwc_ml_0, _epistemic_uncertainty_pwc, \
    _loglike_logreg, _pi_h, _epistemic_uncertainty_logreg, _theta
from skactiveml.utils import MISSING_LABEL


class TestEpistemicUncertainty(unittest.TestCase):

    def setUp(self):
        self.random_state = 1
        self.X_cand = np.array([[8, 1], [9, 1], [5, 1]])
        self.X = np.array([[1, 2], [5, 8], [8, 4], [5, 4]])
        self.y = np.array([0, 0, 1, 1])
        self.y_MISSING_LABEL = np.array([MISSING_LABEL, MISSING_LABEL,
                                         MISSING_LABEL, MISSING_LABEL])
        self.classes = np.array([0, 1])
        self.clf = PWC(classes=self.classes, random_state=self.random_state)
        self.kwargs = dict(X_cand=self.X_cand, X=self.X, y=self.y)
        self.kwargs_MISSING_LABEL = dict(X_cand=self.X_cand, X=self.X,
                                         y=self.y_MISSING_LABEL)

    def test_init_param_precompute(self):
        selector = EpistemicUncertainty(precompute=None)
        self.assertRaises(TypeError, selector.query, **self.kwargs,
                          clf=self.clf)

        selector = EpistemicUncertainty(precompute=[])
        self.assertRaises(TypeError, selector.query, **self.kwargs,
                          clf=self.clf)

        selector = EpistemicUncertainty(precompute=0)
        self.assertRaises(TypeError, selector.query, **self.kwargs,
                          clf=self.clf)

    def test_init_param_random_state(self):
        selector = EpistemicUncertainty(random_state='string')
        self.assertRaises(ValueError, selector.query, **self.kwargs,
                          clf=self.clf)
        selector = EpistemicUncertainty(random_state=self.random_state)
        self.assertTrue(hasattr(selector, 'random_state'))
        self.assertRaises(ValueError, selector.query, X_cand=[[1]],
                          clf=self.clf, X=self.X, y=self.y)

    def test_query_param_X_cand(self):
        selector = EpistemicUncertainty()
        self.assertRaises(ValueError, selector.query, X_cand=[], clf=self.clf,
                          X=self.X, y=self.y)
        self.assertRaises(ValueError, selector.query, X_cand=None,
                          clf=self.clf, X=self.X, y=self.y)
        self.assertRaises(ValueError, selector.query, X_cand=np.nan,
                          clf=self.clf, X=self.X, y=self.y)

    def test_query_param_clf(self):
        selector = EpistemicUncertainty()
        dt = SklearnClassifier(DecisionTreeClassifier())
        for clf in [None, 'string', 1, dt]:
            self.assertRaises(
                TypeError, selector.query, **self.kwargs, clf=clf
            )

    def test_query_param_X(self):
        selector = EpistemicUncertainty()
        self.assertRaises(ValueError, selector.query, X_cand=self.X_cand,
                          clf=self.clf, X=None, y=self.y)
        self.assertRaises(ValueError, selector.query, X_cand=self.X_cand,
                          clf=self.clf, X='string', y=self.y)
        self.assertRaises(ValueError, selector.query, X_cand=self.X_cand,
                          clf=self.clf, X=[], y=self.y)
        self.assertRaises(ValueError, selector.query, X_cand=self.X_cand,
                          clf=self.clf, X=self.X[0:-1], y=self.y)

    def test_query_param_y(self):
        selector = EpistemicUncertainty()
        y_list = [None, 'string', [], self.y[0:-1]]
        for y in y_list:
            self.assertRaises(
                ValueError, selector.query, X_cand=self.X_cand, clf=self.clf,
                X=self.X, y=y
            )

    def test_query_param_sample_weight(self):
        selector = EpistemicUncertainty()
        sample_weight_list = [
            'string', self.X_cand, self.X_cand[:-2],
            np.empty((len(self.X) - 1)), np.empty((len(self.X) + 1))
        ]
        for sample_weight in sample_weight_list:
            self.assertRaises(ValueError, selector.query, **self.kwargs,
                              clf=self.clf, sample_weight=sample_weight)

    def test_query_param_batch_size(self):
        selector = EpistemicUncertainty()
        for batch_size in ['string', 1.2]:
            self.assertRaises(TypeError, selector.query, **self.kwargs,
                              clf=self.clf, batch_size=batch_size)
        for batch_size in [0, -10]:
            self.assertRaises(ValueError, selector.query, **self.kwargs,
                              clf=self.clf, batch_size=batch_size)

    def test_query_param_return_utilities(self):
        selector = EpistemicUncertainty()
        for return_utilities in [None, [], 0]:
            self.assertRaises(TypeError, selector.query, **self.kwargs,
                              clf=self.clf, return_utilities=return_utilities)

    # tests for epistemic PWC
    def test_interpolate(self):
        interpolated = _interpolate(np.array([[0, 0], [1, 1]]),
                                    np.array([[0.5, 0.5]]))
        np.testing.assert_array_equal(interpolated, np.array([0.5]))

    def test_pwc_ml_1(self):
        self.assertEqual(1.0, -_pwc_ml_1(None, 0.0, 0.0))
        self.assertEqual(0.0, -_pwc_ml_1(1, 0.5, 0.8))
        self.assertAlmostEqual(0.36, -_pwc_ml_1(0.9, 1, 1))
        self.assertEqual(-0.8, -_pwc_ml_1(0.1, 1, 1))

    def test_pwc_ml_0(self):
        self.assertEqual(1.0, -_pwc_ml_0(None, 0.0, 0.0))
        self.assertEqual(-1.0, -_pwc_ml_0(1, 0.5, 0.8))
        self.assertAlmostEqual(0.36, -_pwc_ml_0(0.1, 1, 1))
        self.assertEqual(-0.8, -_pwc_ml_0(0.9, 1, 1))

    def test_epistemic_uncertainty_pwc(self):
        freq = np.empty((121, 2))
        for n in range(11):
            for p in range(11):
                freq[n * 11 + p] = n, p

        indices = [39, 27, 18, 68, 20]
        expected = np.array([0.23132135217407046,
                             0.22057583593855598,
                             0.056099946963575974,
                             0.16316360415548017,
                             0.021220951860586187])

        utilities, arr = _epistemic_uncertainty_pwc(freq, None)
        self.assertEqual(utilities.shape, (121,))
        np.testing.assert_allclose(expected, utilities[indices])
        _epistemic_uncertainty_pwc(np.array([[2.5, 1.5]]), None)

        val_utilities = utilities
        precompute_array = np.full((1, 1), np.nan)

        utilities, precompute_array = _epistemic_uncertainty_pwc(
            freq, precompute_array)
        np.testing.assert_array_equal(val_utilities, utilities)
        np.testing.assert_array_equal(
            val_utilities, precompute_array[:11, :11].flatten())

        class Dummy_PWC(PWC):
            def predict_freq(self, X):
                return freq

        selector = EpistemicUncertainty(precompute=True)
        _, utilities = selector.query(**self.kwargs,
                                      clf=Dummy_PWC(classes=self.classes),
                                      return_utilities=True)
        np.testing.assert_array_equal(val_utilities, utilities[0])

        selector = EpistemicUncertainty()
        self.assertRaises(ValueError, selector.query,
                          clf=PWC(classes=[0, 1, 2]), **self.kwargs)


    # tests for epistemic logistic regression
    def test_loglike_logreg(self):
        w = np.array([0, 0])
        X = np.array([[0]])
        y = np.array([0])
        self.assertEqual(0, _loglike_logreg(None, X=[], y=[]))
        self.assertEqual(2.0, np.exp(_loglike_logreg(w=w, X=X, y=y)))

    def test_pi_h(self):
        w = np.array([0, 0])
        X = np.array([[3]])
        y = np.array([1])
        expected = np.exp(-_loglike_logreg(w, X, y))

        # w has to be np.zeros for the follow tests
        self.assertEqual(expected, _pi_h(w, 1, X, y))
        self.assertEqual(2 ** -len(X), _pi_h(w, 1, X, y))

    def test_theta(self):
        def func1(x):
            return x[0] * x[0] - x[1] * x[1]

        def func2(x):
            return -x[0] * x[0] + x[1] * x[1]

        alpha = 0.5
        x0 = np.array([1, 0])
        A = np.array([0, 1])
        self.assertTrue((_theta(func1, alpha, x0, A) == 0).all())
        self.assertTrue(np.isnan(_theta(func2, alpha, x0, A)).all())

    def test_epistemic_uncertainty_logreg(self):
        clf = SklearnClassifier(
            LogisticRegression(), classes=[0, 1, 2],
            random_state=self.random_state
        )
        self.assertRaises(ValueError, _epistemic_uncertainty_logreg,
                          **self.kwargs, clf=clf)

        clf = SklearnClassifier(
            DecisionTreeClassifier(), classes=[0, 1],
            random_state=self.random_state
        )
        self.assertRaises(TypeError, _epistemic_uncertainty_logreg,
                          **self.kwargs, clf=clf)

        self.assertRaises(TypeError, _epistemic_uncertainty_logreg,
                          **self.kwargs, clf=self.clf)

        probas = np.array([[0.5, 0.5]])
        X = np.array([[0]])
        X_cand = np.array([[3]])
        y = np.array([0])
        #utils_expected = np.array()
        clf = SklearnClassifier(LogisticRegression(), classes=[0, 1])
        clf.fit(X, y)
        utils = _epistemic_uncertainty_logreg(X_cand, X, y, clf, probas)
        #np.testing.assert_array_equal(utils_expected, utils)
        # TODO

    def test_query(self):
        selector = EpistemicUncertainty()

        # return_utilities
        L = list(selector.query(**self.kwargs, clf=self.clf,
                                return_utilities=True))
        self.assertTrue(len(L) == 2)
        L = list(selector.query(**self.kwargs, clf=self.clf,
                                return_utilities=False))
        self.assertTrue(len(L) == 1)

        # batch_size
        bs = 3
        selector = EpistemicUncertainty()
        best_idx = selector.query(**self.kwargs, clf=self.clf,
                                  batch_size=bs)
        self.assertEqual(bs, len(best_idx))

        # query - PWC
        clf = PWC(classes=self.classes, random_state=self.random_state)
        selector = EpistemicUncertainty()
        selector.query(**self.kwargs, clf=clf)
        selector.query(**self.kwargs_MISSING_LABEL, clf=clf)

        best_indices, utilities = selector.query(**self.kwargs, clf=clf,
                                                 return_utilities=True)
        self.assertEqual(utilities.shape, (1, len(self.X_cand)))
        self.assertEqual(best_indices.shape, (1,))

        # query - logistic regression
        clf = SklearnClassifier(
            LogisticRegression(), classes=self.classes,
            random_state=self.random_state
        )

        selector = EpistemicUncertainty()
        selector.query(**self.kwargs, clf=clf)
        selector.query(**self.kwargs_MISSING_LABEL, clf=clf)

        best_indices, utilities = selector.query(**self.kwargs, clf=clf,
                                                 return_utilities=True)
        self.assertEqual(utilities.shape, (1, len(self.X_cand)))
        self.assertEqual(best_indices.shape, (1,))

        best_indices_s, utilities_s = selector.query(
            **self.kwargs, clf=clf, return_utilities=True,
            sample_weight=[0.5, 1, 1, 1]
        )
        comp = utilities_s == utilities
        self.assertTrue(not comp.all())

