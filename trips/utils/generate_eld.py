from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
from io import BytesIO
import os


def generate_eld_sheet(
    duty_blocks: List[Dict], day_number: int, total_sheets: int, daily_info: Dict = None
) -> Image.Image:
    """
    Generate a professional ELD sheet from duty blocks for a single day with:
    - 24-hour grid (1-hour blocks)
    - Fractional hour filling
    - Half-hour visual guides
    - Color-coded activities
    - Vehicle info & driver signature
    - Activity summary
    - Automatic number scaling for small fractions
    """
    daily_info = daily_info or {}

    width, height = 1500, 1800
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26
        )
        header_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
        )
        normal_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10
        )
    except:
        title_font = header_font = normal_font = small_font = ImageFont.load_default()

    y_pos = 20

    draw.text(
        (50, y_pos), "U.S. DEPARTMENT OF TRANSPORTATION", font=normal_font, fill="black"
    )
    draw.text(
        (450, y_pos),
        "DRIVER'S DAILY LOG\n(ONE CALENDAR DAY — 24 HOURS)",
        font=title_font,
        fill="black",
    )
    draw.text(
        (1000, y_pos),
        "ORIGINAL — Submit to carrier within 13 days\nDUPLICATE — Driver retains possession for eight days",
        font=small_font,
        fill="black",
    )

    y_pos += 60
    date_str = daily_info.get("date", datetime.now().strftime("%m/%d/%Y"))
    month, day, year = date_str.split("/")
    draw.text((50, y_pos), month, font=title_font, fill="black")
    draw.text((150, y_pos), day, font=title_font, fill="black")
    draw.text((250, y_pos), year, font=title_font, fill="black")
    draw.text((50, y_pos + 30), "(MONTH)", font=small_font, fill="black")
    draw.text((150, y_pos + 30), "(DAY)", font=small_font, fill="black")
    draw.text((250, y_pos + 30), "(YEAR)", font=small_font, fill="black")

    total_miles = daily_info.get("total_miles_today", 0)
    draw.text((400, y_pos), str(total_miles), font=title_font, fill="black")
    draw.text(
        (400, y_pos + 30), "(TOTAL MILES DRIVING TODAY)", font=small_font, fill="black"
    )

    vehicle_number = daily_info.get("vehicle_number", "ABC-123")
    draw.text((1000, y_pos + 20), vehicle_number, font=title_font, fill="black")
    draw.text(
        (1000, y_pos + 50),
        "VEHICLE NUMBERS — (SHOW EACH UNIT)",
        font=small_font,
        fill="black",
    )

    y_pos += 90
    carrier_name = daily_info.get("carrier_name", "John Doe's Transportation")
    carrier_address = daily_info.get("home_terminal_address", "Washington, D.C.")
    draw.text((50, y_pos), carrier_name, font=title_font, fill="black")
    draw.text(
        (50, y_pos + 30), "(NAME OF CARRIER OR CARRIERS)", font=small_font, fill="black"
    )
    draw.text((50, y_pos + 60), carrier_address, font=title_font, fill="black")
    draw.text((50, y_pos + 90), "(MAIN OFFICE ADDRESS)", font=small_font, fill="black")

    driver_sig = daily_info.get("driver_signature", "________________")
    co_driver = daily_info.get("co_driver", "________________")
    draw.text((700, y_pos), driver_sig, font=title_font, fill="black")
    draw.text(
        (700, y_pos + 30), "(DRIVER'S SIGNATURE IN FULL)", font=small_font, fill="black"
    )
    draw.text((700, y_pos + 60), co_driver, font=title_font, fill="black")
    draw.text((700, y_pos + 90), "(NAME OF CO-DRIVER)", font=small_font, fill="black")

    y_pos += 100
    draw.text(
        (50, y_pos),
        "24-HOUR STATUS GRID (1-Hour Blocks, Half-Hour Guides, Color-Coded)",
        font=header_font,
        fill="black",
    )
    y_pos += 35

    grid_x_start = 160
    grid_y_start = y_pos
    col_width = 40
    row_height = 35
    hours_per_day = 24

    activity_labels = ["Off Duty", "Sleeper Berth", "Driving", "On Duty (not driving)"]
    activities = ["off_duty", "sleeper_berth", "driving", "on_duty"]

    activity_colors = {
        "off_duty": "#90EE90",
        "sleeper_berth": "#ADD8E6",
        "driving": "#FF6347",
        "on_duty": "#FFD700",
    }

    for row_idx, label in enumerate(activity_labels):
        row_y = grid_y_start + row_idx * row_height
        draw.rectangle(
            [(50, row_y), (grid_x_start - 10, row_y + row_height)],
            outline="black",
            width=1,
        )
        draw.text((55, row_y + 10), label, font=small_font, fill="black")

    for h in range(hours_per_day):
        col_x = grid_x_start + h * col_width
        draw.rectangle(
            [(col_x, grid_y_start - 25), (col_x + col_width, grid_y_start)],
            outline="black",
            width=1,
        )
        draw.text(
            (col_x + 5, grid_y_start - 23), f"{h:02d}:00", font=small_font, fill="black"
        )

    for row_idx in range(len(activity_labels)):
        for h in range(hours_per_day):
            col_x1 = grid_x_start + h * col_width
            col_x2 = col_x1 + col_width
            row_y1 = grid_y_start + row_idx * row_height
            row_y2 = row_y1 + row_height
            draw.rectangle(
                [(col_x1, row_y1), (col_x2, row_y2)], outline="black", width=1
            )
            # Half-hour guide line
            draw.line(
                [(col_x1 + col_width / 2, row_y1), (col_x1 + col_width / 2, row_y2)],
                fill="gray",
                width=1,
            )

    def map_activity_to_status(activity_str):
        activity_lower = activity_str.lower()
        if "off-duty" in activity_lower or "rest" in activity_lower:
            return "off_duty"
        elif "sleeper" in activity_lower:
            return "sleeper_berth"
        elif "driving" in activity_lower:
            return "driving"
        elif (
            "on-duty" in activity_lower
            or "pickup" in activity_lower
            or "dropoff" in activity_lower
            or "fuel" in activity_lower
        ):
            return "on_duty"
        else:
            return "off_duty"  

    current_hour = 0.0
    for block_idx, block in enumerate(duty_blocks, start=1):
        activity_status = map_activity_to_status(block["activity"])
        hours_needed = block["hours"]

        if activity_status not in activities:
            continue

        row_idx = activities.index(activity_status)
        color = activity_colors.get(activity_status, "lightgray")

        while hours_needed > 0 and current_hour < hours_per_day:
            hours_to_fill = min(hours_needed, 1.0 - (current_hour % 1.0))
            if hours_to_fill <= 0:
                hours_to_fill = min(hours_needed, 1.0)

            start_col = int(current_hour)
            start_fraction = current_hour - start_col
            col_x1 = grid_x_start + start_col * col_width + (start_fraction * col_width)
            col_x2 = col_x1 + (hours_to_fill * col_width)

            row_y1 = grid_y_start + row_idx * row_height
            row_y2 = row_y1 + row_height

            draw.rectangle(
                [(col_x1, row_y1), (col_x2, row_y2)],
                fill=color,
                outline="black",
            )

            if (
                hours_to_fill >= 0.25
            ):  
                try:
                    scale_font_size = max(6, int(10 * hours_to_fill))
                    block_font = ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        scale_font_size,
                    )
                except:
                    block_font = small_font

                text = str(block_idx)
                bbox = block_font.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = col_x1 + ((col_x2 - col_x1) - text_width) / 2
                text_y = row_y1 + (row_height - text_height) / 2
                draw.text((text_x, text_y), text, font=block_font, fill="black")

            hours_needed -= hours_to_fill
            current_hour += hours_to_fill

    daily_hours = defaultdict(float)
    for block in duty_blocks:
        activity_status = map_activity_to_status(block["activity"])
        if activity_status in activities:
            daily_hours[activity_status] += block["hours"]

    y_pos = grid_y_start + len(activity_labels) * row_height + 20
    draw.rectangle([(50, y_pos), (1150, y_pos + 100)], outline="black", width=2)
    draw.text((60, y_pos + 5), "ACTIVITY SUMMARY:", font=header_font, fill="black")
    for i, act in enumerate(activities):
        draw.text(
            (60, y_pos + 30 + 25 * i),
            f"{activity_labels[i]}: {daily_hours.get(act, 0):.2f} hrs",
            font=normal_font,
            fill="black",
        )

    y_pos += 120
    draw.rectangle([(50, y_pos), (1450, y_pos + 100)], outline="black", width=2)
    draw.text((60, y_pos + 5), "REMARKS:", font=header_font, fill="black")
    remarks = daily_info.get("remarks", "")
    words = remarks.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if len(test_line) < 100: 
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines[:3]):  
        draw.text((60, y_pos + 30 + 20 * i), line, font=normal_font, fill="black")

    y_pos += 120
    draw.rectangle([(50, y_pos), (1450, y_pos + 80)], outline="black", width=2)
    draw.text((60, y_pos + 5), "SHIPPING DOCUMENTS:", font=header_font, fill="black")
    draw.text(
        (60, y_pos + 30),
        daily_info.get("shipping_docs", ""),
        font=normal_font,
        fill="black",
    )

    draw.text(
        (1400, height - 30),
        f"Page {day_number} of {total_sheets}",
        font=normal_font,
        fill="black",
    )

    return img


def generate_multiple_eld_sheets(
    duty_blocks: List[Dict], daily_info_dict: Dict = None
) -> List[str]:
    """
    Generate all ELD sheets needed for the trip, grouped by day.

    Args:
        duty_blocks: List of all duty blocks for the trip
        daily_info_dict: Optional dict mapping day_number -> info dict (mileage, carrier, etc.)

    Returns:
        List of file paths to generated ELD sheet images
    """

    daily_info_dict = daily_info_dict or {}
    day_blocks = defaultdict(list)
    for block in duty_blocks:
        day_num = int(block["day"])
        day_blocks[day_num].append(block)

    generated_files = []
    total_sheets = len(day_blocks)

    for day_num in sorted(day_blocks.keys()):
        blocks_for_day = day_blocks[day_num]
        info_for_day = daily_info_dict.get(day_num, {})
        sheet_image = generate_eld_sheet(
            blocks_for_day, day_num, total_sheets, info_for_day
        )

        filename = f"ELD_Sheet_Day_{day_num}_of_{total_sheets}.png"
        filepath = os.path.join("/tmp", filename)
        sheet_image.save(filepath)
        generated_files.append(filepath)

    return generated_files


def merge_eld_sheets(sheet_paths: List[str]) -> bytes:
    """
    Merge multiple ELD sheet images into a single PDF and return its binary content.
    """
    if not sheet_paths:
        raise ValueError("No sheet paths provided to merge.")

    images = [Image.open(p).convert("RGB") for p in sheet_paths]

    pdf_buffer = BytesIO()
    images[0].save(pdf_buffer, format="PDF", save_all=True, append_images=images[1:])
    pdf_buffer.seek(0)

    return pdf_buffer.getvalue()
