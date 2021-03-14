import numpy as np

from sklearn.base import is_classifier, clone
from skactiveml.utils import check_random_state

import skactiveml.pool._probal as probal
from ..base import SingleAnnotStreamBasedQueryStrategy
from ..classifier import PWC

from .budget_manager import BIQF


class PAL(SingleAnnotStreamBasedQueryStrategy):
    def __init__(
        self,
        clf=None,
        budget_manager=BIQF(),
        random_state=None,
        prior=1.0e-3,
        m_max=2,
    ):
        self.clf = clf
        self.budget_manager = budget_manager
        self.random_state = random_state
        self.prior = prior
        self.m_max = m_max

    def query(
        self, X_cand, X, y, return_utilities=False, simulate=False, **kwargs
    ):
        """Ask the query strategy which instances in X_cand to acquire.

        Please note that, when the decisions from this function may differ from
        the final sampling, simulate=True can set, so that the query strategy
        can be updated later with update(...) with the final sampling. This is
        especially helpful, when developing wrapper query strategies.

        Parameters
        ----------
        X_cand : {array-like, sparse matrix} of shape (n_samples, n_features)
            The instances which may be sampled. Sparse matrices are accepted
            only if they are supported by the base query strategy.

        return_utilities : bool, optional
            If true, also return the utilities based on the query strategy.
            The default is False.

        simulate : bool, optional
            If True, the internal state of the query strategy before and after
            the query is the same. This should only be used to prevent the
            query strategy from adapting itself. Note, that this is propagated
            to the budget_manager, as well. The default is False.

        Returns
        -------
        sampled_indices : ndarray of shape (n_sampled_instances,)
            The indices of instances in X_cand which should be sampled, with
            0 <= n_sampled_instances <= n_samples.

        utilities: ndarray of shape (n_samples,), optional
            The utilities based on the query strategy. Only provided if
            return_utilities is True.
        """
        self._validate_data(X_cand, return_utilities, X, y, simulate)

        k_vec = self.clf_.predict_freq(X_cand)
        utilities = probal._cost_reduction(
            k_vec, prior=self.prior, m_max=self.m_max
        )
        sampled_indices = self.budget_manager_.sample(utilities)

        if return_utilities:
            return sampled_indices, utilities
        else:
            return sampled_indices

    def update(self, X_cand, sampled, budget_manager_kwargs={}, **kwargs):
        # check if a budget_manager is set
        self._validate_budget_manager()
        self.budget_manager_.update(sampled, **budget_manager_kwargs)
        return self

    def _validate_data(
        self,
        X_cand,
        return_utilities,
        X,
        y,
        simulate,
        reset=True,
        **check_X_cand_params
    ):
        """Validate input data and set or check the `n_features_in_` attribute.

        Parameters
        ----------
        X_cand: array-like, shape (n_candidates, n_features)
            Candidate samples.
        return_utilities : bool,
            If true, also return the utilities based on the query strategy.
        reset : bool, default=True
            Whether to reset the `n_features_in_` attribute.
            If False, the input will be checked for consistency with data
            provided when reset was last True.
        **check_X_cand_params : kwargs
            Parameters passed to :func:`sklearn.utils.check_array`.

        Returns
        -------
        X_cand: np.ndarray, shape (n_candidates, n_features)
            Checked candidate samples
        return_utilities : bool,
            Checked boolean value of `return_utilities`.
        random_state : np.random.RandomState,
            Checked random state to use.
        """
        X_cand, return_utilities, simulate = super()._validate_data(
            X_cand,
            return_utilities,
            simulate,
            reset=reset,
            **check_X_cand_params
        )

        self._validate_clf(X, y)
        self._validate_prior()
        self._validate_m_max()
        self._validate_random_state()

        return X_cand, return_utilities, X, y, simulate

    def _validate_clf(self, X, y):
        # check if clf is a classifier
        if X is not None and y is not None:
            if self.clf is None:
                self.clf_ = PWC(
                    random_state=self.random_state_.randint(2 ** 31 - 1)
                )
            elif is_classifier(self.clf):
                self.clf_ = clone(self.clf)
            else:
                raise TypeError(
                    "clf is not a classifier. Please refer to "
                    + "sklearn.base.is_classifier"
                )
            self.clf_.fit(X, y)
            # check if y is not multi dimensinal
            if isinstance(y, np.ndarray):
                if y.ndim > 1:
                    raise ValueError("{} is not a valid Value for y")
        else:
            self.clf_ = self.clf

    def _validate_prior(self):
        # check if prior is set
        if not isinstance(self.prior, float) and not None:
            raise TypeError("{} is not a valid type for prior")
        if self.prior <= 0:
            raise ValueError(
                "The value of prior is incorrect."
                + " prior must be greater than 0"
            )

    def _validate_m_max(self):
        # check if m_max is set
        if not isinstance(self.m_max, int):
            raise TypeError("{} is not a valid type for m_max")
        if self.m_max <= 0:
            raise ValueError(
                "The value of m_max is incorrect."
                + " m_max must be greater than 0"
            )

    def _validate_random_state(self):
        if not hasattr(self, "random_state_"):
            self.random_state_ = self.random_state
        self.random_state_ = check_random_state(self.random_state_)
