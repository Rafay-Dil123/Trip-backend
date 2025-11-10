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

    def drive_segment(
        remaining_distance, label, day_on_duty, day_driving, day, cycle_used
    ):
        """Drive between two points respecting HOS rules, fuel stops, and cycle reset."""
        while remaining_distance > 0:

            segment_distance = min(FUEL_INTERVAL_MILES, remaining_distance)
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
            remaining_distance -= segment_distance

            if remaining_distance > 0:
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

        return day_on_duty, day_driving, day, cycle_used

    def add_pickup_dropoff_activity(
        activity_type, day_on_duty, day_driving, day, cycle_used
    ):
        """Safely add pickup or dropoff activity with cycle reset check."""
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
