import time
import warnings

from .utils.sys_info import get_sys_info


class _Callback:
    """Callback class to monitor convergence.

    Parameters
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver that is currently run. This allows to retrieve the results
        with :method:`benchopt.base.Solver.get_result` in the callback.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective and data names, problem dimension, etc.
    stopping_criterion : instance of StoppingCriterion
        Object to check if we need to stop a solver.

    Attributes
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    stopping_criterion : StoppingCriterion
        Object to check if we need to stop a solver.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective and data names, problem dimension, etc.
    info : dict
        A dictionary with info from the current system.
    curve : list
        The convergence curve stored as a list of dict.
    status : 'running' | 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver is or was stopped.
    time_iter : float
        Computation time to reach the current iteration.
        Excluding the times to evaluate objective.
    it : int
        The number of times the callback has been called. It's
        initialized with 0.
    next_stopval : int
        The next iteration for which the curve should be
        updated.
    time_callback : float
        The time when exiting the callback call.
    """

    def __init__(self, objective, solver, meta, stopping_criterion):
        self.objective = objective
        self.solver = solver
        self.meta = meta
        self.stopping_criterion = stopping_criterion

        # Initialize local variables
        self.info = get_sys_info()
        self.curve = []
        self.status = 'running'
        self.it = 0
        self.time_iter = 0.
        self.next_stopval = self.stopping_criterion.init_stop_val()

    def start(self):
        self.time_callback = time.perf_counter()

    def __call__(self, *args):
        # Stop time and update computation time since the beginning
        t0 = time.perf_counter()

        self.time_iter += t0 - self.time_callback

        # Evaluate the iteration if necessary.
        if self.it == self.next_stopval:
            if self.log_value(*args):
                return False

        # Update iteration number and restart time measurement.
        self.it += 1
        self.time_callback = time.perf_counter()
        return True

    def log_value(self, *args):
        """Store the objective value with running time and stop if needed.

        Return True if the solver should be stopped.
        """
        # XXX: remove in 1.5
        if len(args) > 0:
            warnings.warn(
                "Starting 1.5, the callback does not take any arguments. "
                "The results are passed to `Objective.evaluate_result` "
                "directly from `Solver.get_result`.", FutureWarning
            )
            result = args[0]
        else:
            result = self.solver.get_result()

        objective_dict = self.objective(result)
        self.curve.append(dict(
            **self.meta, stop_val=self.it,
            time=self.time_iter,
            **objective_dict, **self.info
        ))

        # Check the stopping criterion
        should_stop_res = self.stopping_criterion.should_stop(
            self.next_stopval, self.curve
        )
        stop, self.status, self.next_stopval = should_stop_res
        return stop

    def get_results(self):
        """Get the results stored by the callback

        Returns
        -------
        curve : list
            Details on the run and the objective value obtained.
        status : 'done' | 'diverged' | 'timeout' | 'max_runs'
            The status on which the solver was stopped.
        """
        return self.curve, self.status
