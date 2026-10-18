"""Generate a five-pin key profile from key_blank.stl.

Install:
    py -m pip install trimesh manifold3d numpy

Place this script beside key_blank.stl and run:
    py key_code_generator_v9.py
"""

from pathlib import Path
import sys

import numpy as np
import trimesh

# ------------------------- FILE SETTINGS -------------------------
INPUT_STL = Path(__file__).with_name("key_blank.stl")
OUTPUT_DIR = Path(__file__).with_name("generated_keys")

# -------------------- MEASURED STL COORDINATES ------------------
TIP_Y_MM = -8.288       # Key tip; Y gets more negative toward the handle
EDITABLE_EDGE_X_MM = 5.919  # Cut starts at this edge and progresses toward -X

# The specified ramp + coded pattern is 50 mm (10 + 40). The measured edge
# continues to Y=-61.287 mm, about 53 mm from the tip. The last ~3 mm continue
# at the fifth pin's level so there is no sudden return to the original edge.
PROFILE_LENGTH_MM = 50.0
EDITABLE_EDGE_END_Y_MM = -61.287
CUT_SPAN_MM = TIP_Y_MM - EDITABLE_EDGE_END_Y_MM  # 52.999 mm toward -Y
LEAD_IN_RAMP_MM = 10.0
CODED_LENGTH_MM = 40.0
# Move the original tip ramp 2.1 mm deeper into the key. This offset applies
# only to the tip's lead-in ramp; all five coded pin levels remain unchanged.
TIP_RAMP_EXTRA_DEPTH_MM = 2.1
# Extend the cutter past the measured tip plane along Y. This is a Boolean
# cleanup allowance only; it does not change the ramp profile on the key.
TIP_CUTTER_OVERSHOOT_MM = 0.5

# -------------------------- PIN LAYOUT --------------------------
PIN_COUNT = 5
PIN_ZONE_DIAMETER_MM = 5.0
PIN_GAP_MM = 2.5
PIN_END_MARGIN_MM = 2.5
PIN_PITCH_MM = PIN_ZONE_DIAMETER_MM + PIN_GAP_MM
FLAT_LENGTH_MM = 3.0
FIRST_PIN_CENTER_FROM_CODE_START_MM = PIN_END_MARGIN_MM + PIN_ZONE_DIAMETER_MM / 2.0

# Pin height + key height = 15.1 mm. Input code is front-to-back; because
# the profile is generated from tip to handle, the input is reversed for placement.
TOTAL_PIN_PLUS_KEY_HEIGHT_MM = 15.1
PIN_HEIGHTS_MM = {
    1: 6.5,
    2: 7.5,
    3: 8.5,
    4: 9.5,
    5: 10.5,
    6: 11.5,
    7: 12.5,
}
MAX_EDITABLE_DEPTH_MM = 8.1

# ----------------------- GEOMETRY HELPERS ------------------------

def y_from_distance(distance_from_tip_mm: float) -> float:
    """Map distance from tip to STL Y; toward the handle means Y decreases."""
    return TIP_Y_MM - distance_from_tip_mm


def make_extruded_cutter(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    far_x: float,
    z0: float,
    z1: float,
) -> trimesh.Trimesh:
    """Closed four-sided prism removing material in the +X direction of edge.

    The inner boundary follows (x1,y1) to (x2,y2); the opposite side extends
    beyond the STL's +X bounds. Therefore the cutter removes material starting
    at the measured X=5.919 edge and extending in the negative-X direction by
    the programmed depth.
    """
    # Keep x/y point associations intact while ordering polygon vertices by Y.
    if y1 > y2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1

    polygon = [(x1, y1), (far_x, y1), (far_x, y2), (x2, y2)]

    area2 = sum(
        polygon[i][0] * polygon[(i + 1) % 4][1]
        - polygon[(i + 1) % 4][0] * polygon[i][1]
        for i in range(4)
    )
    if area2 < 0:
        polygon.reverse()

    vertices = np.array(
        [[x, y, z0] for x, y in polygon]
        + [[x, y, z1] for x, y in polygon],
        dtype=float,
    )
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7)]
    for i in range(4):
        j = (i + 1) % 4
        faces.extend([(i, j, j + 4), (i, j + 4, i + 4)])

    cutter = trimesh.Trimesh(
        vertices=vertices, faces=np.asarray(faces, dtype=np.int64), process=True
    )
    if not cutter.is_volume:
        raise RuntimeError("Internal error: generated cutter is not a valid volume.")
    return cutter


def build_profile_points(cut_depths_mm: list[float]) -> list[tuple[float, float]]:
    """Return the original single-ramp profile, with the tip ramp shifted 2.1 mm deeper."""
    max_depth = max(PIN_HEIGHTS_MM.values()) - min(PIN_HEIGHTS_MM.values())
    tip_depth = max_depth + TIP_RAMP_EXTRA_DEPTH_MM
    lead_end_depth = cut_depths_mm[0] + TIP_RAMP_EXTRA_DEPTH_MM
    points: list[tuple[float, float]] = [
        # The first point lies 0.5 mm beyond the tip plane. Because it has the
        # same depth as the tip point, it extends the cutter without changing
        # the single ramp itself inside the original key blank.
        (-TIP_CUTTER_OVERSHOOT_MM, tip_depth),
        (0.0, tip_depth),
        (LEAD_IN_RAMP_MM, lead_end_depth),
    ]

    for i, depth in enumerate(cut_depths_mm):
        center = (
            LEAD_IN_RAMP_MM
            + FIRST_PIN_CENTER_FROM_CODE_START_MM
            + i * PIN_PITCH_MM
        )
        flat_start = center - FLAT_LENGTH_MM / 2.0
        flat_end = center + FLAT_LENGTH_MM / 2.0

        if flat_start > points[-1][0] + 1e-9:
            points.append((flat_start, depth))
        elif abs(flat_start - points[-1][0]) <= 1e-9:
            points[-1] = (flat_start, depth)
        points.append((flat_end, depth))

    if points[-1][0] < CUT_SPAN_MM:
        points.append((CUT_SPAN_MM, cut_depths_mm[-1]))

    cleaned: list[tuple[float, float]] = []
    for distance, depth in points:
        if cleaned and abs(distance - cleaned[-1][0]) < 1e-9:
            cleaned[-1] = (distance, depth)
        else:
            cleaned.append((distance, depth))
    return cleaned


def main() -> int:
    expected_coded = (
        2 * PIN_END_MARGIN_MM
        + PIN_COUNT * PIN_ZONE_DIAMETER_MM
        + (PIN_COUNT - 1) * PIN_GAP_MM
    )
    if abs(expected_coded - CODED_LENGTH_MM) > 1e-6:
        print(f"Pin layout sums to {expected_coded:.2f} mm, not {CODED_LENGTH_MM:.2f} mm.")
        return 2
    if abs(LEAD_IN_RAMP_MM + CODED_LENGTH_MM - PROFILE_LENGTH_MM) > 1e-6:
        print("Lead-in ramp + coded length must equal the 50 mm coded profile length.")
        return 2
    if CUT_SPAN_MM < PROFILE_LENGTH_MM:
        print("Measured editable edge ends before the required 50 mm profile ends.")
        return 2

    if not INPUT_STL.is_file():
        print(f"Could not find: {INPUT_STL}")
        print("Place key_blank.stl in the same folder as this script, or edit INPUT_STL.")
        return 2

    code = input("Enter the five-digit key code (digits 1-7, front to back): ").strip()
    if len(code) != PIN_COUNT or any(c not in "1234567" for c in code):
        print("Invalid code. Enter exactly five digits, each from 1 through 7, e.g. 13572.")
        return 2

    try:
        mesh = trimesh.load_mesh(INPUT_STL, force="mesh")
    except Exception as exc:
        print(f"Could not read the STL: {exc}")
        return 2

    if mesh.is_empty or not mesh.is_volume:
        print("Input STL is not a non-empty, watertight solid; stopping.")
        print(f"Watertight: {mesh.is_watertight}; valid volume: {mesh.is_volume}")
        return 2

    bounds = mesh.bounds
    min_y, max_y = float(bounds[0, 1]), float(bounds[1, 1])
    min_x, max_x = float(bounds[0, 0]), float(bounds[1, 0])
    min_z, max_z = float(bounds[0, 2]), float(bounds[1, 2])

    # Verify tip and edited edge are within the supplied mesh bounds.
    if not (min_y - 0.05 <= TIP_Y_MM <= max_y + 0.05):
        print(f"Configured tip Y={TIP_Y_MM:.3f} is outside STL bounds {min_y:.3f}..{max_y:.3f}.")
        return 2
    if not (min_x - 0.05 <= EDITABLE_EDGE_X_MM <= max_x + 0.05):
        print(f"Configured editable edge X={EDITABLE_EDGE_X_MM:.3f} is outside STL bounds {min_x:.3f}..{max_x:.3f}.")
        return 2

    # Report the part of the mesh in the intended 10-50 mm blade segment.
    y_start = y_from_distance(LEAD_IN_RAMP_MM)
    y_end = EDITABLE_EDGE_END_Y_MM
    blade_mask = (mesh.vertices[:, 1] <= y_start + 1e-5) & (mesh.vertices[:, 1] >= y_end - 1e-5)
    local = mesh.vertices[blade_mask]
    if len(local):
        local_x_min, local_x_max = float(local[:, 0].min()), float(local[:, 0].max())
        near_edge_count = int(np.count_nonzero(np.abs(local[:, 0] - EDITABLE_EDGE_X_MM) < 0.15))
    else:
        local_x_min = local_x_max = float("nan")
        near_edge_count = 0

    physical_code = code[::-1]  # Place first input digit at the front/handle side.
    key_heights = {
        digit: TOTAL_PIN_PLUS_KEY_HEIGHT_MM - pin_height
        for digit, pin_height in PIN_HEIGHTS_MM.items()
    }
    max_key_height = max(key_heights.values())
    cut_depths = [max_key_height - key_heights[int(c)] for c in physical_code]
    max_cut = max(PIN_HEIGHTS_MM.values()) - min(PIN_HEIGHTS_MM.values())
    if max_cut > MAX_EDITABLE_DEPTH_MM + 1e-9:
        print(f"Maximum cut {max_cut:.2f} mm exceeds editable depth {MAX_EDITABLE_DEPTH_MM:.2f} mm.")
        return 2

    print("\nCoordinate check")
    print(f"  STL X: {min_x:.3f} to {max_x:.3f} mm")
    print(f"  STL Y: {min_y:.3f} to {max_y:.3f} mm")
    print(f"  STL Z: {min_z:.3f} to {max_z:.3f} mm")
    print(f"  Configured tip: (X edge varies, Y={TIP_Y_MM:.3f})")
    print(f"  Editable edge: X={EDITABLE_EDGE_X_MM:.3f}; cuts progress toward -X")
    print(f"  Blade-segment vertex X range: {local_x_min:.3f} to {local_x_max:.3f} mm")
    print(f"  Segment vertices within 0.15 mm of edge X: {near_edge_count}")
    if near_edge_count == 0:
        print("  WARNING: No sampled segment vertices lie close to X=5.919. Verify the edge coordinate.")
    print(f"  Cut Y span: {TIP_Y_MM:.3f} to {y_end:.3f} mm ({CUT_SPAN_MM:.3f} mm)")
    print(f"  Pattern: {LEAD_IN_RAMP_MM:.1f} mm lead-in + {CODED_LENGTH_MM:.1f} mm pin section; final level continues to the measured edge end")
    print(f"  Input code: {code} (front-to-back)")
    print(f"  Physical placement tip-to-handle: {physical_code}")
    print(f"  Tip ramp: original profile shifted {TIP_RAMP_EXTRA_DEPTH_MM:.2f} mm deeper")
    print(f"  Tip cutter overrun: {TIP_CUTTER_OVERSHOOT_MM:.2f} mm beyond the tip plane (cutter only)")
    print("Pin | Placed digit | Pin height | Key height | Cut depth | Distance from tip | STL Y")
    for i, char in enumerate(physical_code):
        digit = int(char)
        center_s = LEAD_IN_RAMP_MM + FIRST_PIN_CENTER_FROM_CODE_START_MM + i * PIN_PITCH_MM
        print(
            f" {i+1}  | {digit:>12} | {PIN_HEIGHTS_MM[digit]:>10.2f} | {key_heights[digit]:>10.2f} | "
            f"{cut_depths[i]:>9.2f} | {center_s:>17.2f} | {y_from_distance(center_s):>8.3f}"
        )

    # The cutters pass fully through Z and extend beyond the +X bounds, while
    # their inner edge follows the designed cut-depth profile.
    far_x = max(max_x, EDITABLE_EDGE_X_MM) + 2.0
    z0 = min_z - 2.0
    z1 = max_z + 2.0
    profile = build_profile_points(cut_depths)
    cutters: list[trimesh.Trimesh] = []
    for (s1, d1), (s2, d2) in zip(profile, profile[1:]):
        # x boundary starts at X=5.919 and moves left (negative X) with depth.
        x1 = EDITABLE_EDGE_X_MM - d1
        x2 = EDITABLE_EDGE_X_MM - d2
        cutters.append(
            make_extruded_cutter(
                x1=x1,
                y1=y_from_distance(s1),
                x2=x2,
                y2=y_from_distance(s2),
                far_x=far_x,
                z0=z0,
                z1=z1,
            )
        )

    try:
        result = trimesh.boolean.difference([mesh, *cutters], engine="manifold", check_volume=True)
    except Exception as exc:
        print(f"\nBoolean cut failed: {exc}")
        print("Confirm manifold3d is installed: py -m pip install manifold3d")
        return 2

    if result is None or result.is_empty or not result.is_volume:
        print("The result did not validate as a solid; no file was exported.")
        return 2

    volume_removed = float(mesh.volume - result.volume)
    pct_removed = (volume_removed / float(mesh.volume) * 100.0) if mesh.volume else 0.0
    if volume_removed <= 1e-5:
        print("WARNING: the Boolean operation removed essentially no volume. Do not print this file.")
    else:
        print(f"\nMaterial removed: {volume_removed:.3f} cubic mm ({pct_removed:.3f}% of original volume)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"key_{code}.stl"
    result.export(output_path)
    print(f"Exported: {output_path}")
    print(f"Output watertight: {result.is_watertight}")
    print(f"Output valid volume: {result.is_volume}")
    print("Inspect the STL in Fusion 360 before printing, especially the single tip ramp.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
