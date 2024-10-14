import warnings

import numpy as np
from enum import Enum
from scipy.optimize import curve_fit
from nicos.guisupport.qt import QObject


class FitType(Enum):
    LINEAR = 0
    QUADRATIC = 1
    GAUSSIAN = 2


class Fitter1D(QObject):
    """Fitter class for fitting pyqtgraph data."""

    def __init__(self, x_data, y_data, fit_type, parent=None):
        super().__init__(parent)

        self.x_data = x_data
        self.y_data = y_data
        self.fit_type = fit_type
        self.fit_params = None

    def fit(self):
        estimator_func = self._get_estimator_func()
        function = self._get_function()

        initial_guess = estimator_func()

        if initial_guess is None:
            self.fit_params = None
            return None

        try:
            self.fit_params, _ = curve_fit(
                function, self.x_data, self.y_data, p0=initial_guess
            )
        except RuntimeError as e:
            self.fit_params = None
            print(f"Fit failed: {e}")
        return self.fit_params

    def get_result(self):
        """
        Get the result of the fit.
        """
        if self.fit_params is None:
            self.fit()
        if self.fit_params is None:
            return None
        function = self._get_function()
        return function(self.x_data, *self.fit_params)

    def _get_estimator_func(self):
        """
        Get the correct estimator for the fit type.
        The estimator will generate the initial guess for the fit.
        """
        if self.fit_type == FitType.LINEAR:
            return self._linear_estimator
        elif self.fit_type == FitType.QUADRATIC:
            return self._quadratic_estimator
        elif self.fit_type == FitType.GAUSSIAN:
            return self._gaussian_estimator
        else:
            raise ValueError("Invalid fit type")

    def _get_function(self):
        """
        Get the correct function for the fit type.
        """
        if self.fit_type == FitType.LINEAR:
            return self._linear
        elif self.fit_type == FitType.QUADRATIC:
            return self._quadratic
        elif self.fit_type == FitType.GAUSSIAN:
            return self._gaussian
        else:
            raise ValueError("Invalid fit type")

    def _linear(self, x, a, b):
        return a * x + b

    def _quadratic(self, x, a, b, c):
        return a * x**2 + b * x + c

    def _gaussian(self, x, amplitude, xo, sigma, offset):
        return offset + amplitude * np.exp(-((x - xo) ** 2) / (2 * sigma**2))

    def _linear_estimator(self):
        """
        Estimator for linear fit. Returns initial guesses for the slope and intercept.
        """
        A = np.vstack([self.x_data, np.ones(len(self.x_data))]).T
        slope, intercept = np.linalg.lstsq(A, self.y_data, rcond=None)[0]
        return slope, intercept

    def _quadratic_estimator(self):
        """
        Estimator for quadratic fit. Returns initial guesses for a, b, and c.
        """
        # Fit a simple quadratic to the data using polyfit

        with warnings.catch_warnings():
            warnings.filterwarnings("error")
            try:
                p = np.polyfit(self.x_data, self.y_data, 2)
            except np.RankWarning:
                print("Data not suitable for quadratic fit")
                return None

        return p[0], p[1], p[2]

    def _gaussian_estimator(self):
        """
        Estimator for Gaussian fit. Returns initial guesses for amplitude,
        xo, sigma, and offset.
        """
        amplitude_guess = np.max(self.y_data) - np.min(self.y_data)
        xo_guess = self.x_data[np.argmax(self.y_data)]
        sigma_guess = np.std(self.x_data)
        offset_guess = np.min(self.y_data)
        return amplitude_guess, xo_guess, sigma_guess, offset_guess


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Test 1: Linear Fit
    x_linear = np.linspace(0, 10, 100)
    y_linear = (
        3 * x_linear + 5 + np.random.normal(0, 1, size=x_linear.size)
    )  # y = 3x + 5 with noise

    linear_fitter = Fitter1D(x_linear, y_linear, FitType.LINEAR)
    linear_fitter.fit()
    y_linear_fit = linear_fitter.get_result()

    # Plot linear fit
    plt.figure(figsize=(10, 6))
    plt.scatter(x_linear, y_linear, label="Noisy Data")
    plt.plot(x_linear, y_linear_fit, label="Linear Fit", color="red")
    plt.title("Linear Fit")
    plt.legend()
    plt.show()

    # Test 2: Quadratic Fit
    x_quadratic = np.linspace(-5, 5, 100)
    y_quadratic = (
        2 * x_quadratic**2
        + 3 * x_quadratic
        + 1
        + np.random.normal(0, 2, size=x_quadratic.size)
    )  # y = 2x^2 + 3x + 1 with noise

    quadratic_fitter = Fitter1D(x_quadratic, y_quadratic, FitType.QUADRATIC)
    quadratic_fitter.fit()
    y_quadratic_fit = quadratic_fitter.get_result()

    # Plot quadratic fit
    plt.figure(figsize=(10, 6))
    plt.scatter(x_quadratic, y_quadratic, label="Noisy Data")
    plt.plot(x_quadratic, y_quadratic_fit, label="Quadratic Fit", color="green")
    plt.title("Quadratic Fit")
    plt.legend()
    plt.show()

    # Test 3: Gaussian Fit
    x_gaussian = np.linspace(0, 10, 100)
    y_gaussian = 4 * np.exp(-((x_gaussian - 5) ** 2) / (2 * 1.2**2)) + np.random.normal(
        0, 0.2, size=x_gaussian.size
    )  # Gaussian with noise

    gaussian_fitter = Fitter1D(x_gaussian, y_gaussian, FitType.GAUSSIAN)
    gaussian_fitter.fit()
    y_gaussian_fit = gaussian_fitter.get_result()

    # Plot Gaussian fit
    plt.figure(figsize=(10, 6))
    plt.scatter(x_gaussian, y_gaussian, label="Noisy Data")
    plt.plot(x_gaussian, y_gaussian_fit, label="Gaussian Fit", color="purple")
    plt.title("Gaussian Fit")
    plt.legend()
    plt.show()
