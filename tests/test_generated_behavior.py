"""Compile and execute generated C against independent numerical expectations.

Both real_T configurations run on the host; this is not target-hardware testing.
A C compiler is a required test dependency, not a silently skipped check.
"""
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from bakec.engine import CodegenEngine, c_real_literal
from bakec.parser import parse_model, parse_platform
from bakec.validator import validate_model
from bakec.writer import write_generated_files


@pytest.fixture(params=["desktop", "cortex_m4"])
def platform(request):
    return request.param


def execute(tmp_path, model, platform, body):
    compiler = shutil.which("cc") or shutil.which("gcc")
    assert compiler, "Generated-C behavior tests require a C99 compiler (cc or gcc)"
    model_path = tmp_path / "model.yaml"
    model_path.write_text(yaml.safe_dump(model), encoding="utf-8")
    parsed = parse_model(model_path)
    assert validate_model(parsed) == []
    platform_path = Path(f"platforms/{platform}.yaml")
    engine = CodegenEngine(parsed, parse_platform(platform_path), str(model_path), str(platform_path))
    write_generated_files(engine.render_all(), tmp_path)
    name = parsed["model"]["name"]
    driver = tmp_path / "driver.c"
    driver.write_text(f'#include <stdio.h>\n#include "{name}_controller.h"\n'
                      f'int main(void) {{\n{body}\nreturn 0;\n}}\n')
    executable = tmp_path / "run"
    built = subprocess.run([compiler, "-std=c99", "-O2", "-pedantic-errors",
                            str(tmp_path / f"{name}_controller.c"),
                            str(tmp_path / f"{name}_controller_data.c"), str(driver),
                            "-lm", "-o", str(executable)], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    ran = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    return [float(line) for line in ran.stdout.splitlines()]


def pid():
    return parse_model(Path("models/pid_controller.yaml"))


def test_pid_repeat_initialize(tmp_path, platform):
    values = execute(tmp_path, pid(), platform, '''
        for (int run = 0; run < 3; ++run) {
            pid_pressure_initialize();
            pid_pressure_U.setpoint = 1;
            pid_pressure_step();
            printf("%.17g\\n", (double)pid_pressure_Y.command);
            pid_pressure_step();
            printf("%.17g\\n", (double)pid_pressure_Y.command);
        }
    ''')
    # P=2.5, I=0.8 * accumulated(error * 0.001), D=0.1 * delta(error)/0.001.
    assert values == pytest.approx([102.5008, 2.5016] * 3, rel=2e-6)


@pytest.mark.parametrize("state_mode,first,second", [
    ("absent", 102.5008, 2.5016),
    ("default", 102.5008, 2.5016),
    ("initial", 54.1008, 4.1016),
])
def test_pid_optional_and_initial_state(tmp_path, platform, state_mode, first, second):
    model = pid()
    if state_mode == "absent":
        del model["model"]["state"]
    elif state_mode == "default":
        for state in model["model"]["state"]:
            del state["initial_value"]
    else:
        model["model"]["state"][0]["initial_value"] = 2
        model["model"]["state"][1]["initial_value"] = 0.5
    values = execute(tmp_path, model, platform, '''
        for (int run = 0; run < 2; ++run) {
            pid_pressure_initialize();
            pid_pressure_U.setpoint = 1;
            pid_pressure_step();
            printf("%.17g\\n", (double)pid_pressure_Y.command);
            pid_pressure_step();
            printf("%.17g\\n", (double)pid_pressure_Y.command);
        }
    ''')
    assert values == pytest.approx([first, second] * 2, rel=2e-6)


@pytest.mark.parametrize("dt,kp,ki,kd,limit,expected", [
    (0.00001, 0, 0, 0.001, 1000, 100),
    (0.001, 1, 0, 0, 0.04, 0.04),
    (0.001, 0.0000123456789, 0, 0, 1, 0.0000123456789),
    (0.001, 0, 0.0000123456789, 0, 1, 0.0000000123456789),
    (0.001, 0, 0, 0.0000123456789, 1, 0.0123456789),
])
def test_pid_parameter_precision(tmp_path, platform, dt, kp, ki, kd, limit, expected):
    model = pid()
    model["model"]["sample_time_s"] = dt
    model["model"]["blocks"][0]["params"].update(
        Kp=kp, Ki=ki, Kd=kd, output_min=-limit, output_max=limit)
    values = execute(tmp_path, model, platform, '''
        for (int sign = -1; sign <= 1; sign += 2) {
            pid_pressure_initialize();
            pid_pressure_U.setpoint = (real_T)sign;
            pid_pressure_step();
            printf("%.17g\\n", (double)pid_pressure_Y.command);
        }
    ''')
    assert values == pytest.approx([-expected, expected], rel=2e-6, abs=1e-15)


@pytest.mark.parametrize("count", [3, 10])
def test_lookup_boundaries_and_small_table_values(tmp_path, platform, count):
    model = parse_model(Path("models/lookup_table_1d.yaml"))
    del model["model"]["state"]
    # Exactly representable small knots, smaller than old four-decimal formatting.
    spacing = 2 ** -17
    table = [i * 0.0000123456789 for i in range(count)]
    model["model"]["blocks"][0]["params"].update(
        breakpoints=[i * spacing for i in range(count)], table_data=table)
    inputs = [-spacing, 0, spacing / 2, spacing, (count - 1) * spacing, count * spacing]
    body = 'temp_sensor_initialize();\n'
    for value in inputs:
        body += f'temp_sensor_U.voltage = {value!r}; temp_sensor_step();\n'
        body += 'printf("%.17g\\n", (double)temp_sensor_Y.temperature);\n'
    values = execute(tmp_path, model, platform, body)
    assert values == pytest.approx([table[0], table[0], table[1] / 2, table[1], table[-1], table[-1]],
                                   rel=2e-6, abs=1e-15)


def test_basis_coefficients_knots_and_offset_precision(tmp_path, platform):
    model = parse_model(Path("models/lung_mnarx.yaml"))
    model["model"]["state"][0]["initial_value"] = 0.00002
    model["model"]["state"][1]["initial_value"] = 2
    basis = model["model"]["blocks"][0]
    basis["params"].update(num_basis_functions=1, coefficients=[0.0000123456789],
                            knots=[0.00001, 0.00003])
    offset = model["model"]["blocks"][2]
    offset["params"]["coefficient"] = 0.0000234567891
    model["model"]["blocks"] = [basis, offset]
    values = execute(tmp_path, model, platform, '''
        mnarx_lung_initialize();
        mnarx_lung_U.volume = 1;
        mnarx_lung_step();
        printf("%.17g\\n", (double)mnarx_lung_Y.Paw);
    ''')
    # Initial pressure is halfway through descending first basis, plus coefficient * P0.
    assert values == pytest.approx([0.5 * 0.0000123456789 + 2 * 0.0000234567891], rel=2e-6)


@pytest.mark.parametrize("value,kind", [
    (float("inf"), "double"), (float("nan"), "float"),
    (1e40, "float"), (1e-50, "float"), (10 ** 400, "double"),
])
def test_unrepresentable_literals_fail(value, kind):
    with pytest.raises(ValueError, match="representable"):
        c_real_literal(value, kind)


@pytest.mark.parametrize("model_path,key,values", [
    ("models/lookup_table_1d.yaml", "breakpoints", [1.0, 1.0 + 1e-9]),
    ("models/lung_mnarx.yaml", "knots", [1.0, 1.0 + 1e-9]),
])
def test_knots_collapsing_in_float_fail(model_path, key, values):
    model = parse_model(Path(model_path))
    model["model"]["blocks"][0]["params"][key] = values
    with pytest.raises(ValueError, match="strictly increasing in float"):
        CodegenEngine(model, parse_platform(Path("platforms/cortex_m4.yaml")),
                      model_path, "platforms/cortex_m4.yaml")
