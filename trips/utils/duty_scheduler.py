from trips.constants.scheduler_constants import (
    CYCLE_LIMIT_HOURS,
    DAY_HOURS,
    DAILY_MAX_DRIVING,
    DAILY_MAX_ON_DUTY,
    OFF_DUTY_HOURS,
    CYCLE_RESET_HOURS,
    FUEL_INTERVAL_MILES,
    AVG_SPEED_MPH,
    FUEL_STOP_HOURS,
    PICKUP_DROP_HOURS,
)


def generate_duty_blocks(
    current_to_pickup_miles, pickup_to_dropoff_miles, current_cycle_used=0
):
    """
    HOS Compliant Duty Block Generator for Property-Carrying Driver
    ASSUMPTIONS:
    - Property-carrying driver, 70hrs/8days, no adverse driving conditions
    - Fueling at least once every 1,000 miles
    - 1 hour for pickup and drop-off

    Returns: (duty_blocks, cycle_used) - maintaining your exact format
    """
    if current_cycle_used > CYCLE_LIMIT_HOURS:
        raise ValueError(
            f"Driver starts in violation: {current_cycle_used}h > {CYCLE_LIMIT_HOURS}h cycle limit"
        )

    duty_blocks = []
    day = 1
    cycle_used = current_cycle_used

    def ensure_cycle_compliance(
        day_on_duty, day_driving, day, cycle_used, activity_hours=0
    ):
        """Check if we need cycle reset before starting an activity."""
        blocks = []

        if cycle_used + activity_hours > CYCLE_LIMIT_HOURS:
            reset_blocks, day_on_duty, day_driving, day, cycle_used = (
                handle_cycle_reset(day_on_duty, day_driving, day, cycle_used)
            )
            blocks.extend(reset_blocks)

        return blocks, day_on_duty, day_driving, day, cycle_used

    def split_block(hours, activity, day_on_duty, day_driving, day, cycle_used):
        """
        Split any block to fit within daily limits: 24h/day, 11h driving, 14h on-duty.
        """
        blocks = []
        remaining_hours = hours

        while remaining_hours > 0:
            reset_blocks, day_on_duty, day_driving, day, cycle_used = (
                ensure_cycle_compliance(
                    day_on_duty, day_driving, day, cycle_used, remaining_hours
                )
            )
            blocks.extend(reset_blocks)

            elapsed_today = day_on_duty + day_driving
            remaining_day_hours = DAY_HOURS - elapsed_today
            allowed_driving_today = DAILY_MAX_DRIVING - day_driving
            allowed_on_duty_today = DAILY_MAX_ON_DUTY - day_on_duty

            max_hours = min(remaining_hours, remaining_day_hours)
            if "driving" in activity:
                max_hours = min(max_hours, allowed_driving_today)
            else:
                max_hours = min(max_hours, allowed_on_duty_today)

            if max_hours <= 0:
                blocks.append(
                    {"day": day, "activity": "off-duty (rest)", "hours": OFF_DUTY_HOURS}
                )
                day_on_duty = 0
                day_driving = 0
                day += 1
                continue

            blocks.append(
                {"day": day, "activity": activity, "hours": round(max_hours, 2)}
            )
            remaining_hours -= max_hours

            if "driving" in activity:
                day_driving += max_hours
                cycle_used += max_hours
            if activity not in ["off-duty (rest)", "sleeper-berth"]:
                day_on_duty += max_hours
                if "driving" not in activity:
                    cycle_used += max_hours

            if day_driving >= DAILY_MAX_DRIVING or day_on_duty >= DAILY_MAX_ON_DUTY:
                blocks.append(
                    {"day": day, "activity": "off-duty (rest)", "hours": OFF_DUTY_HOURS}
                )
                day_on_duty = 0
                day_driving = 0
                day += 1

        return blocks, day_on_duty, day_driving, day, cycle_used

    def handle_cycle_reset(day_on_duty, day_driving, day, cycle_used):
        """Handle 34-hour reset when cycle limit is reached."""
        blocks = []
        remaining_reset = CYCLE_RESET_HOURS

        while remaining_reset > 0:
            reset_hours_today = min(OFF_DUTY_HOURS, remaining_reset)
            blocks.append(
                {"day": day, "activity": "sleeper-berth", "hours": reset_hours_today}
            )
            remaining_reset -= reset_hours_today
            cycle_used = max(0, cycle_used - reset_hours_today)

            if remaining_reset > 0:
                day += 1
                day_on_duty = 0
                day_driving = 0
        return blocks, day_on_duty, day_driving, day, cycle_used

    def calculate_fuel_stops_required(distance):
        """Calculate fuel stops based on 1000-mile interval assumption"""
        if distance <= FUEL_INTERVAL_MILES:
            return 0
        # Fuel every 1000 miles as per assumption
        return int((distance - 1) // FUEL_INTERVAL_MILES)

    def plan_fuel_stops(total_distance, fuel_stops_required):
        """Plan where fuel stops should occur in the journey"""
        if fuel_stops_required == 0:
            return []

        fuel_stop_points = []
        for i in range(1, fuel_stops_required + 1):
            stop_point = i * FUEL_INTERVAL_MILES
            if stop_point < total_distance:
                fuel_stop_points.append(stop_point)

        return fuel_stop_points

    def drive_segment(
        remaining_distance, label, day_on_duty, day_driving, day, cycle_used
    ):
        """Drive between two points with planned fuel stops every 1000 miles"""
        total_segment_distance = remaining_distance
        fuel_stops_required = calculate_fuel_stops_required(total_segment_distance)
        fuel_stop_points = plan_fuel_stops(total_segment_distance, fuel_stops_required)

        distance_driven = 0
        next_fuel_stop_index = 0

        while remaining_distance > 0:
            if next_fuel_stop_index < len(fuel_stop_points):
                next_stop_distance = (
                    fuel_stop_points[next_fuel_stop_index] - distance_driven
                )
                is_fuel_stop = True
            else:
                next_stop_distance = remaining_distance
                is_fuel_stop = False

            segment_distance = min(next_stop_distance, remaining_distance)
            driving_hours = segment_distance / AVG_SPEED_MPH

            reset_blocks, day_on_duty, day_driving, day, cycle_used = (
                ensure_cycle_compliance(
                    day_on_duty, day_driving, day, cycle_used, driving_hours
                )
            )
            duty_blocks.extend(reset_blocks)

            blocks, day_on_duty, day_driving, day, cycle_used = split_block(
                driving_hours,
                f"driving ({label})",
                day_on_duty,
                day_driving,
                day,
                cycle_used,
            )
            duty_blocks.extend(blocks)

            distance_driven += segment_distance
            remaining_distance -= segment_distance

            if (
                is_fuel_stop
                and abs(distance_driven - fuel_stop_points[next_fuel_stop_index]) < 1.0
            ):
                reset_blocks, day_on_duty, day_driving, day, cycle_used = (
                    ensure_cycle_compliance(
                        day_on_duty, day_driving, day, cycle_used, FUEL_STOP_HOURS
                    )
                )
                duty_blocks.extend(reset_blocks)

                blocks, day_on_duty, day_driving, day, cycle_used = split_block(
                    FUEL_STOP_HOURS,
                    "on-duty (fuel)",
                    day_on_duty,
                    day_driving,
                    day,
                    cycle_used,
                )
                duty_blocks.extend(blocks)
                next_fuel_stop_index += 1

        return day_on_duty, day_driving, day, cycle_used

    def add_pickup_dropoff_activity(
        activity_type, day_on_duty, day_driving, day, cycle_used
    ):
        """Add 1-hour pickup or dropoff activity as per assumption"""
        reset_blocks, day_on_duty, day_driving, day, cycle_used = (
            ensure_cycle_compliance(
                day_on_duty, day_driving, day, cycle_used, PICKUP_DROP_HOURS
            )
        )
        duty_blocks.extend(reset_blocks)

        blocks, day_on_duty, day_driving, day, cycle_used = split_block(
            PICKUP_DROP_HOURS,
            f"on-duty ({activity_type})",
            day_on_duty,
            day_driving,
            day,
            cycle_used,
        )
        duty_blocks.extend(blocks)
        return day_on_duty, day_driving, day, cycle_used

    day_on_duty = 0
    day_driving = 0

    if current_to_pickup_miles > 0:
        day_on_duty, day_driving, day, cycle_used = drive_segment(
            current_to_pickup_miles, "empty", day_on_duty, day_driving, day, cycle_used
        )

    day_on_duty, day_driving, day, cycle_used = add_pickup_dropoff_activity(
        "pickup", day_on_duty, day_driving, day, cycle_used
    )

    day_on_duty, day_driving, day, cycle_used = drive_segment(
        pickup_to_dropoff_miles, "loaded", day_on_duty, day_driving, day, cycle_used
    )

    day_on_duty, day_driving, day, cycle_used = add_pickup_dropoff_activity(
        "dropoff", day_on_duty, day_driving, day, cycle_used
    )

    return duty_blocks, cycle_used
