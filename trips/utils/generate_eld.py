from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import Dict, List
from collections import defaultdict


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

    # Page setup
    width, height = 1500, 1800
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Fonts
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

    # --- DOT Form Top Headings ---
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
    # Date boxes
    date_str = daily_info.get("date", datetime.now().strftime("%m/%d/%Y"))
    month, day, year = date_str.split("/")
    draw.text((50, y_pos), month, font=title_font, fill="black")
    draw.text((150, y_pos), day, font=title_font, fill="black")
    draw.text((250, y_pos), year, font=title_font, fill="black")
    draw.text((50, y_pos + 30), "(MONTH)", font=small_font, fill="black")
    draw.text((150, y_pos + 30), "(DAY)", font=small_font, fill="black")
    draw.text((250, y_pos + 30), "(YEAR)", font=small_font, fill="black")

    # Total miles today
    total_miles = daily_info.get("total_miles_today", 0)
    draw.text((400, y_pos), str(total_miles), font=title_font, fill="black")
    draw.text(
        (400, y_pos + 30), "(TOTAL MILES DRIVING TODAY)", font=small_font, fill="black"
    )

    # Vehicle numbers
    vehicle_number = daily_info.get("vehicle_number", "ABC-123")
    draw.text((1000, y_pos + 20), vehicle_number, font=title_font, fill="black")
    draw.text(
        (1000, y_pos + 50),
        "VEHICLE NUMBERS — (SHOW EACH UNIT)",
        font=small_font,
        fill="black",
    )

    y_pos += 90
    # Carrier name and address
    carrier_name = daily_info.get("carrier_name", "John Doe's Transportation")
    carrier_address = daily_info.get("home_terminal_address", "Washington, D.C.")
    draw.text((50, y_pos), carrier_name, font=title_font, fill="black")
    draw.text(
        (50, y_pos + 30), "(NAME OF CARRIER OR CARRIERS)", font=small_font, fill="black"
    )
    draw.text((50, y_pos + 60), carrier_address, font=title_font, fill="black")
    draw.text((50, y_pos + 90), "(MAIN OFFICE ADDRESS)", font=small_font, fill="black")

    # Driver signature and co-driver
    driver_sig = daily_info.get("driver_signature", "John E. Doe")
    co_driver = daily_info.get("co_driver", "________________")
    draw.text((700, y_pos), driver_sig, font=title_font, fill="black")
    draw.text(
        (700, y_pos + 30), "(DRIVER'S SIGNATURE IN FULL)", font=small_font, fill="black"
    )
    draw.text((700, y_pos + 60), co_driver, font=title_font, fill="black")
    draw.text((700, y_pos + 90), "(NAME OF CO-DRIVER)", font=small_font, fill="black")

    # --- 24-Hour Grid ---
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
            (col_x + 5, grid_y_start - 23), f"{h}:00", font=small_font, fill="black"
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
            draw.line(
                [(col_x1 + col_width / 2, row_y1), (col_x1 + col_width / 2, row_y2)],
                fill="gray",
                width=1,
            )

    block_pointer = 0.0
    for idx, block in enumerate(duty_blocks, start=1):
        act = block["activity"].split("(")[0].strip().lower().replace(" ", "_")
        if act not in activities:
            continue
        row_idx = activities.index(act)
        hours_filled = block["hours"]
        color = activity_colors.get(act, "lightgray")

        while hours_filled > 0 and int(block_pointer) < hours_per_day:
            col_x1 = grid_x_start + int(block_pointer) * col_width
            col_x2 = col_x1 + col_width
            row_y1 = grid_y_start + row_idx * row_height
            row_y2 = row_y1 + row_height

            fill_fraction = min(1, hours_filled)
            fill_height = row_height * fill_fraction
            draw.rectangle(
                [(col_x1, row_y2 - fill_height), (col_x2, row_y2)],
                fill=color,
                outline="black",
            )

            # Scale font size for very small fractions
            scale_font_size = max(6, int(small_font.size * fill_fraction))
            try:
                block_font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", scale_font_size
                )
            except:
                block_font = ImageFont.load_default()

            text = str(idx)
            text = str(idx)

            bbox = block_font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = col_x1 + (col_width - text_width) / 2
            text_y = row_y2 - fill_height + (fill_height - text_height) / 2
            draw.text((text_x, text_y), text, font=block_font, fill="black")
            text_x = col_x1 + (col_width - text_width) / 2
            text_y = row_y2 - fill_height + (fill_height - text_height) / 2
            draw.text((text_x, text_y), text, font=block_font, fill="black")

            hours_filled -= fill_fraction
            block_pointer += fill_fraction

    daily_hours = defaultdict(float)
    for block in duty_blocks:
        act = block["activity"].split("(")[0].strip().lower().replace(" ", "_")
        if act in activities:
            daily_hours[act] += block["hours"]

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
    draw.text(
        (60, y_pos + 30), daily_info.get("remarks", ""), font=normal_font, fill="black"
    )

    y_pos += 120
    draw.rectangle([(50, y_pos), (1450, y_pos + 80)], outline="black", width=2)
    draw.text((60, y_pos + 5), "SHIPPING DOCUMENTS:", font=header_font, fill="black")
    draw.text(
        (60, y_pos + 30),
        daily_info.get("shipping_docs", ""),
        font=normal_font,
        fill="black",
    )

    return img


from typing import List, Dict
from collections import defaultdict
from PIL import Image
import os


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
        day_blocks[int(block["day"])].append(block)

    generated_files = []
    total_sheets = len(day_blocks)
    for idx, day_number in enumerate(sorted(day_blocks.keys()), start=1):
        blocks_for_day = day_blocks[day_number]
        info_for_day = daily_info_dict.get(day_number, {})
        sheet_image = generate_eld_sheet(
            blocks_for_day, idx, total_sheets, info_for_day
        )

        filename = f"ELD_Sheet_Day_{day_number}_of_{total_sheets}.png"
        filepath = os.path.join("/tmp", filename)
        sheet_image.save(filepath)
        generated_files.append(filepath)

    return generated_files


def merge_eld_sheets(
    sheet_paths: List[str], output_path: str = "/tmp/complete_eld_log.pdf"
) -> str:
    """
    Merge multiple ELD sheet images into a single PDF.

    Args:
        sheet_paths: List of image file paths
        output_path: Path for the merged PDF

    Returns:
        Path to merged PDF
    """
    if not sheet_paths:
        raise ValueError("No sheet paths provided to merge.")

    images = [Image.open(p).convert("RGB") for p in sheet_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    return output_path
