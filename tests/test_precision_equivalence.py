"""Precision equivalence tests: float32 vs float64 PID.

Proves the PID algorithm is numerically stable under single-precision
(cortex_m4, aurix_tc397) by comparing against double-precision (desktop).
Uses struct module for float32 truncation — no numpy dependency.
"""

import struct
from pathlib import Path

import yaml


def _to_float32(x: float) -> float:
    """Truncate a Python float to IEEE 754 single precision."""
    return struct.unpack('f', struct.pack('f', x))[0]


def _load_pid_params() -> dict:
    """Load PID parameters from the model YAML."""
    model_path = Path(__file__).parent.parent / "models" / "pid_controller.yaml"
    with open(model_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    model = data["model"]
    pid_block = next(b for b in model["blocks"] if b["type"] == "pid")
    return {
        "Kp": pid_block["params"]["Kp"],
        "Ki": pid_block["params"]["Ki"],
        "Kd": pid_block["params"]["Kd"],
        "output_min": pid_block["params"]["output_min"],
        "output_max": pid_block["params"]["output_max"],
        "dt": model["sample_time_s"],
    }


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi]."""
    if value > hi:
        return hi
    if value < lo:
        return lo
    return value


def _pid_step_f64(
    setpoint: float, measured: float, integral: float, prev_error: float,
    Kp: float, Ki: float, Kd: float, output_min: float, output_max: float, dt: float,
) -> tuple[float, float, float]:
    """One PID step in double precision. Returns (output, integral, prev_error)."""
    error = setpoint - measured
    p_term = Kp * error
    integral += error * dt
    integral = _clamp(integral, output_min, output_max)
    i_term = Ki * integral
    d_term = Kd * (error - prev_error) / dt if dt > 0 else 0.0
    output = _clamp(p_term + i_term + d_term, output_min, output_max)
    return output, integral, error


def _pid_step_f32(
    setpoint: float, measured: float, integral: float, prev_error: float,
    Kp: float, Ki: float, Kd: float, output_min: float, output_max: float, dt: float,
) -> tuple[float, float, float]:
    """One PID step in single precision (all intermediates truncated to float32)."""
    f = _to_float32
    error = f(f(setpoint) - f(measured))
    p_term = f(f(Kp) * error)
    integral = f(f(integral) + f(error * f(dt)))
    integral = f(_clamp(integral, f(output_min), f(output_max)))
    i_term = f(f(Ki) * integral)
    d_term = f(f(Kd) * f(f(error - f(prev_error)) / f(dt))) if f(dt) > 0.0 else 0.0
    output = f(_clamp(f(p_term + f(i_term + d_term)), f(output_min), f(output_max)))
    return output, integral, error


# --- Tests ---

class TestPrecisionEquivalence:
    """Verify float32 and float64 PID produce equivalent results."""

    def setup_method(self) -> None:
        self.params = _load_pid_params()

    def test_zero_input_both_precisions(self):
        """Both precisions should produce zero output for zero input."""
        p = self.params
        out64, _, _ = _pid_step_f64(0.0, 0.0, 0.0, 0.0, **p)
        out32, _, _ = _pid_step_f32(0.0, 0.0, 0.0, 0.0, **p)
        assert out64 == 0.0
        assert out32 == 0.0

    def test_single_step_equivalence(self):
        """A single step with nonzero input should match within tolerance."""
        p = self.params
        out64, _, _ = _pid_step_f64(10.0, 5.0, 0.0, 0.0, **p)
        out32, _, _ = _pid_step_f32(10.0, 5.0, 0.0, 0.0, **p)
        assert abs(out64 - out32) < 1e-2, f"f64={out64}, f32={out32}"

    def test_100_step_trajectory(self):
        """Run 100 steps and verify outputs stay within 1e-4 relative tolerance."""
        p = self.params
        Kp, Ki, Kd = p["Kp"], p["Ki"], p["Kd"]
        omin, omax, dt = p["output_min"], p["output_max"], p["dt"]

        int64 = prev64 = 0.0
        int32 = prev32 = 0.0

        max_rel_error = 0.0

        for i in range(100):
            # Varying setpoint, constant measured — simulates step response
            setpoint = 50.0 if i < 50 else 25.0
            measured = 30.0 + i * 0.1

            out64, int64, prev64 = _pid_step_f64(
                setpoint, measured, int64, prev64, Kp, Ki, Kd, omin, omax, dt
            )
            out32, int32, prev32 = _pid_step_f32(
                setpoint, measured, int32, prev32, Kp, Ki, Kd, omin, omax, dt
            )

            # Relative error (avoid division by zero)
            denom = max(abs(out64), 1e-10)
            rel_error = abs(out64 - out32) / denom
            max_rel_error = max(max_rel_error, rel_error)

        assert max_rel_error < 1e-4, f"Max relative error {max_rel_error:.6e} exceeds 1e-4"

    def test_saturation_equivalence(self):
        """Both precisions should saturate at the same limits."""
        p = self.params
        # Large error → should saturate at output_max
        out64, _, _ = _pid_step_f64(1000.0, 0.0, 0.0, 0.0, **p)
        out32, _, _ = _pid_step_f32(1000.0, 0.0, 0.0, 0.0, **p)
        assert out64 == p["output_max"]
        assert out32 == _to_float32(p["output_max"])

    def test_negative_saturation_equivalence(self):
        """Both precisions should saturate at output_min for large negative error."""
        p = self.params
        out64, _, _ = _pid_step_f64(0.0, 1000.0, 0.0, 0.0, **p)
        out32, _, _ = _pid_step_f32(0.0, 1000.0, 0.0, 0.0, **p)
        assert out64 == p["output_min"]
        assert out32 == _to_float32(p["output_min"])

    def test_integral_accumulation_stability(self):
        """Integral should not diverge between precisions over 100 steps."""
        p = self.params
        Kp, Ki, Kd = p["Kp"], p["Ki"], p["Kd"]
        omin, omax, dt = p["output_min"], p["output_max"], p["dt"]

        int64 = prev64 = 0.0
        int32 = prev32 = 0.0

        for _ in range(100):
            _, int64, prev64 = _pid_step_f64(
                10.0, 9.5, int64, prev64, Kp, Ki, Kd, omin, omax, dt
            )
            _, int32, prev32 = _pid_step_f32(
                10.0, 9.5, int32, prev32, Kp, Ki, Kd, omin, omax, dt
            )

        # Integral values should be very close
        assert abs(int64 - int32) < 1e-3, f"Integral divergence: f64={int64}, f32={int32}"
