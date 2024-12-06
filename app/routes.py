# -*- coding: utf-8 -*-
import os
import argparse
from flask import Flask, render_template
from bs4 import BeautifulSoup

app = Flask(__name__)


def scrape_table(file_path):
    try:
        if file_path.startswith("file:///"):
            file_path = file_path.replace("file:///", "", 1)
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        soup = BeautifulSoup(content, 'html.parser')
        first_td = soup.find('b')
        date = None
        if first_td:
            date_text = first_td.text.strip()
            if "Absence Cover Summary for" in date_text:
                date = date_text.split("for")[-1].strip().split("\n")[0]

        table = soup.find('table')
        if not table:
            return None, None, date
        headers = [header.text.strip() for header in table.find_all('tr')[1].find_all('td')]

        # Adjust column order and rename "Room" to "New Rm"
        columns = ["Period", "Class", "Old Rm", "Room", "Absent"]
        indices = {col: headers.index(col) for col in columns if col in headers}
        if "Absent" not in indices:
            return None, None, date

        rows = []
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            cell_values = [cell.text.strip() for cell in cells]
            if (
                    cell_values
                    and cell_values[indices["Absent"]].strip().upper() == "ROOM"
                    and cell_values[indices["Room"]].strip().upper() != "NO COVER REQD"
            ):
                if "Period" in indices:
                    period_index = indices["Period"]
                    if ":" in cell_values[period_index]:
                        cell_values[period_index] = cell_values[period_index].split(":", 1)[-1].strip()

                # Construct the filtered row with swapped columns and renamed header
                filtered_row = [
                    cell_values[indices["Period"]],
                    cell_values[indices["Class"]],
                    cell_values[indices["Old Rm"]],
                    cell_values[indices["Room"]]  # "Room" will later be renamed to "New Rm"
                ]
                rows.append(filtered_row)

        # Return headers with renamed "Room" to "New Rm"
        return ["Period", "Class", "Old Rm", "New Rm"], rows, date
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Generate a static HTML file from an input HTML table.")
    parser.add_argument("input_file", help="Path to the input HTML file")
    parser.add_argument("output_dir", help="Full path to save the generated HTML file, including the file name")
    args = parser.parse_args()

    file_path = args.input_file.strip()
    headers, rows, date = scrape_table(file_path)

    if not rows:
        pages = []
    else:
        chunk_size = 7
        pages = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]

    with app.app_context():
        rendered_html = render_template("index.html", headers=headers, pages=pages, date=date)

    save_directory = os.path.dirname(args.output_dir)  # Extract the directory path
    os.makedirs(save_directory, exist_ok=True)         # Ensure directory exists
    output_file = args.output_dir                      # Full file path to write output

    # Avoid PermissionError by removing existing file
    if os.path.exists(output_file):
        os.remove(output_file)

    with open(output_file, "w", encoding="UTF-8") as f:
        f.write(rendered_html)

    print(f"Static HTML file generated: {output_file}")


if __name__ == "__main__":
    main()
